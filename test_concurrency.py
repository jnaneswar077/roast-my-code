import time
import requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://127.0.0.1:8000"


def call_endpoint(endpoint: str, label: str):
    start = time.perf_counter()
    response = requests.post(f"{BASE_URL}/{endpoint}", json={"code": "x", "language": "python"})
    elapsed = time.perf_counter() - start
    print(f"[{label}] status={response.status_code} took={elapsed:.2f}s")


def run_test(endpoint: str):
    print(f"\n--- Testing /{endpoint} (firing 2 requests at once) ---")
    overall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(call_endpoint, endpoint, "Request A")
        executor.submit(call_endpoint, endpoint, "Request B")

    overall_elapsed = time.perf_counter() - overall_start
    print(f"Total wall-clock time: {overall_elapsed:.2f}s")


if __name__ == "__main__":
    run_test("roast-slow-async")   # expect ~10s total (serialized)
    run_test("roast-slow-sync")    # expect ~5s total (parallel via threadpool)