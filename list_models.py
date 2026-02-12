
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=api_key)

print("Listing available models:")
try:
    for m in client.models.list(config={"page_size": 100}):
        print(f"  - {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
