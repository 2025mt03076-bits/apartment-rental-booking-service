from datetime import datetime, time, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pymongo import ReturnDocument

from app import database, listing_client
from app.models import BookingCreate, BookingList, BookingOut, BookingStatus

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail=f"Invalid booking id: {value}")
    return ObjectId(value)


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


async def _get_or_404(booking_id: str) -> dict:
    doc = await database.get_db().bookings.find_one({"_id": _object_id(booking_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return doc


async def _set_status(booking_id: ObjectId, status: BookingStatus) -> dict:
    return await database.get_db().bookings.find_one_and_update(
        {"_id": booking_id},
        {"$set": {"status": status.value, "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )


# Command: createBookingRequest
@router.post("", response_model=BookingOut, status_code=201)
async def create_booking(payload: BookingCreate):
    # Synchronous call to the Listing Service: is this apartment bookable?
    listing = await listing_client.get_listing(payload.listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing["status"] != "AVAILABLE":
        raise HTTPException(
            status_code=409, detail=f"Listing is not available (current status: {listing['status']})"
        )

    doc = {
        "listing_id": payload.listing_id,
        "tenant_id": payload.tenant_id,
        "start_date": datetime.combine(payload.start_date, time.min),
        "message": payload.message,
        "status": BookingStatus.PENDING.value,
        "created_at": _now(),
        "updated_at": _now(),
    }
    result = await database.get_db().bookings.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


# Query: getTenantBookings / getOwnerBookingRequests
@router.get("", response_model=BookingList)
async def list_bookings(
    tenant_id: Optional[str] = None,
    listing_id: Optional[str] = None,
    status: Optional[BookingStatus] = None,
):
    query: dict = {}
    if tenant_id:
        query["tenant_id"] = tenant_id
    if listing_id:
        query["listing_id"] = listing_id
    if status:
        query["status"] = status.value
    cursor = database.get_db().bookings.find(query).sort("created_at", -1)
    items = [_serialize(doc) async for doc in cursor]
    return {"total": len(items), "items": items}


# Query: getBookingStatus
@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(booking_id: str):
    return _serialize(await _get_or_404(booking_id))


# Command: approveBooking
@router.patch("/{booking_id}/approve", response_model=BookingOut)
async def approve_booking(booking_id: str):
    booking = await _get_or_404(booking_id)
    if booking["status"] != BookingStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Only PENDING bookings can be approved (current status: {booking['status']})",
        )

    # Re-check availability: another request may have been approved in the meantime
    listing = await listing_client.get_listing(booking["listing_id"])
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing no longer exists")
    if listing["status"] != "AVAILABLE":
        raise HTTPException(
            status_code=409, detail=f"Listing is not available (current status: {listing['status']})"
        )

    await listing_client.set_listing_status(booking["listing_id"], "RENTED")
    updated = await _set_status(booking["_id"], BookingStatus.APPROVED)

    # The apartment is taken, so other pending requests for it are rejected
    await database.get_db().bookings.update_many(
        {"listing_id": booking["listing_id"], "status": "PENDING", "_id": {"$ne": booking["_id"]}},
        {"$set": {"status": BookingStatus.REJECTED.value, "updated_at": _now()}},
    )
    return _serialize(updated)


# Command: rejectBooking
@router.patch("/{booking_id}/reject", response_model=BookingOut)
async def reject_booking(booking_id: str):
    booking = await _get_or_404(booking_id)
    if booking["status"] != BookingStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Only PENDING bookings can be rejected (current status: {booking['status']})",
        )
    return _serialize(await _set_status(booking["_id"], BookingStatus.REJECTED))


# Command: cancelBooking
@router.patch("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(booking_id: str):
    booking = await _get_or_404(booking_id)
    if booking["status"] not in (BookingStatus.PENDING.value, BookingStatus.APPROVED.value):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a booking that is {booking['status']}")
    # If it was approved, free the apartment again (compensating action)
    if booking["status"] == BookingStatus.APPROVED.value:
        await listing_client.set_listing_status(booking["listing_id"], "AVAILABLE")
    return _serialize(await _set_status(booking["_id"], BookingStatus.CANCELLED))
