# ChromaDB Ingestion + Hybrid Search Pipeline

Runnable code for the pipeline covered in the session and learning notes:
**chunk → JSON → embed → store in ChromaDB → keyword-filter + similarity search → inspect via dashboard.**

Every script prints a `[STEP]` / `[STAGE]` labeled trace of exactly what it's
doing, so nothing is a black box.

## Files

| File | Purpose |
|---|---|
| `data/hr_helpdesk_policy_chunks.json` | **Default input.** 25 chunks from `HR_Helpdesk_Policy_Handbook.docx` — one chunk per subsection across Employee Leave, Maternity, Remote Work, and Insurance Benefits policies. Schema: `chunk_id, category, subcategory, description`. |
| `data/hr_policy_chunks.json` | Earlier 8-chunk sample (kept for reference / as a second test file). |
| `ingest_to_chroma.py` | Reads the chunks, builds + prints a JSON record per chunk, embeds them, stores them in a persistent ChromaDB collection, then prints record count / embedding dimension / db size. |
| `search_chroma.py` | Command-line **hybrid search**: Stage 1 filters by `category`/`subcategory` (keyword match), Stage 2 runs semantic similarity search only within that narrowed pool, and prints ranked results with similarity scores. |
| `chroma_dashboard.py` | Streamlit UI standing in for the console ChromaDB doesn't ship with — browse every collection, its documents/metadata, a raw embedding vector, and run ad-hoc hybrid searches. |

### Chunk schema

```json
{
  "chunk_id": "chunk_01",
  "category": "employee_leave_policy",
  "subcategory": "purpose",
  "description": "This policy defines the types of leave available to employees..."
}
```

`category` and `subcategory` become Chroma **metadata** (used by Stage 1's
keyword filter). `description` is the only field that gets embedded and
semantically searched — this is deliberate: metadata should describe the
chunk, not duplicate its content.

## Setup

```bash
pip install -r requirements.txt
```

The first time you run `ingest_to_chroma.py`, Chroma downloads its default
embedding model (`sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions,
~80MB) — that requires internet access once; it's cached locally after that.

## 1. Ingest the sample data

```bash
python ingest_to_chroma.py
```

This ingests `data/hr_helpdesk_policy_chunks.json` (the default) into a
collection named `HR_Helpdesk_Policy`. Optional overrides (defaults are
baked in, same as the session's approach):

```bash
python ingest_to_chroma.py --input data/hr_helpdesk_policy_chunks.json --db-dir chroma_db --collection HR_Helpdesk_Policy
```

Watch the console — it prints every chunk's JSON record before storing it,
then confirms the record count, embedding dimension, and on-disk size
after the write.

## 2. Search it

```bash
python search_chroma.py
Enter text to search: how many sick leave days do I get
```

Or non-interactively, with the two-stage hybrid search:

```bash
# Stage 1 narrows to just the maternity-policy chunks, Stage 2 ranks by similarity within them
python search_chroma.py --query "how many weeks of maternity leave" --category maternity_policy

python search_chroma.py --query "reporting a lost laptop" --category remote_work_policy --top-k 2

python search_chroma.py --query "insurance claim reimbursement" --top-k 3
```

Available `--category` values in the default dataset: `employee_leave_policy`,
`maternity_policy`, `remote_work_policy`, `insurance_benefits_policy`.

## 3. Inspect it visually

```bash
streamlit run chroma_dashboard.py
```

Opens a browser dashboard showing every collection's records, metadata,
raw embedding vectors, and a live search box.

## Using your own document instead of the sample HR policy

Point `--input` at your own JSON file with a list of chunks in the same
shape:

```json
[
  {"chunk_id": "chunk_01", "category": "...", "subcategory": "...", "description": "..."}
]
```

Keep `category`/`subcategory` short and deliberate — that's what Stage 1
keyword filtering runs against. Don't put the chunk's own content into
metadata; only the `text` field should hold the actual passage.



## Size based chunking - Prompt
Generate a sized based chunkig. Lets go with 300 tokens per size. Plan and suggest the design
I dont want the splitting or chunking as per the headings or sub headings, I dont want meta data as well. replan generate a new python file with the code