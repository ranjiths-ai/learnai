from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
import streamlit as st

from config import Config, logger
from triage_agent import DefectTriageAgent
from vector_store import GeminiEmbeddingFunction


APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = APP_DIR / Config.CHROMA_PERSIST_DIR


st.set_page_config(
    page_title="Jira defect intelligence",
    page_icon=":material/bug_report:",
    layout="wide",
)


def directory_size(path: Path) -> int:
    return sum(
        file_path.stat().st_size
        for file_path in path.rglob("*")
        if file_path.is_file()
    )


def format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024**2:
        return f"{value / 1024:.1f} KB"
    if value < 1024**3:
        return f"{value / 1024**2:.1f} MB"
    return f"{value / 1024**3:.1f} GB"


@st.cache_resource
def get_client(db_path: str):
    return chromadb.PersistentClient(path=db_path)


def collection_names(client: Any) -> list[str]:
    return sorted(
        item.name if hasattr(item, "name") else str(item)
        for item in client.list_collections()
    )


def collection_snapshot(collection: Any) -> dict[str, Any]:
    count = collection.count()
    data = collection.get(include=["documents", "metadatas", "embeddings"])
    embeddings = data.get("embeddings")
    if embeddings is None:
        embeddings = []
    dimension = len(embeddings[0]) if len(embeddings) > 0 else 0
    rows = []
    for record_id, document, metadata in zip(
        data.get("ids", []),
        data.get("documents", []),
        data.get("metadatas", []),
    ):
        rows.append(
            {
                "id": record_id,
                "document": document or "",
                **(metadata or {}),
            }
        )
    return {
        "count": count,
        "dimension": dimension,
        "metadata": collection.metadata or {},
        "rows": rows,
        "ids": data.get("ids", []),
        "embeddings": embeddings,
    }


def run_similarity_search(collection: Any, query: str, top_k: int) -> dict[str, Any]:
    embedding_function = GeminiEmbeddingFunction(
        api_key=Config.GEMINI_API_KEY,
        model_name=Config.GEMINI_EMBEDDING_MODEL,
    )
    query_embedding = embedding_function([query])
    return collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )


st.title("Jira defect intelligence")
st.caption(
    "Inspect Gemini-backed Chroma data, test retrieval, and post a targeted fix recommendation to Jira."
)

with st.sidebar:
    st.header("Data source")
    db_path_text = st.text_input("Chroma data directory", value=str(DEFAULT_DB_PATH))
    refresh = st.button("Refresh database", icon=":material/refresh:")
    st.divider()
    st.caption(f"Jira project: `{Config.JIRA_PROJECT_KEY}`")
    st.caption(f"Embedding model: `{Config.GEMINI_EMBEDDING_MODEL}`")

if refresh:
    get_client.clear()

DB_PATH = Path(db_path_text).expanduser()
if not DB_PATH.exists():
    st.error(f"Chroma data directory does not exist: `{DB_PATH}`")
    st.stop()

client = get_client(str(DB_PATH))
names = collection_names(client)
if not names:
    st.warning("The Chroma database has no collections yet. Run `python main.py --index` first.")
    st.stop()

selected_name = st.selectbox("Collection", names, index=names.index(Config.CHROMA_COLLECTION_NAME) if Config.CHROMA_COLLECTION_NAME in names else 0)
collection = client.get_collection(selected_name)
snapshot = collection_snapshot(collection)

with st.container(horizontal=True):
    st.metric("Database size", format_bytes(directory_size(DB_PATH)), border=True)
    st.metric("Collections", len(names), border=True)
    st.metric("Records", snapshot["count"], border=True)
    st.metric("Vector dimensions", snapshot["dimension"] or "-", border=True)

with st.container(border=True):
    st.subheader("Collection details")
    st.json({
        "name": selected_name,
        "metadata": snapshot["metadata"],
        "embedding_model": Config.GEMINI_EMBEDDING_MODEL,
        "database_path": str(DB_PATH),
    })

