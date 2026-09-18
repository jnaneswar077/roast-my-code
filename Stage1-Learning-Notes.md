# 🧠 Stage 1 Learning Notes — Roast My Code

**Everything learned while building Stage 1: Pydantic schemas, lifespan, Depends(), async vs sync, streaming, and file uploads.**

---

## 1. What Stage 1 Actually Built

Starting from a bare-minimum `/roast` endpoint (Stage 0: one file, no schemas, model loaded inline), Stage 1 rebuilt it properly with:

- Pydantic schemas for request/response validation
- A shared LLM client created once at startup (`lifespan`)
- Dependency injection (`Depends()`) to hand that client to routes
- A real, measured comparison of `async def` vs plain `def`
- A live-streaming endpoint (`/roast/stream`)
- An image-upload endpoint with OCR (`/roast/image`)

Along the way, real production issues came up and got debugged (model deprecation, package migration, API overload) — those are documented too, because that debugging process is itself valuable experience.

---

## 2. The File Structure and What Each File Does

```
app/
├── main.py                  # wires everything together, defines routes
├── schemas.py                # Pydantic models — the data "shape" contracts
├── dependencies.py           # small functions that hand shared resources to routes
├── services/
│   ├── groq_client.py       # talks to the Groq LLM API (sync + streaming versions)
│   ├── diffing.py           # pure Python diff generation (no LLM involved)
│   ├── ocr.py                # extracts code text from an uploaded image
```

**Key principle:** routes in `main.py` stay *thin* — they just wire pieces together. The actual logic lives in small, reusable functions inside `services/` that don't know or care which route called them.

---

## 3. `schemas.py` — Defining the "Shape" of Data

```python
class RoastRequest(BaseModel):
    code: str
    language: str = "python"

    @field_validator("code")
    @classmethod
    def code_must_not_be_empty(cls, v: str) -> str:
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
```

**What this does:** these are not functions that run logic — they're *contracts*. FastAPI uses `RoastRequest` to automatically check incoming JSON before your route function even runs (missing fields, wrong types get rejected with a clean 422 error, no code needed from you). `RoastResponse` does the same on the way out — if your route tries to return something missing a field, FastAPI catches that too.

`@field_validator` adds a custom rule beyond basic type-checking — here, rejecting empty/whitespace-only code.

---

## 4. `services/diffing.py` — Pure, Standalone Logic

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

**Key insight:** this function knows nothing about FastAPI, HTTP, or Groq. It just takes two strings and returns a diff. This is what "pure logic" means — reusable in any context, completely decoupled from the web framework. `difflib` is part of Python's standard library, so no extra install was needed.

---

## 5. `services/groq_client.py` — Two Different Jobs, Two Different Functions

```python
def get_roast(client: Groq, code: str, language: str) -> dict:
    # synchronous — returns a complete dict all at once
    ...

async def stream_roast(client: AsyncGroq, code: str, language: str) -> AsyncGenerator[str, None]:
    # async generator — yields text chunks as they arrive
    ...
```

- `get_roast` is **synchronous** — used when you want the full structured JSON response at once (roast + review + improved code + diff)
- `stream_roast` is an **async generator** (`async def` + `yield`) — used when you want text arriving gradually, word by word, for a "live typing" effect

They take *different client types* on purpose: `get_roast` takes a plain `Groq` client, `stream_roast` takes an `AsyncGroq` client. This pairing is not arbitrary — it connects directly to the async vs sync concept (see Section 8).

**Structured JSON output trick:** the prompt to Groq explicitly asks for JSON matching an exact structure, and the API call includes `response_format={"type": "json_object"}` to force valid JSON back — this makes `json.loads(...)` reliable instead of hoping the model formats things correctly on its own.

---

## 6. `dependencies.py` — The Bridge Between Startup and Routes

```python
from fastapi import Request
from groq import Groq, AsyncGroq

def get_groq_client(request: Request) -> Groq:
    return request.app.state.groq_client

def get_async_groq_client(request: Request) -> AsyncGroq:
    return request.app.state.async_groq_client
```

These functions do almost nothing by themselves — their whole purpose is to be passed into `Depends()` so FastAPI calls them automatically per-request, retrieving a resource that was created once and reused everywhere (see Section 7 for exactly how).

