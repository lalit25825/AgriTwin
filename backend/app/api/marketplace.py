import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.models.marketplace import (
    ConnectionMessage,
    StakeholderConnection,
    StakeholderProfile,
    SupplyListing,
)
from backend.app.models.user import User
from backend.app.security.dependencies import get_current_active_user

router = APIRouter(prefix="/marketplace", tags=["Agricultural stakeholder network"])
connections_router = APIRouter(prefix="/connections", tags=["Stakeholder connections & messages"])

ROLE_LABELS = {
    "farmer": "Farmer", "driver": "Driver / Vehicle owner", "storage_owner": "Storage owner",
    "mandi_seller": "Mandi seller / trader", "mandi_owner": "Mandi owner / operator",
    "fpo_manager": "FPO manager", "buyer": "Buyer", "transporter": "Transporter",
    "storage_provider": "Storage provider", "fpo": "FPO manager", "admin": "Administrator",
}
ROLE_ALLOWED_CATEGORIES = {
    "farmer": {"produce", "need_transport", "need_storage", "need_buyer", "need_fpo_support"},
    "driver": {"transport"},
    "transporter": {"transport"},
    "storage_owner": {"storage"},
    "storage_provider": {"storage"},
    "mandi_seller": {"buying"},
    "buyer": {"buying"},
    "mandi_owner": {"mandi_service"},
    "fpo_manager": {"fpo_service", "produce", "need_transport", "need_storage", "need_buyer"},
    "fpo": {"fpo_service", "produce", "need_transport", "need_storage", "need_buyer"},
    "admin": {"produce", "need_transport", "need_storage", "need_buyer", "need_fpo_support", "transport", "storage", "buying", "mandi_service", "fpo_service"},
}
CATEGORY_LABELS = {
    "produce": "Crop for sale", "need_transport": "Transport needed", "need_storage": "Storage needed",
    "need_buyer": "Looking for buyers", "need_fpo_support": "FPO support needed", "transport": "Transport service",
    "storage": "Storage capacity", "buying": "Buying produce", "mandi_service": "Mandi service",
    "fpo_service": "FPO services",
}
COMPATIBILITY = {
    "farmer": {"driver": 96, "storage_owner": 94, "mandi_seller": 95, "mandi_owner": 84, "fpo_manager": 93},
    "driver": {"farmer": 96, "storage_owner": 82, "mandi_seller": 78, "mandi_owner": 90, "fpo_manager": 86},
    "storage_owner": {"farmer": 94, "driver": 82, "mandi_seller": 89, "mandi_owner": 88, "fpo_manager": 86},
    "mandi_seller": {"farmer": 95, "driver": 78, "storage_owner": 89, "mandi_owner": 96, "fpo_manager": 92},
    "mandi_owner": {"farmer": 84, "driver": 90, "storage_owner": 88, "mandi_seller": 96, "fpo_manager": 91},
    "fpo_manager": {"farmer": 98, "driver": 86, "storage_owner": 87, "mandi_seller": 94, "mandi_owner": 91},
    "transporter": {"farmer": 96, "storage_owner": 82, "mandi_seller": 78, "mandi_owner": 90, "fpo_manager": 86},
    "storage_provider": {"farmer": 94, "driver": 82, "mandi_seller": 89, "mandi_owner": 88, "fpo_manager": 86},
    "buyer": {"farmer": 95, "driver": 78, "storage_owner": 89, "mandi_owner": 96, "fpo_manager": 92},
    "fpo": {"farmer": 98, "driver": 86, "storage_owner": 87, "mandi_seller": 94, "mandi_owner": 91},
}


class ProfileUpdate(BaseModel):
    organization: str | None = Field(default=None, max_length=140)
    headline: str | None = Field(default=None, max_length=160)
    village: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    about: str | None = Field(default=None, max_length=1200)
    commodities: list[str] = Field(default_factory=list, max_length=30)
    capacity_tonnes: float | None = Field(default=None, ge=0)
    vehicle_type: str | None = Field(default=None, max_length=100)
    storage_type: str | None = Field(default=None, max_length=100)
    service_radius_km: int | None = Field(default=None, ge=0, le=1000)
    mandi_name: str | None = Field(default=None, max_length=140)
    license_number: str | None = Field(default=None, max_length=100)


