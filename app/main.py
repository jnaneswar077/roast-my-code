import os
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI(title="Roast My Code")

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/roast")
def roast_code(code: str):
    prompt = f"""Roast this code sarcastically but usefully. 
Give a genuine technical review after the roast.

Code:
{code}
"""

    response = client.chat.completions.create(
        model = "openai/gpt-oss-120b",
        messages=[{'role': 'user', "content": prompt}]
    )
    return {"result": response.choices[0].message.content}


