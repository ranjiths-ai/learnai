"""
chroma_dashboard.py
--------------------
A lightweight Streamlit dashboard for inspecting ChromaDB, since Chroma
ships with no built-in visual console (unlike MySQL Workbench or an
Oracle console). Run this any time you want to see what actually got
ingested, without writing one-off inspection scripts.

For every collection in the database it shows:
  - record count, embedding dimension, and db size on disk
  - a table of every stored document + its metadata
  - the raw embedding vector for any record you select
  - a built-in hybrid search box (keyword filter + similarity search)
    so you can test queries directly from the UI

Usage:
    streamlit run chroma_dashboard.py
"""

import os

import chromadb
import streamlit as st

DEFAULT_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")


def get_dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total


st.set_page_config(page_title="ChromaDB Dashboard", layout="wide")
st.title("📊 ChromaDB Inspection Dashboard")
st.caption("A stand-in for the management console ChromaDB doesn't ship with.")

# --- sidebar: connection settings ---
st.sidebar.header("Connection")
db_dir = st.sidebar.text_input("ChromaDB directory", value=DEFAULT_DB_DIR)

if not os.path.exists(db_dir):
    st.warning(f"No database found at `{db_dir}` yet. Run `ingest_to_chroma.py` first.")
    st.stop()

client = chromadb.PersistentClient(path=db_dir)
collections = client.list_collections()

if not collections:
    st.warning("Database exists but has no collections yet. Run `ingest_to_chroma.py` first.")
    st.stop()

st.sidebar.metric("Total DB size on disk", f"{get_dir_size(db_dir) / 1024:.1f} KB")
st.sidebar.metric("Collections found", len(collections))

# --- one section per collection ---
for col_info in collections:
    collection = client.get_collection(col_info.name)
    count = collection.count()

    with st.expander(f"📁 Collection: **{col_info.name}**  —  {count} record(s)", expanded=True):
        if count == 0:
            st.info("This collection is empty.")
            continue

        data = collection.get(include=["documents", "metadatas", "embeddings"])
        dim = len(data["embeddings"][0]) if data["embeddings"] is not None and len(data["embeddings"]) else "-"

        c1, c2, c3 = st.columns(3)
        c1.metric("Records", count)
        c2.metric("Embedding dimension", dim)
        c3.metric("Metadata fields", len(data["metadatas"][0]) if data["metadatas"] else 0)

        st.subheader("Stored documents")
        rows = []
        for id_, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
            row = {"id": id_, "document": doc}
            row.update(meta or {})
            rows.append(row)
        st.dataframe(rows, use_container_width=True)

        st.subheader("Inspect a single embedding vector")
        selected_id = st.selectbox(
            "Choose a record", data["ids"], key=f"select_{col_info.name}"
        )
        idx = data["ids"].index(selected_id)
        vector = data["embeddings"][idx]
        st.caption(f"First 20 of {len(vector)} dimensions for `{selected_id}`:")
        st.code(str(list(vector[:20])))

        st.subheader("🔎 Try a hybrid search")
        search_col1, search_col2, search_col3 = st.columns([2, 1, 1])
        query_text = search_col1.text_input("Query text", key=f"query_{col_info.name}")

        categories = sorted({m.get("category") for m in data["metadatas"] if m.get("category")})
        category_filter = search_col2.selectbox(
            "Category filter (optional)", ["(none)"] + categories, key=f"cat_{col_info.name}"
        )
        top_k = search_col3.number_input("Top-K", min_value=1, max_value=10, value=3, key=f"topk_{col_info.name}")

        if st.button("Search", key=f"btn_{col_info.name}") and query_text:
            where_clause = None if category_filter == "(none)" else {"category": category_filter}
            with st.spinner("Running keyword filter + similarity search..."):
                results = collection.query(
                    query_texts=[query_text],
                    n_results=top_k,
                    where=where_clause,
                    include=["documents", "metadatas", "distances"],
                )
            st.write(f"Filter applied: `{where_clause}`")
            for rank, (id_, doc, meta, dist) in enumerate(
                zip(results["ids"][0], results["documents"][0], results["metadatas"][0], results["distances"][0]),
                start=1,
            ):
                similarity = max(0.0, 1.0 - dist)
                st.markdown(f"**#{rank} — `{id_}`  (similarity: {similarity:.3f})**")
                st.write(f"*{meta}*")
                st.write(doc)
                st.divider()
