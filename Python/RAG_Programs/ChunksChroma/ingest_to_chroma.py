"""
ingest_to_chroma.py
--------------------
Step-by-step ChromaDB ingestion pipeline.

This mirrors the algorithm from the session:
  1. Read each chunk (one JSON object per chunk) from the source file.
  2. Convert / validate each chunk into a clean JSON object: {id, text, metadata}.
  3. Print each JSON object to the console BEFORE it goes anywhere (a checkpoint).
  4. Create the collection if it doesn't exist yet, or reuse it if it does.
  5. Embed + store every chunk's text, metadata and embedding into ChromaDB.
  6. Print collection stats (record count, embedding dimension, db size) after insert.

Every step prints a clearly labeled debug line, so nothing is a "black box" -
you can see exactly what goes INTO Chroma and what comes back OUT.

Usage (all arguments are optional - sensible defaults are baked in, exactly
like the session's approach: "put defaults in the program, override only if
you need to"):

    python ingest_to_chroma.py
    python ingest_to_chroma.py --input data/hr_policy_chunks.json \
                                --db-dir chroma_db \
                                --collection HRL
"""

import argparse
import json
import os
import sys
import time

import chromadb


# ----------------------------------------------------------------------
# STEP 0: Defaults (all overridable via command line)
# ----------------------------------------------------------------------
DEFAULT_INPUT = os.path.join(os.path.dirname(__file__), "data", "hr_helpdesk_policy_chunks.json")
DEFAULT_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
DEFAULT_COLLECTION = "HR_Helpdesk_Policy"


def log(step, msg):
    """Small helper so every debug line has a consistent, readable shape."""
    print(f"[{step}] {msg}")


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest chunked documents into ChromaDB")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to the chunked JSON file")
    parser.add_argument("--db-dir", default=DEFAULT_DB_DIR, help="ChromaDB persistent storage directory")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name (like a table name)")
    return parser.parse_args()


# ----------------------------------------------------------------------
# STEP 1: Read each chunk from the source file
# ----------------------------------------------------------------------
def load_chunks(input_path):
    log("STEP 1", f"Reading chunks from: {input_path}")
    if not os.path.exists(input_path):
        log("STEP 1 - ERROR", f"Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    log("STEP 1", f"Found {len(chunks)} chunk(s) in the source file.")
    return chunks


# ----------------------------------------------------------------------
# STEP 2 & 3: Convert each chunk to a clean JSON object and print it
# ----------------------------------------------------------------------
def build_json_records(raw_chunks):
    """
    Convert each raw chunk into the exact shape ChromaDB wants:
      - id            -> unique string id (from chunk_id)
      - document      -> the actual text that gets embedded (from description)
      - metadata      -> SMALL, deliberate set of fields used for keyword
                          filtering only (never a duplicate of the document text -
                          this is the mistake called out in the session notes)

    Source chunk schema (matches the JSON files in data/):
        {"chunk_id": "...", "category": "...", "subcategory": "...", "description": "..."}

    NOTE ON METADATA DESIGN:
    We deliberately keep metadata to just `category` and `subcategory`.
    That's the fix for the session's bug, where the AI-generated code stuffed
    dozens of extraneous keywords (and even business-rule text) into metadata.
    Metadata should answer "which drawer is this chunk in?", not repeat the
    chunk's own content. The `description` field is the only thing that gets
    embedded and searched semantically.
    """
    log("STEP 2", "Converting each chunk into a clean JSON record (id, document, metadata)...")
    records = []
    for i, chunk in enumerate(raw_chunks):
        record = {
            "id": chunk["chunk_id"],
            "document": chunk["description"],
            "metadata": {
                "category": chunk["category"],
                "subcategory": chunk["subcategory"],
            },
        }
        records.append(record)

        # STEP 3: print every JSON object before it goes anywhere
        log(f"STEP 3 - chunk {i + 1}/{len(raw_chunks)}", json.dumps(record, indent=2))

    return records


# ----------------------------------------------------------------------
# STEP 4: Create (or reuse) the collection
# ----------------------------------------------------------------------
def get_or_create_collection(client, collection_name):
    log("STEP 4", f"Looking for collection '{collection_name}'...")
    existing = [c.name for c in client.list_collections()]

    if collection_name in existing:
        log("STEP 4", f"Collection '{collection_name}' already exists -> reusing it.")
    else:
        log("STEP 4", f"Collection '{collection_name}' not found -> it will be created now.")

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},  # distance metric used for similarity search
    )
    log("STEP 4", f"Collection ready. Existing record count: {collection.count()}")
    return collection


