import re
import requests
import time
from requests.auth import HTTPBasicAuth
from config import Config, logger

class JiraService:
    def __init__(self):
        self.base_url = Config.JIRA_BASE_URL
        self.auth = HTTPBasicAuth(Config.JIRA_USER_EMAIL, Config.JIRA_API_TOKEN)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        logger.info(
            "JiraService initialized: base_url=%s, project=%s",
            self.base_url,
            Config.JIRA_PROJECT_KEY,
        )

    def _clean_text(self, text: str | dict | list) -> str:
        """Removes Jira markup tags, markdown links, and excess whitespace."""
        if not text:
            return ""
        if isinstance(text, dict):
            text = self._clean_text(text.get("content", text.get("text", "")))
        elif isinstance(text, list):
            text = " ".join(self._clean_text(item) for item in text)
        elif not isinstance(text, str):
            text = str(text)
        # Remove Jira markup macros like {code}, {quote}, etc.
        text = re.sub(r"\{.*?\}", "", text)
        # Remove markdown URLs [text|url]
        text = re.sub(r"\[([^\|\]]+)\|[^\]]+\]", r"\1", text)
        return " ".join(text.split())

    def _extract_field_value(self, value: object, default: str = "N/A") -> str:
        """Normalizes Jira custom-field values across string and object shapes."""
        if value is None:
            return default
        if isinstance(value, dict):
            for key in ("value", "name", "text"):
                if key in value:
                    return self._extract_field_value(value[key], default)
            if "content" in value:
                return self._extract_field_value(value["content"], default)
            return default
        if isinstance(value, list):
            values = [self._extract_field_value(item, "") for item in value]
            return ", ".join(item for item in values if item) or default
        normalized = self._clean_text(value)
        return normalized or default

    def fetch_historical_bugs(self, max_results: int | None = None) -> list[dict]:
        """Pulls all Jira bugs and defects using JQL pagination."""
        jql = (
            f"project = '{Config.JIRA_PROJECT_KEY}' "
            f"AND issuetype in ('Bug', 'Defect') "
            f"ORDER BY created DESC"
        )
        url = f"{self.base_url}/rest/api/3/search/jql"
        start_at = 0
        batch_size = 300
        extracted_bugs = []
        
        logger.info("URL for Jira API: %s", url)
        logger.info(f"Starting historical defect extraction using JQL: {jql}")

        while max_results is None or start_at < max_results:
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": batch_size,
                "fields": [
                    "summary", "description", "issuetype",
                    Config.FIELD_FIX, Config.FIELD_ROOT_CAUSE, Config.FIELD_DEFECT_ID
                ]
            }
            try:
                logger.info(
                    "Jira search request: start_at=%s, batch_size=%s",
                    start_at,
                    batch_size,
                )
                request_started = time.perf_counter()
                response = requests.get(url, headers=self.headers, auth=self.auth, params=params)
                logger.info(
                    "Jira search response: status=%s, elapsed_ms=%.0f",
                    response.status_code,
                    (time.perf_counter() - request_started) * 1000,
                )
                response.raise_for_status()
                data = response.json()
                issues = data.get("issues", [])
                logger.info(
                    "Jira search returned %s issue(s); total=%s",
                    len(issues),
                    data.get("total", "unknown"),
                )

                if not issues:
                    break

                for issue in issues:
                    fields = issue.get("fields", {})
                    field_names = list(fields.keys())
                    logger.info(
                        "Fields received for issue %s: %s",
                        issue["key"],
                        field_names,
                    )
                    print(f"[DEBUG] Fields for {issue['key']}: {field_names}")
                    
                    # Extract values safely
                    summary = self._clean_text(fields.get("summary", ""))
                    desc = self._clean_text(fields.get("description", ""))
                    
                    # Handle raw string or dict for custom fields
                    fix_val = self._extract_field_value(fields.get(Config.FIELD_FIX))
                    rc_val = self._extract_field_value(fields.get(Config.FIELD_ROOT_CAUSE))
                    defect_id = self._extract_field_value(
                        fields.get(Config.FIELD_DEFECT_ID),
                        issue["key"],
                    )

                    raw_custom_fields = {
                        Config.FIELD_FIX: fields.get(Config.FIELD_FIX),
                        Config.FIELD_ROOT_CAUSE: fields.get(Config.FIELD_ROOT_CAUSE),
                        Config.FIELD_DEFECT_ID: fields.get(Config.FIELD_DEFECT_ID),
                    }
                    logger.info(
                        "Raw custom-field data for %s: %s",
                        issue["key"],
                        raw_custom_fields,
                    )
                    print(
                        f"[DEBUG] Raw custom fields for {issue['key']}: "
                        f"{raw_custom_fields}"
                    )

                    logger.info(
                        "Custom fields for %s: fix=%s, root_cause=%s, defect_id=%s",
                        issue["key"],
                        fix_val,
                        rc_val,
                        defect_id,
                    )
                    print(
                        f"[DEBUG] Custom fields for {issue['key']}: "
                        f"fix={fix_val!r}, root_cause={rc_val!r}, defect_id={defect_id!r}"
                    )

                    extracted_bugs.append({
                        "issue_key": issue["key"],
                        "issue_id": str(issue["id"]),
                        "issue_type": fields.get("issuetype", {}).get("name", "Bug"),
                        "summary": summary,
                        "description": desc,
                        "fix": fix_val,
                        "root_cause": rc_val,
                        "defect_id": defect_id
                    })
                    logger.debug(
                        "Extracted issue %s: summary_length=%s, description_length=%s",
                        issue["key"],
                        len(summary),
                        len(desc),
                    )

                logger.info(f"Extracted {len(extracted_bugs)} bugs so far...")
                start_at += len(issues)
                if start_at >= data.get("total", 0) or len(issues) < batch_size:
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Error extracting bugs from Jira: {e}")
                if response is not None:
                    logger.debug(f"Response: {response.text}")
                break

        logger.info(f"Finished. Extracted total {len(extracted_bugs)} records.")
        return extracted_bugs

    def fetch_issue_by_key(self, issue_key: str) -> dict:
        """Fetches details for a single issue to be triaged."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        logger.info(f"Retrieving details for issue: {issue_key}")
        
        request_started = time.perf_counter()
        response = requests.get(url, headers=self.headers, auth=self.auth)
        logger.info(
            "Issue response: key=%s, status=%s, elapsed_ms=%.0f",
            issue_key,
            response.status_code,
            (time.perf_counter() - request_started) * 1000,
        )
        response.raise_for_status()
        
        data = response.json()
        fields = data.get("fields", {})
        logger.info("Issue fields received: key=%s, field_count=%s", issue_key, len(fields))
        summary = self._clean_text(fields.get("summary", ""))
        description = self._clean_text(fields.get("description", ""))
        logger.info(
            "Issue text cleaned: key=%s, summary_length=%s, description_length=%s",
            issue_key,
            len(summary),
            len(description),
        )
        return {
            "issue_key": data["key"],
            "summary": summary,
            "description": description,
        }

    def add_comment(self, issue_key: str, comment_body: str) -> bool:
        """Adds a comment to an existing Jira ticket."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        content = []
        for line in comment_body.splitlines():
            text = line.strip()
            if not text:
                continue
            if text.startswith("h3. "):
                content.append({
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": text[4:]}],
                })
            else:
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                })

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": content or [{"type": "paragraph"}],
            }
        }
        logger.info(
            "Posting triage recommendation: issue=%s, content_nodes=%s, body_length=%s",
            issue_key,
            len(content),
            len(comment_body),
        )
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        logger.info("Comment response: issue=%s, status=%s", issue_key, response.status_code)
        
        if response.status_code == 201:
            logger.info("Comment successfully posted to Jira.")
            return True
        else:
            logger.error(f"Failed to post comment. Status: {response.status_code}, Response: {response.text}")
            return False