from backend.app.agents.schemas import AgentRunRequest


PROFILES = {
    "rice": ("Dry, clean grain before long-term storage", "Use a clean, dry, pest-managed warehouse. Keep bags on pallets with wall clearance and monitor moisture and insects."),
    "wheat": ("Dry grain and protect from moisture ingress", "Use a ventilated, dry godown; keep grain off the floor and inspect for insects and moisture regularly."),
    "soybean": ("Control moisture and avoid heating in bulk", "Store only adequately dried seed/beans in a clean, ventilated facility. Monitor moisture, temperature, and insect activity."),
    "onion": ("Ventilated, cured storage", "Use a well-ventilated, shaded onion store with curing and airflow. Avoid damp, enclosed spaces."),
    "tomato": ("Short-chain handling and temperature control", "Prioritise sorting, ventilated crates, shade, and rapid movement. Use a suitable cold chain where available."),
    "potato": ("Dark, ventilated and crop-appropriate storage", "Cure and grade first; use controlled temperature and humidity appropriate to the intended market and storage duration."),
    "banana": ("Gentle handling and ripening control", "Use ventilated crates, avoid compression, and plan a short transit/ripening chain. Do not mix maturity stages without a plan."),
}


def run(request: AgentRunRequest) -> dict:
    crop = request.crop.strip()
    key = crop.lower()
    title, guidance = next((value for name, value in PROFILES.items() if name in key), (
        "Crop-specific storage parameters needed",
        "Use a clean, dry, pest-managed facility and confirm safe moisture, temperature, humidity, and ventilation targets for this crop with a local post-harvest expert.",
    ))
    return {
        "id": "storage", "name": "Storage Agent", "status": "completed",
        "headline": title, "summary": guidance,
        "data": {"crop": crop, "quantity_tonnes": request.quantity_tonnes, "storage_profile": "reference guidance"},
        "actions": ["Inspect facility hygiene and pest control", "Record incoming quantity and moisture", "Separate damaged or wet produce"],
        "source": "Crop-specific post-harvest checklist; advisory only", "live": False,
    }
