import os
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from app.schemas import RoastRequest, RoastResponse
from app.dependencies import get_groq_client
from app.services.groq_client import get_roast
from app.services.diffing import make_diff
load_dotenv()

@asynccontextmanager
async def lifespan(app:FastAPI):
    # startup: create client once
    app.state.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    yield
    #shutdown: nothing to clear up for groq, but this is where you'd close DB/GPU resouorces

# app = FastAPI(title="Roast My Code")
app = FastAPI(title="Roast My Code", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "ok"}


@app.post("/roast", response_model=RoastResponse)
def roast_code(payload: RoastRequest, client: Groq = Depends(get_groq_client)):
    result = get_roast(client, payload.code, payload.language)
    diff = make_diff(payload.code, result["improved_code"])

    return RoastResponse(
        roast_score=result["roast_score"],
        roast=result["roast"],
        review=result["review"],
        suggestions=result["suggestions"],
        improved_code=result["improved_code"],
        diff=diff,
    )