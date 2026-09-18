import chromadb
import google.generativeai as genai
import json
from config import Config, logger

class GeminiEmbeddingFunction:
    def __init__(self, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        logger.info("Gemini embedding function configured: model=%s", model_name)

    def name(self) -> str:
        return "default"

    def __call__(self, input: list[str]) -> list[list[float]]:
        logger.info("Embedding document batch: count=%s", len(input))
        response = genai.embed_content(
            model=self.model_name,
            content=input
        )
        embeddings = response["embedding"]
        normalized = embeddings if input and isinstance(embeddings[0], list) else [embeddings]
        logger.info(
            "Document embeddings received: count=%s, dimensions=%s",
            len(normalized),
            len(normalized[0]) if normalized else 0,
        )
        return normalized

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)


class VectorStoreService:
    def __init__(self):
        logger.info(
            "Initializing VectorStoreService: path=%s, collection=%s",
            Config.CHROMA_PERSIST_DIR,
            Config.CHROMA_COLLECTION_NAME,
        )
        self.client = chromadb.PersistentClient(path=Config.CHROMA_PERSIST_DIR)
        
        self.embedding_fn = GeminiEmbeddingFunction(
            api_key=Config.GEMINI_API_KEY,
            model_name=Config.GEMINI_EMBEDDING_MODEL
        )
        
        self.collection = self.client.get_or_create_collection(
            name=Config.CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )
        logger.info(
            "Connected to ChromaDB collection: name=%s, existing_count=%s",
            Config.CHROMA_COLLECTION_NAME,
            self.collection.count(),
        )

    def ingest_defects(self, defects: list[dict]):
        if not defects:
            logger.warning("No defects supplied for ingestion.")
            return

        logger.info("Preparing %s defect(s) for Chroma ingestion", len(defects))
        documents = []
        metadatas = []
        ids = []

        for defect in defects:
            # Token Saving: Truncate large descriptions to max 1200 characters before embedding
            truncated_desc = (defect["description"][:1200] + "...") if len(defect["description"]) > 1200 else defect["description"]
            
            document_content = f"Summary: {defect['summary']}\nDescription: {truncated_desc}"
            
            # Store summary in metadata so the LLM doesn't need to parse raw documents later
            metadata = {
                "issue_key": defect["issue_key"],
                "summary": defect["summary"][:250],
                "root_cause": defect["root_cause"][:500],
                "fix": defect["fix"][:500],
                "defect_id": defect["defect_id"],
                "issue_type": defect["issue_type"]
            }

            documents.append(document_content)
            metadatas.append(metadata)
            ids.append(defect["issue_key"])

        BATCH_SIZE = 50
        for i in range(0, len(ids), BATCH_SIZE):
            end_idx = i + BATCH_SIZE
            self.collection.upsert(
                ids=ids[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
            logger.info(f"Upserted batch [{i} to {min(end_idx, len(ids))}] into ChromaDB.")
        logger.info("Chroma ingestion complete: collection_count=%s", self.collection.count())

    def ingest_defects_from_json(self, dump_path: str) -> None:
        logger.info("Loading defects for embedding from JSON dump: %s", dump_path)
        with open(dump_path, "r", encoding="utf-8") as dump_file:
            defects = json.load(dump_file)
        if not isinstance(defects, list):
            raise ValueError("Defect dump must contain a JSON array of defect records.")
        logger.info("Loaded %s defect(s) from JSON dump", len(defects))
        self.ingest_defects(defects)

    def sync_defects_from_json(self, dump_path: str) -> None:
        """Make Chroma match defect_dump.json using issue_key as the ID."""
        with open(dump_path, "r", encoding="utf-8") as dump_file:
            defects = json.load(dump_file)
        if not isinstance(defects, list):
            raise ValueError("Defect dump must contain a JSON array of defect records.")

        # Build the latest JSON ID set and compare it with the vector DB IDs.
        latest_ids = {defect["issue_key"] for defect in defects}
        current_ids = set(self.collection.get(include=["metadatas"])["ids"])
        ids_to_delete = sorted(current_ids - latest_ids)
        update_count = len(current_ids & latest_ids)
        insert_count = len(latest_ids - current_ids)

        # Remove records that Jira no longer returned.
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            logger.info("Deleted %s stale defect(s): %s", len(ids_to_delete), ids_to_delete)
            print(f"[DEBUG] Deleted stale defects: {ids_to_delete}")

        # upsert updates existing IDs and inserts new IDs in one operation.
        self.ingest_defects(defects)
        logger.info(
            "Defect sync complete: updated=%s, inserted=%s, deleted=%s, total=%s",
            update_count,
            insert_count,
            len(ids_to_delete),
            self.collection.count(),
        )
        print(
            f"[DEBUG] Defect sync complete: updated={update_count}, "
            f"inserted={insert_count}, deleted={len(ids_to_delete)}, "
            f"total={self.collection.count()}"
        )

    def search_similar_defects(self, query_text: str, n_results: int = 3) -> list[dict]:
        logger.info(
            "Querying ChromaDB: requested_results=%s, query_length=%s",
            n_results,
            len(query_text),
        )
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        formatted_matches = []
        if not results or not results["documents"]:
            logger.warning("Chroma query returned no documents")
            return formatted_matches

        for i in range(len(results["documents"][0])):
            formatted_matches.append({
                "issue_key": results["metadatas"][0][i].get("issue_key"),
                "summary": results["metadatas"][0][i].get("summary"),
                "root_cause": results["metadatas"][0][i].get("root_cause"),
                "fix": results["metadatas"][0][i].get("fix"),
            })
            
        logger.info(f"Retrieved {len(formatted_matches)} matching defect(s).")
        return formatted_matches