import math
import uuid
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents import climate_agent
from backend.app.agents.schemas import AgentRunRequest
from backend.app.core.database import get_db
from backend.app.models.marketplace import StakeholderConnection, StakeholderProfile, SupplyListing
from backend.app.models.role_workspace import FarmPlot, StakeholderOperation
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_active_user

router = APIRouter(prefix="/workspace", tags=["Role-specific stakeholder workspaces"])

ROLE_LABELS = {
    "farmer": "Farmer", "driver": "Driver / vehicle owner", "storage_owner": "Storage owner",
    "mandi_seller": "Mandi seller / trader", "mandi_owner": "Mandi owner / operator", "fpo_manager": "FPO manager",
    "buyer": "Buyer", "transporter": "Transporter", "storage_provider": "Storage provider", "fpo": "FPO manager",
}

CROP_CYCLES = {
    "onion": (120, 150), "wheat": (110, 130), "soybean": (90, 110), "potato": (90, 120),
    "tomato": (90, 120), "rice": (110, 150), "maize": (90, 120), "chilli": (150, 210),
    "cotton": (150, 180), "grapes": (180, 240), "sugarcane": (300, 365), "tur": (150, 180),
    "chickpea": (95, 120), "groundnut": (100, 130),
}

OPERATION_TYPES = {
    "farmer": {"field_activity", "harvest_plan"},
    "driver": {"driver_trip", "vehicle_service", "delivery_issue"},
    "transporter": {"driver_trip", "vehicle_service", "delivery_issue"},
    "storage_owner": {"storage_intake", "storage_dispatch", "storage_inspection"},
    "storage_provider": {"storage_intake", "storage_dispatch", "storage_inspection"},
    "mandi_seller": {"purchase_order", "trade_offer", "quality_check"},
    "buyer": {"purchase_order", "trade_offer", "quality_check"},
    "mandi_owner": {"mandi_arrival", "auction_slot", "market_service"},
    "fpo_manager": {"aggregation_batch", "member_meeting", "bulk_dispatch"},
    "fpo": {"aggregation_batch", "member_meeting", "bulk_dispatch"},
}


class FarmPlotCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    crop: str = Field(min_length=2, max_length=80)
    variety: str | None = Field(default=None, max_length=100)
    sowing_date: date | None = None
    area_acres: float | None = Field(default=None, gt=0, le=100000)
    crop_stage: Literal["unknown", "sowing", "vegetative", "flowering", "grain_filling", "maturity", "ready", "harvested"] = "unknown"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    irrigation_type: str | None = Field(default=None, max_length=80)
    soil_type: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=1200)


class FarmPlotStageUpdate(BaseModel):
    crop_stage: Literal["unknown", "sowing", "vegetative", "flowering", "grain_filling", "maturity", "ready", "harvested"]


class OperationCreate(BaseModel):
    operation_type: str = Field(min_length=3, max_length=48)
    title: str = Field(min_length=3, max_length=180)
    status: Literal["planned", "pending", "in_progress", "completed", "cancelled"] = "planned"
    commodity: str | None = Field(default=None, max_length=100)
    quantity_tonnes: float | None = Field(default=None, gt=0, le=100000)
    origin: str | None = Field(default=None, max_length=180)
    destination: str | None = Field(default=None, max_length=180)
    scheduled_at: str | None = Field(default=None, max_length=48)
    notes: str | None = Field(default=None, max_length=2000)
    details: dict[str, Any] = Field(default_factory=dict)


class OperationStatusUpdate(BaseModel):
    status: Literal["planned", "pending", "in_progress", "completed", "cancelled", "arrived", "weighed", "auctioned", "dispatched"]


