#!/usr/bin/env python3
"""
Multi-CRM Setup Verification Script
Checks if all components are properly configured.
"""

import asyncio
import sys
from loguru import logger

logger.remove()  # Remove default handler
logger.add(sys.stdout, format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")


async def verify_imports():
    """Verify all required modules can be imported."""
    print("\n" + "="*60)
    print("✅ CHECKING IMPORTS")
    print("="*60)

    modules_to_check = [
        ("sqlalchemy", "Database ORM"),
        ("httpx", "HTTP Client"),
        ("fastapi", "Web Framework"),
        ("loguru", "Logging"),
        ("pydantic_settings", "Settings Management"),
    ]

    all_ok = True
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            print(f"✅ {module_name:20} → {description}")
        except ImportError as e:
            print(f"❌ {module_name:20} → MISSING: {e}")
            all_ok = False

    # Check custom modules
    custom_modules = [
        ("crm_base", "CRM Base Adapter"),
        ("crm_amocrm", "AmoCRM Adapter"),
        ("crm_bitrix24", "Bitrix24 Adapter"),
        ("crm_factory", "CRM Factory"),
        ("models", "Database Models"),
        ("crud", "CRUD Operations"),
        ("database", "Database Connection"),
    ]

    for module_name, description in custom_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name:20} → {description}")
        except ImportError as e:
            print(f"❌ {module_name:20} → NOT FOUND: {e}")
            all_ok = False

    return all_ok


async def verify_database():
    """Verify database connection and schema."""
    print("\n" + "="*60)
    print("✅ CHECKING DATABASE")
    print("="*60)

    try:
        from database import AsyncSessionLocal, engine
        from models import Company, ChatSession

        # Test connection
        async with AsyncSessionLocal() as db:
            print(f"✅ Database connection successful")

            # Check tables exist
            from sqlalchemy import inspect
            from sqlalchemy.pool import NullPool

            inspector = inspect(engine)
            tables = inspector.get_table_names()

            required_tables = ["companies", "chat_sessions"]
            for table in required_tables:
                if table in tables:
                    print(f"✅ Table '{table}' exists")
                else:
                    print(f"⚠️  Table '{table}' missing (run: python add_companies.py)")

        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


async def verify_crm_adapters():
    """Verify all CRM adapters are available."""
    print("\n" + "="*60)
    print("✅ CHECKING CRM ADAPTERS")
    print("="*60)

    try:
        from crm_factory import CRMFactory

        supported = CRMFactory.get_supported_crms()
        print(f"✅ {len(supported)} CRM systems supported:\n")

        for crm_type, description in supported.items():
            print(f"   • {crm_type.upper():15} - {description}")

        return True

    except Exception as e:
        print(f"❌ CRM adapter error: {e}")
        return False


async def verify_companies():
    """Check if any companies are configured."""
    print("\n" + "="*60)
    print("✅ CHECKING CONFIGURED COMPANIES")
    print("="*60)

    try:
        from database import AsyncSessionLocal
        from models import Company
        from sqlalchemy.future import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Company))
            companies = result.scalars().all()

            if not companies:
                print("⚠️  No companies configured")
                print("   Run: python add_companies.py")
                print("   To add your first company\n")
                return False

            print(f"✅ Found {len(companies)} company/companies:\n")
            for company in companies:
                status = "✅ Active" if company.is_active else "❌ Inactive"
                print(f"   {company.id}. {company.name:20} | {company.crm_type:10} | {status}")
                print(f"      Created: {company.created_at}")

            return True

    except Exception as e:
        print(f"⚠️  Cannot list companies: {e}")
        return False


async def verify_config():
    """Check if configuration is complete."""
    print("\n" + "="*60)
    print("✅ CHECKING CONFIGURATION")
    print("="*60)

    try:
        from config import settings

        config_items = {
            "App": [
                ("APP_NAME", settings.APP_NAME),
                ("DEBUG", settings.DEBUG),
            ],
            "Database": [
                ("DATABASE_URL", "***" if settings.DATABASE_URL else "NOT SET"),
            ],
            "AI Engine": [
                ("OPENAI_API_KEY", "✅ SET" if settings.OPENAI_API_KEY else "❌ NOT SET"),
                ("GEMINI_API_KEY", "✅ SET" if settings.GEMINI_API_KEY else "❌ NOT SET"),
            ],
            "WhatsApp (Green API)": [
                ("GREEN_API_ID_INSTANCE", "✅ SET" if settings.GREEN_API_ID_INSTANCE else "❌ NOT SET"),
                ("GREEN_API_API_TOKEN_INSTANCE", "✅ SET" if settings.GREEN_API_API_TOKEN_INSTANCE else "❌ NOT SET"),
            ],
        }

        all_ok = True
        for section, items in config_items.items():
            print(f"\n{section}:")
            for key, value in items:
                if value.startswith("✅"):
                    print(f"  ✅ {key:30} {value}")
                elif value.startswith("❌"):
                    print(f"  ❌ {key:30} {value}")
                    all_ok = False
                else:
                    print(f"  ℹ️  {key:30} {value}")

        return all_ok

    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


async def test_crm_connection(company_id: int = 1):
    """Test actual CRM connection for a company."""
    print("\n" + "="*60)
    print("✅ TESTING CRM CONNECTION")
    print("="*60)

    try:
        from database import AsyncSessionLocal
        from crud import crud
        from crm_factory import CRMFactory

        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                print(f"⚠️  Company {company_id} not found")
                return False

            print(f"\nTesting {company.name} ({company.crm_type.upper()})...")

            adapter = await CRMFactory.create_adapter(company.crm_type, company.crm_config)

            if adapter:
                print(f"✅ CRM connection successful!")
                return True
            else:
                print(f"❌ CRM connection failed")
                print(f"   Check credentials in database for company {company_id}")
                return False

    except Exception as e:
        print(f"⚠️  Connection test error: {e}")
        return False


async def main():
    """Run all verification checks."""
    print("\n" + "🔍 MULTI-CRM PLATFORM VERIFICATION")
    print("="*60)

    results = {}

    # Run all checks
    results["imports"] = await verify_imports()
    results["database"] = await verify_database()
    results["crm_adapters"] = await verify_crm_adapters()
    results["companies"] = await verify_companies()
    results["config"] = await verify_config()

    # Test CRM connection if company exists
    if results["companies"]:
        results["crm_connection"] = await test_crm_connection(1)

    # Final summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)

    for check, status in results.items():
        status_icon = "✅" if status else "⚠️"
        status_text = "PASS" if status else "INCOMPLETE"
        print(f"{status_icon} {check.replace('_', ' ').title():20} {status_text}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nYour multi-CRM platform is ready to use!")
        print("\nNext steps:")
        print("  1. Run: python add_companies.py")
        print("  2. Add your 2 companies")
        print("  3. Update main.py with multi-company logic")
        print("  4. Deploy and monitor!")
    else:
        print("⚠️  SOME CHECKS INCOMPLETE")
        print("\nTo complete setup:")
        print("  1. Ensure all dependencies are installed")
        print("  2. Configure .env with API credentials")
        print("  3. Run database migration (create_all)")
        print("  4. Add companies: python add_companies.py")
        print("\nFor detailed help, see: SETUP_SUMMARY.md")

    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    try:
        all_passed = asyncio.run(main())
        sys.exit(0 if all_passed else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Verification cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
