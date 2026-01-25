import requests

print("Testing v2 Endpoints:")
print("1. Shadow Scanner:", requests.get("http://localhost:8000/v1/system/shadow-scan").status_code)
print("2. Compliance Report:", requests.get("http://localhost:8000/v1/compliance/report").status_code)
print("3. Compliance Logs:", requests.get("http://localhost:8000/v1/compliance/logs").status_code)
print("4. Agent Run:", requests.post("http://localhost:8000/v1/agent/run", data={"query": "test"}).status_code)
