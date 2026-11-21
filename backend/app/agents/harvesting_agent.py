from backend.app.agents.schemas import AgentRunRequest


STAGE_GUIDANCE = {
    "sowing": ("Establishment phase", "Track emergence and stand count. Harvest planning is premature at this stage."),
    "vegetative": ("Vegetative growth", "Monitor canopy development, weeds, and nutrient stress. Reassess harvest timing as the crop develops."),
    "flowering": ("Flowering phase", "Protect the crop from avoidable water and heat stress. Do not infer harvest readiness from flowering alone."),
    "grain_filling": ("Grain filling", "Monitor grain development and weather. Prepare labour, equipment, and buyer options, but confirm maturity before cutting."),
    "maturity": ("Maturity check required", "Inspect crop-specific maturity indicators and grain moisture before scheduling harvest."),
    "ready": ("Potentially harvest-ready", "Confirm crop-specific maturity, grain moisture, and a suitable weather window before harvesting."),
    "harvested": ("Harvest recorded", "Move to post-harvest handling: drying, cleaning, grading, and safe storage."),
    "unknown": ("Crop stage not supplied", "Set the crop stage or provide sowing date and local crop observations for a useful harvest assessment."),
}


def run(request: AgentRunRequest) -> dict:
    title, advice = STAGE_GUIDANCE[request.crop_stage]
    readiness = "ready_to_verify" if request.crop_stage == "ready" else "not_confirmed"
    if request.crop_stage == "maturity":
        readiness = "maturity_check"
    elif request.crop_stage == "harvested":
        readiness = "post_harvest"

    return {
        "id": "harvesting",
        "name": "Harvesting Agent",
        "status": "completed",
        "headline": title,
        "summary": advice,
        "data": {
            "crop": request.crop,
            "crop_stage": request.crop_stage,
            "readiness": readiness,
            "quantity_tonnes": request.quantity_tonnes,
        },
        "actions": [
            "Verify crop-specific maturity signs in the field",
            "Check grain moisture and the next 48-hour weather window",
            "Coordinate labour, equipment, and buyer before harvest",
        ],
        "source": "Farmer-provided crop stage; agronomic checklist",
        "live": False,
    }
