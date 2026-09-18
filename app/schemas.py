from pydantic import BaseModel, field_validator

class RoastRequest(BaseModel):
    code: str
    language: str = "python"

    @field_validator("code")
    @classmethod
    def code_must_not_be_empty(cls, v:str) -> str:
        if not v.strip():
            raise ValueError("code must not be empty")
        return v

class RoastResponse(BaseModel):
    roast_score: int
    roast: str
    review: str
    suggestions: list[str]
    improved_code: str
    diff: str

    