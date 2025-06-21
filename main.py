from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from datetime import datetime
from fastapi.responses import JSONResponse

app = FastAPI()

class PremiumRequest(BaseModel):
    strikePrice: float
    optionType: str
    side: str
    expiryDate: str  # Format: "2024-06-27"

@app.post("/premium")
def get_premium(payload: PremiumRequest):
    strike_price = payload.strikePrice
    option_type = payload.optionType.upper()
    side = payload.side
    expiry_input = payload.expiryDate

    if option_type not in ["CE", "PE"]:
        return JSONResponse(status_code=400, content={"error": "Invalid optionType"})

    try:
        # Step 1: Create session and get homepage to trigger cookies
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        })
        session.get("https://www.nseindia.com/option-chain", timeout=10)

        # Step 2: Call Option Chain API
        response = session.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/option-chain",
            "X-Requested-With": "XMLHttpRequest"
        }, timeout=10)

        data = response.json()
        available_expiries = data["records"]["expiryDates"]

        # Step 3: Match expiry date
        input_date = datetime.strptime(expiry_input, "%Y-%m-%d")
        month_str = input_date.strftime('%b')  # e.g., 'Jun'
        day_str = input_date.strftime('%d')    # e.g., '27'

        formatted_expiry = next(
            (e for e in available_expiries if month_str in e and day_str in e),
            None
        )

        if not formatted_expiry:
            return JSONResponse(status_code=404, content={
                "error": f"No data for expiry {expiry_input}",
                "availableExpiries": available_expiries
            })

        # Step 4: Find matching strike
        rows = data["records"]["data"]
        matching = next(
            (r for r in rows if r.get("expiryDate") == formatted_expiry and r.get(option_type) and r[option_type].get("strikePrice") == strike_price),
            None
        )

        if not matching or matching[option_type].get("lastPrice") is None:
            return JSONResponse(status_code=404, content={"error": "No matching strike found"})

        return {
            "strikePrice": strike_price,
            "optionType": option_type,
            "side": side,
            "expiryDate": formatted_expiry,
            "lastPrice": matching[option_type]["lastPrice"]
        }

    except Exception as e:
        print("❌ Error:", e)
        return JSONResponse(status_code=500, content={"error": "Failed to fetch premium"})

# Run this with: uvicorn main:app --reload --port 3000
