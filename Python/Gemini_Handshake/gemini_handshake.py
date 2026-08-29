import os
from dotenv import load_dotenv
from google import genai  # This will now work

# 1. Handshake with .env
load_dotenv()
api_key = os.getenv("google-generativeai")

if not api_key:
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

# 2. Initialize Client
client = genai.Client(api_key=api_key)

# 3. Quick Test
try:
    response = client.models.generate_content(
        model="gemini-3.6-flash", 
        contents="Hello!"
    )
    print(f"Handshake Successful To: {response.text}")
except Exception as e:
    print(f"Handshake Failed: {e}")