class ListingCreate(BaseModel):
    category: str
    title: str = Field(min_length=5, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    commodity: str | None = Field(default=None, max_length=100)
    quantity_tonnes: float | None = Field(default=None, gt=0)
    capacity_tonnes: float | None = Field(default=None, gt=0)
    price_per_quintal: float | None = Field(default=None, ge=0)
    price_note: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pickup_location: str | None = Field(default=None, max_length=180)
    destination: str | None = Field(default=None, max_length=180)
    available_from: str | None = Field(default=None, max_length=40)
    details: dict[str, Any] = Field(default_factory=dict)


class ListingStatusUpdate(BaseModel):
    is_active: bool


class ConnectionCreate(BaseModel):
    recipient_id: uuid.UUID | None = None
    listing_id: uuid.UUID | None = None
    purpose: str = Field(default="general", max_length=60)
    message: str = Field(min_length=8, max_length=2000)
    commodity: str | None = Field(default=None, max_length=100)
    quantity_tonnes: float | None = Field(default=None, gt=0)
    offered_price: float | None = Field(default=None, ge=0)


class ConnectionStatusUpdate(BaseModel):
    status: str


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=3000)


def _profile_data(profile: StakeholderProfile | None) -> dict:
    if not profile:
        return {}
    keys = ["organization", "headline", "village", "district", "state", "address", "latitude", "longitude", "about", "commodities", "capacity_tonnes", "vehicle_type", "storage_type", "service_radius_km", "mandi_name", "license_number"]
    return {key: getattr(profile, key) for key in keys}


def _public_profile_data(profile: StakeholderProfile | None) -> dict:
    if not profile:
        return {}
    # Exact street address, map coordinates and license numbers stay private.
    keys = ["organization", "headline", "village", "district", "state", "about",
            "commodities", "capacity_tonnes", "vehicle_type", "storage_type",
            "service_radius_km", "mandi_name"]
    return {key: getattr(profile, key) for key in keys}


def _public_person(user: User, profile: StakeholderProfile | None) -> dict:
    return {
        "id": str(user.id), "name": user.full_name, "username": user.username,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "role_label": ROLE_LABELS.get(user.role.value if hasattr(user.role, "value") else str(user.role), "Stakeholder"),
        "is_verified": user.is_verified, "profile": _public_profile_data(profile),
    }


def _listing_data(listing: SupplyListing, owner: User, profile: StakeholderProfile | None, viewer: User | None = None) -> dict:
    return {
        "id": str(listing.id), "owner_id": str(owner.id), "owner_name": owner.full_name,
        "owner_role": owner.role.value if hasattr(owner.role, "value") else str(owner.role),
        "owner_role_label": ROLE_LABELS.get(owner.role.value if hasattr(owner.role, "value") else str(owner.role), "Stakeholder"),
        "owner_verified": owner.is_verified, "owner_profile": _public_profile_data(profile),
        "category": listing.category, "category_label": CATEGORY_LABELS.get(listing.category, listing.category.replace("_", " ").title()),
        "title": listing.title, "description": listing.description, "commodity": listing.commodity,
        "quantity_tonnes": listing.quantity_tonnes, "capacity_tonnes": listing.capacity_tonnes,
        "price_per_quintal": listing.price_per_quintal, "price_note": listing.price_note,
        "location": listing.location, "district": listing.district, "state": listing.state,
        "pickup_location": listing.pickup_location, "destination": listing.destination,
        "available_from": listing.available_from, "details": listing.details or {},
        "is_active": listing.is_active, "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "is_mine": bool(viewer and listing.owner_id == viewer.id),
    }


