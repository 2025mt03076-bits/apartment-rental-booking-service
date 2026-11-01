import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from app import database
from app.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("booking-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.client = AsyncIOMotorClient(database.MONGO_URI, serverSelectionTimeoutMS=10000)
    # Fail fast if MongoDB is unreachable so Docker / Kubernetes restarts the container
    await database.client.admin.command("ping")
    log.info("Booking Service connected to MongoDB")
    db = database.get_db()
    await db.bookings.create_index("listing_id")
    await db.bookings.create_index("tenant_id")
    yield
    database.client.close()


app = FastAPI(title="Booking Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)


# Liveness / readiness probe endpoint
@app.get("/health", tags=["health"])
async def health():
    try:
        await database.client.admin.command("ping")
        return {"service": "booking-service", "status": "UP"}
    except Exception:
        return JSONResponse(status_code=503, content={"service": "booking-service", "status": "DOWN"})
