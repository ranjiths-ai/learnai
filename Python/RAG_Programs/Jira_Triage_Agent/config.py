import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("JiraTriage")

class Config:
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

    FIELD_FIX = os.getenv("FIELD_FIX", "customfield_10122")
    FIELD_ROOT_CAUSE = os.getenv("FIELD_ROOT_CAUSE", "customfield_10123")
    FIELD_DEFECT_ID = os.getenv("FIELD_DEFECT_ID", "customfield_10121")

    # Google Gemini Credentials
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "jira_defects_gemini")
    DEFECT_DUMP_PATH = os.getenv("DEFECT_DUMP_PATH", "defect_dump.json")

    @classmethod
    def validate(cls):
        required_vars = [
            "JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN", 
            "JIRA_PROJECT_KEY", "GEMINI_API_KEY"
        ]
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        logger.info("Configuration successfully validated.")

Config.validate()