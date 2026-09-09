from datetime import datetime


# ============================================================
# ACTIVE AMBULANCE TRACKING
# ============================================================

active_emergencies = {}


# ============================================================
# START TRACKING
# ============================================================

def start_tracking(
    ambulance_id,
    latitude,
    longitude,
    route_id=None,
    hospital_id=None,
    route_geometry=None
):

    active_emergencies[ambulance_id] = {

        "ambulance_id": ambulance_id,

        "latitude": float(latitude),

        "longitude": float(longitude),

        "route_id": route_id,

        "hospital_id": hospital_id,

        "route_geometry": route_geometry,

        "status": "EN_ROUTE",

        "last_updated": datetime.now().isoformat()

    }

    print(
        f"🚑 Tracking started for {ambulance_id}"
    )

    return active_emergencies[ambulance_id]


# ============================================================
# UPDATE LOCATION
# ============================================================

def update_location(
    ambulance_id,
    latitude,
    longitude
):

    if ambulance_id not in active_emergencies:

        raise ValueError(
            f"Ambulance '{ambulance_id}' "
            f"is not being tracked."
        )

    active_emergencies[ambulance_id][
        "latitude"
    ] = float(latitude)

    active_emergencies[ambulance_id][
        "longitude"
    ] = float(longitude)

    active_emergencies[ambulance_id][
        "last_updated"
    ] = datetime.now().isoformat()

    return active_emergencies[ambulance_id]


# ============================================================
# GET ONE AMBULANCE
# ============================================================

def get_tracking(
    ambulance_id
):

    return active_emergencies.get(
        ambulance_id
    )


# ============================================================
# GET ALL ACTIVE AMBULANCES
# ============================================================

def get_all_active_emergencies():

    return list(
        active_emergencies.values()
    )


# ============================================================
# COMPLETE EMERGENCY
# ============================================================

def complete_emergency(
    ambulance_id
):

    if ambulance_id not in active_emergencies:

        return {
            "status": "NOT_FOUND",
            "message": (
                f"Ambulance '{ambulance_id}' "
                f"is not currently tracked."
            )
        }

    active_emergencies[ambulance_id][
        "status"
    ] = "COMPLETED"

    active_emergencies[ambulance_id][
        "last_updated"
    ] = datetime.now().isoformat()

    return active_emergencies[ambulance_id]