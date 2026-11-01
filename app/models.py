from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class BookingCreate(BaseModel):
    listing_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    start_date: date
    message: Optional[str] = None


class BookingOut(BaseModel):
    id: str
    listing_id: str
    tenant_id: str
    start_date: datetime
    message: Optional[str] = None
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class BookingList(BaseModel):
    total: int
    items: List[BookingOut]
