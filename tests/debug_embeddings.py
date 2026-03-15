import asyncio
import json
import sys

import httpx


async def test_embeddings():
    url = "http://localhost:8080/v1/embeddings"
    payload = {"input": "The food was delicious", "model": "TinyLlama-1.1B-Chat-v1.0.Q5_K_M"}

    print(f"Testing Embedding Endpoint: {url}")
    print(f"Payload: {json.dumps(payload)}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": "Bearer no-key", "Content-Type": "application/json"},
            )

            print(f"Status Code: {resp.status_code}")
            print(f"Response Headers: {resp.headers}")
            print(f"Response Body: {resp.text}")

            if resp.status_code == 200:
                data = resp.json()
                emb = data.get("data", [{}])[0].get("embedding")
                if emb:
                    print(f"[PASS] Got embedding of length {len(emb)}")
                else:
                    print("[FAIL] No embedding in response data")
            else:
                print("[FAIL] Endpoint returned non-200")

    except Exception as e:
        print(f"[CRITICAL ERROR] Connection failed: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_embeddings())
