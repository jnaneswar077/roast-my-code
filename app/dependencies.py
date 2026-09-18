from fastapi import Request
from groq import Groq, AsyncGroq


def get_groq_client(request: Request) -> Groq:
    return request.app.state.groq_client

def get_async_groq_client(request: Request) -> AsyncGroq:
    return request.app.state.async_groq_client