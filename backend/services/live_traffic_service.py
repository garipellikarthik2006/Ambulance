import os
import requests

from dotenv import load_dotenv

load_dotenv()

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")


def get_live_traffic(latitude, longitude):

    if not TOMTOM_API_KEY:
        raise ValueError("TOMTOM_API_KEY is not configured.")

    url = (
        "https://api.tomtom.com/traffic/services/4/"
        "flowSegmentData/absolute/10/json"
    )

    params = {
        "point": f"{latitude},{longitude}",
        "unit": "KMPH",
        "key": TOMTOM_API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    flow_data = data.get("flowSegmentData", {})

    return {
        "current_speed_kmh": flow_data.get("currentSpeed"),
        "free_flow_speed_kmh": flow_data.get("freeFlowSpeed"),
        "current_travel_time_seconds": flow_data.get(
            "currentTravelTime"
        ),
        "free_flow_travel_time_seconds": flow_data.get(
            "freeFlowTravelTime"
        ),
        "confidence": flow_data.get("confidence"),
        "road_closure": flow_data.get("roadClosure")
    }