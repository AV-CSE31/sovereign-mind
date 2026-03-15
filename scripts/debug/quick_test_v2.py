"""Quick test script for v2 endpoints"""

import requests

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("Testing Sovereign-Mind v2 Endpoints")
print("=" * 60)

# Test 1: Shadow AI Scanner
print("\n1. Testing Shadow AI Scanner...")
try:
    response = requests.get(f"{BASE_URL}/v1/system/shadow-scan", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Total risks: {data['total_risks']}")
        print(f"   [OK] Last scan: {data['last_scan']}")
    else:
        print(f"   [FAIL] Error: {response.text}")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")

# Test 2: Compliance Report
print("\n2. Testing Compliance Report...")
try:
    response = requests.get(f"{BASE_URL}/v1/compliance/report", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Total actions: {data['summary']['total_actions']}")
        print(f"   [OK] High risk: {data['summary']['high_risk_actions']}")
    else:
        print(f"   [FAIL] Error: {response.text}")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")

# Test 3: Compliance Logs
print("\n3. Testing Compliance Logs...")
try:
    response = requests.get(f"{BASE_URL}/v1/compliance/logs?limit=5", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Total actions: {data['total']}")
    else:
        print(f"   [FAIL] Error: {response.text}")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")

# Test 4: Agent Run
print("\n4. Testing Agent Execution...")
try:
    response = requests.post(
        f"{BASE_URL}/v1/agent/run", data={"query": "What is encryption?"}, timeout=60
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Success: {data['success']}")
        print(f"   [OK] Intent: {data['intent']}")
        print(f"   [OK] Run ID: {data['run_id'][:16]}...")
        print(f"   [OK] Compliance: {data['compliance_passed']}")
        print(f"   [OK] Audit trail steps: {len(data['audit_trail'])}")
    else:
        print(f"   [FAIL] Error: {response.text}")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")

print("\n" + "=" * 60)
print("Test Summary Complete")
print("=" * 60)