if snapshot["count"]:
    st.subheader("Stored documents")
    st.dataframe(snapshot["rows"], hide_index=True, height=360)

    with st.expander("Embedding preview"):
        ids = snapshot["ids"]
        selected_id = st.selectbox("Record", ids, key=f"embedding_record_{selected_name}")
        vector = snapshot["embeddings"][ids.index(selected_id)]
        st.caption(f"Showing the first 20 values of {len(vector)} dimensions for `{selected_id}`.")
        st.code(str(list(vector[:20])))
else:
    st.info("This collection is empty.")

st.subheader("Similarity search")
with st.form("similarity_search", border=True):
    query = st.text_area("Search request", placeholder="Describe a defect or failure mode...")
    top_k = st.number_input("Results", min_value=1, max_value=10, value=3)
    search_submitted = st.form_submit_button("Search collection", type="primary", icon=":material/search:")

if search_submitted:
    if not query.strip():
        st.warning("Enter a search request first.")
    elif selected_name != Config.CHROMA_COLLECTION_NAME:
        st.warning(
            "Similarity search is enabled for the Gemini collection only. "
            "Select the configured Gemini collection to avoid legacy embedding providers."
        )
    else:
        with st.spinner("Generating a Gemini embedding and querying Chroma..."):
            search_results = run_similarity_search(collection, query.strip(), int(top_k))
        st.write("Request")
        st.code(query.strip())
        result_rows = []
        for rank, (record_id, document, metadata, distance) in enumerate(
            zip(
                search_results.get("ids", [[]])[0],
                search_results.get("documents", [[]])[0],
                search_results.get("metadatas", [[]])[0],
                search_results.get("distances", [[]])[0],
            ),
            start=1,
        ):
            result_rows.append(
                {
                    "rank": rank,
                    "issue_key": record_id,
                    "distance": round(distance, 4),
                    "similarity": round(max(0.0, 1.0 - distance), 4),
                    "summary": (metadata or {}).get("summary", ""),
                    "root_cause": (metadata or {}).get("root_cause", ""),
                    "fix": (metadata or {}).get("fix", ""),
                    "document": document or "",
                }
            )
        st.write("Response")
        st.dataframe(result_rows, hide_index=True)

st.subheader("Automated Jira update")
st.caption("Use historical Fix fields to generate a Gemini recommendation and post it as a Jira comment.")
with st.form("jira_recommendation", border=True):
    issue_key = st.text_input("New Jira issue key", placeholder=f"{Config.JIRA_PROJECT_KEY}-99")
    recommend_submitted = st.form_submit_button(
        "Recommend a targeted Fix",
        type="primary",
        icon=":material/auto_awesome:",
    )

if recommend_submitted:
    normalized_key = issue_key.strip().upper()
    expected_prefix = f"{Config.JIRA_PROJECT_KEY}-"
    if not normalized_key.startswith(expected_prefix):
        st.error(f"Use an issue key from the `{Config.JIRA_PROJECT_KEY}` project, such as `{Config.JIRA_PROJECT_KEY}-99`.")
    else:
        with st.spinner(f"Fetching {normalized_key}, retrieving similar defects, and posting the recommendation..."):
            try:
                result = DefectTriageAgent().triage_defect(normalized_key)
            except Exception as error:
                logger.exception("Dashboard triage failed for %s", normalized_key)
                st.error(f"Triage failed: {error}")
            else:
                if result["recommendation"]:
                    st.markdown("#### Recommendation")
                    st.code(result["recommendation"])
                if result["posted"]:
                    st.success(f"Recommendation posted to Jira issue {normalized_key}.")
                else:
                    st.warning("No Jira comment was posted because no historical matches were available or the request failed.")
                if result["matches"]:
                    st.write("Historical references and Fix evidence")
                    st.dataframe(
                        [
                            {
                                "issue_key": match.get("issue_key"),
                                "summary": match.get("summary"),
                                "root_cause": match.get("root_cause"),
                                "fix": match.get("fix"),
                            }
                            for match in result["matches"]
                        ],
                        hide_index=True,
                    )
