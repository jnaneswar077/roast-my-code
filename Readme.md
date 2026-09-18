# 🔥 Roast My Code — FastAPI Learning Project

**A staged, hands-on project to master FastAPI for AI/ML backend development**

---

## 1. Project Overview

**What it is:** A FastAPI backend that accepts a piece of code (or a screenshot of code) and returns an AI-generated "roast" — a sarcastic, funny critique paired with a genuinely useful technical code review (bugs, complexity issues, style problems). The response streams back word-by-word like a chatbot typing in real time.

**Why this project:** It's built specifically to make you touch every important FastAPI concept used in real ML/DL/AI backend serving — while being fun enough to actually finish and demo, instead of a generic Iris-classifier tutorial.

**Core "model":** An LLM (Gemini, since you've already used the Gemini API in your Resume Analyzer project) does the actual reasoning — no need to train anything. The focus of this project is 100% the backend/API layer, not the ML model itself.

**Beyond just roasting:** The API doesn't just criticize — it also returns an improved/corrected version of the submitted code, plus a clean diff showing exactly what changed between the original and the improved version.

---

## 2. End Goal

By the end of this project, you will have a **working, demoable ML inference API** that:

- Loads your LLM client once at startup (not per-request)
- Serves both instant JSON responses and live-streaming text responses
- Accepts plain text code AND image uploads (screenshots of code)
- Validates all input before it reaches the model
- Logs every roast in the background without slowing down responses
- Fails gracefully with clean error messages instead of crashing
- Can be safely called from a browser/frontend (CORS handled)
- Is versioned, rate-limited, and covered by basic tests
- Returns an improved version of the submitted code, plus a line-by-line diff of what changed

This becomes a genuine portfolio piece — postable on LinkedIn, tied to your existing DSA/competitive programming content brand, and something you can explain line-by-line in an interview.

---

## 3. Tech Stack

| Layer | Tool |
|---|---|
| Backend framework | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic v2 |
| LLM | Gemini API (reuse from Resume Analyzer) |
| Background logging | FastAPI `BackgroundTasks` + SQLite or a flat file |
| Rate limiting | `slowapi` |
| Testing | `pytest` + FastAPI `TestClient` |
| Code diffing | `difflib` (Python standard library — no extra install needed) |
| Optional frontend (for demo/CORS testing) | Simple HTML/JS page or Streamlit |
| Containerization (optional, later) | Docker (you already know this) |

---

## 4. Response Schema (Updated)

This is purely a prompt engineering + schema change — no new FastAPI concept required.

```python
class RoastResponse(BaseModel):
    roast_score: int
    roast: str
    review: str
    suggestions: list[str]
    improved_code: str    # corrected/optimized version, from the LLM
    diff: str             # line-by-line diff between original and improved_code
```

**How it works:**
- The prompt to Gemini asks for a roast, a genuine technical review, suggestions, AND a corrected/optimized version of the code — all returned in one structured JSON response matching this schema.
- Once you have `code` (original) and `improved_code` (from Gemini), you generate the `diff` field yourself using Python's built-in `difflib` module — no LLM call needed for this part, and no extra dependency to install.
- A minimal example:
  ```python
  import difflib

  def make_diff(original: str, improved: str) -> str:
      diff = difflib.unified_diff(
          original.splitlines(),
          improved.splitlines(),
          lineterm="",
          fromfile="original",
          tofile="improved",
      )
      return "\n".join(diff)
  ```
- **Reliability note:** LLMs don't always perfectly follow a requested JSON structure. Plan for basic retry logic or a fallback parse if Gemini's JSON response is malformed — this ties directly into the custom exception handling concept in Stage 2, so it's not wasted effort.

---

## 5. Concept-to-Feature Map

This is the master reference — every FastAPI concept from your priority list mapped to the exact feature that teaches it.

### 🔴 Priority 1 (Core — must know cold)
| Concept | Feature in this project |
|---|---|
| Pydantic schemas | `code`, `language` as request input; `roast_score`, `review`, `suggestions`, `improved_code`, `diff` as response output |
| `lifespan` context manager | Load the Gemini client once when the server starts |
| `Depends()` | Inject the Gemini client into route handlers |
| `async def` vs `def` routes | The `/roast` route calling Gemini (I/O-bound) — deliberately compare async vs sync behavior |
| `StreamingResponse` + async generators | The roast "typing out live" feature |
| `UploadFile` | Screenshot-of-code upload endpoint (OCR extracts code, then roasts it) |
| Pydantic schema design (extended) | `improved_code` and `diff` fields added to `RoastResponse` |

### 🟠 Priority 2 (Important)
| Concept | Feature in this project |
|---|---|
| `BackgroundTasks` | Log every roast (code, score, timestamp) for a "hall of fame" history/leaderboard |
| Custom exception handling | Handle empty code, unsupported language, Gemini API timeout/failure, and malformed/unparseable JSON from Gemini (retry once, then fail cleanly) |
| `@field_validator` | Reject code over a character limit; reject empty submissions |
| CORS middleware | Needed once you build a small frontend to demo/share the project |
| ~~WebSockets~~ | **Skipped intentionally** — `StreamingResponse` already covers real-time output; learn WebSockets separately later with a small dedicated example |
| Batching/queuing (conceptual) | Optional stretch feature: "Roast my whole repo" (multiple files at once) |

### 🟡 Priority 3 (Polish)
| Concept | Feature in this project |
|---|---|
| `Annotated` types | Refactor dependencies for cleaner syntax |
| `response_model_exclude` | Hide raw Gemini API debug fields from the client response |
| API versioning (`/v1/...`) | Wrap all routes under a version prefix |
| Rate limiting (`slowapi`) | Genuinely important here since Gemini API calls cost money/quota |
| Testing (`TestClient` + `pytest`) | Write tests for the `/roast` endpoint and validation rules |

---

## 6. Staged Build Plan

The project is **one evolving codebase**, not separate projects. Each stage adds maturity.

---

### 🟩 Stage 0 — Bare Minimum ("It Runs")

**Goal:** Get a working `/roast` endpoint, no polish.

- Single FastAPI app, one file
- One endpoint: `POST /roast` — accepts raw code as a plain string, calls Gemini synchronously, returns the roast + review as plain text
- No schemas yet (just accept a raw string body)
- Model/API key loaded inline, not properly managed
- Test manually via Swagger UI (`/docs`) or `curl`

**What "done" looks like:** You can paste code into `/docs`, hit "Execute," and get a roast back.

---

### 🟦 Stage 1 — Priority 1 Concepts ("It Runs Correctly and Efficiently")

**Goal:** Rebuild Stage 0 the right way.

1. Define Pydantic models:
   - `RoastRequest` — `code: str`, `language: str`
   - `RoastResponse` — `roast_score: int`, `roast: str`, `review: str`, `suggestions: list[str]`, `improved_code: str`, `diff: str`
2. Update the Gemini prompt to explicitly request a roast, a genuine review, suggestions, AND an improved/corrected version of the code — all as structured JSON matching the schema
3. Write a `make_diff()` helper using `difflib.unified_diff()` to generate the `diff` field from `code` and `improved_code` — pure Python, no LLM call needed
4. Move Gemini client initialization into a `lifespan` context manager — load it once at startup
5. Create a dependency (`Depends()`) that provides the Gemini client to routes instead of using a global variable directly
6. Add a second, deliberately slow/blocking version of the route to compare `async def` vs `def` behavior — hit both with concurrent requests and observe the difference
7. Add `POST /roast/stream` — same functionality, but streams the roast back word-by-word using `StreamingResponse` + an async generator
8. Add `POST /roast/image` — accepts an `UploadFile` (screenshot), runs OCR (e.g., `pytesseract`) to extract code, then roasts it

**What "done" looks like:** Clean request/response contracts (including improved code + diff), model loaded once, one streaming endpoint working, one image-upload endpoint working.

---

### 🟨 Stage 2 — Priority 2 Concepts ("It Runs Reliably and Safely")

**Goal:** Make the app robust enough that bad input or failures don't break it.

1. Add `BackgroundTasks` to log every roast (input code, score, timestamp) to SQLite or a flat file — this becomes the data source for a future "hall of fame" leaderboard feature
2. Add custom exception handlers for:
   - Empty/whitespace-only code submissions
   - Unsupported language values
   - Gemini API timeouts or failures (don't leak raw stack traces to the client)
   - Malformed/unparseable JSON from Gemini — retry the call once, then return a clean error if it still fails
3. Add `@field_validator` on `RoastRequest`:
   - Reject code over a set character limit (e.g., 5,000 chars)
   - Reject empty strings
4. Add CORS middleware and build a minimal HTML/JS page (or Streamlit app) that calls your API directly from the browser — this is where CORS becomes real, not theoretical
5. *(Optional stretch)* Add a "Roast my whole repo" endpoint that accepts multiple files and processes them — introduces batching-style thinking even without a formal queue system

**What "done" looks like:** You can throw garbage input at the API and it responds with clean errors, never crashes, and every roast gets logged automatically.

---

### 🟧 Stage 3 — Priority 3 Concepts ("It's Production-Polished")

**Goal:** Refinement — this stage is about code quality and safety, not new features.

1. Refactor dependencies to use `Annotated` syntax
2. Add `response_model_exclude` to hide any raw/internal Gemini response fields from the client
3. Version the API — wrap all routes under `/v1/`
4. Add rate limiting via `slowapi` (important here since Gemini API calls have real cost/quota)
5. Write a small test suite with `pytest` + FastAPI's `TestClient`:
   - Test a valid roast request returns 200 and expected schema
   - Test empty code returns a validation error
   - Test oversized code is rejected

**What "done" looks like:** The project feels like something you could hand off to another developer — versioned, tested, rate-limited, and clean.

---

## 7. Suggested Folder Structure (by Stage 1)

```
roast-my-code/
├── app/
│   ├── main.py              # FastAPI app, lifespan, router includes
│   ├── schemas.py           # Pydantic models (RoastRequest, RoastResponse)
│   ├── dependencies.py      # Gemini client dependency
│   ├── routes/
│   │   ├── roast.py         # /roast, /roast/stream, /roast/image
│   ├── services/
│   │   ├── gemini_client.py # Gemini API wrapper logic
│   │   ├── ocr.py           # Image-to-code extraction
│   │   ├── diffing.py       # difflib-based diff generation
├── tests/
│   ├── test_roast.py
├── requirements.txt
├── .env                     # Gemini API key
└── README.md
```

---

## 8. Learning Method (How to Actually Absorb Each Concept)

- **Don't read FastAPI docs top-to-bottom** — use them as reference while building: https://fastapi.tiangolo.com/
- When you hit `lifespan`: deliberately load the model inside the route first, time 20 requests, then switch to `lifespan` and time again. Feel the difference.
- When you hit async vs sync: put `time.sleep(3)` in an `async def` route and hit it twice concurrently — watch it serialize. Move it to plain `def` — watch FastAPI's threadpool handle it correctly.
- When you hit CORS: don't just add the middleware and assume it works — build the tiny frontend and *trigger* a CORS error first, so you understand what problem the middleware solves.
- Treat each stage as a checkpoint: don't move to the next stage until the current one's "done" criteria are met.

---

## 9. Open Questions / Decisions Still Needed

- [ ] Which OCR library for the image-upload feature — `pytesseract` (simpler, local) vs a cloud OCR API?
- [ ] SQLite vs flat-file JSON for the roast logging in Stage 2?
- [ ] Final tone/personality for the "roast" — how sarcastic vs constructive should the prompt make it?
- [ ] Whether to build the optional "Roast my whole repo" stretch feature in Stage 2

---

## 10. Timeline (Suggested)

| Week | Focus |
|---|---|
| Week 1 | Stage 0 + Stage 1 (Priority 1 concepts) |
| Week 2 | Stage 2 (Priority 2 concepts) |
| Week 3 | Stage 3 (Priority 3 concepts) + polish + LinkedIn demo post |

---

*Generated as a personal learning roadmap for mastering FastAPI in an AI/ML backend context.*