**Why not just write `request.app.state.groq_client` inline in every route?**
1. Avoids repeating that line in every single route that needs the client
2. Makes it possible to swap in a fake/test client later without changing route code (a technique called dependency overriding)

---

## 7. `app.state` and `lifespan` — How the Client Gets Shared

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    app.state.async_groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    yield
    # shutdown: nothing to clean up for Groq, but this is where you'd close DB/GPU resources

app = FastAPI(title="Roast My Code", lifespan=lifespan)
```

**What `app.state` is:** `app` is the single `FastAPI` instance created once when the server starts, and it stays alive for the server's entire lifetime. `.state` is just a plain object attached to it that acts as a shared whiteboard — you can stick any attribute name you want onto it (`app.state.groq_client`, `app.state.anything`), and any code with access to `app` can read it back later.

**Why not a global variable instead?** You could use a global, but `app.state` ties the data's lifetime directly to the app object rather than a loose module-level variable — this matters especially for testing, where multiple `FastAPI()` instances each get their own separate `.state`.

**The full chain, in order:**
1. Server starts → `lifespan` runs → `app.state.groq_client = Groq(...)` writes the client onto the whiteboard — **this happens exactly once**
2. A request comes in for `/roast` → FastAPI sees `client: Groq = Depends(get_groq_client)` in the route's signature
3. FastAPI calls `get_groq_client(request)`, automatically passing in the current request
4. Inside that function, `request.app` is — literally, the same object in memory as — the `app` variable from `main.py`
5. `.state.groq_client` reads back the *same* client object written in step 1
6. That client gets returned and handed to the route function as the `client` parameter

**Why this matters:** the model/client is expensive to create. Creating it once at startup and sharing it via `app.state` avoids re-creating it on every single request — a classic beginner mistake that tanks latency.

---

## 8. Async `def` vs Plain `def` — The Core Concept

### The decision rule
**Can you `await` the slow thing inside your route?**
- **Yes** (an async-compatible client like `AsyncGroq`, an async DB driver) → use `async def` and `await` it
- **No** (a blocking call like `time.sleep()`, the sync `Groq` client, a plain `requests.get()`) → use plain `def`

### Why this matters: FastAPI has ONE event loop
The event loop is a single thread that runs your code and switches between tasks — but only at points where code says "I'm waiting on something, go do something else." That checkpoint is exactly what `await` creates.

- **`await` on something genuinely awaitable:** the event loop goes off to handle other requests while waiting, then resumes exactly where it left off once the response is ready.
- **A blocking call with no `await` (even inside `async def`):** there's no checkpoint. The call just freezes there, and since there's only one event loop, it freezes the *entire application* — not just that one request.

### The measured proof (from a real experiment)
Two nearly-simultaneous requests were fired at two test routes:

| Route | Type | Result |
|---|---|---|
| `/roast-slow-async` | `async def` + `time.sleep(5)` (WRONG — blocking call inside async) | Request A: 5.02s, Request B: 10.02s — **serialized**, because the sleep froze the one event loop |
| `/roast-slow-sync` | plain `def` + `time.sleep(5)` | Both requests: ~5.04s — **ran in parallel**, because FastAPI automatically runs plain `def` routes in a separate worker thread from a threadpool |

### Why plain `def` isn't "worse"
FastAPI's logic: *if a route is plain `def`, it might block, so hand the whole function to a worker thread automatically.* This is real parallelism (separate OS threads), but it's limited by the threadpool's size (often ~40 threads by default) — unlike async, where a single event loop can juggle thousands of waiting connections cheaply, since a paused coroutine costs almost nothing while a thread is a heavier resource.

### The trap
```python
async def bad_route():
    time.sleep(5)   # async def, but nothing is awaited — this is WORSE than plain def
