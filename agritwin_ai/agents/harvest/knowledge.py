import json
from pathlib import Path


KNOWLEDGE_FILE = Path(__file__).resolve().parents[2] / "knowledge" / "crops" / "crops.json"


def get_crop_info(crop):

    crop = crop.lower()

    with open(KNOWLEDGE_FILE, "r") as file:

        data = json.load(file)

    if crop not in data:

        return {
            "error": f"No knowledge found for '{crop}'."
        }

    info = data[crop]

    return {
        "crop": crop,
        **info
    }
