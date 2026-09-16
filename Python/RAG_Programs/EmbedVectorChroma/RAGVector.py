import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Initialize Persistent Vector Store (ChromaDB)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Use a standard sentence transformer model for local vector embeddings
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="rag_knowledge_base",
    embedding_function=embedding_fn
)

# 2. Ingest Historical Data / Knowledge Base Documents
documents = [
    "Employees are eligible for 18 days of paid annual leave per calendar year.",
    "Remote work policy requires approval from the immediate line manager.",
    "Insurance benefits cover up to $100,000 for inpatient hospitalizations.",
    "Breach of confidential data results in immediate disciplinary review."
]
doc_ids = [f"doc_{i}" for i in range(len(documents))]
metadata_list = [{"category": "Policy", "doc_id": i} for i in range(len(documents))]

# Insert into ChromaDB (Persistent)
collection.upsert(
    documents=documents,
    ids=doc_ids,
    metadatas=metadata_list
)
print(f"Successfully stored {collection.count()} documents into ChromaDB.")

# 3. Query & Similarity Search
query_text = "How many days off do I get each year?"
results = collection.query(
    query_texts=[query_text],
    n_results=2
)

retrieved_docs = results['documents'][0]
print("\n--- Similarity Search Results ---")
for idx, doc in enumerate(retrieved_docs, 1):
    print(f"Rank {idx}: {doc}")

# 4. Generate Grounded Response using Google Gemini API
# Pass the retrieved context to Gemini for a domain-specific answer.
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
	raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY was not found in the .env file.")

genai.configure(api_key=api_key)
gemini = genai.GenerativeModel("gemini-3.6-flash")

context = "\n".join(retrieved_docs)
prompt = f"""
You are an HR Assistant. Answer the user's question using ONLY the context provided below.

Context:
{context}

Question:
{query_text}

Answer:
"""

response = gemini.generate_content(prompt)

print("\n--- Final LLM Response ---")
print(response.text)