```
Writing `async def` does nothing by itself. It only helps if something *inside* it is actually `await`ed. An `async def` full of blocking calls blocks the one shared event loop — strictly worse than plain `def`, which at least gets threadpooled safely.

### What this meant concretely for the project
- `/roast` uses the **sync** `Groq` client and is plain `def` — correct, because FastAPI threadpools it automatically
- `/roast/stream` uses the **async** `AsyncGroq` client and is `async def` — required, because `await` and `async for` only work with an awaitable, async-iterable client, and streaming specifically needs the event loop to stay free to progressively send chunks

---

## 9. Two Concurrent Users on One Event Loop — The Deeper Nuance

**Question explored:** if two users hit an async endpoint around the same time, does the event loop run them on separate threads simultaneously?

**Answer: No.** It's still just ONE thread. Here's what actually happens:

1. User A's request arrives → event loop runs A's code up to `await` → A goes into a "waiting" state → the loop is now free
2. User B's request arrives shortly after → event loop runs B's code up to its `await` → B also waits → the loop is free again
3. Both A and B are "waiting" on their LLM calls *at the same time*, on the *same single thread* — this works because waiting doesn't require active CPU work
4. When both LLM responses become ready (even within microseconds of each other), the OS delivers these as two separate events
5. The event loop processes whichever one is ready first, finishes that request's remaining (usually tiny) code, sends the response, then immediately does the same for the second

**Key distinction:** this is "one thread doing extremely fast sequential switching," not "two threads running genuinely in parallel." That's the real difference between:
- **`async def` + await** → one thread, cooperative switching, strictly one-at-a-time (just very fast)
- **plain `def`** → FastAPI hands different requests to different real OS threads → genuine parallelism, limited by threadpool size

It feels simultaneous to users because the only CPU work the loop does per request (parsing a response, running a few lines) is tiny — the slow part (waiting on the LLM) doesn't touch the loop at all.

---

## 10. The Full Request Lifecycle — What Happens When Someone Hits `/roast`

**Key terms defined:**
- **Request**: the raw HTTP message sent over the network — method, path, headers, and body (e.g. `POST /roast` with a JSON body)
- **Route**: the registered mapping between a URL+method combination (`POST /roast`) and the specific Python function that should handle it (`roast_code`)
- **Request object**: FastAPI/Starlette's parsed Python representation of that raw message — has attributes like `.method`, `.headers`, `.app`, etc. Not something you build yourself; FastAPI builds it for you per request.

**Step-by-step trace:**
1. **Client sends the request** — raw HTTP text goes out over the network
2. **Uvicorn receives it** — the ASGI server process listening on the port, hands raw bytes to FastAPI (doesn't know anything about roast logic itself)
3. **FastAPI's router matches it** — looks up `POST /roast` in its internal table, finds `roast_code`
4. **FastAPI builds the `Request` object** — parses the raw bytes into a Python object
5. **FastAPI resolves dependencies** — sees `client: Groq = Depends(get_groq_client)`, calls `get_groq_client(request)` using the object from step 4
6. **Inside `get_groq_client`** — `request.app` gives back the same `FastAPI()` instance from `main.py`; `.state.groq_client` retrieves what `lifespan` stored there at startup
7. **FastAPI validates the body** — parses the JSON body into a dict, then builds a `RoastRequest` instance from it (running any `@field_validator` checks) — this becomes `payload`
8. **Your function finally runs** — `roast_code(payload, client)` executes, with both arguments already fully prepared
9. **Response goes back** — whatever gets `return`ed is converted to JSON and sent back to the client

**Important precision:** `payload` is NOT `request.body` (which would just be raw bytes). It's the *parsed and validated* Python object — a real `RoastRequest` instance with proper `.code` and `.language` attributes — that FastAPI builds only after successfully parsing and validating the raw body against the schema.

**Also important:** FastAPI doesn't necessarily resolve things in one strict linear order ("first dependencies, then validation"). The real guarantee is: your route function is never called until **every single parameter** it asks for has been successfully built — whether that's a validated body or a resolved dependency. If any of that fails, an error goes back immediately and your function never runs.

---

## 11. Real Debugging Journey (Worth Remembering — This Is a Real Skill)

### Problem 1: Gemini model deprecated
- `google.generativeai` package was fully retired (not just deprecated) — replaced by `google-genai`
- Old code: `genai.configure()` + `genai.GenerativeModel(...)` + `model.generate_content(...)`
- New code: `genai.Client(api_key=...)` + `client.models.generate_content(model="...", contents=...)`
- Model name also changed: `gemini-2.0-flash` no longer existed; needed a current model name

### Problem 2: 503 "high demand" errors
- Not a code bug — Google's servers were temporarily overloaded
- Diagnosed by testing directly with a standalone script instead of guessing through FastAPI restarts
- Confirmed model validity by listing all available models via `client.models.list()`

### Problem 3: Switched providers entirely — Gemini → Groq
- Decision: use Groq (hosted open-source models on fast infrastructure) instead of fighting Gemini's instability
- Groq uses an OpenAI-style chat completions API shape: `client.chat.completions.create(model=..., messages=[...])`
- Response text lives at `response.choices[0].message.content` (not `.text` like Gemini)
- Model used: `openai/gpt-oss-120b` — OpenAI's own open-weight model, running on Groq's infrastructure

### Lesson learned
Package deprecations, model retirements, and provider outages are normal, recurring realities in AI backend work — not signs something is fundamentally wrong with the approach. Isolating a bug by testing outside the full app (a standalone script) is faster than guessing through repeated server restarts.

---

## 12. Testing Techniques Learned

- **Swagger UI (`/docs`)** — good for simple JSON request/response testing, but doesn't render streaming responses well
- **`curl` on Windows** — PowerShell's built-in `curl` is actually an alias for `Invoke-WebRequest`; use `curl.exe` explicitly, and for JSON bodies with special characters, write the JSON to a file and use `-d "@filename.json"` instead of fighting shell escaping
- **Python `requests` with `stream=True`** — a reliable cross-platform way to test streaming endpoints, avoiding shell quoting issues entirely:
  ```python
  response = requests.post(url, json={...}, stream=True)
  for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
      print(chunk, end="", flush=True)
  ```
- **Concurrency testing** — using `ThreadPoolExecutor` to fire two requests at once and measure wall-clock time was the concrete way to *prove* async vs sync behavior, rather than just trusting the theory

---

## 13. `/roast/image` — Reuse in Action

```python
@app.post("/roast/image", response_model=RoastResponse)
async def roast_image(file: UploadFile = File(...), language: str = "python", client: Groq = Depends(get_groq_client)):
    image_bytes = await file.read()
    code = extract_code_from_image(image_bytes)
    result = get_roast(client, code, language)          # SAME function as /roast
    diff = make_diff(code, result["improved_code"])       # SAME function as /roast
    return RoastResponse(...)
