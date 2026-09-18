import os
import time
from dotenv import load_dotenv
from groq import Groq, AsyncGroq
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from fastapi import UploadFile, File

from app.services.ocr import extract_code_from_image
from app.schemas import RoastRequest, RoastResponse
from app.dependencies import get_groq_client, get_async_groq_client
from app.services.groq_client import get_roast, stream_roast
from app.services.diffing import make_diff
load_dotenv()

@asynccontextmanager
async def lifespan(app:FastAPI):
    # startup: create client once
    app.state.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    app.state.async_groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

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

@app.post("/roast/stream")
async def roast_stream(payload: RoastRequest, client: AsyncGroq = Depends(get_async_groq_client)):
    return StreamingResponse(
        stream_roast(client, payload.code, payload.language),
        media_type="text/plain",
    )


@app.post("/roast-slow-async")
async def roast_slow_async(payload: RoastRequest):
    time.sleep(5)  # simulates a slow blocking call, done WRONG inside async def
    return {"status": "done"}

@app.post("/roast-slow-sync")
def roast_slow_sync(payload: RoastRequest):
    time.sleep(5)
    return {"status": "done"}


@app.post("/roast/image", response_model=RoastResponse)
async def roast_image(
    file: UploadFile = File(...),
    language: str = "python",
    client: Groq = Depends(get_groq_client),
):
    image_bytes = await file.read()
    code = extract_code_from_image(image_bytes)

    result = get_roast(client, code, language)
    diff = make_diff(code, result["improved_code"])

    return RoastResponse(
        roast_score=result["roast_score"],
        roast=result["roast"],
        review=result["review"],
        suggestions=result["suggestions"],
        improved_code=result["improved_code"],
        diff=diff,
    )