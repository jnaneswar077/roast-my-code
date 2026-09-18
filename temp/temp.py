import os
from dotenv import load_dotenv
from google import genai
from fastapi import FastAPI

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
for m in client.models.list():
    print(m.name)