```

**The core insight:** this route doesn't duplicate any roast logic. It only adds one new step — `extract_code_from_image()` (OCR) — then calls the exact same `get_roast()` and `make_diff()` functions that `/roast` uses. The only real difference between `/roast` and `/roast/image` is *where the code string comes from* (JSON body vs. an uploaded image) — everything downstream of getting that string is identical, shared code.

**New concepts here:**
- `UploadFile = File(...)` — file uploads use `multipart/form-data`, not JSON, so FastAPI handles the parameter differently
- `await file.read()` — reading an uploaded file is async in FastAPI since it may be streamed from disk/network
- Real-world OCR imperfection was observed firsthand: a screenshot with a stray `python` label line and a misread `E` → `€` character still got correctly roasted and fixed by the LLM, which reasoned past the noise to find the actual logic bugs

---

## 14. Reuse Summary Table

| What's reused | `/roast` | `/roast/image` | `/roast/stream` |
|---|---|---|---|
| `get_groq_client` (via `Depends`) | ✅ | ✅ | — |
| `get_async_groq_client` (via `Depends`) | — | — | ✅ |
| `get_roast()` | ✅ | ✅ | — (uses `stream_roast()` instead) |
| `make_diff()` | ✅ | ✅ | — |
| `RoastResponse` schema | ✅ | ✅ | — (streams plain text instead) |

---

## 15. Where Things Stand

✅ Pydantic schemas (`RoastRequest`, `RoastResponse`, custom validator)
✅ `lifespan` for one-time client creation
✅ `Depends()` for dependency injection
✅ Measured, real comparison of `async def` vs plain `def`
✅ `StreamingResponse` + async generator for live text streaming
✅ `UploadFile` + OCR pipeline, reusing existing roast logic

**Stage 1 is complete.** Every Priority 1 FastAPI concept was built and personally tested end-to-end — including real debugging of package deprecations and provider outages, which is itself valuable, realistic experience.

**Next up: Stage 2** — `BackgroundTasks` for logging every roast, proper exception handling (including the OCR-garbage-input case observed firsthand), stricter input validation, and CORS for a frontend demo.
