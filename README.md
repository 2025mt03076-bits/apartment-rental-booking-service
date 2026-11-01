# Booking Service

Part of the Apartment Rental Platform (SEZG583 assignment). Manages rental requests and their lifecycle.
Calls the Listing Service over REST to check and update apartment availability.

- Stack: Python 3.12, FastAPI, Motor (async MongoDB driver), httpx - database `bookingdb`
- Port: 3002 (interactive API docs at `/docs`)
- Config: `MONGO_URI`, `LISTING_SERVICE_URL`

## API
| Method | Path | Description |
|---|---|---|
| POST | /bookings | Create request `{listing_id, tenant_id, start_date, message?}` (checks listing availability) |
| GET | /bookings?tenant_id=&listing_id=&status= | List bookings |
| GET | /bookings/{id} | Booking status |
| PATCH | /bookings/{id}/approve | Approve (marks listing RENTED, rejects other pending requests) |
| PATCH | /bookings/{id}/reject | Reject a pending request |
| PATCH | /bookings/{id}/cancel | Cancel (frees the listing if it was approved) |
| GET | /health | Health check |

## Run locally
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
MONGO_URI=mongodb://localhost:27017/bookingdb LISTING_SERVICE_URL=http://localhost:3001 \
  uvicorn app.main:app --port 3002 --reload
```

## Kubernetes (minikube)
Deploy the Listing Service first.
```
eval $(minikube docker-env)
docker build -t booking-service:1.0 .
kubectl apply -f k8s/mongo.yaml -f k8s/deployment.yaml
```
