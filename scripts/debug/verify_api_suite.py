import requests

BASE_URL = "http://localhost:8000"


def log(msg, status="INFO"):
    print(f"[{status}] {msg}")


def check_endpoint(method, path, data=None):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, data=data)  # Form data for agent run

        if response.status_code == 200:
            log(f"{method} {path} - OK ({response.elapsed.total_seconds():.2f}s)", "PASS")
            return response.json()
        else:
            log(f"{method} {path} - FAILED ({response.status_code})", "FAIL")
            print(response.text[:200])
            return None
    except Exception as e:
        log(f"{method} {path} - ERROR: {e!s}", "FAIL")
        return None


def main():
    log("Starting API Verification Suite...")

    # 1. System Health
    health = check_endpoint("GET", "/v1/system/health")
    if health:
        print(f"   v{health.get('version')} | Status: {health.get('status')}")

    # 2. Models
    check_endpoint("GET", "/v1/models")

    # 3. Collection Stats
    check_endpoint("GET", "/v1/system/collection")

    # 4. Memory (Mem0)
    check_endpoint("GET", "/v1/system/memory/default_user")

    # 5. Traces
    check_endpoint("GET", "/v1/system/traces")

    # 6. Compliance Report
    check_endpoint("GET", "/v1/compliance/report")

    # 7. Agent Run (Dry Run / Test Query)
    # We send a simple query that should hopefully be quick or fail gracefully
    log("Testing Agent Execution (this may take time)...")
    agent_res = check_endpoint(
        "POST",
        "/v1/agent/run",
        data={"query": "Hello, are you online?", "session_id": "test_verification"},
    )

    if agent_res:
        print("   Agent Answer:", agent_res.get("answer"))

    log("Verification Complete.")


if __name__ == "__main__":
    main()
