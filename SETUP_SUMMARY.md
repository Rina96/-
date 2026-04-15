# 🎯 Multi-CRM Platform Setup Summary

## ✅ What's Been Created

### 1️⃣ Core CRM Infrastructure
| File | Purpose |
|------|---------|
| `crm_base.py` | Abstract base class for all CRM adapters |
| `crm_amocrm.py` | AmoCRM integration adapter |
| `crm_bitrix24.py` | Bitrix24 integration adapter |
| `crm_factory.py` | Factory to instantiate correct CRM adapter |

### 2️⃣ Company Management
| File | Purpose |
|------|---------|
| `models.py` | Updated with Company model and ChatSession.company_id |
| `crud.py` | Company CRUD operations + session management |
| `add_companies.py` | Interactive wizard to add companies |

### 3️⃣ Documentation & Examples
| File | Purpose |
|------|---------|
| `MULTI_CRM_SETUP.md` | Complete setup and integration guide |
| `main_multi_company_example.py` | Example of multi-company message processing |

### 4️⃣ Updated Files
- `integrations.py` — AlfaCrmManager now inherits from BaseCRMAdapter
- `models.py` — Added Company model and company_id FK in ChatSession

---

## 🚀 Quick Start (3 Steps)

### Step 1: Add Your Companies

```bash
python add_companies.py
```

Follow the interactive wizard to add:
- **Company 1** — Name + CRM Type + Credentials
- **Company 2** — Name + CRM Type + Credentials

### Step 2: Verify Database

```bash
# Check companies were created
from database import AsyncSessionLocal
from models import Company
from sqlalchemy.future import select
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company))
        companies = result.scalars().all()
        for c in companies:
            print(f"{c.id}. {c.name} ({c.crm_type})")

asyncio.run(check())
```

### Step 3: Use in Your Code

```python
from crm_factory import CRMFactory

# Get adapter for a company
crm_adapter = await CRMFactory.create_adapter(
    crm_type="amocrm",  # or "bitrix24", "alfarc"
    config={...}  # CRM credentials
)

# Use standard interface
lead = await crm_adapter.get_lead_by_phone("+1234567890")
await crm_adapter.update_lead(lead.id, {"name": "New Name"})
```

---

## 📋 Supported CRM Systems

### AmoCRM
- **Ideal for:** Sales teams, complex sales funnels
- **Setup time:** 10-15 min
- **Region:** Global

```python
{
    "domain": "company.amocrm.ru",
    "client_id": "xxx",
    "client_secret": "xxx",
    "redirect_uri": "https://example.com/callback",
    "refresh_token": "xxx"
}
```

### Bitrix24
- **Ideal for:** All-in-one CRM + communications
- **Setup time:** 5 min
- **Region:** Global

```python
{
    "webhook_url": "https://company.bitrix24.com/rest/1/webhookid/"
}
```

### AlfaCRM
- **Ideal for:** Educational institutions, sales funnels
- **Setup time:** 2 min
- **Region:** Kazakhstan, Russia

```python
{
    "base_url": "https://company.s20.online",
    "email": "user@example.com",
    "api_key": "xxx",
    "app_key": "xxx"
}
```

---

## 🔄 Message Flow (Multi-Company)

```
WhatsApp Message
       ↓
   [webhook: /webhook/whatsapp]
       ↓
   Extract: chat_id, text, company_id
       ↓
   [CRM Factory] ← Select adapter based on company_id
       ↓
   ┌─────────────────────────────┐
   │   Get lead from CRM         │
   │   (AmoCRM/Bitrix/AlfaCRM)   │
   │                             │
   ├─────────────────────────────┤
   │   Generate AI response      │
   │   (OpenAI/Gemini)           │
   │                             │
   ├─────────────────────────────┤
   │   Update CRM (set status)   │
   │   Add comments              │
   │                             │
   ├─────────────────────────────┤
   │   Send to WhatsApp          │
   │   Save to database          │
   └─────────────────────────────┘
       ↓
   ✅ Complete
```

---

## 💡 Common Use Cases

