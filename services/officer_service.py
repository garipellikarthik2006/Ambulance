import math


officers = {
    "OFF-001": {
        "name": "Officer 1",
        "location": "Junction A",
        "latitude": 17.4200,
        "longitude": 78.3900,
        "status": "AVAILABLE",
        "corridor_active": False
    },

    "OFF-002": {
        "name": "Officer 2",
        "location": "Junction B",
        "latitude": 17.4000,
        "longitude": 78.4500,
        "status": "AVAILABLE",
        "corridor_active": False
    },

    "OFF-003": {
        "name": "Officer 3",
        "location": "Junction C",
        "latitude": 17.3700,
        "longitude": 78.5000,
        "status": "BUSY",
        "corridor_active": False
    }
}


def calculate_distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    earth_radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


def get_available_officers():

    result = []

    for officer_id, officer in officers.items():

        if officer["status"] == "AVAILABLE":

            result.append({
                "officer_id": officer_id,
                **officer
            })

    return result


def find_nearest_officer(
    latitude,
    longitude
):

    available = get_available_officers()

    if not available:
        return None

    nearest = None
    nearest_distance = float("inf")

    for officer in available:

        distance = calculate_distance_km(
            latitude,
            longitude,
            officer["latitude"],
            officer["longitude"]
        )

        if distance < nearest_distance:

            nearest_distance = distance

            nearest = {
                **officer,
                "distance_to_route_km": round(
                    distance,
                    2
                )
            }

    return nearest


def activate_corridor(officer_id):

    if officer_id not in officers:
        raise ValueError(
            f"Officer '{officer_id}' not found."
        )

    officers[officer_id]["status"] = "BUSY"

    officers[officer_id]["corridor_active"] = True

    return {
        "officer_id": officer_id,
        **officers[officer_id]
    }


def deactivate_corridor(officer_id):

    if officer_id not in officers:
        raise ValueError(
            f"Officer '{officer_id}' not found."
        )

    officers[officer_id]["status"] = "AVAILABLE"

    officers[officer_id]["corridor_active"] = False

    return {
        "officer_id": officer_id,
        **officers[officer_id]
    }