def _connection_data(connection: StakeholderConnection, requester: User, recipient: User, viewer: User) -> dict:
    other = recipient if requester.id == viewer.id else requester
    return {
        "id": str(connection.id), "requester_id": str(requester.id), "recipient_id": str(recipient.id),
        "other_person": {"id": str(other.id), "name": other.full_name, "username": other.username,
                         "role": other.role.value if hasattr(other.role, "value") else str(other.role),
                         "role_label": ROLE_LABELS.get(other.role.value if hasattr(other.role, "value") else str(other.role), "Stakeholder")},
        "purpose": connection.purpose, "message": connection.message, "commodity": connection.commodity,
        "quantity_tonnes": connection.quantity_tonnes, "offered_price": connection.offered_price,
        "status": connection.status, "is_incoming": connection.recipient_id == viewer.id,
        "created_at": connection.created_at.isoformat() if connection.created_at else None,
        "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
    }


def _match_score(viewer: User, viewer_profile: StakeholderProfile | None, listing: SupplyListing, owner: User, owner_profile: StakeholderProfile | None) -> tuple[int, list[str]]:
    viewer_role = viewer.role.value if hasattr(viewer.role, "value") else str(viewer.role)
    owner_role = owner.role.value if hasattr(owner.role, "value") else str(owner.role)
    score = 35
    reasons: list[str] = []
    compatible_roles = COMPATIBILITY.get(viewer_role, {})
    role_score = compatible_roles.get(owner_role, 35)
    score += round(role_score * 0.20)
    reasons.append("Stakeholder roles work together" if role_score >= 80 else "Potential cross-network connection")

    viewer_commodities = {str(item).strip().lower() for item in ((viewer_profile.commodities or []) if viewer_profile else []) if item}
    if viewer_profile and viewer_role == "farmer" and viewer_profile.headline:
        viewer_commodities.add(viewer_profile.headline.lower())
    if listing.commodity and listing.commodity.strip().lower() in viewer_commodities:
        score += 24
        reasons.append(f"Works with {listing.commodity}")
    elif not listing.commodity:
        score += 7

    v_district = (viewer_profile.district or "").strip().lower() if viewer_profile else ""
    l_district = (listing.district or (owner_profile.district if owner_profile else "") or "").strip().lower()
    v_state = (viewer_profile.state or "").strip().lower() if viewer_profile else ""
    l_state = (listing.state or (owner_profile.state if owner_profile else "") or "").strip().lower()
    if v_district and l_district and v_district == l_district:
        score += 18
        reasons.append("Same district")
    elif v_state and l_state and v_state == l_state:
        score += 12
        reasons.append("Same state")

    requested = listing.quantity_tonnes
    capacity = listing.capacity_tonnes or (owner_profile.capacity_tonnes if owner_profile else None)
    if requested and capacity:
        if capacity >= requested:
            score += 13
            reasons.append("Capacity can cover the quantity")
        else:
            score += 3
            reasons.append("Capacity may need multiple trips or batches")
    elif requested or capacity:
        score += 6

    if listing.price_per_quintal is not None or listing.price_note:
        score += 5
        reasons.append("Commercial terms are visible")
    return min(99, max(25, score)), reasons[:4]


async def _listing_rows(db: AsyncSession, active_only: bool = True):
    stmt = select(SupplyListing, User, StakeholderProfile).join(User, User.id == SupplyListing.owner_id).outerjoin(StakeholderProfile, StakeholderProfile.user_id == User.id)
    if active_only:
        stmt = stmt.where(SupplyListing.is_active.is_(True))
    stmt = stmt.order_by(SupplyListing.created_at.desc()).limit(250)
    return (await db.execute(stmt)).all()


@router.get("/roles")
async def stakeholder_roles():
    roles = ["farmer", "driver", "storage_owner", "mandi_seller", "mandi_owner", "fpo_manager"]
    return {"roles": [{"value": role, "label": ROLE_LABELS[role]} for role in roles]}


