import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException

app = FastAPI(title="RythuCall API")
FARMERS_FILE = Path(__file__).resolve().parent.parent / "demo-data" / "farmers.json"
STORES_FILE = Path(__file__).resolve().parent.parent / "demo-data" / "stores.json"
BOOKINGS = []
RESERVED_STOCK = {}
LATEST_SIMULATED_SMS = None


@app.get("/")
def root():
    return {
        "message": "RythuCall API is running",
        "status": "success"
    }


def _load_json(file_path: Path):
    with file_path.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def _find_farmer(mobile: str):
    farmers = _load_json(FARMERS_FILE)
    return next((farmer for farmer in farmers if str(farmer["mobile"]) == mobile), None)


def _today():
    return date.today()


def _display_date(iso_date):
    return date.fromisoformat(iso_date).strftime("%d-%b-%Y")


def _store_type(store):
    store_name = store["name"].lower()
    return "Vyavasaya/Rythu Kendram" if "cooperative" in store_name or "kendram" in store_name else "Private fertilizer store"


def _active_bookings():
    today = _today()
    for booking in BOOKINGS:
        if booking["status"] == "ACTIVE" and today > date.fromisoformat(booking["valid_until"]):
            booking["status"] = "EXPIRED"
            for store_id, quantity in booking.get("reserved_allocations", {}).items():
                RESERVED_STOCK[store_id] = max(RESERVED_STOCK.get(store_id, 0) - quantity, 0)
    return [booking for booking in BOOKINGS if booking["status"] == "ACTIVE"]


def _village_data(village):
    active_bookings = [booking for booking in _active_bookings() if booking["village"] == village]
    stores = [store.copy() for store in _load_json(STORES_FILE) if store["village"] == village]
    total_stock = sum(store["urea_stock"] for store in stores)
    available_stock = sum(
        max(store["urea_stock"] - RESERVED_STOCK.get(store["store_id"], 0), 0)
        for store in stores
    )
    booked_quantity = sum(booking["urea_bags"] for booking in active_bookings)
    return {
        "stores": [
            {
                **store,
                "urea_stock": max(store["urea_stock"] - RESERVED_STOCK.get(store["store_id"], 0), 0),
                "store_type": _store_type(store),
            }
            for store in stores
        ],
        "demand": {
            "total_active_bookings": len(active_bookings),
            "total_booked_urea": booked_quantity,
            "total_village_stock": total_stock,
            "current_village_stock": available_stock,
            "additional_urea_required": max(booked_quantity - total_stock, 0),
            "supply_status": "VILLAGE SUPPLY REQUIREMENT" if booked_quantity > total_stock else "Stock available",
        },
    }


@app.get("/farmer/{mobile}")
def get_farmer(mobile: str):
    farmer = _find_farmer(mobile)
    if farmer is None:
        raise HTTPException(status_code=404, detail=f"No farmer found for mobile number {mobile}")

    return {
        "farmer_id": farmer["farmer_id"],
        "name": farmer["name"],
        "mobile": farmer["mobile"],
        "village": farmer["village"],
        "land_acres": farmer["land_acres"],
        "urea_eligible_bags": farmer["urea_eligible_bags"],
    }


@app.get("/village/{village}/stores")
def get_village_stores(village: str):
    return _village_data(village)


@app.get("/notifications/sms/latest")
def get_latest_simulated_sms():
    return {"sms": LATEST_SIMULATED_SMS}


@app.post("/booking/{mobile}")
def create_booking(mobile: str):
    global LATEST_SIMULATED_SMS

    farmer = _find_farmer(mobile)
    if farmer is None:
        raise HTTPException(status_code=404, detail=f"No farmer found for mobile number {mobile}")

    village = farmer["village"]
    urea_bags = farmer["urea_eligible_bags"]
    village_data = _village_data(village)
    available_store = next((store for store in village_data["stores"] if store["urea_stock"] >= urea_bags), None)
    reserved_allocations = {}
    if available_store is not None:
        RESERVED_STOCK[available_store["store_id"]] = RESERVED_STOCK.get(available_store["store_id"], 0) + urea_bags
        reserved_allocations[available_store["store_id"]] = urea_bags
    booking_date = _today()
    valid_until = booking_date + timedelta(days=2)
    booking = {
        "booking_id": f"BOOK-{uuid4().hex[:8].upper()}",
        "name": farmer["name"],
        "village": village,
        "urea_bags": urea_bags,
        "store_name": available_store["name"] if available_store else village_data["stores"][0]["name"] if village_data["stores"] else "Village supply point",
        "store_village": village,
        "store_type": available_store["store_type"] if available_store else "Village supply point",
        "distance_km": available_store["distance_km"] if available_store else None,
        "pickup_code": uuid4().hex[:6].upper(),
        "booking_date": booking_date.isoformat(),
        "valid_until": valid_until.isoformat(),
        "status": "ACTIVE",
        "reserved": available_store is not None,
        "reserved_allocations": reserved_allocations,
    }
    booking["simulated_sms"] = "\n".join([
        "RythuCall Booking Confirmed!",
        f"Farmer: {booking['name']}",
        f"Urea: {booking['urea_bags']} bags",
        f"Village: {booking['village']}",
        f"Pickup Store: {booking['store_name']}",
        f"Pickup Code: {booking['pickup_code']}",
        f"Valid Until: {_display_date(booking['valid_until'])}",
    ])
    LATEST_SIMULATED_SMS = booking["simulated_sms"]
    BOOKINGS.append(booking)
    updated_village_data = _village_data(village)
    return {**booking, "village_stores": updated_village_data["stores"], "village_demand": updated_village_data["demand"]}