# ----------------------------------------------------------------------
# STEP 5: Embed + store every record (embedding happens automatically
#          inside collection.add(), using Chroma's default embedding
#          function: sentence-transformers/all-MiniLM-L6-v2, 384 dims)
# ----------------------------------------------------------------------
def embed_and_store(collection, records):
    log("STEP 5", f"Embedding + storing {len(records)} record(s) into ChromaDB...")

    ids = [r["id"] for r in records]
    documents = [r["document"] for r in records]
    metadatas = [r["metadata"] for r in records]

    log("STEP 5", f"IDs going in       : {ids}")
    log("STEP 5", f"Metadata going in  : {metadatas}")
    log("STEP 5", "Calling collection.add() -> this is where the embedding model runs "
                  "and the vectors + documents + metadata are written to disk.")

    start = time.time()
    # add() upserts by id: same id => overwritten, new id => appended.
    # This is the behavior the session's "replace instead of append" bug was
    # actually missing - here it's explicit and correct.
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    elapsed = time.time() - start

    log("STEP 5", f"Insert complete in {elapsed:.3f} seconds.")


# ----------------------------------------------------------------------
# STEP 6: Print stats after inserting
# ----------------------------------------------------------------------
def print_stats(collection, db_dir):
    log("STEP 6", "Reading back collection stats to confirm the write succeeded...")

    count = collection.count()
    log("STEP 6", f"Total records in collection '{collection.name}': {count}")

    if count > 0:
        peek = collection.peek(limit=1)
        sample_embedding = peek["embeddings"][0] if peek.get("embeddings") is not None and len(peek["embeddings"]) else None
        if sample_embedding is not None:
            log("STEP 6", f"Embedding dimension (per record): {len(sample_embedding)}")
            log("STEP 6", f"Sample of first embedding's values: {list(sample_embedding[:5])} ...")

    db_size_bytes = get_dir_size(db_dir)
    log("STEP 6", f"ChromaDB storage directory: {db_dir}")
    log("STEP 6", f"ChromaDB storage size on disk: {db_size_bytes / 1024:.1f} KB")


def get_dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def main():
    args = parse_args()

    print("=" * 70)
    print("CHROMA DB INGESTION PIPELINE")
    print("=" * 70)
    log("CONFIG", f"input file      = {args.input}")
    log("CONFIG", f"db directory    = {args.db_dir}")
    log("CONFIG", f"collection name = {args.collection}")
    print("-" * 70)

    # STEP 1: read raw chunks
    raw_chunks = load_chunks(args.input)

    # STEP 2 + 3: build + print clean JSON records
    records = build_json_records(raw_chunks)

    # Connect to (or create) the persistent ChromaDB store on disk
    log("CONNECT", f"Starting persistent ChromaDB client at: {args.db_dir}")
    client = chromadb.PersistentClient(path=args.db_dir)

    # STEP 4: get or create the collection
    collection = get_or_create_collection(client, args.collection)

    # STEP 5: embed + store
    embed_and_store(collection, records)

    # STEP 6: print stats
    print("-" * 70)
    print_stats(collection, args.db_dir)
    print("=" * 70)
    log("DONE", "Ingestion complete. Run search_chroma.py to query this data, "
                "or streamlit run chroma_dashboard.py to inspect it visually.")


if __name__ == "__main__":
    main()
