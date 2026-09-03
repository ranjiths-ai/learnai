import os 
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()
# Retrieve the API key from environment variables
api_key = os.getenv("google-generativeai")

# Initialize the GenAI client with the API key
client = genai.Client(api_key=api_key)

# List available models that support embedding content
for m in client.models.list():
    if 'embedContent' in m.supported_actions:
        print(m.name)

# Generate embeddings for a sample text
sample_text = "Generative AI is transforming technology."

try:
    # 1. ADD 'models/' prefix to the model name
    result = client.models.embed_content(
        model="models/gemini-embedding-001", 
        contents=sample_text
    )

    # 2. FIX attribute name to 'embeddings' (plural)
    embedding_vector = result.embeddings[0].values
    
    print(f"Embedding length: {len(embedding_vector)}")
    print(f"Sample values: {embedding_vector[:5]}")

except Exception as e:
    print(f"An error occurred: {e}")
