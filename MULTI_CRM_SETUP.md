# 🌐 Multi-CRM Integration Guide

This guide explains how to add multiple companies with different CRM integrations (AmoCRM, Bitrix24, AlfaCRM) to the WhatsApp AI Agent platform.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│   WhatsApp AI Agent Platform (Julia)    │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐  │
│  │   Company Management            │  │
│  │  (Models: Company, ChatSession) │  │
│  └──────────────┬──────────────────┘  │
│                 │                      │
│  ┌──────────────▼──────────────────┐  │
│  │  CRM Factory                     │  │
│  │  (Route to correct adapter)      │  │
│  └──────────────┬──────────────────┘  │
│                 │                      │
│     ┌───────────┼───────────┐          │
│     │           │           │          │
│  ┌──▼──┐  ┌──────▼──┐  ┌───▼───┐     │
│  │ Amo │  │ Bitrix  │  │ Alfa  │     │
│  │ CRM │  │   24    │  │  CRM  │     │
│  └─────┘  └─────────┘  └───────┘     │
│                                       │
└───────────────────────────────────────┘
```

## 📁 New Files Created

### Core CRM Infrastructure
- **`crm_base.py`** — Abstract base class for all CRM adapters
- **`crm_amocrm.py`** — AmoCRM adapter implementation
- **`crm_bitrix24.py`** — Bitrix24 adapter implementation
- **`crm_factory.py`** — Factory pattern to instantiate correct CRM adapter
- **`add_companies.py`** — Interactive wizard to add companies

### Updated Files
- **`models.py`** — Added Company model, updated ChatSession with company_id
- **`crud.py`** — Added company management functions
- **`integrations.py`** — Updated AlfaCrmManager to inherit from BaseCRMAdapter

## 🚀 Quick Start: Adding Companies

### Option 1: Interactive Setup (Recommended)

```bash
python add_companies.py
```

This launches an interactive wizard:
1. Enter company name
2. Select CRM type (amocrm, bitrix24, alfarc)
3. Enter CRM credentials
4. Test connection

### Option 2: Programmatic Setup

```python
import asyncio
from database import AsyncSessionLocal
from crud import crud
from crm_factory import CRMFactory

async def setup():
    # Define configuration for Company 1 (AmoCRM)
    company1_config = {
        "domain": "mycompany.amocrm.ru",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "redirect_uri": "https://example.com/callback",
        "refresh_token": "your_refresh_token"
    }

    # Define configuration for Company 2 (Bitrix24)
    company2_config = {
        "webhook_url": "https://mycompany.bitrix24.com/rest/1/webhookid/"
    }

    async with AsyncSessionLocal() as db:
        # Create Company 1
        company1 = await crud.create_company(
            db,
            name="CompanyA",
            crm_type="amocrm",
            crm_config=company1_config
        )

        # Create Company 2
        company2 = await crud.create_company(
            db,
            name="CompanyB",
            crm_type="bitrix24",
            crm_config=company2_config
        )

        print(f"Created: {company1.name} (ID: {company1.id})")
        print(f"Created: {company2.name} (ID: {company2.id})")

asyncio.run(setup())
```

## 🔐 CRM Credentials Guide

### AmoCRM Configuration

Get credentials from https://www.amocrm.ru/

```python
{
    "domain": "mycompany.amocrm.ru",          # Your subdomain
    "client_id": "xxxx",                      # OAuth Client ID
    "client_secret": "xxxx",                  # OAuth Client Secret
    "redirect_uri": "https://example.com",    # OAuth Redirect URI
    "refresh_token": "xxxx"                   # OAuth Refresh Token
}
```

**Steps to get credentials:**
1. Go to https://www.amocrm.ru/developers/
2. Create an app/integration
3. Get Client ID and Secret
4. Get a refresh token using OAuth flow

### Bitrix24 Configuration

Get webhook from https://www.bitrix24.com/

**Option A: Webhook URL (Recommended)**
```python
{
    "webhook_url": "https://mycompany.bitrix24.com/rest/1/abc123def456/"
}
```

**Option B: API Credentials**
```python
{
    "domain": "mycompany.bitrix24.com",
    "access_token": "xxxx"
}
```

**Steps to get webhook:**
1. Go to Settings → Integrations → Webhooks
2. Create new webhook with required scopes
3. Copy the webhook URL

### AlfaCRM Configuration

Get credentials from https://www.s20.online/

```python
{
    "base_url": "https://shkolago.s20.online",  # Your AlfaCRM domain
    "email": "user@example.com",                # Account email
    "api_key": "xxxx-xxxx-xxxx-xxxx",          # API Key
    "app_key": "xxxx"                           # App Key
}
```

**Steps to get credentials:**
1. Go to Settings → API
2. Create API key
3. Copy API Key and App Key

## 💻 Using Multiple CRMs in Code

Once companies are set up, route requests to the correct CRM:

```python
from crm_factory import CRMFactory
from database import AsyncSessionLocal
from crud import crud

