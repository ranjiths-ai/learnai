import google.generativeai as genai
from config import Config, logger
from jira_service import JiraService
from vector_store import VectorStoreService

class DefectTriageAgent:
    def __init__(self):
        logger.info("Initializing DefectTriageAgent...")
        self.jira = JiraService()
        self.vector_store = VectorStoreService()
        
        # Configure Google Generative AI
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 400  # Token limit on LLM response to prevent rambling
            }
        )
        logger.info("DefectTriageAgent initialized with Gemini model=%s", Config.GEMINI_MODEL)

    def _generate_recommendation(self, new_defect: dict, matches: list[dict]) -> str:
        """Constructs a compressed, token-optimized context prompt."""
        
        # TOKEN SAVER: Include only Summary, Root Cause, and Fix from past matches.
        # Exclude historical descriptions entirely!
        context_lines = []
        for i, match in enumerate(matches, start=1):
            context_lines.append(
                f"{i}. [{match['issue_key']}] {match['summary']}\n"
                f"   - Past Root Cause: {match['root_cause']}\n"
                f"   - Past Fix: {match['fix']}"
            )
            logger.info(
                "Historical fix evidence #%s: issue=%s, fix=%s",
                i,
                match["issue_key"],
                match["fix"],
            )
            print(
                f"[DEBUG] Historical fix evidence #{i}: "
                f"{match['issue_key']} -> {match['fix']}"
            )
        compact_context = "\n".join(context_lines)
        logger.info(
            "Building recommendation prompt: issue=%s, matches=%s, context_length=%s",
            new_defect["issue_key"],
            len(matches),
            len(compact_context),
        )

        # TOKEN SAVER: Truncate current ticket description to 1500 chars to drop stack traces
        truncated_curr_desc = (new_defect['description'][:1500] + "...") if len(new_defect['description']) > 1500 else new_defect['description']

        prompt = f"""
### INPUT DATA:
NEW BUG:
Key: {new_defect['issue_key']}
Summary: {new_defect['summary']}
Description: {truncated_curr_desc}

HISTORICAL REFERENCES:
{compact_context}

### INSTRUCTIONS & CONSTRAINTS:
1. Source of Truth: Base your "Suggested Fix" STRICTLY on the non-empty "Fix Details" / "Resolution" / "Root Cause" fields of the most relevant historical bug(s).
2. Prioritization: 
   - Rank the historical bugs by technical similarity (symptoms, component, error logs, and failure point).
   - Base your recommendation primarily on the highest-matching historical fix.
   - Combine fixes ONLY if multiple bugs share the exact same root failure mechanism.
3. No Hallucinations: Do NOT invent, assume, or generalize a technical fix that is not explicitly backed by the provided historical fix data.
4. Fallback Condition: If the historical bugs have empty, "N/A", or non-actionable fix details, respond ONLY with: "No historical fix available based on provided records."
5. Output Directness: Provide the actual concrete fix. Do not provide meta-commentary, generic advice, or placeholder text.

### OUTPUT FORMAT:
- Reference Ticket(s): [Jira Key(s) of the matching bug(s) used as evidence must be clear full text without truncating data]
- Suggested Fix: [Direct, actionable technical solution extracted from the historical fix data]
- Context/Rationale: [1-2 sentences explaining why this historical fix applies to the new bug]
"""
        logger.info(f"Calling Gemini ({Config.GEMINI_MODEL}) with compressed context...")
        response = self.model.generate_content(prompt)
        logger.info("Gemini response received: response_length=%s", len(response.text or ""))
        print(f"[DEBUG] Gemini recommendation generated: {response.text}")
        return response.text

    def triage_defect(self, issue_key: str):
        logger.info(f"=== Starting Triage for: {issue_key} ===")
        
        # 1. Fetch details from Jira
        new_defect = self.jira.fetch_issue_by_key(issue_key)
        logger.info(
            "New defect loaded: key=%s, summary=%s",
            issue_key,
            new_defect["summary"][:120],
        )
        
        # Truncate search input query to save embedding tokens
        query_text = f"Summary: {new_defect['summary']}\nDescription: {new_defect['description'][:1000]}"
        
        # 2. Similarity search in ChromaDB (Top 3)
        matches = self.vector_store.search_similar_defects(query_text=query_text, n_results=3)
        logger.info(
            "Similarity search complete: count=%s, keys=%s",
            len(matches),
            [match.get("issue_key") for match in matches],
        )
        if not matches:
            logger.warning("No historical defects found to compare against.")
            return {"recommendation": "", "matches": [], "posted": False}
        
        # 3. LLM Recommendation
        recommendation = self._generate_recommendation(new_defect, matches)
        logger.info("--- Recommendation Generated ---")
        print(f"\n{recommendation}\n")
        
        # 4. Write back to Jira
        success = self.jira.add_comment(issue_key=issue_key, comment_body=recommendation)
        if success:
            logger.info(f"Triage successfully posted to Jira issue {issue_key}.")
            print(f"[DEBUG] Recommendation posted to {issue_key}")
        else:
            logger.error(f"Failed to post comment to {issue_key}.")
            print(f"[DEBUG] Recommendation was not posted to {issue_key}")

        return {
            "recommendation": recommendation,
            "matches": matches,
            "posted": success,
        }