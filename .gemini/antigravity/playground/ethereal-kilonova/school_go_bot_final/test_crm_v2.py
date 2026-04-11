import asyncio
import httpx
import json
from integrations import alfa_crm
from config import settings

async def diagnose_crm():
    print(f"🔍 Testing AlfaCRM connection to {settings.ALFA_BASE_URL}...")
    
    # 1. Test Login
    login_success = await alfa_crm._login()
    if not login_success:
        print("❌ Login failed. Check ALFA_EMAIL and ALFA_API_KEY.")
        return
    print("✅ Login successful.")

    # 2. Test Sync with the failing number
    test_phone = "77022255888" # The number that failed in the logs
    print(f"🧪 Testing lookup and creation for {test_phone}...")
    
    # Perform the same logic as sync_customer but with print statements
    existing = await alfa_crm.get_customer_by_phone(test_phone)
    if existing:
        print(f"✅ Found existing customer: ID={existing.get('id')}")
    else:
        print("ℹ️ No customer found. Attempting creation...")
        headers = await alfa_crm.get_headers()
        url = f"{alfa_crm.base_url}/{alfa_crm.BRANCH_ID}/customer/create"
        payload = {
            "name": "Julia Test Lead",
            "is_lead": 1,
            "phone": [test_phone],
            "lead_status_id": 1,
            "branch_ids": [1],
            "is_study": 0,
            "legal_type": 1
        }
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(url, headers=headers, json=payload, timeout=5.0)
            print(f"➕ Response Status: {r.status_code}")
            print(f"➕ Response Text: {r.text}")

if __name__ == "__main__":
    asyncio.run(diagnose_crm())
