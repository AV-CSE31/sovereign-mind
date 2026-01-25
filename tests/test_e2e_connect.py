
import asyncio
import httpx
import sys

async def test_backend_connectivity():
    print("Testing Backend Connectivity...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Health Check (Docs)
            resp = await client.get("http://localhost:8000/docs", timeout=5.0)
            if resp.status_code == 200:
                print("[OK] Backend Swagger UI is reachable.")
            else:
                print(f"[FAIL] Backend returned status {resp.status_code}")
                
            # 2. Compliance Report (Public Endpoint)
            resp = await client.get("http://localhost:8000/v1/compliance/report", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                print(f"[OK] Compliance API is reachable. Total actions: {data.get('summary', {}).get('total_actions')}")
            else:
                 print(f"[FAIL] Compliance API returned status {resp.status_code}")

        except httpx.ConnectError:
            print("[FAIL] Could not connect to localhost:8000. Is the backend running?")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_backend_connectivity())