def _role(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _plot_data(plot: FarmPlot) -> dict:
    return {
        "id": str(plot.id), "name": plot.name, "crop": plot.crop, "variety": plot.variety,
        "sowing_date": plot.sowing_date.isoformat() if plot.sowing_date else None,
        "area_acres": plot.area_acres, "crop_stage": plot.crop_stage,
        "latitude": plot.latitude, "longitude": plot.longitude,
        "irrigation_type": plot.irrigation_type, "soil_type": plot.soil_type, "notes": plot.notes,
    }


def _operation_data(op: StakeholderOperation) -> dict:
    return {
        "id": str(op.id), "operation_type": op.operation_type, "title": op.title, "status": op.status,
        "commodity": op.commodity, "quantity_tonnes": op.quantity_tonnes, "origin": op.origin,
        "destination": op.destination, "scheduled_at": op.scheduled_at, "notes": op.notes,
        "details": op.details or {}, "created_at": op.created_at.isoformat() if op.created_at else None,
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _listing_summary(row: tuple[SupplyListing, User, StakeholderProfile | None]) -> dict:
    listing, owner, profile = row
    return {
        "id": str(listing.id), "owner_id": str(owner.id), "owner_name": owner.full_name,
        "owner_role": _role(owner), "owner_role_label": ROLE_LABELS.get(_role(owner), _role(owner).replace("_", " ").title()),
        "title": listing.title, "category": listing.category, "commodity": listing.commodity,
        "quantity_tonnes": listing.quantity_tonnes, "capacity_tonnes": listing.capacity_tonnes,
        "price_per_quintal": listing.price_per_quintal, "price_note": listing.price_note,
        "district": listing.district or (profile.district if profile else None),
        "state": listing.state or (profile.state if profile else None),
        "location": listing.location, "pickup_location": listing.pickup_location,
        "destination": listing.destination, "available_from": listing.available_from,
    }


async def _all_listing_rows(db: AsyncSession):
    stmt = (select(SupplyListing, User, StakeholderProfile)
            .join(User, User.id == SupplyListing.owner_id)
            .outerjoin(StakeholderProfile, StakeholderProfile.user_id == User.id)
            .where(SupplyListing.is_active.is_(True), User.is_active.is_(True))
            .order_by(SupplyListing.created_at.desc()).limit(500))
    return (await db.execute(stmt)).all()


def _nearby(profile: StakeholderProfile | None, other: StakeholderProfile | None, radius_km: float) -> tuple[bool, float | None, str]:
    if profile and other and None not in (profile.latitude, profile.longitude, other.latitude, other.longitude):
        distance = _haversine_km(profile.latitude, profile.longitude, other.latitude, other.longitude)
        return distance <= radius_km, distance, "coordinates"
    if profile and other and profile.district and other.district and profile.district.casefold() == other.district.casefold():
        return True, None, "same_district"
    return False, None, "unknown"


@router.get("/role-dashboard")
async def role_dashboard(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    role = _role(current_user)
    profile = await db.get(StakeholderProfile, current_user.id)
    rows = await _all_listing_rows(db)
    ops = (await db.execute(select(StakeholderOperation).where(StakeholderOperation.owner_id == current_user.id).order_by(StakeholderOperation.created_at.desc()).limit(40))).scalars().all()
    operation_data = [_operation_data(item) for item in ops]
    district = (profile.district or "").strip().casefold() if profile else ""
    commodities = {str(item).strip().casefold() for item in ((profile.commodities or []) if profile else []) if item}
    plots: list[FarmPlot] = []
    alerts: list[dict] = []
    recommendations: list[dict] = []
    role_data: dict[str, Any] = {}

    if role == "farmer":
        plots = (await db.execute(select(FarmPlot).where(FarmPlot.farmer_id == current_user.id).order_by(FarmPlot.created_at.desc()))).scalars().all()
        today = date.today()
        total_area = sum(item.area_acres or 0 for item in plots)
        for plot in plots:
            crop_key = plot.crop.casefold()
            cycle = next((value for key, value in CROP_CYCLES.items() if key in crop_key), None)
            days_old = (today - plot.sowing_date).days if plot.sowing_date else None
            if plot.crop_stage == "ready":
                alerts.append({"level": "attention", "title": f"{plot.name}: maturity check", "message": "Your field is marked as ready. Verify crop-specific maturity signs, quality and weather before booking labour or transport."})
            elif plot.crop_stage == "maturity":
                alerts.append({"level": "attention", "title": f"{plot.name}: field inspection due", "message": "Check crop maturity and quality with local agronomic guidance before choosing a harvest date."})
            elif cycle and days_old is not None and days_old >= cycle[0] - 14 and plot.crop_stage not in {"harvested", "sowing"}:
                alerts.append({"level": "info", "title": f"{plot.name}: harvest window approaching", "message": f"The crop is {days_old} days from sowing. A broad reference cycle for {plot.crop} is {cycle[0]}–{cycle[1]} days; start field checks. This is a planning reminder, not a harvest decision."})
            elif plot.crop_stage == "harvested":
                alerts.append({"level": "success", "title": f"{plot.name}: post-harvest checklist", "message": "Record quantity and grade, arrange drying/curing where applicable, then compare storage and buyer options."})
            elif not plot.sowing_date and plot.crop_stage == "unknown":
                alerts.append({"level": "info", "title": f"{plot.name}: improve crop record", "message": "Add the sowing date and crop stage to receive more useful season reminders."})
        if not plots:
            alerts.append({"level": "info", "title": "Add your first farm plot", "message": "Record crop, sowing date, area and field stage to unlock harvest-window reminders and location-specific weather checks."})

        # Pull one live 3-day forecast per farmer workspace using the first geo-tagged plot.
        geo_plot = next((item for item in plots if item.latitude is not None and item.longitude is not None), None)
        weather = None
        if geo_plot:
            weather_result = await climate_agent.run(AgentRunRequest(
                crop=geo_plot.crop, crop_stage=geo_plot.crop_stage, latitude=geo_plot.latitude,
                longitude=geo_plot.longitude, location=geo_plot.name,
            ))
            weather = weather_result
            if weather_result.get("status") == "completed":
                for message in (weather_result.get("data", {}).get("alerts") or []):
                    no_flag = "no threshold-based weather flag" in message.casefold()
                    alerts.append({"level": "success" if no_flag else "attention", "title": "Weather outlook" if no_flag else "Weather risk alert", "message": message})
            else:
                alerts.append({"level": "info", "title": "Weather provider unavailable", "message": weather_result.get("summary") or "The forecast provider did not return data. Retry later; no values were fabricated."})
        elif plots:
            alerts.append({"level": "info", "title": "Add field coordinates", "message": "Set latitude and longitude on a farm plot to receive a local 3-day forecast. Exact coordinates remain private."})

        harvest_windows = []
        for plot in plots:
            crop_key = plot.crop.casefold()
            cycle = next((value for key, value in CROP_CYCLES.items() if key in crop_key), None)
            if not cycle or not plot.sowing_date:
                continue
            window_start = date.fromordinal(plot.sowing_date.toordinal() + cycle[0])
            window_end = date.fromordinal(plot.sowing_date.toordinal() + cycle[1])
            days_until_start = (window_start - today).days
            harvest_windows.append({
                "plot_id": str(plot.id), "plot_name": plot.name, "crop": plot.crop,
                "days_after_sowing": (today - plot.sowing_date).days,
                "window_start": window_start.isoformat(), "window_end": window_end.isoformat(),
                "days_until_window": days_until_start,
                "status": "harvested" if plot.crop_stage == "harvested" else (
                    "window_open" if window_start <= today <= window_end else
                    "window_passed" if today > window_end else "upcoming"
                ),
                "reference_cycle_days": list(cycle),
            })
        harvest_windows.sort(key=lambda item: (item["status"] != "window_open", abs(item["days_until_window"])))

        relevant = []
        for row in rows:
            item = _listing_summary(row)
            if item["owner_id"] == str(current_user.id):
                continue
            commodity = (item.get("commodity") or "").casefold()
            category = item.get("category")
            score = 0
            reasons = []
            if commodity and commodity in commodities | {p.crop.casefold() for p in plots}:
                score += 40; reasons.append("Matches a crop you grow")
            if district and (item.get("district") or "").casefold() == district:
                score += 30; reasons.append("Same district")
            if category in {"transport", "storage", "buying", "fpo_service"}:
                score += 20; reasons.append("Supports your next supply-chain step")
            if item.get("capacity_tonnes"):
                score += 5
            if score >= 20:
                relevant.append({**item, "fit_score": min(score, 95), "reasons": reasons})
        relevant.sort(key=lambda item: (item["fit_score"], item.get("quantity_tonnes") or 0), reverse=True)
        recommendations = relevant[:8]
        role_data = {
            "plots": [_plot_data(item) for item in plots], "total_area_acres": round(total_area, 2),
            "active_crop_count": sum(1 for item in plots if item.crop_stage != "harvested"),
            "harvest_windows": harvest_windows,
            "weather": weather, "harvest_alerts": alerts,
            "recommendations": recommendations,
            "next_steps": ["Keep sowing dates and crop stages current", "Check market quotes again on the planned sale date", "Compare transport and storage before committing a harvest lot"],
        }

    elif role in {"driver", "transporter"}:
        radius = (profile.service_radius_km if profile and profile.service_radius_km is not None else 100)
        farmers = (await db.execute(select(User, StakeholderProfile).outerjoin(StakeholderProfile, StakeholderProfile.user_id == User.id).where(User.role == "farmer", User.is_active.is_(True)))).all()
        nearby_farmers = 0
        for farmer, farmer_profile in farmers:
            is_near, _, _ = _nearby(profile, farmer_profile, radius)
            if is_near:
                nearby_farmers += 1
        jobs = []
        driver_has_coordinates = bool(profile and profile.latitude is not None and profile.longitude is not None)
        driver_has_location = bool(driver_has_coordinates or district)
        for row in rows:
            item = _listing_summary(row)
            if item["owner_role"] not in {"farmer", "fpo_manager", "fpo"} or item["category"] != "need_transport":
                continue
            owner_profile = row[2]
            is_near, distance, basis = _nearby(profile, owner_profile, radius)
            listing_district = (item.get("district") or "").casefold()
            same_district = bool(district and listing_district == district)
            if driver_has_coordinates:
                include_job = is_near
                distance_basis = basis
            elif district:
                include_job = same_district
                distance_basis = "same_district"
            else:
                include_job = True
                distance_basis = "network_wide_until_location_added"
            if include_job:
                item["approx_distance_km"] = round(distance, 1) if distance is not None else None
                item["distance_basis"] = distance_basis
                required_capacity = item.get("quantity_tonnes")
                available_capacity = profile.capacity_tonnes if profile else None
                item["capacity_fit"] = None if required_capacity is None or available_capacity is None else required_capacity <= available_capacity
                item["capacity_fit_note"] = (
                    "Set vehicle capacity to check this load" if item["capacity_fit"] is None else
                    "Within vehicle capacity" if item["capacity_fit"] else "Load exceeds listed vehicle capacity"
                )
                jobs.append(item)
        jobs.sort(key=lambda item: (item.get("capacity_fit") is False, item.get("approx_distance_km") is None, item.get("approx_distance_km") or 9999))
        jobs.sort(key=lambda item: (item.get("approx_distance_km") is None, item.get("approx_distance_km") or 9999))
        role_data = {
            "service_radius_km": radius, "nearby_farmers": nearby_farmers,
            "available_orders": len(jobs), "open_orders": jobs[:30],
            "location_setup_needed": not driver_has_location,
            "opportunity_scope": "within_radius" if driver_has_coordinates else "same_district" if district else "network_wide_until_location_added",
            "vehicle_capacity_tonnes": profile.capacity_tonnes if profile else None,
            "vehicle_type": profile.vehicle_type if profile else None,
            "route_note": "The route map uses OpenStreetMap geocoding and the public OSRM routing service. It is a road-route estimate and does not include live traffic or guaranteed road restrictions.",
        }

    elif role in {"storage_owner", "storage_provider"}:
        requests = []
        for row in rows:
            item = _listing_summary(row)
            if item["category"] == "need_storage" and (not district or (item.get("district") or "").casefold() == district):
                requests.append(item)
        inbound = sum((item.quantity_tonnes or 0) for item in ops if item.operation_type == "storage_intake" and item.status in {"completed", "in_progress"})
        outbound = sum((item.quantity_tonnes or 0) for item in ops if item.operation_type == "storage_dispatch" and item.status in {"completed", "in_progress"})
        occupied = max(0.0, inbound - outbound)
        capacity = profile.capacity_tonnes if profile and profile.capacity_tonnes is not None else 0
        role_data = {
            "capacity_tonnes": capacity, "occupied_tonnes": round(occupied, 2),
            "available_capacity_tonnes": round(max(0, capacity - occupied), 2) if capacity else None,
            "storage_type": profile.storage_type if profile else None,
            "storage_requests": requests[:30], "inventory_records": operation_data,
            "capacity_note": "Occupancy is calculated from recorded intake minus dispatch entries. Enter all movements to keep this figure useful.",
        }

    elif role in {"mandi_seller", "buyer"}:
        supply = []
        for row in rows:
            item = _listing_summary(row)
            if item["category"] == "produce" and item["owner_role"] in {"farmer", "fpo_manager", "fpo"}:
                matches_crop = not commodities or (item.get("commodity") or "").casefold() in commodities
                if matches_crop and (not district or not item.get("district") or item["district"].casefold() == district):
                    supply.append(item)
        buying = [item for item in operation_data if item["operation_type"] in {"purchase_order", "trade_offer", "quality_check"}]
        role_data = {
            "available_supply": supply[:30], "active_buy_plans": sum(1 for item in buying if item["status"] not in {"completed", "cancelled"}),
            "trade_records": buying, "focus_commodities": sorted(commodities),
            "trade_guidance": ["Compare variety, grade, moisture and size before price negotiation", "Record weighment and deductions", "Agree payment terms and dispatch responsibility in writing"],
        }

    elif role == "mandi_owner":
        mandi_name = (profile.mandi_name or "").casefold() if profile else ""
        arrivals = []
        for row in rows:
            item = _listing_summary(row)
            destination = (item.get("destination") or "").casefold()
            same_district = district and (item.get("district") or "").casefold() == district
            mandi_match = mandi_name and mandi_name in destination
            if item["category"] in {"produce", "need_transport"} and (same_district or mandi_match):
                arrivals.append(item)
        scheduled = [item for item in operation_data if item["operation_type"] in {"mandi_arrival", "auction_slot", "market_service"}]
        role_data = {
            "expected_arrivals": arrivals[:40],
            "scheduled_arrivals": sum(1 for item in scheduled if item["operation_type"] == "mandi_arrival" and item["status"] in {"planned", "pending", "in_progress"}),
            "market_operations": scheduled,
            "mandi_name": profile.mandi_name if profile else None,
            "arrival_note": "Expected arrivals are inferred from active marketplace listings in your district or with a destination matching your mandi. They are not confirmed gate bookings.",
        }

    elif role in {"fpo_manager", "fpo"}:
        accepted = (await db.execute(select(StakeholderConnection).where(
            or_(StakeholderConnection.requester_id == current_user.id, StakeholderConnection.recipient_id == current_user.id),
            StakeholderConnection.status == "accepted",
        ))).scalars().all()
        partner_ids = {item.requester_id if item.recipient_id == current_user.id else item.recipient_id for item in accepted}
        farmer_ids = set()
        if partner_ids:
            connected_farmers = (await db.execute(select(User.id).where(User.id.in_(partner_ids), User.role == "farmer"))).scalars().all()
            farmer_ids = set(connected_farmers)
        farmer_supply = [
            _listing_summary(row) for row in rows
            if row[1].id in farmer_ids and row[0].category == "produce"
        ]
        member_plots = []
        if farmer_ids:
            member_plot_rows = (await db.execute(
                select(FarmPlot, User.full_name)
                .join(User, User.id == FarmPlot.farmer_id)
                .where(FarmPlot.farmer_id.in_(farmer_ids))
                .order_by(FarmPlot.sowing_date.asc().nullslast())
                .limit(100)
            )).all()
            today = date.today()
            for plot, farmer_name in member_plot_rows:
                cycle = next((value for key, value in CROP_CYCLES.items() if key in plot.crop.casefold()), None)
                window_start = date.fromordinal(plot.sowing_date.toordinal() + cycle[0]) if cycle and plot.sowing_date else None
                window_end = date.fromordinal(plot.sowing_date.toordinal() + cycle[1]) if cycle and plot.sowing_date else None
                member_plots.append({
                    "farmer_name": farmer_name, "plot_name": plot.name, "crop": plot.crop,
                    "area_acres": plot.area_acres, "crop_stage": plot.crop_stage,
                    "sowing_date": plot.sowing_date.isoformat() if plot.sowing_date else None,
                    "expected_harvest_start": window_start.isoformat() if window_start else None,
                    "expected_harvest_end": window_end.isoformat() if window_end else None,
                    "days_until_harvest_window": (window_start - today).days if window_start else None,
                })
        local_farmers = (await db.execute(select(User, StakeholderProfile).outerjoin(StakeholderProfile, StakeholderProfile.user_id == User.id).where(User.role == "farmer", User.is_active.is_(True)))).all()
        available_members = sum(1 for user, farmer_profile in local_farmers if district and farmer_profile and (farmer_profile.district or "").casefold() == district)
        batches = [item for item in operation_data if item["operation_type"] in {"aggregation_batch", "bulk_dispatch", "member_meeting"}]
        role_data = {
            "connected_farmers": len(farmer_ids), "local_farmers_in_district": available_members,
            "connected_supply_tonnes": round(sum(item.get("quantity_tonnes") or 0 for item in farmer_supply), 2),
            "member_supply": farmer_supply[:40], "member_crop_watchlist": member_plots,
            "aggregation_records": batches,
            "fpo_guidance": ["Confirm member consent and lot ownership", "Aggregate by crop, grade and dispatch date", "Share transparent weighing, transport and payment records"],
        }
    else:
        role_data = {"message": "This account uses the shared stakeholder workspace. Update your profile role to access role-specific operations."}

    return {
        "role": role, "role_label": ROLE_LABELS.get(role, role.replace("_", " ").title()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alerts": alerts, "recommendations": recommendations,
        "operations": operation_data, "data": role_data,
    }


@router.get("/farm-plots")
async def list_farm_plots(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    if _role(current_user) != "farmer":
        raise HTTPException(status_code=403, detail="Farm plot records are available to farmer accounts")
    plots = (await db.execute(select(FarmPlot).where(FarmPlot.farmer_id == current_user.id).order_by(FarmPlot.created_at.desc()))).scalars().all()
    return {"plots": [_plot_data(item) for item in plots]}


@router.post("/farm-plots", status_code=status.HTTP_201_CREATED)
async def create_farm_plot(payload: FarmPlotCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    if _role(current_user) != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can create farm plot records")
    if (payload.latitude is None) != (payload.longitude is None):
        raise HTTPException(status_code=422, detail="Provide both latitude and longitude, or leave both blank")
    plot = FarmPlot(farmer_id=current_user.id, **payload.model_dump())
    db.add(plot)
    await db.commit()
    await db.refresh(plot)
    return {"message": "Farm plot saved", "plot": _plot_data(plot)}


@router.patch("/farm-plots/{plot_id}")
async def update_farm_plot(plot_id: uuid.UUID, payload: FarmPlotStageUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    plot = await db.get(FarmPlot, plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="Farm plot not found")
    if plot.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own farm plots")
    plot.crop_stage = payload.crop_stage
    await db.commit()
    await db.refresh(plot)
    return {"message": "Crop stage updated", "plot": _plot_data(plot)}


@router.delete("/farm-plots/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farm_plot(plot_id: uuid.UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    plot = await db.get(FarmPlot, plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="Farm plot not found")
    if plot.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only remove your own farm plots")
    await db.delete(plot)
    await db.commit()


@router.get("/operations")
async def list_operations(limit: int = Query(default=50, ge=1, le=100), current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(StakeholderOperation).where(StakeholderOperation.owner_id == current_user.id).order_by(StakeholderOperation.created_at.desc()).limit(limit))).scalars().all()
    return {"operations": [_operation_data(item) for item in rows]}


@router.post("/operations", status_code=status.HTTP_201_CREATED)
async def create_operation(payload: OperationCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    role = _role(current_user)
    allowed = OPERATION_TYPES.get(role, set())
    if payload.operation_type not in allowed:
        raise HTTPException(status_code=403, detail=f"The {ROLE_LABELS.get(role, role)} workspace cannot create this operation type")
    operation = StakeholderOperation(owner_id=current_user.id, **payload.model_dump())
    db.add(operation)
    await db.commit()
    await db.refresh(operation)
    return {"message": "Operation saved", "operation": _operation_data(operation)}


@router.patch("/operations/{operation_id}")
async def update_operation(operation_id: uuid.UUID, payload: OperationStatusUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    operation = await db.get(StakeholderOperation, operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")
    if operation.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own operations")
    operation.status = payload.status
    await db.commit()
    await db.refresh(operation)
    return {"message": "Operation status updated", "operation": _operation_data(operation)}
