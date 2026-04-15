"""
Abstract base class for CRM integrations.
All CRM adapters must inherit from this and implement required methods.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class CRMLead:
    """Standardized lead object across all CRMs."""
    id: str
    phone: str
    name: str
    email: Optional[str] = None
    status: Optional[str] = None
    custom_fields: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_fields is None:
            self.custom_fields = {}


@dataclass
class CRMResponse:
    """Standardized response object."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class BaseCRMAdapter(ABC):
    """Abstract base class for CRM integrations."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CRM adapter with configuration.

        Args:
            config: Dictionary with CRM-specific credentials
                Example: {"api_key": "xxx", "subdomain": "yyy"}
        """
        self.config = config
        self.is_authenticated = False

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with CRM API.
        Returns True if successful.
        """
        pass

    @abstractmethod
    async def get_lead_by_phone(self, phone: str) -> Optional[CRMLead]:
        """
        Fetch lead/customer by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            CRMLead object or None if not found
        """
        pass

    @abstractmethod
    async def create_lead(self, name: str, phone: str, email: Optional[str] = None) -> Optional[str]:
        """
        Create a new lead in CRM.

        Args:
            name: Lead name
            phone: Phone number
            email: Email (optional)

        Returns:
            New lead ID or None if failed
        """
        pass

    @abstractmethod
    async def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing lead.

        Args:
            lead_id: Lead ID in CRM
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def get_lead_status(self, lead_id: str) -> Optional[str]:
        """Get current status of a lead."""
        pass

    @abstractmethod
    async def set_lead_status(self, lead_id: str, status: str) -> bool:
        """Set lead status (e.g., "booked", "paid")."""
        pass

    @abstractmethod
    async def get_next_available_slots(self, service_type: str = None) -> Dict[str, str]:
        """
        Get available time slots for booking.

        Returns:
            Dictionary with available slots (format depends on CRM)
        """
        pass

    async def health_check(self) -> bool:
        """Check if CRM connection is alive. Override if needed."""
        return self.is_authenticated
