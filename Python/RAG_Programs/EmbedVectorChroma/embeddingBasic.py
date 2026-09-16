from sentence_transformers import SentenceTransformer
import numpy as np
import os
from dotenv import load_dotenv
import google.generativeai as genai


# 25 words and terms related to AI and databases.
words = [
	"artificial intelligence",
	"machine learning",
	"deep learning",
	"neural network",
	"natural language processing",
	"computer vision",
	"embedding",
	"transformer",
	"algorithm",
	"dataset",
	"database",
	"SQL",
	"query",
	"table",
	"schema",
	"index",
	"transaction",
	"record",
	"column",
	"vector database",
	"retrieval",
	"metadata",
	"knowledge base",
	"semantic search",
	"RAG",
]

## Load the sentence transformer model and generate embeddings for the words.
print("Loading the sentence transformer model...")
#model = SentenceTransformer("all-MiniLM-L6-v2", device="cuda")  # Use GPU if available
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Generating embeddings...")
#embeddings = model.encode(words, convert_to_tensor=True)  # Convert to tensor for GPU acceleration
embeddings = model.encode(words, truncate_dim=70)

user_text = input("\nEnter text to search: ").strip()
if not user_text:
	raise ValueError("Input text cannot be empty.")

query_embedding = model.encode([user_text], truncate_dim=70)[0]

# Calculate cosine similarity between the input and each predefined term.
embedding_norms = np.linalg.norm(embeddings, axis=1)
query_norm = np.linalg.norm(query_embedding)
similarities = (embeddings @ query_embedding) / (embedding_norms * query_norm)

top_indices = np.argsort(similarities)[-3:][::-1]
print("\nTop 3 similar values:")
for index in top_indices:
	print(f"{words[index]}: {similarities[index]:.4f}")

# Pass the retrieved context to Gemini for a domain-specific answer.
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
	raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY was not found in the .env file.")

genai.configure(api_key=api_key)
gemini = genai.GenerativeModel("gemini-3.6-flash")
retrieved_words = [words[index] for index in top_indices]
prompt = (
	'result returned from myrag systems post similarity search now give me the accurate '
	'synonym for ''{user_text}'' in a AI domain\n\n'
	"Top 3 retrieved words from similarity search:\n"
	+ "\n".join(f"- {word}" for word in retrieved_words)
	+ "\n\nProvide the best synonym and explain your reasoning based on these retrieved words."
)

try:
    response = gemini.generate_content(prompt)
    print("\nGemini response:")
    print(response.text)
except Exception as e:
    print(f"Handshake Failed: {e}")