@router.get("/connection-matrix")
async def connection_matrix(current_user: User = Depends(get_current_active_user)):
    roles = ["farmer", "driver", "storage_owner", "mandi_seller", "mandi_owner", "fpo_manager"]
    return {
        "roles": [{"value": role, "label": ROLE_LABELS[role]} for role in roles],
        "matrix": [{"from_role": role, "from_label": ROLE_LABELS[role],
                    "scores": {target: COMPATIBILITY.get(role, {}).get(target)
                               for target in roles if target != role}}
                   for role in roles],
        "note": "Workflow-compatibility scores (0–100), not statistical probabilities of successful transactions. Starting weights are expert-defined and need calibration against real completed and failed transactions.",
    }


@router.get("/connection-map")
async def connection_map(current_user: User = Depends(get_current_active_user)):
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    scores = COMPATIBILITY.get(role, COMPATIBILITY["farmer"])
    workflows = {
        "farmer": ["Move produce from farm", "Find a safe storage slot", "Compare and negotiate mandi offers", "Aggregate quantity through an FPO"],
        "driver": ["Collect produce from farms", "Deliver to storage or mandi", "Coordinate return loads"],
        "storage_owner": ["Receive harvest from farmers", "Hold inventory for traders and FPOs", "Arrange onward dispatch with drivers"],
        "mandi_seller": ["Source produce from farms and FPOs", "Connect with mandi operators", "Arrange storage and transportation"],
        "mandi_owner": ["Connect buyers and sellers", "Coordinate gate, weighing and auction services", "Schedule inbound vehicles"],
        "fpo_manager": ["Aggregate member produce", "Consolidate transport and storage demand", "Negotiate bulk sales with traders"],
    }
    return {
        "current_role": role,
        "note": "These are workflow-compatibility scores (0–100), not measured probabilities of a successful transaction. They are expert-defined starting weights and should be calibrated against real platform outcomes.",
        "connections": [{"role": key, "label": ROLE_LABELS[key], "score": value, "workflows": workflows.get(role, [])} for key, value in scores.items()],
    }


