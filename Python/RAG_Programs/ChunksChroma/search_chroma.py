"""
search_chroma.py 
-----------------
Two-stage HYBRID search against ChromaDB:

  STAGE 1 - Keyword / metadata filter
            Narrow the candidate pool using an exact metadata match
            (e.g. category = "employee_leave_policy") BEFORE doing any
            vector math. This is fast and removes obviously-irrelevant
            chunks up front.

  STAGE 2 - Semantic similarity search
            Run the embedding-based similarity search only within the
            (already narrowed) candidate pool, and return the Top-K
            closest chunks with their similarity scores.

This is the design the session sketched conceptually (search by keyword
first, then confine the semantic search to that "room") but did not
build - this script implements it end to end, with full debug output at
every step so you can see exactly what goes into Chroma and what comes
back out.

Usage:
    python search_chroma.py
    python search_chroma.py --query "how many days sick leave" --category employee_leave_policy
    python search_chroma.py --query "reporting harassment" --top-k 2
"""

import argparse
import os
import time

import chromadb

DEFAULT_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
DEFAULT_COLLECTION = "HR_Helpdesk_Policy"


def log(step, msg):
    print(f"[{step}] {msg}")


def parse_args():
    parser = argparse.ArgumentParser(description="Hybrid (keyword + similarity) search over ChromaDB")
    parser.add_argument("--db-dir", default=DEFAULT_DB_DIR, help="ChromaDB persistent storage directory")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name to search")
    parser.add_argument("--query", default=None, help="Search text. If omitted, you'll be prompted.")
    parser.add_argument("--category", default=None, help="Optional STAGE 1 keyword filter, e.g. employee_leave_policy")
    parser.add_argument("--subcategory", default=None, help="Optional STAGE 1 keyword filter, e.g. sick_leave")
    parser.add_argument("--top-k", type=int, default=3, help="How many results to return from STAGE 2")
    return parser.parse_args()


def distance_to_similarity(distance):
    """
    Chroma (with cosine space) returns a DISTANCE - smaller is better.
    Convert it to an intuitive 0-1 SIMILARITY score where higher is better,
    so the printed output reads naturally.
    """
    return max(0.0, 1.0 - distance)


def stage1_keyword_filter(category, subcategory):
    """
    Build the Chroma `where` clause for the metadata (keyword) filter.
    Returns None if no filter was requested (search the whole collection).
    """
    log("STAGE 1", "Building keyword/metadata filter...")

    conditions = []
    if category:
        conditions.append({"category": category})
        log("STAGE 1", f"  filter -> category == '{category}'")
    if subcategory:
        conditions.append({"subcategory": subcategory})
        log("STAGE 1", f"  filter -> subcategory == '{subcategory}'")

    if not conditions:
        log("STAGE 1", "  No keyword filter provided -> searching the ENTIRE collection.")
        return None

    where_clause = conditions[0] if len(conditions) == 1 else {"$and": conditions}
    log("STAGE 1", f"  Final Chroma 'where' clause: {where_clause}")
    return where_clause


def stage2_similarity_search(collection, query_text, where_clause, top_k):
    log("STAGE 2", f"Running semantic similarity search for query: '{query_text}'")
    log("STAGE 2", f"  requested result count (Top-K): {top_k}")
    log("STAGE 2", f"  candidate pool restricted by STAGE 1 filter: {where_clause if where_clause else '(none - full collection)'}")

    start = time.time()
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=where_clause,
        include=["documents", "metadatas", "distances"],
    )
    elapsed = time.time() - start
    log("STAGE 2", f"  query completed in {elapsed:.3f} seconds")

    return results


def print_results(results):
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not ids:
        log("RESULT", "No matches found. Try removing the --category/--subcategory filter, "
                       "or check that you've run ingest_to_chroma.py first.")
        return

    print("-" * 70)
    print(f"TOP {len(ids)} RESULT(S)")
    print("-" * 70)
    for rank, (id_, doc, meta, dist) in enumerate(zip(ids, documents, metadatas, distances), start=1):
        similarity = distance_to_similarity(dist)
        print(f"#{rank}  id={id_}  similarity={similarity:.3f}  distance={dist:.3f}")
        print(f"     category={meta.get('category')}  subcategory={meta.get('subcategory')}")
        print(f"     text: {doc}")
        print()


def main():
    args = parse_args()

    print("=" * 70)
    print("CHROMA DB HYBRID SEARCH (keyword filter -> similarity search)")
    print("=" * 70)

    query_text = args.query or input("Enter text to search: ").strip()
    if not query_text:
        log("ERROR", "No query text provided. Exiting.")
        return

    log("CONFIG", f"db directory    = {args.db_dir}")
    log("CONFIG", f"collection name = {args.collection}")
    log("CONFIG", f"query text      = '{query_text}'")
    print("-" * 70)

    log("CONNECT", f"Opening persistent ChromaDB client at: {args.db_dir}")
    client = chromadb.PersistentClient(path=args.db_dir)

    try:
        collection = client.get_collection(args.collection)
    except Exception:
        log("ERROR", f"Collection '{args.collection}' does not exist yet. "
                      f"Run ingest_to_chroma.py first.")
        return

    log("CONNECT", f"Collection '{args.collection}' found, total records: {collection.count()}")
    print("-" * 70)

    # STAGE 1
    where_clause = stage1_keyword_filter(args.category, args.subcategory)
    print("-" * 70)

    # STAGE 2
    results = stage2_similarity_search(collection, query_text, where_clause, args.top_k)
    print("-" * 70)

    print_results(results)
    print("=" * 70)


if __name__ == "__main__":
    main()
