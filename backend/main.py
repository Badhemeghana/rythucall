import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="RythuCall API")
BASE_DIR = Path(__file__).resolve().parent.parent
FARMERS_FILE = BASE_DIR / "demo-data" / "farmers.json"
STORES_FILE = BASE_DIR / "demo-data" / "stores.json"
DATABASE_FILE = Path(__file__).resolve().parent / "rythucall.db"
LATEST_SIMULATED_SMS = None
IVR_LANGUAGES = {1: "Telugu", 2: "English", 3: "Hindi"}
DEMO_AADHAAR_LAST4 = {"9000000001": "1234", "9000000002": "5678"}
IVR_MENU_PROMPTS = {
    "Telugu": {1: "యూరియా బుక్ చేసుకోవడానికి 1 నొక్కండి", 2: "మీ బుకింగ్ స్థితిని తెలుసుకోవడానికి 2 నొక్కండి", 3: "ఇతర సహాయం కోసం 3 నొక్కండి"},
    "English": {1: "Press 1 to book Urea", 2: "Press 2 to check your booking status", 3: "Press 3 for other help"},
    "Hindi": {1: "यूरिया बुक करने के लिए 1 दबाएं", 2: "बुकिंग की स्थिति जानने के लिए 2 दबाएं", 3: "अन्य सहायता के लिए 3 दबाएं"},
}
IVR_MENU_NEXT_STEPS = {1: "fertilizer_booking", 2: "booking_status", 3: "other_help"}


class IvrLanguageRequest(BaseModel):
    selection: Literal[1, 2, 3]


class IvrVerifyRequest(BaseModel):
    mobile: str
    aadhaar_last4: str
    language: Literal["Telugu", "English", "Hindi"]


class IvrMenuRequest(BaseModel):
    farmer_id: str
    language: Literal["Telugu", "English", "Hindi"]
    option: Literal[1, 2, 3]


class PickupVerificationRequest(BaseModel):
    pickup_code: str


class SupplyReceiveRequest(BaseModel):
    store_id: str
    quantity: int


class AiRequest(BaseModel):
    language: Literal["Telugu", "Hindi", "English"]
    message: str