@router.get("/profile/me")
async def get_my_profile(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await db.get(StakeholderProfile, current_user.id)
    return {"user": {"id": str(current_user.id), "full_name": current_user.full_name, "username": current_user.username,
                     "email": current_user.email, "phone": current_user.phone,
                     "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)},
            "profile": _profile_data(profile)}


@router.put("/profile/me")
async def update_my_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await db.get(StakeholderProfile, current_user.id)
    if not profile:
        profile = StakeholderProfile(user_id=current_user.id)
        db.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return {"message": "Profile saved", "profile": _profile_data(profile)}


@router.get("/dashboard")
async def dashboard(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await db.get(StakeholderProfile, current_user.id)
    own_listings = await db.scalar(select(func.count(SupplyListing.id)).where(SupplyListing.owner_id == current_user.id, SupplyListing.is_active.is_(True))) or 0
    incoming = await db.scalar(select(func.count(StakeholderConnection.id)).where(StakeholderConnection.recipient_id == current_user.id, StakeholderConnection.status == "pending")) or 0
    outgoing = await db.scalar(select(func.count(StakeholderConnection.id)).where(StakeholderConnection.requester_id == current_user.id, StakeholderConnection.status == "pending")) or 0
    active_connections = await db.scalar(select(func.count(StakeholderConnection.id)).where(or_(StakeholderConnection.requester_id == current_user.id, StakeholderConnection.recipient_id == current_user.id), StakeholderConnection.status == "accepted")) or 0
    matches = []
    for listing, owner, owner_profile in await _listing_rows(db):
        if owner.id == current_user.id:
            continue
        score, reasons = _match_score(current_user, profile, listing, owner, owner_profile)
        matches.append({**_listing_data(listing, owner, owner_profile, current_user), "match_score": score, "match_reasons": reasons})
    matches.sort(key=lambda item: (item["match_score"], item["created_at"] or ""), reverse=True)
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    role_copy = {
        "farmer": ("Your crop, your choices.", "Find transport, compare storage, reach buyers and coordinate your next move from one place."),
        "driver": ("Loads worth driving for.", "Discover nearby produce movements, connect with farmers and keep your vehicle capacity working."),
        "storage_owner": ("Turn free capacity into business.", "Publish available space and connect directly with farmers, FPOs and traders."),
        "mandi_seller": ("Source produce with confidence.", "Find farmers and FPO supply, share buying requirements and negotiate directly."),
        "mandi_owner": ("Keep your market connected.", "Coordinate sellers, buyers, vehicles and storage around your mandi operations."),
        "fpo_manager": ("Coordinate the whole network.", "Aggregate member produce and connect your FPO with transport, storage and buyers."),
    }
    from sqlalchemy.orm import aliased
    Requester = aliased(User)
    Recipient = aliased(User)
    recent_stmt = (select(StakeholderConnection, Requester, Recipient)
                   .join(Requester, Requester.id == StakeholderConnection.requester_id)
                   .join(Recipient, Recipient.id == StakeholderConnection.recipient_id)
                   .where(StakeholderConnection.recipient_id == current_user.id)
                   .order_by(StakeholderConnection.created_at.desc()).limit(5))
    recent_rows = (await db.execute(recent_stmt)).all()
    recent = [_connection_data(conn, requester, recipient, current_user)
              for conn, requester, recipient in recent_rows]
    return {
        "user": {"id": str(current_user.id), "name": current_user.full_name, "role": role, "role_label": ROLE_LABELS.get(role, "Stakeholder")},
        "welcome": {"title": role_copy.get(role, ("Your supply chain, connected.", "Coordinate partners across the agricultural value chain."))[0],
                    "subtitle": role_copy.get(role, ("Your supply chain, connected.", "Coordinate partners across the agricultural value chain."))[1]},
        "metrics": {"active_listings": int(own_listings), "incoming_requests": int(incoming), "outgoing_requests": int(outgoing), "active_connections": int(active_connections), "recommended_matches": len(matches)},
        "profile": _profile_data(profile), "profile_completion": _profile_completion(profile),
        "recommended_matches": matches[:8], "recent_requests": recent,
        "connection_note": "Match scores are guidance based on role fit, commodity, location and capacity. They are not guarantees or statistical win probabilities.",
    }


def _profile_completion(profile: StakeholderProfile | None) -> int:
    if not profile:
        return 0
    fields = [profile.organization, profile.district, profile.state, profile.about, profile.commodities, profile.capacity_tonnes]
    return round(sum(bool(value) for value in fields) / len(fields) * 100)


@router.get("/directory")
async def directory(role: str | None = None, district: str | None = None, state: str | None = None,
                    q: str | None = None, limit: int = Query(default=60, ge=1, le=100),
                    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    stmt = select(User, StakeholderProfile).outerjoin(StakeholderProfile, StakeholderProfile.user_id == User.id).where(User.is_active.is_(True), User.id != current_user.id)
    if role:
        allowed = {item.value for item in UserRole}
        if role not in allowed:
            raise HTTPException(status_code=422, detail="Unknown stakeholder role")
        stmt = stmt.where(User.role == role)
    if district:
        stmt = stmt.where(func.lower(StakeholderProfile.district) == district.lower())
    if state:
        stmt = stmt.where(func.lower(StakeholderProfile.state) == state.lower())
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), StakeholderProfile.organization.ilike(pattern), StakeholderProfile.commodities.cast(String).ilike(pattern)))
    rows = (await db.execute(stmt.order_by(User.created_at.desc()).limit(limit))).all()
    people = []
    my_profile = await db.get(StakeholderProfile, current_user.id)
    for user, profile in rows:
        role_key = user.role.value if hasattr(user.role, "value") else str(user.role)
        current_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        base_score = COMPATIBILITY.get(current_role, {}).get(role_key, 42)
        score = min(99, base_score + (8 if profile and my_profile and profile.district and my_profile.district and profile.district.lower() == my_profile.district.lower() else 0))
        people.append({**_public_person(user, profile), "match_score": score})
    return {"people": people, "count": len(people)}


@router.get("/listings")
async def listings(category: str | None = None, commodity: str | None = None, district: str | None = None,
                   state: str | None = None, q: str | None = None, limit: int = Query(default=80, ge=1, le=150),
                   current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    rows = await _listing_rows(db)
    output = []
    for listing, owner, profile in rows:
        if category and listing.category != category:
            continue
        if commodity and (listing.commodity or "").lower() != commodity.lower():
            continue
        if district and (listing.district or (profile.district if profile else "") or "").lower() != district.lower():
            continue
        if state and (listing.state or (profile.state if profile else "") or "").lower() != state.lower():
            continue
        if q and q.lower() not in " ".join([listing.title or "", listing.description or "", listing.commodity or "", listing.location or "", owner.full_name or ""]).lower():
            continue
        item = _listing_data(listing, owner, profile, current_user)
        if owner.id != current_user.id:
            item["match_score"], item["match_reasons"] = _match_score(current_user, await db.get(StakeholderProfile, current_user.id), listing, owner, profile)
        else:
            item["match_score"], item["match_reasons"] = None, []
        output.append(item)
        if len(output) >= limit:
            break
    return {"listings": output, "count": len(output)}


@router.post("/listings", status_code=status.HTTP_201_CREATED)
async def create_listing(payload: ListingCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    allowed = ROLE_ALLOWED_CATEGORIES.get(role, set())
    if payload.category not in allowed:
        raise HTTPException(status_code=403, detail=f"Your {ROLE_LABELS.get(role, role)} account cannot publish this listing type")
    data = payload.model_dump()
    listing = SupplyListing(owner_id=current_user.id, **data)
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    profile = await db.get(StakeholderProfile, current_user.id)
    return _listing_data(listing, current_user, profile, current_user)


@router.patch("/listings/{listing_id}")
async def update_listing_status(listing_id: uuid.UUID, payload: ListingStatusUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    listing = await db.get(SupplyListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the listing owner can change its status")
    listing.is_active = payload.is_active
    await db.commit()
    return {"message": "Listing updated", "is_active": listing.is_active}


@connections_router.get("")
async def get_connections(box: str = Query(default="all", pattern="^(all|incoming|outgoing)$"),
                          current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    # Use explicit aliases so each side of the connection is represented independently.
    from sqlalchemy.orm import aliased
    Requester = aliased(User)
    Recipient = aliased(User)
    stmt = select(StakeholderConnection, Requester, Recipient).join(Requester, Requester.id == StakeholderConnection.requester_id).join(Recipient, Recipient.id == StakeholderConnection.recipient_id)
    if box == "incoming":
        stmt = stmt.where(StakeholderConnection.recipient_id == current_user.id)
    elif box == "outgoing":
        stmt = stmt.where(StakeholderConnection.requester_id == current_user.id)
    else:
        stmt = stmt.where(or_(StakeholderConnection.requester_id == current_user.id, StakeholderConnection.recipient_id == current_user.id))
    rows = (await db.execute(stmt.order_by(StakeholderConnection.created_at.desc()).limit(150))).all()
    return {"connections": [_connection_data(conn, requester, recipient, current_user) for conn, requester, recipient in rows], "count": len(rows)}


@connections_router.post("", status_code=status.HTTP_201_CREATED)
async def create_connection(payload: ConnectionCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    listing = None
    recipient_id = payload.recipient_id
    if payload.listing_id:
        listing = await db.get(SupplyListing, payload.listing_id)
        if not listing or not listing.is_active:
            raise HTTPException(status_code=404, detail="Active listing not found")
        if listing.owner_id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot connect to your own listing")
        if recipient_id and recipient_id != listing.owner_id:
            raise HTTPException(status_code=400, detail="Recipient does not own this listing")
        recipient_id = listing.owner_id
    if not recipient_id:
        raise HTTPException(status_code=422, detail="Provide recipient_id or listing_id")
    if recipient_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot connect to yourself")
    recipient = await db.get(User, recipient_id)
    if not recipient or not recipient.is_active:
        raise HTTPException(status_code=404, detail="Stakeholder account not found")
    existing = await db.scalar(select(StakeholderConnection).where(
        StakeholderConnection.requester_id == current_user.id,
        StakeholderConnection.recipient_id == recipient_id,
        StakeholderConnection.status.in_(["pending", "accepted"]),
        StakeholderConnection.listing_id == (listing.id if listing else None),
    ))
    if existing:
        raise HTTPException(status_code=409, detail="An open connection already exists for this stakeholder and listing")
    connection = StakeholderConnection(
        requester_id=current_user.id, recipient_id=recipient_id,
        listing_id=listing.id if listing else None, purpose=payload.purpose,
        message=payload.message, commodity=payload.commodity or (listing.commodity if listing else None),
        quantity_tonnes=payload.quantity_tonnes or (listing.quantity_tonnes if listing else None),
        offered_price=payload.offered_price,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return {"message": "Connection request sent", "id": str(connection.id), "status": connection.status}


@connections_router.patch("/{connection_id}")
async def update_connection(connection_id: uuid.UUID, payload: ConnectionStatusUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"accepted", "declined", "completed", "cancelled"}:
        raise HTTPException(status_code=422, detail="Status must be accepted, declined, completed, or cancelled")
    connection = await db.get(StakeholderConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection request not found")
    if current_user.id not in {connection.requester_id, connection.recipient_id} and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You are not part of this connection")
    if payload.status in {"accepted", "declined"}:
        if connection.recipient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the recipient can accept or decline this request")
        if connection.status != "pending":
            raise HTTPException(status_code=409, detail="Only pending requests can be accepted or declined")
    if payload.status == "cancelled":
        if connection.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the requester can cancel this request")
        if connection.status != "pending":
            raise HTTPException(status_code=409, detail="Only pending requests can be cancelled")
    if payload.status == "completed" and connection.status != "accepted":
        raise HTTPException(status_code=409, detail="Only accepted connections can be completed")
    connection.status = payload.status
    await db.commit()
    return {"message": f"Connection {payload.status}", "status": connection.status}


async def _get_accepted_connection(connection_id: uuid.UUID, current_user: User, db: AsyncSession) -> StakeholderConnection:
    connection = await db.get(StakeholderConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    if current_user.id not in {connection.requester_id, connection.recipient_id}:
        raise HTTPException(status_code=403, detail="You are not part of this connection")
    if connection.status != "accepted":
        raise HTTPException(status_code=409, detail="Messaging opens after the connection is accepted")
    return connection


@connections_router.get("/{connection_id}/messages")
async def get_messages(connection_id: uuid.UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    await _get_accepted_connection(connection_id, current_user, db)
    rows = (await db.execute(select(ConnectionMessage, User).join(User, User.id == ConnectionMessage.sender_id).where(ConnectionMessage.connection_id == connection_id).order_by(ConnectionMessage.created_at.asc()).limit(300))).all()
    return {"messages": [{"id": str(message.id), "sender_id": str(message.sender_id), "sender_name": sender.full_name, "body": message.body, "created_at": message.created_at.isoformat() if message.created_at else None, "is_mine": message.sender_id == current_user.id} for message, sender in rows]}


@connections_router.post("/{connection_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(connection_id: uuid.UUID, payload: MessageCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    await _get_accepted_connection(connection_id, current_user, db)
    message = ConnectionMessage(connection_id=connection_id, sender_id=current_user.id, body=payload.body.strip())
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return {"id": str(message.id), "sender_name": current_user.full_name, "body": message.body, "created_at": message.created_at.isoformat() if message.created_at else None}