### Use Case 1: Two Companies, Different CRMs
```python
# Company A uses AmoCRM
company_a_config = {...amocrm...}

# Company B uses Bitrix24
company_b_config = {...bitrix24...}

# Route messages to correct CRM
if company_id == 1:
    crm_adapter = AmoCRMAdapter(company_a_config)
else:
    crm_adapter = Bitrix24Adapter(company_b_config)
```

### Use Case 2: Migrate Existing System
```python
# Old: Single company with AlfaCRM
# New: Multiple companies, flexible CRM

# Create "Default" company with same AlfaCRM config
company = Company(
    name="Default",
    crm_type="alfarc",
    crm_config={...existing_alfarc_config...}
)
db.add(company)
await db.commit()

# All existing sessions now linked to company.id = 1
```

### Use Case 3: Add New Company Later
```python
# Easy to add more companies at any time
python add_companies.py  # Just run again!

# Or programmatically:
new_company = await crud.create_company(
    db, "NewCompany", "bitrix24", {...config...}
)
```

---

## 🧪 Testing Your Setup

### 1. Test CRM Connection
```bash
# In Python shell:
from crm_factory import CRMFactory

config = {
    "webhook_url": "https://company.bitrix24.com/rest/1/webhookid/"
}
adapter = await CRMFactory.create_adapter("bitrix24", config)

if adapter:
    print("✅ Connected!")
else:
    print("❌ Connection failed")
```

### 2. Test Lead Lookup
```python
lead = await adapter.get_lead_by_phone("+1234567890")
print(f"Found: {lead.name if lead else 'Not found'}")
```

### 3. Test Lead Update
```python
success = await adapter.update_lead("lead_id", {
    "name": "Test Update"
})
print(f"Update: {'Success' if success else 'Failed'}")
```

### 4. Test Health Endpoint
```bash
curl http://localhost:8000/health
```

Output shows all companies and CRM connection status.

---

## ⚠️ Migration from Single-Company

If you're upgrading from the single-company system:

### Database Migration
```python
# Run migration to add company_id and foreign keys
# Models already updated, just run:

async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

### Code Changes
**Before (single company):**
```python
async with AsyncSessionLocal() as db:
    session = await crud.get_or_create_session(db, chat_id)
    # ... uses AlfaCRM hardcoded
```

**After (multi-company):**
```python
async with AsyncSessionLocal() as db:
    session = await crud.get_or_create_session(db, chat_id, company_id=1)
    # ... uses company_id to select CRM
```

**Or use the provided example:**
```bash
# Copy multi-company logic from:
cp main_multi_company_example.py main.py  # After reviewing!
```

---

## 📞 Support

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `pip install -r requirements.txt` |
| "Authentication failed" | Check CRM credentials in config |
| "Lead not found" | Verify phone format, check CRM database |
| "Company not found" | Run `python add_companies.py` first |

---

## 📚 Documentation

- **Full Setup Guide:** `MULTI_CRM_SETUP.md`
- **Code Example:** `main_multi_company_example.py`
- **Interactive Setup:** `python add_companies.py`
- **Factory Pattern:** `crm_factory.py` (see `CRMFactory.create_adapter()`)

---

## ✨ Features Included

✅ Support for 3 major CRM systems (AmoCRM, Bitrix24, AlfaCRM)  
✅ Easy expansion to other CRMs  
✅ Unified interface (BaseCRMAdapter)  
✅ Company management with CRUD operations  
✅ Interactive setup wizard  
✅ Connection health checks  
✅ Token/auth caching  
✅ Error handling & logging  
✅ Full database integration  

---

## 🎯 Next Steps

1. **Add your 2 companies:**
   ```bash
   python add_companies.py
   ```

2. **Verify in database:**
   ```bash
   # Check companies are created
   ```

3. **Test CRM connections:**
   ```bash
   # Use test script from TESTING.md
   ```

4. **Update main.py** with multi-company logic (see example)

5. **Deploy and monitor:**
   ```bash
   curl http://localhost:8000/health  # Check all companies
   ```

---

## 🚀 You're Ready!

The platform now supports multiple companies with different CRM systems. Start by running `add_companies.py` and follow the interactive guide!

**Questions?** Check `MULTI_CRM_SETUP.md` for detailed documentation.
