import json
import sys
from pathlib import Path
from config import Config, logger

def run_historical_indexing():
    """Extracts historical bugs and persists them into ChromaDB."""
    from jira_service import JiraService
    from vector_store import VectorStoreService

    logger.info("Running Historical Data Indexing Workflow...")
    print("[DEBUG] Starting historical indexing")
    jira = JiraService()
    # 1. Extract from Jira
    bugs = jira.fetch_historical_bugs()
    print(f"[DEBUG] Jira extraction complete: {len(bugs)} defect(s)")

    # 2. Persist the normalized Jira records as the embedding source
    dump_path = Path(Config.DEFECT_DUMP_PATH)
    with dump_path.open("w", encoding="utf-8") as dump_file:
        json.dump(bugs, dump_file, indent=2, ensure_ascii=False)
    logger.info("Wrote %s defect(s) to JSON dump: %s", len(bugs), dump_path)
    print(f"[DEBUG] Defect dump written: {dump_path}")

    # 3. Embed the JSON dump into ChromaDB
    vector_store = VectorStoreService()
    vector_store.sync_defects_from_json(str(dump_path))
    logger.info("Historical data extracted, dumped, and synchronized successfully.")
    print("[DEBUG] Historical indexing and vector sync complete")

def run_triage(issue_key: str):
    """Runs the triage agent on a specific issue key."""
    expected_prefix = f"{Config.JIRA_PROJECT_KEY}-"
    if not issue_key.startswith(expected_prefix):
        logger.error(
            "Issue key '%s' does not belong to configured Jira project '%s'. "
            "Use an issue key such as '%s-5432'.",
            issue_key,
            Config.JIRA_PROJECT_KEY,
            Config.JIRA_PROJECT_KEY,
        )
        return
    from triage_agent import DefectTriageAgent

    print(f"[DEBUG] Starting triage for {issue_key}")
    agent = DefectTriageAgent()
    result = agent.triage_defect(issue_key=issue_key)
    print(
        f"[DEBUG] Triage complete for {issue_key}: "
        f"historical_matches={len(result['matches'])}, posted={result['posted']}"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("1. To populate Vector Store:  python main.py --index")
        print("2. To triage a new defect:   python main.py --triage <JIRA_KEY>")
        print("\nExample: python main.py --triage PROJ-102")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "--index":
        run_historical_indexing()
    elif mode == "--triage":
        if len(sys.argv) < 3:
            logger.error("Please specify a Jira Issue Key! E.g. python main.py --triage PROJ-1234")
            sys.exit(1)
        target_key = sys.argv[2].strip().upper()
        run_triage(target_key)
    else:
        logger.error(f"Unknown command: {mode}")