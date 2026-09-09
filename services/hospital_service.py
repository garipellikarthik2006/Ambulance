hospitals = {
    "HOSP-001": {
        "hospital_name": "City Emergency Hospital",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "emergency_ready": True,
        "icu_available": 5,
        "beds_available": 12,
        "status": "READY"
    },

    "HOSP-002": {
        "hospital_name": "Metro Care Hospital",
        "latitude": 17.4000,
        "longitude": 78.4800,
        "emergency_ready": True,
        "icu_available": 2,
        "beds_available": 6,
        "status": "READY"
    },

    "HOSP-003": {
        "hospital_name": "Central Medical Hospital",
        "latitude": 17.3700,
        "longitude": 78.5000,
        "emergency_ready": False,
        "icu_available": 0,
        "beds_available": 3,
        "status": "BUSY"
    }
}


def get_hospital(hospital_id):
    hospital = hospitals.get(hospital_id)

    if hospital is None:
        raise ValueError(
            f"Hospital '{hospital_id}' not found."
        )

    return {
        "hospital_id": hospital_id,
        **hospital
    }


def update_hospital_status(
    hospital_id,
    emergency_ready,
    icu_available,
    beds_available
):
    if hospital_id not in hospitals:
        raise ValueError(
            f"Hospital '{hospital_id}' not found."
        )

    hospitals[hospital_id]["emergency_ready"] = emergency_ready
    hospitals[hospital_id]["icu_available"] = icu_available
    hospitals[hospital_id]["beds_available"] = beds_available

    if emergency_ready and icu_available > 0:
        hospitals[hospital_id]["status"] = "READY"

    elif beds_available > 0:
        hospitals[hospital_id]["status"] = "LIMITED"

    else:
        hospitals[hospital_id]["status"] = "BUSY"

    return get_hospital(hospital_id)


def get_ready_hospitals():
    ready = []

    for hospital_id in hospitals:
        hospital = get_hospital(hospital_id)

        if hospital["emergency_ready"]:
            ready.append(hospital)

    return ready

def calculate_hospital_score(
    hospital,
    travel_time_minutes
):

    if not hospital["emergency_ready"]:
        return float("inf")

    score = travel_time_minutes

    score -= hospital[
        "icu_available"
    ] * 0.5

    score -= hospital[
        "beds_available"
    ] * 0.1

    return score

def choose_best_hospital(
    hospitals,
    estimated_travel_time
):

    ready_hospitals = [
        hospital
        for hospital in hospitals
        if hospital["emergency_ready"]
    ]

    if not ready_hospitals:
        return None

    best = min(
        ready_hospitals,
        key=lambda hospital:
        calculate_hospital_score(
            hospital,
            estimated_travel_time
        )
    )

    return best