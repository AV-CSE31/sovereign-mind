import asyncio
import sys

import httpx


async def verify_fixes():
    base_url = "http://localhost:8000"
    print(f"Testing against {base_url}...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Verify compliance/verify (was crashing due to missing datetime)
        print("\n--- Verifying Compliance Integrity ---")
        try:
            resp = await client.get(f"{base_url}/v1/compliance/verify")
            if resp.status_code == 200:
                print(f"[PASS] Compliance Verify: {resp.json()}")
            else:
                print(f"[FAIL] Compliance Verify: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[ERROR] Compliance Verify: {e}")

        # 2. Verify Models (should only have 1)
        print("\n--- Verifying Model List ---")
        try:
            resp = await client.get(f"{base_url}/v1/models")
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                print(f"[PASS] Models found: {len(models)}")
                for m in models:
                    print(f"  - {m['id']}")
                if len(models) == 1:
                    print("[PASS] Only 1 model listed as requested.")
                else:
                    print("[WARN] More than 1 model listed.")
            else:
                print(f"[FAIL] Models: {resp.status_code}")
        except Exception as e:
            print(f"[ERROR] Models: {e}")

        # 3. Verify Document Ingestion (Text Mode)
        print("\n--- Verifying Ingestion (Text) ---")
        try:
            form_data = {
                "content": "This is a test document for verification.",
                "metadata": '{"source": "verification_script"}',
            }
            resp = await client.post(f"{base_url}/v1/system/ingest", data=form_data)
            if resp.status_code == 200:
                print(f"[PASS] Ingestion: {resp.json()}")
            else:
                print(f"[FAIL] Ingestion: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[ERROR] Ingestion: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_fixes())
