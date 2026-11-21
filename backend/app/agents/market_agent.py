from collections import defaultdict
from datetime import datetime
import math
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
from backend.app.agents.schemas import AgentRunRequest


class _MarketSettings(BaseSettings):
    data_gov_in_api_key: str | None = None
    agmarknet_resource_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


async def run(request: AgentRunRequest) -> dict:
    settings = _MarketSettings()
    commodity = request.commodity or request.crop
    if not settings.data_gov_in_api_key or not settings.agmarknet_resource_id:
        missing = []
        if not settings.data_gov_in_api_key:
            missing.append("DATA_GOV_IN_API_KEY")
        if not settings.agmarknet_resource_id:
            missing.append("AGMARKNET_RESOURCE_ID")
        return {
            "id": "market", "name": "Market Agent", "status": "configuration_required",
            "headline": "Live mandi data is not configured",
            "summary": "Set the data.gov.in API key and current Agmarknet resource ID in the backend .env file. This agent will not substitute sample prices for live market data.",
            "data": {"commodity": commodity, "missing_environment": missing},
            "actions": ["Configure the required market data credentials", "Retry to retrieve mandi arrivals and prices"],
            "source": "data.gov.in / Agmarknet API", "live": False,
        }

    params = {
        "api-key": settings.data_gov_in_api_key,
        "format": "json",
        "limit": 100,
    }
    # Agmarknet resource field names are case-sensitive in the data.gov.in API.
    filters = {
        "Commodity": commodity,
        "State": request.state,
        "District": request.district,
        "Market": request.mandi,
    }
    for key, value in filters.items():
        if value:
            params[f"filters[{key}]"] = value
    url = f"https://api.data.gov.in/resource/{settings.agmarknet_resource_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        records = payload.get("records") or []
        parsed = [_normalise_record(record) for record in records]
        parsed = [record for record in parsed if record.get("modal_price") is not None]
        if not parsed:
            return {
                "id": "market", "name": "Market Agent", "status": "no_data",
                "headline": "No matching mandi records returned",
                "summary": "The provider responded, but no usable price records matched the filters. Check commodity spelling, state, district, mandi, and resource ID.",
                "data": {"commodity": commodity, "records_received": len(records)},
                "actions": ["Review the selected mandi filters"], "source": "data.gov.in / Agmarknet API", "live": False,
            }
        parsed.sort(key=lambda item: item.get("arrival_date") or "", reverse=True)
        grouped = defaultdict(list)
        for record in parsed:
            grouped[record.get("arrival_date") or "undated"].append(record["modal_price"])
        daily = sorted(
            [{"date": day, "modal_price": round(sum(values) / len(values), 2)} for day, values in grouped.items() if day != "undated"],
            key=lambda item: item["date"],
        )
        forecast = _trend_forecast(daily)
        latest = parsed[0]
        return {
            "id": "market", "name": "Market Agent", "status": "completed",
            "headline": f"Latest modal price: ₹{latest['modal_price']:,.0f}/quintal",
            "summary": f"Retrieved {len(parsed)} mandi price records for {commodity}. Forecast is a simple trend projection, not a guaranteed future price.",
            "data": {
                "commodity": commodity,
                "latest": latest,
                "records": parsed[:20],
                "daily_series": daily[-14:],
                "forecast": forecast,
                "total_records": len(parsed),
            },
            "actions": ["Compare nearby mandis before dispatch", "Recheck prices on the planned sale date", "Treat the trend projection as indicative only"],
            "source": "data.gov.in / Agmarknet API", "live": True,
        }
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "id": "market", "name": "Market Agent", "status": "unavailable",
            "headline": "Mandi data could not be retrieved",
            "summary": "The market-data request failed. Verify the API key, resource ID, provider access, and filters. No estimated live price is displayed.",
            "data": {"reason": str(exc)[:240], "commodity": commodity},
            "actions": ["Check the market API configuration and retry"],
            "source": "data.gov.in / Agmarknet API", "live": False,
        }


def _normalise_record(record: dict) -> dict:
    lower = {str(key).lower().replace(" ", "_"): value for key, value in record.items()}
    price_value = lower.get("modal_price") or lower.get("modal price")
    try:
        price = float(str(price_value).replace(",", "")) if price_value not in (None, "") else None
        if price is not None and not math.isfinite(price):
            price = None
    except (TypeError, ValueError):
        price = None
    return {
        "commodity": lower.get("commodity"),
        "market": lower.get("market") or lower.get("mandi"),
        "district": lower.get("district"),
        "state": lower.get("state"),
        "arrival_date": _normalise_date(lower.get("arrival_date") or lower.get("date")),
        "min_price": _number(lower.get("min_price")),
        "max_price": _number(lower.get("max_price")),
        "modal_price": price,
        "unit": "INR/quintal",
    }


def _normalise_date(value):
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def _number(value):
    try:
        return float(str(value).replace(",", "")) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _trend_forecast(daily: list[dict]) -> list[dict]:
    if len(daily) < 3:
        return []
    points = [item["modal_price"] for item in daily[-7:]]
    n = len(points)
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(points) / n
    denom = sum((x - x_mean) ** 2 for x in xs)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, points)) / denom if denom else 0
    intercept = y_mean - slope * x_mean
    last_date = daily[-1]["date"]
    try:
        last = datetime.strptime(last_date, "%Y-%m-%d")
    except ValueError:
        return []
    return [
        {"date": (last.fromordinal(last.toordinal() + day)).strftime("%Y-%m-%d"),
         "projected_modal_price": round(max(0, intercept + slope * (n - 1 + day)), 2)}
        for day in range(1, 4)
    ]
