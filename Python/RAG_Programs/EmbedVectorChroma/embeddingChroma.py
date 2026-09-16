from pathlib import Path
from typing import Any

import chromadb
import streamlit as st
from sentence_transformers import SentenceTransformer


WORDS = [
	"hospital",
	"doctor",
	"nurse",
	"patient",
	"emergency room",
	"operating room",
	"intensive care unit",
	"outpatient clinic",
	"inpatient ward",
	"medical record",
	"diagnosis",
	"treatment",
	"prescription",
	"pharmacy",
	"laboratory",
	"radiology",
	"X-ray",
	"health center",
	"blood test",
	"surgery",
	"ambulance",
	"appointment",
	"healthcare",
	"medical equipment",
	"discharge",
]

DATABASE_PATH = Path(__file__).with_name("chroma_db")
COLLECTION_NAME = "hospital_terms"
MODEL_NAME = "all-MiniLM-L6-v2"


def format_bytes(size: int) -> str:
	units = ("B", "KB", "MB", "GB")
	value = float(size)
	for unit in units:
		if value < 1024 or unit == units[-1]:
			return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
		value /= 1024
	return f"{value:.1f} GB"


def database_size() -> int:
	return sum(path.stat().st_size for path in DATABASE_PATH.rglob("*") if path.is_file())


@st.cache_resource(show_spinner=False)
def load_model() -> SentenceTransformer:
	return SentenceTransformer(MODEL_NAME)


@st.cache_resource(show_spinner=False)
def load_client() -> chromadb.PersistentClient:
	return chromadb.PersistentClient(path=str(DATABASE_PATH))


def get_collection_stats(collection: chromadb.Collection) -> dict[str, Any]:
	count = collection.count()
	peek = collection.peek(limit=1) if count else {"ids": [], "embeddings": [], "documents": []}
	embeddings = peek.get("embeddings")
	documents = peek.get("documents") or []
	return {
		"name": collection.name,
		"count": count,
		"embedding_dimensions": len(embeddings[0]) if embeddings is not None and len(embeddings) else 0,
		"sample_id": peek["ids"][0] if peek.get("ids") else "",
		"sample_document": documents[0] if documents else "",
		"metadata": collection.metadata or {},
	}


def inspect_database(client: chromadb.PersistentClient) -> dict[str, Any]:
	collections = client.list_collections()
	collection_stats = [get_collection_stats(collection) for collection in collections]
	total_records = sum(item["count"] for item in collection_stats)
	vector_dimensions = sorted(
		{item["embedding_dimensions"] for item in collection_stats if item["embedding_dimensions"]}
	)
	return {
		"path": str(DATABASE_PATH),
		"size": database_size(),
		"collections": collection_stats,
		"total_collections": len(collection_stats),
		"total_records": total_records,
		"vector_dimensions": vector_dimensions,
	}


def print_database_stats(collection: chromadb.Collection) -> None:
	"""Print the collection size and a small sample of stored records."""
	count = collection.count()
	sample = collection.peek(limit=min(3, count)) if count else {"ids": []}
	print(f"[DEBUG] Database stats: {count} embedding(s) stored")
	print(f"[DEBUG] Stored IDs sample: {sample['ids']}")


def store_embeddings(collection: chromadb.Collection, model: SentenceTransformer) -> None:
	ids = [f"term-{index}" for index in range(len(WORDS))]
	print(f"[DEBUG] Seed data prepared: {len(WORDS)} hospital terms")
	print(f"[DEBUG] Checking existing IDs in collection: {ids}")
	stored = collection.get(ids=ids, include=[])["ids"]
	print(f"[DEBUG] Existing matching IDs returned by ChromaDB: {stored}")
	new_items = [
		(word_id, word)
		for word_id, word in zip(ids, WORDS)
		if word_id not in stored
	]
	print(f"[DEBUG] New items to store: {len(new_items)}")

	if not new_items:
		print("[DEBUG] No new data to store.")
		print_database_stats(collection)
		return

	words_to_embed = [word for _, word in new_items]
	print(f"[DEBUG] Embedding input text: {words_to_embed}")
	print(f"[DEBUG] Generating {len(words_to_embed)} new embedding(s)...")
	embeddings = model.encode(words_to_embed).tolist()
	print(
		f"[DEBUG] Embedding output: {len(embeddings)} vectors, "
		f"{len(embeddings[0])} dimensions each"
	)
	for (word_id, word), embedding in zip(new_items, embeddings):
		print(
			f"[DEBUG] ChromaDB add request: id={word_id!r}, "
			f"document={word!r}, embedding_preview={embedding[:5]}"
		)
		collection.add(
			ids=[word_id],
			documents=[word],
			embeddings=[embedding],
		)
		print(f"[DEBUG] ChromaDB add completed: '{word}' ({word_id})")
		print_database_stats(collection)