async def handle_incoming_message(chat_id: str, company_id: int, text: str):
    """Process message for specific company."""

    async with AsyncSessionLocal() as db:
        # Get company
        company = await crud.get_company(db, company_id)
        if not company:
            print(f"Company {company_id} not found")
            return

        # Create appropriate CRM adapter
        crm_adapter = await CRMFactory.create_adapter(
            company.crm_type,
            company.crm_config
        )

        if not crm_adapter:
            print(f"Failed to initialize CRM for {company.name}")
            return

        # Use the adapter
        lead = await crm_adapter.get_lead_by_phone(chat_id)
        if lead:
            print(f"Lead found in {company.crm_type}: {lead.name}")
            await crm_adapter.update_lead(lead.id, {"name": "Updated Name"})

        # Get chat session for this company
        session = await crud.get_or_create_session(db, chat_id, company.id)
        print(f"Session: {session.whatsapp_chat_id} (Company: {company.name})")
```

## 📊 Standard CRM Interface

All CRM adapters implement `BaseCRMAdapter` with these methods:

```python
async def authenticate() -> bool
    """Authenticate with CRM API."""

async def get_lead_by_phone(phone: str) -> Optional[CRMLead]
    """Get lead by phone number."""

async def create_lead(name: str, phone: str, email: Optional[str] = None) -> Optional[str]
    """Create new lead."""

async def update_lead(lead_id: str, updates: Dict[str, Any]) -> bool
    """Update existing lead."""

async def get_lead_status(lead_id: str) -> Optional[str]
    """Get lead status."""

async def set_lead_status(lead_id: str, status: str) -> bool
    """Update lead status."""

async def get_next_available_slots(service_type: str = None) -> Dict[str, str]
    """Get available booking slots."""
```

## 🧪 Testing CRM Connections

```python
from crm_factory import CRMFactory

async def test_crm(crm_type: str, config: dict):
    """Test CRM connection."""
    adapter = await CRMFactory.create_adapter(crm_type, config)
    
    if adapter:
        print(f"✅ {crm_type} connected successfully")
        
        # Test operations
        lead = await adapter.get_lead_by_phone("+1234567890")
        if lead:
            print(f"Found lead: {lead.name}")
    else:
        print(f"❌ Failed to connect to {crm_type}")
```

## 🔄 Extending with New CRMs

To add support for a new CRM (e.g., Zoho CRM):

1. **Create adapter file** (`crm_zoho.py`):
```python
from crm_base import BaseCRMAdapter, CRMLead

class ZohoCRMAdapter(BaseCRMAdapter):
    async def authenticate(self) -> bool:
        # Implementation
        pass
    
    async def get_lead_by_phone(self, phone: str) -> Optional[CRMLead]:
        # Implementation
        pass
    
    # ... implement other abstract methods
```

2. **Register in factory** (`crm_factory.py`):
```python
from crm_zoho import ZohoCRMAdapter

SUPPORTED_CRMS = {
    # ... existing
    "zoho": ZohoCRMAdapter,
}
```

3. **Add validation**:
```python
elif crm_type == "zoho":
    required_fields = ["org_id", "api_key"]
    # ... validation logic
```

## 📝 Database Schema

### Companies Table
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    crm_type VARCHAR NOT NULL,
    crm_config JSON,
    whatsapp_api_id VARCHAR,
    whatsapp_api_token VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    updated_at DATETIME
);
```

### ChatSessions Table
```sql
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY,
    company_id INTEGER FOREIGN KEY,
    whatsapp_chat_id VARCHAR UNIQUE,
    history_json JSON,
    -- ... other fields
);
```

## 🐛 Troubleshooting

### Authentication Failed
- ❌ Check credentials are correct
- ❌ Verify API keys haven't expired
- ❌ Check network connectivity

### Lead Not Found
- ❌ Verify phone number format
- ❌ Check if lead exists in target CRM
- ❌ Verify CRM has permission to search

### Connection Timeout
- ❌ Check CRM API status
- ❌ Verify webhook URL is correct
- ❌ Check firewall/proxy settings

## 📚 References

- [AmoCRM API Docs](https://www.amocrm.ru/developers/content/crm_platform/)
- [Bitrix24 REST API](https://dev.bitrix24.com/rest-api/)
- [AlfaCRM API Docs](https://www.s20.online/docs/)

## 🎯 Next Steps

1. Run `python add_companies.py` to add your companies
2. Test CRM connections in production
3. Update `main.py` to route messages by company_id
4. Monitor CRM sync logs in production

---

**Questions?** Check the CRM-specific documentation or contact support.
