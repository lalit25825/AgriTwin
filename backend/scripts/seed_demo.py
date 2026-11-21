"""Create clearly labelled local demo stakeholders and listings.

Run only for a local demonstration:
    python -m backend.scripts.seed_demo --confirm-demo-data
All six demo users use the password printed by this script. Never expose these
accounts in a deployed environment.
"""
import argparse
import asyncio
import uuid
from datetime import date, timedelta

from sqlalchemy import or_, select

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.enums import AuthProvider, UserRole
from backend.app.models.marketplace import ConnectionMessage, StakeholderConnection, StakeholderProfile, SupplyListing
from backend.app.models.user import User
from backend.app.models.role_workspace import FarmPlot, StakeholderOperation
from backend.app.security.password import hash_password

DEMO_PASSWORD = "AgriTwinDemo!2026"
DEMO_USERS = [
    {"username": "demo_farmer", "full_name": "Demo Farmer · Ramesh Patil", "email": "demo.farmer@agritwin.local", "phone": "9000000001", "role": UserRole.FARMER,
     "profile": {"organization": "Patil Family Farms (DEMO)", "headline": "Onion grower · 8 tonnes available", "village": "Sinnar", "district": "Nashik", "state": "Maharashtra", "latitude": 19.845, "longitude": 73.985, "about": "Demo farmer profile. Growing red onion and looking for transparent transport, storage and buyer connections.", "commodities": ["Onion", "Tomato"], "capacity_tonnes": 8}},
    {"username": "demo_driver", "full_name": "Demo Driver · Ganesh Jadhav", "email": "demo.driver@agritwin.local", "phone": "9000000002", "role": UserRole.DRIVER,
     "profile": {"organization": "Jadhav Transport (DEMO)", "headline": "12-tonne truck · Nashik routes", "village": "Sinnar", "district": "Nashik", "state": "Maharashtra", "latitude": 19.845, "longitude": 73.985, "about": "Demo vehicle owner offering farm pickup and mandi deliveries. Confirm timing and freight before booking.", "commodities": ["Onion", "Tomato", "Grapes"], "capacity_tonnes": 12, "vehicle_type": "12-tonne covered truck", "service_radius_km": 180}},
    {"username": "demo_storage", "full_name": "Demo Storage · Sahyadri Warehousing", "email": "demo.storage@agritwin.local", "phone": "9000000003", "role": UserRole.STORAGE_OWNER,
     "profile": {"organization": "Sahyadri Warehousing (DEMO)", "headline": "Ventilated onion storage", "village": "Lasalgaon", "district": "Nashik", "state": "Maharashtra", "about": "Demo storage provider. Availability, quality standards and storage charges must be confirmed directly.", "commodities": ["Onion", "Potato"], "capacity_tonnes": 1200, "storage_type": "Ventilated onion storage", "service_radius_km": 100}},
    {"username": "demo_trader", "full_name": "Demo Trader · Kisan Fresh Trading", "email": "demo.trader@agritwin.local", "phone": "9000000004", "role": UserRole.MANDI_SELLER,
     "profile": {"organization": "Kisan Fresh Trading (DEMO)", "headline": "Onion buyer · Lasalgaon market", "village": "Lasalgaon", "district": "Nashik", "state": "Maharashtra", "about": "Demo mandi trader buying graded produce. Final price depends on quality, grade, weight and market conditions.", "commodities": ["Onion", "Tomato"], "capacity_tonnes": 40, "mandi_name": "Lasalgaon APMC"}},
    {"username": "demo_mandi", "full_name": "Demo Mandi · Lasalgaon Market Desk", "email": "demo.mandi@agritwin.local", "phone": "9000000005", "role": UserRole.MANDI_OWNER,
     "profile": {"organization": "Lasalgaon Market Desk (DEMO)", "headline": "Mandi coordination and facilities", "village": "Lasalgaon", "district": "Nashik", "state": "Maharashtra", "about": "Demo mandi operator profile for market coordination, arrivals and facility enquiries.", "commodities": ["Onion"], "mandi_name": "Lasalgaon APMC"}},
    {"username": "demo_fpo", "full_name": "Demo FPO · Nashik Farmer Collective", "email": "demo.fpo@agritwin.local", "phone": "9000000006", "role": UserRole.FPO_MANAGER,
     "profile": {"organization": "Nashik Farmer Collective FPO (DEMO)", "headline": "Aggregation and farmer coordination", "village": "Niphad", "district": "Nashik", "state": "Maharashtra", "about": "Demo FPO manager coordinating farmer aggregation, bulk transport and buyer connections.", "commodities": ["Onion", "Tomato", "Grapes"], "capacity_tonnes": 100}},
]

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-demo-data", action="store_true", help="Confirm that clearly labelled demo data should be added")
    args = parser.parse_args()
    if not args.confirm_demo_data:
        parser.error("Pass --confirm-demo-data to add demo accounts and listings")

    async with AsyncSessionLocal() as db:
        users: dict[str, User] = {}
        for spec in DEMO_USERS:
            user = await db.scalar(select(User).where(User.username == spec["username"]))
            if user is None:
                user = User(
                    id=uuid.uuid4(), username=spec["username"], full_name=spec["full_name"],
                    email=spec["email"], phone=spec["phone"], password_hash=hash_password(DEMO_PASSWORD),
                    auth_provider=AuthProvider.LOCAL, role=spec["role"], is_active=True, is_verified=False,
                )
                db.add(user)
                await db.flush()
            users[spec["username"]] = user
            profile = await db.get(StakeholderProfile, user.id)
            if profile is None:
                db.add(StakeholderProfile(user_id=user.id, **spec["profile"]))
            else:
                # Fill only missing demonstration profile values; never overwrite a real value.
                for field, value in spec["profile"].items():
                    if getattr(profile, field, None) in (None, "", []):
                        setattr(profile, field, value)
        await db.flush()

        farmer = users["demo_farmer"]
        driver = users["demo_driver"]
        storage = users["demo_storage"]
        trader = users["demo_trader"]
        mandi = users["demo_mandi"]
        fpo = users["demo_fpo"]
        existing = await db.scalar(select(SupplyListing.id).limit(1))
        if existing is None:
            sample_listings = [
                SupplyListing(owner_id=farmer.id, category="produce", title="8 tonnes of red onion ready for buyer discussion", description="DEMO listing. Medium-size red onion; grade, moisture, packaging and final weighment to be confirmed before sale.", commodity="Onion", quantity_tonnes=8, price_per_quintal=2400, price_note="Indicative asking price · negotiable after grading", location="Sinnar", district="Nashik", state="Maharashtra"),
                SupplyListing(owner_id=farmer.id, category="need_transport", title="Need a truck for 8 tonnes of onion", description="DEMO requirement. Farm pickup from Sinnar with delivery to Lasalgaon market. Confirm loading date and freight directly.", commodity="Onion", quantity_tonnes=8, location="Sinnar", district="Nashik", state="Maharashtra", pickup_location="Sinnar farm", destination="Lasalgaon APMC"),
                SupplyListing(owner_id=driver.id, category="transport", title="12-tonne covered truck available on Nashik routes", description="DEMO service. Farm pickup and mandi delivery. Freight and timings are to be agreed directly.", commodity="Onion", capacity_tonnes=12, price_note="Freight on request", location="Sinnar", district="Nashik", state="Maharashtra", pickup_location="Nashik district", destination="Lasalgaon / nearby mandis"),
                SupplyListing(owner_id=storage.id, category="storage", title="Ventilated onion storage capacity available", description="DEMO capacity. Confirm current vacancy, storage method, handling, insurance and charges before delivery.", commodity="Onion", capacity_tonnes=1200, price_note="Storage charges on enquiry", location="Lasalgaon", district="Nashik", state="Maharashtra"),
                SupplyListing(owner_id=trader.id, category="buying", title="Buying graded red onion for wholesale trade", description="DEMO buying requirement. Interested in farm and FPO lots; grade, size, weight and payment terms will be inspected and agreed.", commodity="Onion", quantity_tonnes=15, price_note="Price after quality inspection", location="Lasalgaon APMC", district="Nashik", state="Maharashtra"),
                SupplyListing(owner_id=mandi.id, category="mandi_service", title="Lasalgaon market coordination desk", description="DEMO service listing for market-arrival and facility enquiries. Confirm current operating rules and fees with the market office.", commodity="Onion", location="Lasalgaon", district="Nashik", state="Maharashtra"),
                SupplyListing(owner_id=fpo.id, category="fpo_service", title="Farmer aggregation and bulk-market coordination", description="DEMO FPO service. Helps member farmers coordinate lots, transport planning and buyer introductions.", commodity="Onion", capacity_tonnes=100, location="Niphad", district="Nashik", state="Maharashtra"),
            ]
            db.add_all(sample_listings)
        existing_connection = await db.scalar(select(StakeholderConnection.id).limit(1))
        if existing_connection is None:
            inbound_driver = StakeholderConnection(
                requester_id=driver.id, recipient_id=farmer.id, purpose="transport",
                message="DEMO request: I have a 12-tonne covered truck available. Can we discuss pickup timing and delivery to Lasalgaon?",
                commodity="Onion", quantity_tonnes=8, status="pending",
            )
            inbound_storage = StakeholderConnection(
                requester_id=storage.id, recipient_id=farmer.id, purpose="storage",
                message="DEMO request: We have ventilated onion storage capacity listed. Would you like to discuss dates and storage charges?",
                commodity="Onion", quantity_tonnes=8, status="pending",
            )
            farmer_trader = StakeholderConnection(
                requester_id=farmer.id, recipient_id=trader.id, purpose="buying_selling",
                message="DEMO connection: I have an onion lot available and would like to discuss grade, inspection and terms.",
                commodity="Onion", quantity_tonnes=8, offered_price=2400, status="accepted",
            )
            db.add_all([inbound_driver, inbound_storage, farmer_trader])
            await db.flush()
            db.add_all([
                ConnectionMessage(connection_id=farmer_trader.id, sender_id=farmer.id, body="Hello, this is a demo conversation. Can you share your required onion grade and size?"),
                ConnectionMessage(connection_id=farmer_trader.id, sender_id=trader.id, body="Certainly. We should confirm grade, sample quality, weight and payment terms before agreeing on a rate."),
            ])
        # Add role-workspace sample records without duplicating them on a later seed run.
        existing_plot = await db.scalar(select(FarmPlot.id).where(FarmPlot.farmer_id == farmer.id).limit(1))
        if existing_plot is None:
            db.add(FarmPlot(
                farmer_id=farmer.id, name="Sinnar North Field (DEMO)", crop="Onion", variety="Red onion",
                sowing_date=date.today() - timedelta(days=112), area_acres=4.5, crop_stage="maturity",
                latitude=19.845, longitude=73.985, irrigation_type="Drip",
                notes="Fictional demo field record. Inspect bulbs and local weather before setting a harvest date.",
            ))

        demo_operations = [
            (driver, "driver_trip", "DEMO trip · Sinnar to Lasalgaon", "Onion", 8, "Sinnar farm", "Lasalgaon APMC", "completed", "Fictional demo delivery record; not a real booking."),
            (storage, "storage_intake", "DEMO onion stock intake", "Onion", 120, "Farm collection", "Demo warehouse bay A", "completed", "Fictional stock intake to demonstrate capacity tracking."),
            (storage, "storage_dispatch", "DEMO onion stock dispatch", "Onion", 25, "Demo warehouse bay A", "Wholesale buyer", "completed", "Fictional stock dispatch to demonstrate capacity tracking."),
            (trader, "purchase_order", "DEMO purchase plan · graded red onion", "Onion", 15, "Farmer / FPO lots", "Lasalgaon trading yard", "planned", "Fictional sourcing plan. Confirm grade, weight and price directly."),
            (mandi, "mandi_arrival", "DEMO gate arrival · onion lot", "Onion", 8, "Sinnar farm", "Lasalgaon APMC Gate 2", "planned", "Fictional expected arrival; not a confirmed gate booking."),
            (fpo, "aggregation_batch", "DEMO aggregation batch · Nashik onion", "Onion", 30, "Member farms · Niphad", "Lasalgaon APMC", "planned", "Fictional aggregation record for dashboard demonstration."),
        ]
        for owner, operation_type, title, commodity, quantity, origin, destination, op_status, notes in demo_operations:
            existing_op = await db.scalar(select(StakeholderOperation.id).where(
                StakeholderOperation.owner_id == owner.id,
                StakeholderOperation.title == title,
            ).limit(1))
            if existing_op is None:
                db.add(StakeholderOperation(
                    owner_id=owner.id, operation_type=operation_type, title=title, commodity=commodity,
                    quantity_tonnes=quantity, origin=origin, destination=destination, status=op_status,
                    scheduled_at=date.today().isoformat(), notes=notes, details={"demo": True},
                ))

        # Ensure FPO demo dashboard has one accepted farmer partner, even if the script was run earlier.
        fpo_link = await db.scalar(select(StakeholderConnection.id).where(
            or_(
                (StakeholderConnection.requester_id == farmer.id) & (StakeholderConnection.recipient_id == fpo.id),
                (StakeholderConnection.requester_id == fpo.id) & (StakeholderConnection.recipient_id == farmer.id),
            )
        ).limit(1))
        if fpo_link is None:
            db.add(StakeholderConnection(
                requester_id=fpo.id, recipient_id=farmer.id, purpose="fpo_support",
                message="DEMO connection: This FPO can coordinate farmer aggregation, transport and buyer introductions.",
                commodity="Onion", quantity_tonnes=8, status="accepted",
            ))

        await db.commit()

    print("AgriTwin demo data is ready.")
    print("Demo password for all six demo accounts:", DEMO_PASSWORD)
    print("Accounts:")
    for spec in DEMO_USERS:
        print(f"  {spec['username']}  |  {spec['email']}  |  {spec['role'].value}")
    print("WARNING: Demo profiles and listings are fictional. Do not use these accounts in production.")

if __name__ == "__main__":
    asyncio.run(main())