def get_collection_records(collection: chromadb.Collection) -> list[dict[str, Any]]:
	result = collection.get(include=["documents", "embeddings", "metadatas"])
	records = []
	for index, record_id in enumerate(result["ids"]):
		embeddings = result.get("embeddings")
		vector = embeddings[index] if embeddings is not None else []
		records.append(
			{
				"id": record_id,
				"document": result["documents"][index] if result.get("documents") else "",
				"metadata": result["metadatas"][index] if result.get("metadatas") else {},
				"vector_dimensions": len(vector),
				"vector_preview": [round(float(value), 6) for value in vector[:5]],
			}
		)
	return records


def run_search(collection: chromadb.Collection, model: SentenceTransformer, user_text: str) -> None:
	query_embedding = model.encode([user_text])[0].tolist()
	request = {
		"collection": collection.name,
		"query_text": user_text,
		"query_embedding_dimensions": len(query_embedding),
		"requested_results": 3,
	}
	st.subheader("ChromaDB request")
	st.json(request)

	results = collection.query(query_embeddings=[query_embedding], n_results=3)
	response = {
		"ids": results["ids"][0],
		"documents": results["documents"][0],
		"distances": results["distances"][0],
	}
	st.subheader("ChromaDB response")
	st.json(response)

	st.subheader("Nearest records")
	st.dataframe(
		[
			{"id": record_id, "document": document, "distance": distance}
			for record_id, document, distance in zip(
				response["ids"], response["documents"], response["distances"]
			)
		],
		hide_index=True,
		width="stretch",
	)


def render_dashboard() -> None:
	st.set_page_config(
		page_title="ChromaDB inspector",
		page_icon=":material/storage:",
		layout="wide",
	)
	st.title("ChromaDB inspector")
	st.caption("Persistent vector database dashboard for the hospital embedding collection")

	client = load_client()
	with st.sidebar:
		st.header("Controls")
		if st.button("Refresh database stats", icon=":material/refresh:", width="stretch"):
			st.rerun()
		st.divider()
		st.caption(f"Database path: {DATABASE_PATH}")
		st.caption(f"Embedding model: {MODEL_NAME}")

	collection = client.get_or_create_collection(name=COLLECTION_NAME)
	with st.status("Inspecting ChromaDB", expanded=False) as status:
		info = inspect_database(client)
		status.update(label="Database inspection complete", state="complete")

	st.subheader("Database summary")
	metric_columns = st.columns(4)
	with metric_columns[0]:
		st.metric("Database size", format_bytes(info["size"]), border=True)
	with metric_columns[1]:
		st.metric("Total collections", info["total_collections"], border=True)
	with metric_columns[2]:
		st.metric("Total records", info["total_records"], border=True)
	with metric_columns[3]:
		st.metric(
			"Vector dimensions",
			", ".join(str(value) for value in info["vector_dimensions"]) or "Not available",
			border=True,
		)

	st.caption(f"Persistent location: {info['path']}")

	st.subheader("Collections")
	collection_rows = [
		{
			"collection": item["name"],
			"records": item["count"],
			"embedding dimensions": item["embedding_dimensions"],
			"sample ID": item["sample_id"],
			"sample document": item["sample_document"],
			"metadata": item["metadata"],
		}
		for item in info["collections"]
	]
	st.dataframe(collection_rows, hide_index=True, width="stretch")

	st.subheader("Collection details")
	collection_names = [item["name"] for item in info["collections"]]
	selected_collection_name = st.selectbox("Inspect collection", collection_names)
	selected_collection = client.get_collection(selected_collection_name)
	selected_stats = get_collection_stats(selected_collection)
	detail_columns = st.columns(3)
	with detail_columns[0]:
		st.metric("Selected records", selected_stats["count"], border=True)
	with detail_columns[1]:
		st.metric("Embedding dimensions", selected_stats["embedding_dimensions"], border=True)
	with detail_columns[2]:
		st.metric("Metadata fields", len(selected_stats["metadata"]), border=True)
	st.json(
		{
			"collection": selected_stats["name"],
			"metadata": selected_stats["metadata"],
			"sample_id": selected_stats["sample_id"],
			"sample_document": selected_stats["sample_document"],
		}
	)
	st.dataframe(get_collection_records(selected_collection), hide_index=True, width="stretch")

	st.subheader("Semantic search")
	with st.form("search_form"):
		query_text = st.text_input("Search hospital terms", placeholder="Try: operation or patient")
		search_submitted = st.form_submit_button("Search ChromaDB", type="primary")
	if search_submitted:
		if not query_text.strip():
			st.warning("Enter a search query before submitting.")
		else:
			with st.spinner("Loading the embedding model and querying ChromaDB..."):
				run_search(selected_collection, load_model(), query_text.strip())

	with st.expander("Seed data actions"):
		st.write(f"Hospital seed terms configured: {len(WORDS)}")
		if st.button("Sync hospital seed embeddings", icon=":material/sync:"):
			with st.spinner("Generating and storing missing embeddings..."):
				store_embeddings(collection, load_model())
			st.success("Seed synchronization completed. Refresh the inspector to see updated stats.")


if __name__ == "__main__":
	render_dashboard()