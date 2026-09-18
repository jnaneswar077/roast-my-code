from fastapi import Request
from groq import Groq


def get_groq_client(request: Request) -> Groq:
    return request.app.state.groq_client