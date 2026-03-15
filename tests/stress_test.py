import asyncio
import statistics
import time
from typing import Any

import httpx
from tqdm.asyncio import tqdm

# --- Configuration ---
BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    {"name": "Chat", "url": f"{BASE_URL}/v1/chat/completions", "type": "json"},
    {"name": "Agent", "url": f"{BASE_URL}/v1/agent/run", "type": "form"},
]
TOTAL_QUERIES = 1000
CONCURRENCY_LIMIT = 5
TIMEOUT = 300.0  # 5 minutes for very long queues

# Sample queries
QUERIES = [
    "Tell me a short joke.",
    "What is 2+2?",
    "Hello!",
    "Who are you?",
    "Explain local-first AI in one sentence.",
]


async def fire_query(
    client: httpx.AsyncClient, endpoint: dict, query: str, semaphore: asyncio.Semaphore
) -> dict[str, Any]:
    async with semaphore:
        start_time = time.perf_counter()
        try:
            if endpoint["type"] == "json":
                payload = {
                    "model": "qwen2.5:0.5b",
                    "messages": [{"role": "user", "content": query}],
                    "config": {"mode": "local", "depth": "fast"},
                }
                response = await client.post(endpoint["url"], json=payload, timeout=TIMEOUT)
            else:
                # Agent endpoint uses Form data
                data = {"query": query}
                response = await client.post(endpoint["url"], data=data, timeout=TIMEOUT)

            latency = time.perf_counter() - start_time
            return {
                "success": response.status_code == 200,
                "latency": latency,
                "status": response.status_code,
                "endpoint": endpoint["name"],
            }
        except Exception as e:
            latency = time.perf_counter() - start_time
            return {
                "success": False,
                "latency": latency,
                "error": str(e),
                "endpoint": endpoint["name"],
            }


async def run_stress_test(count: int = TOTAL_QUERIES):
    avg_lat_estimate = 57.0  # Based on pilot test
    est_total_min = (count * avg_lat_estimate) / (CONCURRENCY_LIMIT * 60)

    print(f"\n🚀 Starting Massive Stress Test: {count} queries")
    print(f"⏱️  Estimated Total Time: {est_total_min:.1f} minutes")
    print(f"📡 Concurrency: {CONCURRENCY_LIMIT} | Targets: {[e['name'] for e in ENDPOINTS]}")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    results = []

    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(count):
            endpoint = ENDPOINTS[i % len(ENDPOINTS)]
            query = QUERIES[i % len(QUERIES)]
            tasks.append(fire_query(client, endpoint, query, semaphore))

        # Use tqdm for progress
        for f in tqdm.as_completed(tasks, total=count, desc="Processing Queries"):
            result = await f
            results.append(result)

    # --- Report Generation ---
    successes = [r for r in results if r["success"]]
    latencies = [r["latency"] for r in successes]

    print("\n" + "=" * 50)
    print("📈 STRESS TEST RESULTS")
    print("=" * 50)
    print(f"Total Queries:    {len(results)}")
    print(f"Successful:       {len(successes)} ({len(successes) / len(results) * 100:.1f}%)")
    print(f"Failed:           {len(results) - len(successes)}")

    if latencies:
        print(f"Avg Latency:      {statistics.mean(latencies):.2f}s")
        print(f"Min Latency:      {min(latencies):.2f}s")
        print(f"Max Latency:      {max(latencies):.2f}s")
        if len(latencies) > 1:
            print(f"P95 Latency:      {statistics.quantiles(latencies, n=20)[18]:.2f}s")
            print(f"P99 Latency:      {statistics.quantiles(latencies, n=100)[98]:.2f}s")

    # Endpoint breakdown
    for e_name in [e["name"] for e in ENDPOINTS]:
        e_res = [r for r in results if r["endpoint"] == e_name]
        e_succ = [r for r in e_res if r["success"]]
        print(f"\n[{e_name} Endpoint]")
        print(f"  Success Rate:   {len(e_succ)}/{len(e_res)}")
        if e_succ:
            print(f"  Avg Latency:    {statistics.mean([r['latency'] for r in e_succ]):.2f}s")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(run_stress_test())
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user.")
