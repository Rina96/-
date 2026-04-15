"""
Script to add companies with different CRM integrations.
Usage: python add_companies.py
"""
import asyncio
from database import AsyncSessionLocal
from crud import crud
from crm_factory import CRMFactory
from loguru import logger


async def add_company_interactive():
    """Interactive company setup wizard."""
    print("\n" + "="*60)
    print("🚀 MULTI-CRM COMPANY SETUP WIZARD")
    print("="*60)

    # Get company details
    company_name = input("\n📝 Company name (e.g., 'ShoolaGo', 'CompanyX'): ").strip()
    if not company_name:
        print("❌ Company name is required!")
        return

    # Show supported CRMs
    print("\n📊 Supported CRM Systems:")
    supported_crms = CRMFactory.get_supported_crms()
    for i, (crm_key, crm_name) in enumerate(supported_crms.items(), 1):
        print(f"  {i}. {crm_key.upper()}: {crm_name}")

    crm_choice = input("\n🔗 Select CRM type (amocrm/bitrix24/alfarc): ").strip().lower()

    if crm_choice not in CRMFactory.SUPPORTED_CRMS:
        print(f"❌ Unsupported CRM: {crm_choice}")
        return

    # Get CRM configuration
    print(f"\n🔐 Enter {crm_choice.upper()} credentials:")
    crm_config = get_crm_config(crm_choice)

    # Validate configuration
    is_valid, msg = CRMFactory.validate_config(crm_choice, crm_config)
    if not is_valid:
        print(f"❌ Configuration error: {msg}")
        return

    # Save to database
    async with AsyncSessionLocal() as db:
        company = await crud.create_company(db, company_name, crm_choice, crm_config)

        if company:
            print(f"\n✅ SUCCESS! Company added:")
            print(f"   ID: {company.id}")
            print(f"   Name: {company.name}")
            print(f"   CRM: {company.crm_type}")
            print(f"   Status: {'Active' if company.is_active else 'Inactive'}")

            # Test connection
            print(f"\n🧪 Testing CRM connection...")
            adapter = await CRMFactory.create_adapter(crm_choice, crm_config)
            if adapter:
                print(f"✅ CRM connection successful!")
            else:
                print(f"⚠️ CRM connection test failed - check credentials")
        else:
            print(f"\n❌ Failed to create company")


def get_crm_config(crm_type: str) -> dict:
    """Get CRM-specific configuration from user input."""
    config = {}

    if crm_type == "amocrm":
        config["domain"] = input("  Domain (e.g., mycompany.amocrm.ru): ").strip()
        config["client_id"] = input("  Client ID: ").strip()
        config["client_secret"] = input("  Client Secret: ").strip()
        config["redirect_uri"] = input("  Redirect URI (e.g., https://example.com/callback): ").strip()
        config["refresh_token"] = input("  Refresh Token: ").strip()

    elif crm_type == "bitrix24":
        webhook_url = input("  Webhook URL (leave empty to use credentials): ").strip()
        if webhook_url:
            config["webhook_url"] = webhook_url
        else:
            config["domain"] = input("  Domain (e.g., mycompany.bitrix24.com): ").strip()
            config["access_token"] = input("  Access Token: ").strip()

    elif crm_type in ("alfarc", "alfacrm"):
        config["base_url"] = input("  Base URL (e.g., https://shkolago.s20.online): ").strip()
        config["email"] = input("  Email: ").strip()
        config["api_key"] = input("  API Key: ").strip()
        config["app_key"] = input("  App Key: ").strip()

    return config


async def list_companies():
    """List all companies in the database."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy.future import select
        from models import Company

        result = await db.execute(select(Company))
        companies = result.scalars().all()

        if not companies:
            print("\n📭 No companies found")
            return

        print("\n" + "="*60)
        print("📋 COMPANIES")
        print("="*60)
        for company in companies:
            print(f"\nID: {company.id}")
            print(f"  Name: {company.name}")
            print(f"  CRM: {company.crm_type.upper()}")
            print(f"  Status: {'✅ Active' if company.is_active else '❌ Inactive'}")
            print(f"  Created: {company.created_at}")


async def main():
    """Main menu."""
    while True:
        print("\n" + "="*60)
        print("💼 COMPANY MANAGEMENT MENU")
        print("="*60)
        print("1. Add new company")
        print("2. List all companies")
        print("3. Exit")

        choice = input("\nSelect option (1-3): ").strip()

        if choice == "1":
            await add_company_interactive()
        elif choice == "2":
            await list_companies()
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    asyncio.run(main())