def _load_json(file_path):
    with file_path.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def _connect():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize_database():
    with _connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS farmers (
                farmer_id TEXT PRIMARY KEY, name TEXT NOT NULL, mobile TEXT UNIQUE NOT NULL,
                village TEXT NOT NULL, land_acres REAL NOT NULL, urea_eligible_bags INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY, name TEXT NOT NULL, village TEXT NOT NULL,
                distance_km REAL NOT NULL, initial_urea_stock INTEGER NOT NULL,
                urea_stock INTEGER NOT NULL, last_updated_minutes INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id TEXT PRIMARY KEY, farmer_id TEXT NOT NULL, name TEXT NOT NULL,
                mobile TEXT NOT NULL, village TEXT NOT NULL, urea_bags INTEGER NOT NULL,
                store_id TEXT, store_name TEXT NOT NULL, store_village TEXT NOT NULL,
                store_type TEXT NOT NULL, distance_km REAL, pickup_code TEXT NOT NULL,
                booking_date TEXT NOT NULL, valid_until TEXT NOT NULL, status TEXT NOT NULL,
                reserved INTEGER NOT NULL, reserved_quantity INTEGER NOT NULL DEFAULT 0,
                simulated_sms TEXT, collected_date TEXT
            );
            CREATE TABLE IF NOT EXISTS supply_requests (
                request_id TEXT PRIMARY KEY, village TEXT NOT NULL, required_quantity INTEGER NOT NULL,
                current_stock INTEGER NOT NULL, active_booked_quantity INTEGER NOT NULL,
                status TEXT NOT NULL, created_date TEXT NOT NULL, updated_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sms_messages (
                sms_id TEXT PRIMARY KEY, mobile TEXT NOT NULL, booking_id TEXT NOT NULL,
                message TEXT NOT NULL, timestamp TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS call_events (
                call_id TEXT PRIMARY KEY, mobile TEXT NOT NULL, language TEXT NOT NULL,
                verification_status TEXT NOT NULL, result TEXT NOT NULL, timestamp TEXT NOT NULL
            );
        """)
        if connection.execute("SELECT COUNT(*) FROM farmers").fetchone()[0] == 0:
            farmers = _load_json(FARMERS_FILE)
            connection.executemany(
                "INSERT INTO farmers VALUES (?, ?, ?, ?, ?, ?)",
                [(str(item["farmer_id"]), item["name"], str(item["mobile"]), item["village"], item["land_acres"], item["urea_eligible_bags"]) for item in farmers],
            )
        if connection.execute("SELECT COUNT(*) FROM stores").fetchone()[0] == 0:
            stores = _load_json(STORES_FILE)
            connection.executemany(
                "INSERT INTO stores VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(item["store_id"], item["name"], item["village"], item["distance_km"], item["urea_stock"], item["urea_stock"], item["last_updated_minutes"]) for item in stores],
            )


_initialize_database()


@app.get("/")
def root():
    return {"message": "RythuCall API is running", "status": "success"}


@app.post("/ai/understand")
def understand_farmer_request(request: AiRequest):
    message = request.message.strip().lower()
    quantity_match = re.search(r"\d+", message)
    quantity = int(quantity_match.group()) if quantity_match else None
    if not message:
        intent = "UNKNOWN"
    elif any(term in message for term in ("status", "స్థితి", "स्थिति", "बुकिंग की स्थिति")):
        intent = "BOOKING_STATUS"
    elif any(term in message for term in ("help", "సహాయం", "मदद")):
        intent = "HELP"
    elif any(term in message for term in ("available", "availability", "దొరుకుతుంద", "లభ్యత", "उपलब्ध", "मिलेगा")):
        intent = "SUPPLY_AVAILABILITY"
    elif any(term in message for term in ("urea", "యూరియా", "యూరియ", "यूरिया")) and any(term in message for term in ("need", "want", "book", "కావాలి", "బుక్", "చేయాలి", "चाहिए", "बुक")):
        intent = "UREA_REQUEST"
    else:
        intent = "UNKNOWN"
    responses = {
        "English": {"UREA_REQUEST": f"I can help you book {quantity or 'the eligible quantity'} bags of Urea.", "BOOKING_STATUS": "I can check your active booking status.", "HELP": "I can help with bookings, status, and store information.", "SUPPLY_AVAILABILITY": "I can check Urea availability in your village.", "UNKNOWN": "Please ask about booking Urea, booking status, availability, or help."},
        "Telugu": {"UREA_REQUEST": f"మీ గ్రామంలో {quantity or 'అర్హత ఉన్న'} యూరియా బస్తాలను బుక్ చేయడంలో సహాయం చేస్తాను.", "BOOKING_STATUS": "మీ బుకింగ్ స్థితిని చెక్ చేయడంలో సహాయం చేస్తాను.", "HELP": "బుకింగ్, స్థితి మరియు స్టోర్ సమాచారం కోసం సహాయం చేస్తాను.", "SUPPLY_AVAILABILITY": "మీ గ్రామంలో యూరియా లభ్యతను చెక్ చేస్తాను.", "UNKNOWN": "యూరియా బుకింగ్, బుకింగ్ స్థితి, లభ్యత లేదా సహాయం గురించి అడగండి."},
        "Hindi": {"UREA_REQUEST": f"मैं आपके गांव से {quantity or 'पात्र मात्रा'} बोरी यूरिया बुक करने में मदद करूंगा।", "BOOKING_STATUS": "मैं आपकी सक्रिय बुकिंग की स्थिति जांच सकता हूं।", "HELP": "मैं बुकिंग, स्थिति और स्टोर की जानकारी में मदद कर सकता हूं।", "SUPPLY_AVAILABILITY": "मैं आपके गांव में यूरिया की उपलब्धता जांच सकता हूं।", "UNKNOWN": "यूरिया बुकिंग, बुकिंग स्थिति, उपलब्धता या मदद के बारे में पूछें।"},
    }
    return {"intent": intent, "language": request.language, "quantity": quantity, "response": responses[request.language][intent]}


def _find_farmer(mobile):
    with _connect() as connection:
        row = connection.execute("SELECT * FROM farmers WHERE mobile = ?", (mobile,)).fetchone()
    return dict(row) if row else None


@app.post("/ivr/language")
def select_ivr_language(request: IvrLanguageRequest):
    return {"selected_language": IVR_LANGUAGES[request.selection], "next_step": "aadhaar_last_4_verification", "verification_type": "DEMO_LAST_4_DIGITS"}


@app.post("/ivr/verify")
def verify_ivr_farmer(request: IvrVerifyRequest):
    if len(request.aadhaar_last4) != 4 or not request.aadhaar_last4.isdigit():
        raise HTTPException(status_code=400, detail="Verification could not be completed.")
    farmer = _find_farmer(request.mobile)
    if farmer is None or DEMO_AADHAAR_LAST4.get(request.mobile) != request.aadhaar_last4:
        raise HTTPException(status_code=400, detail="Verification could not be completed.")
    with _connect() as connection:
        connection.execute("INSERT INTO call_events VALUES (?, ?, ?, ?, ?, ?)", (f"CALL-{uuid4().hex[:8].upper()}", request.mobile, request.language, "VERIFIED", "Eligibility found", datetime.now().isoformat(timespec="seconds")))
    return {"verified": True, "farmer_id": farmer["farmer_id"], "name": farmer["name"], "village": farmer["village"], "land_acres": farmer["land_acres"], "urea_eligible_bags": farmer["urea_eligible_bags"], "selected_language": request.language, "next_step": "fertilizer_booking", "verification_type": "DEMO_LAST_4_DIGITS"}


@app.post("/ivr/menu")
def select_ivr_menu_option(request: IvrMenuRequest):
    return {"selected_language": request.language, "selected_option": request.option, "next_step": IVR_MENU_NEXT_STEPS[request.option], "prompt": IVR_MENU_PROMPTS[request.language][request.option]}


def _today():
    return date.today()


def _display_date(iso_date):
    return date.fromisoformat(iso_date).strftime("%d-%b-%Y")


def _store_type(store):
    store_name = store["name"].lower()
    return "Vyavasaya/Rythu Kendram" if "cooperative" in store_name or "kendram" in store_name else "Private fertilizer store"


def _row_booking(row):
    booking = dict(row)
    booking["reserved"] = bool(booking["reserved"])
    booking["reserved_allocations"] = {booking["store_id"]: booking["reserved_quantity"]} if booking["reserved"] and booking["store_id"] else {}
    return booking


def _expire_bookings(connection):
    expired = connection.execute("SELECT * FROM bookings WHERE status = 'ACTIVE' AND valid_until < ?", (_today().isoformat(),)).fetchall()
    for row in expired:
        if row["reserved"] and row["store_id"]:
            connection.execute("UPDATE stores SET urea_stock = urea_stock + ? WHERE store_id = ?", (row["reserved_quantity"], row["store_id"]))
        connection.execute("UPDATE bookings SET status = 'EXPIRED' WHERE booking_id = ?", (row["booking_id"],))


def _active_bookings():
    with _connect() as connection:
        _expire_bookings(connection)
        rows = connection.execute("SELECT * FROM bookings WHERE status = 'ACTIVE'").fetchall()
    return [_row_booking(row) for row in rows]


def _rank_stores(stores, required_quantity=0):
    return sorted(stores, key=lambda store: (store["urea_stock"] < required_quantity, store["distance_km"], -store["urea_stock"]))


def _village_data(village):
    active_bookings = [booking for booking in _active_bookings() if booking["village"] == village]
    with _connect() as connection:
        stores = [dict(row) for row in connection.execute("SELECT * FROM stores WHERE village = ?", (village,)).fetchall()]
    total_stock = sum(store["initial_urea_stock"] for store in stores)
    available_stock = sum(store["urea_stock"] for store in stores)
    booked_quantity = sum(booking["urea_bags"] for booking in active_bookings)
    demand = {"total_active_bookings": len(active_bookings), "total_booked_urea": booked_quantity, "total_village_stock": total_stock, "current_village_stock": available_stock, "additional_urea_required": max(booked_quantity - total_stock, 0), "supply_status": "VILLAGE SUPPLY REQUIREMENT" if booked_quantity > total_stock else "Stock available"}
    _sync_supply_request(village, demand)
    ranked_stores = _rank_stores(stores)
    return {"stores": [{**store, "store_type": _store_type(store)} for store in ranked_stores], "demand": demand}


def _sync_supply_request(village, demand):
    now = _today().isoformat()
    with _connect() as connection:
        existing = connection.execute("SELECT * FROM supply_requests WHERE village = ?", (village,)).fetchone()
        required = demand["additional_urea_required"]
        if existing is None and required > 0:
            connection.execute("INSERT INTO supply_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (f"SUP-{uuid4().hex[:8].upper()}", village, required, demand["current_village_stock"], demand["total_booked_urea"], "SUPPLY REQUIRED", now, now))
        elif existing is not None:
            status = "STOCK AVAILABLE" if required == 0 else ("SUPPLY REQUIRED" if existing["status"] in ("STOCK AVAILABLE", "SUPPLY RECEIVED") else existing["status"])
            connection.execute("UPDATE supply_requests SET required_quantity = ?, current_stock = ?, active_booked_quantity = ?, status = ?, updated_date = ? WHERE request_id = ?", (required, demand["current_village_stock"], demand["total_booked_urea"], status, now, existing["request_id"]))


@app.get("/farmer/{mobile}")
def get_farmer(mobile):
    farmer = _find_farmer(mobile)
    if farmer is None:
        raise HTTPException(status_code=404, detail=f"No farmer found for mobile number {mobile}")
    return {"farmer_id": farmer["farmer_id"], "name": farmer["name"], "mobile": farmer["mobile"], "village": farmer["village"], "land_acres": farmer["land_acres"], "urea_eligible_bags": farmer["urea_eligible_bags"]}


@app.get("/village/{village}/stores")
def get_village_stores(village, quantity: int = 0):
    data = _village_data(village)
    data["stores"] = [{**store, "can_fulfill": store["urea_stock"] >= quantity} for store in _rank_stores(data["stores"], quantity)]
    return data


@app.get("/notifications/sms/latest")
def get_latest_simulated_sms():
    return {"sms": LATEST_SIMULATED_SMS}


def _mask_mobile(mobile):
    return f"{mobile[:2]}******{mobile[-2:]}"


@app.get("/sms")
def get_sms():
    with _connect() as connection:
        rows = connection.execute("SELECT sms_id, mobile, booking_id, message, timestamp, status FROM sms_messages ORDER BY timestamp DESC LIMIT 50").fetchall()
    return [{**dict(row), "mobile": _mask_mobile(row["mobile"])} for row in rows]


@app.get("/calls")
def get_calls():
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM call_events ORDER BY timestamp DESC LIMIT 50").fetchall()
    return [{**dict(row), "mobile": _mask_mobile(row["mobile"])} for row in rows]


@app.get("/supply-requests")
def get_supply_requests():
    with _connect() as connection:
        villages = [row["village"] for row in connection.execute("SELECT DISTINCT village FROM stores").fetchall()]
    for village in villages:
        _village_data(village)
    with _connect() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM supply_requests ORDER BY updated_date DESC, request_id DESC").fetchall()]


@app.post("/supply-requests/{request_id}/dispatch")
def dispatch_supply(request_id: str):
    with _connect() as connection:
        row = connection.execute("SELECT * FROM supply_requests WHERE request_id = ?", (request_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Supply request not found.")
        if row["status"] == "STOCK AVAILABLE":
            raise HTTPException(status_code=409, detail="Supply request is already satisfied.")
        connection.execute("UPDATE supply_requests SET status = 'SUPPLY DISPATCHED', updated_date = ? WHERE request_id = ?", (_today().isoformat(), request_id))
        return dict(connection.execute("SELECT * FROM supply_requests WHERE request_id = ?", (request_id,)).fetchone())


@app.post("/supply-requests/{request_id}/receive")
def receive_supply(request_id: str, request: SupplyReceiveRequest):
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Supply quantity must be positive.")
    with _connect() as connection:
        row = connection.execute("SELECT * FROM supply_requests WHERE request_id = ?", (request_id,)).fetchone()
        store = connection.execute("SELECT * FROM stores WHERE store_id = ? AND village = ?", (request.store_id, row["village"] if row else "")).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Supply request not found.")
        if store is None:
            raise HTTPException(status_code=404, detail="Village store not found.")
        connection.execute("UPDATE stores SET initial_urea_stock = initial_urea_stock + ?, urea_stock = urea_stock + ? WHERE store_id = ?", (request.quantity, request.quantity, request.store_id))
        connection.execute("UPDATE supply_requests SET status = 'SUPPLY RECEIVED', updated_date = ? WHERE request_id = ?", (_today().isoformat(), request_id))
    _village_data(row["village"])
    with _connect() as connection:
        return dict(connection.execute("SELECT * FROM supply_requests WHERE request_id = ?", (request_id,)).fetchone())


def _booking_response(booking):
    response = booking.copy()
    response.pop("reserved_allocations", None)
    response.pop("store_id", None)
    mobile = response.pop("mobile", "")
    response["masked_mobile"] = f"{mobile[:2]}******{mobile[-2:]}" if mobile else "Unavailable"
    response.pop("reserved_quantity", None)
    return response


def _find_booking(booking_id):
    with _connect() as connection:
        _expire_bookings(connection)
        row = connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    return _row_booking(row) if row else None


@app.get("/booking/{booking_id}")
def get_booking(booking_id):
    booking = _find_booking(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return _booking_response(booking)


@app.get("/bookings")
def get_bookings():
    with _connect() as connection:
        _expire_bookings(connection)
        rows = connection.execute("SELECT * FROM bookings ORDER BY booking_date DESC, booking_id DESC LIMIT 50").fetchall()
    return [_booking_response(_row_booking(row)) for row in rows]


@app.post("/booking/{booking_id}/verify-pickup")
def verify_booking_pickup(booking_id, request: PickupVerificationRequest):
    booking = _find_booking(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking["status"] == "EXPIRED":
        raise HTTPException(status_code=409, detail="Booking expired.")
    if booking["status"] == "COLLECTED":
        raise HTTPException(status_code=409, detail="Booking already collected.")
    if request.pickup_code.strip().upper() != booking["pickup_code"]:
        raise HTTPException(status_code=400, detail="Invalid pickup code.")
    return {"verified": True, "booking": _booking_response(booking)}


@app.post("/booking/{booking_id}/collect")
def collect_booking(booking_id):
    with _connect() as connection:
        _expire_bookings(connection)
        row = connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Booking not found.")
        if row["status"] == "EXPIRED":
            raise HTTPException(status_code=409, detail="Booking expired.")
        if row["status"] == "COLLECTED":
            raise HTTPException(status_code=409, detail="Booking already collected.")
        connection.execute("UPDATE bookings SET status = 'COLLECTED', collected_date = ? WHERE booking_id = ?", (_today().isoformat(), booking_id))
        collected = dict(connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone())
    return {"collected": True, "booking": _booking_response(_row_booking(collected))}


@app.post("/booking/{booking_id}/cancel")
def cancel_booking(booking_id):
    with _connect() as connection:
        _expire_bookings(connection)
        row = connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Booking not found.")
        if row["status"] == "EXPIRED":
            raise HTTPException(status_code=409, detail="Booking expired and cannot be cancelled.")
        if row["status"] == "COLLECTED":
            raise HTTPException(status_code=409, detail="Collected booking cannot be cancelled.")
        if row["status"] == "CANCELLED":
            raise HTTPException(status_code=409, detail="Booking already cancelled.")
        if row["status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail=f"Booking with status {row['status']} cannot be cancelled.")
        if row["reserved"] and row["store_id"]:
            connection.execute("UPDATE stores SET urea_stock = urea_stock + ? WHERE store_id = ?", (row["reserved_quantity"], row["store_id"]))
        connection.execute("UPDATE bookings SET status = 'CANCELLED', reserved = 0, reserved_quantity = 0 WHERE booking_id = ?", (booking_id,))
        cancelled = connection.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    _village_data(row["village"])
    return {"cancelled": True, "booking": _booking_response(_row_booking(cancelled))}


@app.post("/booking/{mobile}")
def create_booking(mobile, language: Literal["Telugu", "Hindi", "English"] = "English", store_id=None):
    global LATEST_SIMULATED_SMS
    farmer = _find_farmer(mobile)
    if farmer is None:
        raise HTTPException(status_code=404, detail=f"No farmer found for mobile number {mobile}")
    village = farmer["village"]
    urea_bags = farmer["urea_eligible_bags"]
    with _connect() as connection:
        _expire_bookings(connection)
        stores = [dict(row) for row in connection.execute("SELECT * FROM stores WHERE village = ?", (village,)).fetchall()]
        ranked_stores = _rank_stores(stores, urea_bags)
        selected_store = next((store for store in ranked_stores if store["store_id"] == store_id), None) if store_id else None
        if store_id and (selected_store is None or selected_store["urea_stock"] < urea_bags):
            raise HTTPException(status_code=409, detail="Selected store cannot fulfill this booking.")
        available_store = selected_store or next((store for store in ranked_stores if store["urea_stock"] >= urea_bags), None)
        reserved = available_store is not None
        if reserved:
            connection.execute("UPDATE stores SET urea_stock = urea_stock - ? WHERE store_id = ?", (urea_bags, available_store["store_id"]))
        booking_date = _today()
        valid_until = booking_date + timedelta(days=2)
        store = available_store or (stores[0] if stores else {"name": "Village supply point", "store_id": None, "distance_km": None, "store_type": "Village supply point"})
        booking = {"booking_id": f"BOOK-{uuid4().hex[:8].upper()}", "farmer_id": farmer["farmer_id"], "name": farmer["name"], "mobile": farmer["mobile"], "village": village, "urea_bags": urea_bags, "store_id": store.get("store_id"), "store_name": store["name"], "store_village": village, "store_type": store.get("store_type") or _store_type(store), "distance_km": store.get("distance_km"), "pickup_code": uuid4().hex[:6].upper(), "booking_date": booking_date.isoformat(), "valid_until": valid_until.isoformat(), "status": "ACTIVE", "reserved": reserved, "reserved_quantity": urea_bags if reserved else 0, "reserved_allocations": {store["store_id"]: urea_bags} if reserved else {}}
        booking["simulated_sms"] = "\n".join([f"Kisan Connect: Your Urea booking {booking['booking_id']} is confirmed.", f"Farmer: {booking['name']}", f"Urea: {booking['urea_bags']} bags", f"Village: {booking['village']}", f"Pickup Store: {booking['store_name']}", f"Pickup Code: {booking['pickup_code']}", f"Valid Until: {_display_date(booking['valid_until'])}"])
        connection.execute("INSERT INTO bookings (booking_id, farmer_id, name, mobile, village, urea_bags, store_id, store_name, store_village, store_type, distance_km, pickup_code, booking_date, valid_until, status, reserved, reserved_quantity, simulated_sms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (booking["booking_id"], booking["farmer_id"], booking["name"], booking["mobile"], booking["village"], booking["urea_bags"], booking["store_id"], booking["store_name"], booking["store_village"], booking["store_type"], booking["distance_km"], booking["pickup_code"], booking["booking_date"], booking["valid_until"], booking["status"], int(booking["reserved"]), booking["reserved_quantity"], booking["simulated_sms"]))
    LATEST_SIMULATED_SMS = booking["simulated_sms"]
    with _connect() as connection:
        timestamp = datetime.now().isoformat(timespec="seconds")
        connection.execute("INSERT INTO sms_messages VALUES (?, ?, ?, ?, ?, ?)", (f"SMS-{uuid4().hex[:8].upper()}", booking["mobile"], booking["booking_id"], booking["simulated_sms"], timestamp, "SIMULATED"))
        connection.execute("INSERT INTO call_events VALUES (?, ?, ?, ?, ?, ?)", (f"CALL-{uuid4().hex[:8].upper()}", booking["mobile"], language, "VERIFIED", "Booking created", timestamp))
    updated_village_data = _village_data(village)
    return {**booking, "village_stores": updated_village_data["stores"], "village_demand": updated_village_data["demand"]}
