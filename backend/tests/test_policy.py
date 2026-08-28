from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test():
    print("=== Testing Policy Routes ===")
    
    # 1. POST /policy
    payload = {
        "max_amount": 200000,
        "merchant_id": "merchant_001",
        "allowed_categories": ["books", "electronics"],
        "expires_at": "2027-12-31T23:59:59",
        "require_confirmation_above": 100000
    }
    
    print("\n1. Creating a new policy (POST /policy)...")
    resp = client.post("/policy", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    
    # 2. GET /policy/active
    print("\n2. Fetching the active policy (GET /policy/active)...")
    resp2 = client.get("/policy/active")
    print(f"Status: {resp2.status_code}")
    print(f"Response: {json.dumps(resp2.json(), indent=2)}")

if __name__ == "__main__":
    test()
