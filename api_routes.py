"""
FastAPI routes for multi-company CRM management.
Integrate these endpoints into your main.py application.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from database import AsyncSessionLocal
from crud import crud
from crm_factory import CRMFactory
from models import Company, ChatSession
from loguru import logger
from typing import Optional, List
import datetime

router = APIRouter(prefix="/api", tags=["companies"])


# ============================================
# COMPANY MANAGEMENT ENDPOINTS
# ============================================

@router.get("/companies")
async def get_companies(
    active_only: bool = False,
    crm_type: Optional[str] = None
):
    """Get all companies with optional filters."""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Company)

            if active_only:
                query = query.where(Company.is_active == True)

            if crm_type:
                query = query.where(Company.crm_type == crm_type.lower())

            result = await db.execute(query)
            companies = result.scalars().all()

            return {
                "companies": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "crm_type": c.crm_type,
                        "is_active": c.is_active,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                    }
                    for c in companies
                ],
                "total": len(companies)
            }
    except Exception as e:
        logger.error(f"❌ Error fetching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}")
async def get_company(company_id: int):
    """Get company by ID."""
    try:
        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            return {
                "id": company.id,
                "name": company.name,
                "crm_type": company.crm_type,
                "crm_config": company.crm_config,
                "whatsapp_api_id": company.whatsapp_api_id,
                "is_active": company.is_active,
                "created_at": company.created_at.isoformat() if company.created_at else None,
                "updated_at": company.updated_at.isoformat() if company.updated_at else None,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companies")
async def create_company(name: str, crm_type: str, crm_config: dict):
    """Create a new company."""
    try:
        # Validate CRM type
        is_valid, msg = CRMFactory.validate_config(crm_type, crm_config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=msg)

        async with AsyncSessionLocal() as db:
            company = await crud.create_company(db, name, crm_type, crm_config)

            if not company:
                raise HTTPException(status_code=500, detail="Failed to create company")

            return {
                "id": company.id,
                "name": company.name,
                "crm_type": company.crm_type,
                "is_active": company.is_active,
                "created_at": company.created_at.isoformat() if company.created_at else None,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating company: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/companies/{company_id}")
async def update_company(company_id: int, name: Optional[str] = None, is_active: Optional[bool] = None):
    """Update company details."""
    try:
        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            if name:
                company.name = name
            if is_active is not None:
                company.is_active = is_active

            company.updated_at = datetime.datetime.utcnow()

            await db.commit()
            await db.refresh(company)

            return {
                "id": company.id,
                "name": company.name,
                "is_active": company.is_active,
                "updated_at": company.updated_at.isoformat() if company.updated_at else None,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/companies/{company_id}")
async def delete_company(company_id: int):
    """Delete a company."""
    try:
        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            await db.delete(company)
            await db.commit()

            logger.success(f"✅ Company {company_id} deleted")

            return {"message": "Company deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CRM CONNECTION TESTING
# ============================================

@router.post("/companies/{company_id}/test-connection")
async def test_crm_connection(company_id: int):
    """Test CRM connection for a company."""
    try:
        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            adapter = await CRMFactory.create_adapter(company.crm_type, company.crm_config)

            if not adapter:
                return {
                    "status": "failed",
                    "crm_type": company.crm_type,
                    "error": f"Failed to authenticate with {company.crm_type.upper()}"
                }

            # Test with health check
            is_healthy = await adapter.health_check()

            return {
                "status": "connected" if is_healthy else "failed",
                "crm_type": company.crm_type,
                "company_name": company.name,
                "message": f"✅ {company.crm_type.upper()} connection successful" if is_healthy else f"❌ {company.crm_type.upper()} connection failed"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Connection test failed for company {company_id}: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================
# STATISTICS ENDPOINTS
# ============================================

@router.get("/statistics")
async def get_statistics():
    """Get global statistics."""
    try:
        async with AsyncSessionLocal() as db:
            # Count companies
            result = await db.execute(select(Company))
            all_companies = result.scalars().all()
            total_companies = len(all_companies)
            active_companies = len([c for c in all_companies if c.is_active])

            # CRM distribution
            crm_distribution = {}
            for c in all_companies:
                crm_distribution[c.crm_type] = crm_distribution.get(c.crm_type, 0) + 1

            # Chat sessions
            result = await db.execute(select(ChatSession))
            chat_sessions = result.scalars().all()
            total_sessions = len(chat_sessions)

            # Calculate metrics
            total_messages = sum(len(s.history_json or []) for s in chat_sessions)
            booked_sessions = len([s for s in chat_sessions if s.booked_at])
            paid_sessions = len([s for s in chat_sessions if s.is_paid])

            return {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "companies": {
                    "total": total_companies,
                    "active": active_companies,
                    "inactive": total_companies - active_companies,
                    "by_crm_type": crm_distribution
                },
                "chat_sessions": {
                    "total": total_sessions,
                    "booked": booked_sessions,
                    "paid": paid_sessions,
                    "total_messages": total_messages
                }
            }
    except Exception as e:
        logger.error(f"❌ Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CHAT SESSIONS ENDPOINTS
# ============================================

@router.get("/companies/{company_id}/chat-sessions")
async def get_chat_sessions(
    company_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None
):
    """Get chat sessions for a company."""
    try:
        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            query = select(ChatSession).where(ChatSession.company_id == company_id)

            # Apply status filter
            if status == "booked":
                query = query.where(ChatSession.booked_at != None)
            elif status == "paid":
                query = query.where(ChatSession.is_paid == True)
            elif status == "qualified":
                query = query.where(ChatSession.is_qualified == True)

            # Pagination
            query = query.offset(offset).limit(limit)

            result = await db.execute(query)
            sessions = result.scalars().all()

            # Count total
            count_result = await db.execute(select(ChatSession).where(ChatSession.company_id == company_id))
            total = len(count_result.scalars().all())

            return {
                "company_id": company_id,
                "chat_sessions": [
                    {
                        "id": s.id,
                        "whatsapp_chat_id": s.whatsapp_chat_id,
                        "client_name": s.client_name,
                        "is_qualified": s.is_qualified,
                        "booked_date": s.booked_date,
                        "is_paid": s.is_paid,
                        "crm_lead_id": s.crm_lead_id,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                        "last_interaction": s.last_interaction.isoformat() if s.last_interaction else None,
                    }
                    for s in sessions
                ],
                "total": total,
                "limit": limit,
                "offset": offset
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching chat sessions for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/leads")
async def get_leads(
    company_id: int,
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None
):
    """Get leads from company's CRM."""
    try:
        async with AsyncSessionLocal() as db:
            company = await crud.get_company(db, company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            # Get sessions for this company
            query = select(ChatSession).where(ChatSession.company_id == company_id)
            if search:
                query = query.where(
                    (ChatSession.client_name.ilike(f"%{search}%")) |
                    (ChatSession.whatsapp_chat_id.ilike(f"%{search}%"))
                )

            query = query.limit(limit)
            result = await db.execute(query)
            sessions = result.scalars().all()

            return {
                "company_id": company_id,
                "crm_type": company.crm_type,
                "leads": [
                    {
                        "crm_lead_id": s.crm_lead_id,
                        "name": s.client_name,
                        "phone": s.whatsapp_chat_id,
                        "is_qualified": s.is_qualified,
                        "booked": s.booked_date is not None,
                        "paid": s.is_paid,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in sessions
                ],
                "total": len(sessions)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching leads for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/messages/{chat_id}")
async def get_chat_history(
    company_id: int,
    chat_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """Get message history for a chat session."""
    try:
        async with AsyncSessionLocal() as db:
            query = select(ChatSession).where(
                (ChatSession.company_id == company_id) &
                (ChatSession.whatsapp_chat_id == chat_id)
            )

            result = await db.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")

            history = session.history_json or []
            history = history[-limit:] if limit else history

            return {
                "company_id": company_id,
                "chat_id": chat_id,
                "client_name": session.client_name,
                "messages": history,
                "total": len(history)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HEALTH CHECK
# ============================================

@router.get("/health")
async def health_check():
    """Check system health and all CRM connections."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Company))
            companies = result.scalars().all()

            company_statuses = []
            for company in companies:
                adapter = await CRMFactory.create_adapter(company.crm_type, company.crm_config)
                is_connected = adapter is not None

                company_statuses.append({
                    "id": company.id,
                    "name": company.name,
                    "crm_type": company.crm_type,
                    "active": company.is_active,
                    "crm_connected": is_connected
                })

            return {
                "status": "healthy",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "companies": company_statuses,
                "total_companies": len(companies),
                "connected_companies": sum(1 for c in company_statuses if c["crm_connected"])
            }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================
# INTEGRATION INSTRUCTIONS
# ============================================

"""
To integrate these endpoints into your FastAPI app:

1. In main.py, add this import:
   from api_routes import router as api_router

2. Include the router:
   app.include_router(api_router)

3. Your API will be available at:
   GET  /api/companies
   POST /api/companies
   GET  /api/companies/{id}
   PUT  /api/companies/{id}
   DELETE /api/companies/{id}
   POST /api/companies/{id}/test-connection
   GET  /api/statistics
   GET  /api/companies/{id}/chat-sessions
   GET  /api/companies/{id}/leads
   GET  /api/companies/{id}/messages/{chat_id}
   GET  /health

4. Open client_dashboard.html in your browser
   It will automatically connect to these endpoints
"""
