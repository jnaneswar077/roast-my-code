import json
from groq import Groq

PROMPT_TEMPLATE = """You are a witty senior engineer reviewing code.
Roast this {language} code sarcastically but usefully, then give a genuine
technical review, then rewrite it as an improved version.

Respond ONLY with valid JSON matching this exact structure, no markdown fences:
{{
  "roast_score": <int 1-10, how roastable this code is>,
  "roast": "<sarcastic roast text>",
  "review": "<genuine technical review>",
  "suggestions": ["<suggestion 1>", "<suggestion 2>"],
  "improved_code": "<corrected/optimized code as a plain string>"
}}

Code:
{code}
"""


def get_roast(client: Groq, code: str, language: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(language=language, code=code)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)