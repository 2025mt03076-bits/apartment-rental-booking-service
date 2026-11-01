import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/bookingdb")

# Set during application startup (see main.py)
client = None


def get_db():
    """Return the database named in MONGO_URI (bookingdb by default)."""
    return client.get_default_database("bookingdb")
