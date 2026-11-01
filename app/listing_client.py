import os
from typing import Optional

import httpx
from fastapi import HTTPException

BASE_URL = os.getenv("LISTING_SERVICE_URL", "http://localhost:3001")
TIMEOUT_SECONDS = float(os.getenv("LISTING_TIMEOUT_SECONDS", "3"))


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            return await client.request(method, f"{BASE_URL}{path}", **kwargs)
    except httpx.HTTPError:
        # network failure or timeout: the dependency is down
        raise HTTPException(status_code=503, detail="Listing Service is unavailable, please try again later")


async def get_listing(listing_id: str) -> Optional[dict]:
    """Return the listing, or None if it does not exist."""
    response = await _request("GET", f"/listings/{listing_id}")
    if response.status_code in (400, 404):
        return None
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Listing Service returned {response.status_code}")
    return response.json()


async def set_listing_status(listing_id: str, status: str) -> dict:
    response = await _request("PATCH", f"/listings/{listing_id}/status", json={"status": status})
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Could not update listing status (Listing Service returned {response.status_code})",
        )
    return response.json()
