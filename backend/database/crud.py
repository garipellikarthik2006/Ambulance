from sqlalchemy import func, text
from geoalchemy2 import WKTElement

from database.models import (
    User,
    Hospital,
    Ambulance,
    TrafficOfficer,
    Emergency,
    AmbulanceTracking,
    TrafficObservation,
    Route
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _safe_int(value):

    if value is None:
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def _point_wkt(latitude, longitude):

    return WKTElement(
        f"POINT({float(longitude)} {float(latitude)})",
        srid=4326
    )


def _linestring_wkt_from_geometry(geometry):

    if geometry is None:
        return None

    if isinstance(geometry, str):

        geometry = geometry.strip()

        if not geometry:
            return None

        if geometry.upper().startswith("LINESTRING"):
            return geometry

        try:
            import json

            geometry = json.loads(geometry)

        except Exception:
            return None

    if not isinstance(geometry, dict):
        return None

    coordinates = geometry.get("coordinates")

    if not coordinates or len(coordinates) < 2:
        return None

    points = []

    for coordinate in coordinates:

        if not isinstance(
            coordinate,
            (list, tuple)
        ):
            continue

        if len(coordinate) < 2:
            continue

        try:

            longitude = float(
                coordinate[0]
            )

            latitude = float(
                coordinate[1]
            )

            points.append(
                f"{longitude} {latitude}"
            )

        except (
            TypeError,
            ValueError
        ):
            continue

    if len(points) < 2:
        return None

    return (
        "LINESTRING("
        +
        ", ".join(points)
        +
        ")"
    )


# ============================================================
# USER CRUD
# ============================================================

def get_user_by_id(
    db,
    user_id
):

    user_db_id = _safe_int(
        user_id
    )

    if user_db_id is None:
        return None

    return (
        db.query(User)
        .filter(
            User.user_id
            ==
            user_db_id
        )
        .first()
    )


def get_user_by_email(
    db,
    email
):

    if not email:
        return None

    return (
        db.query(User)
        .filter(
            func.lower(User.email)
            ==
            func.lower(email)
        )
        .first()
    )


# ============================================================
# HOSPITAL CRUD
# ============================================================

def get_hospital_by_id(
    db,
    hospital_id
):

    hospital_db_id = _safe_int(
        hospital_id
    )

    if hospital_db_id is None:
        return None

    return (
        db.query(Hospital)
        .filter(
            Hospital.hospital_id
            ==
            hospital_db_id
        )
        .first()
    )


def get_ready_hospitals_db(
    db
):

    results = (
        db.query(Hospital, User)
        .join(
            User,
            Hospital.user_id
            ==
            User.user_id
        )
        .filter(
            Hospital.status
            ==
            "READY",

            Hospital.emergency_readiness
            ==
            True,

            User.is_verified
            ==
            True,

            User.is_active
            ==
            True
        )
        .all()
    )

    return results


def register_hospital(
    db,
    full_name,
    email,
    phone,
    password_hash,
    hospital_name,
    latitude,
    longitude,
    icu_available=0,
    beds_available=0
):

    existing_user = get_user_by_email(
        db,
        email
    )

    if existing_user:

        raise ValueError(
            "Email already registered."
        )

    user = User(

        full_name=full_name,

        email=email,

        phone=phone,

        password_hash=password_hash,

        role="HOSPITAL",

        is_verified=False,

        is_active=True

    )

    db.add(user)

    db.flush()

    hospital = Hospital(

        user_id=user.user_id,

        hospital_name=hospital_name,

        phone=phone,

        status="NOT_READY",

        emergency_readiness=False,

        icu_available=int(
            icu_available
        ),

        beds_available=int(
            beds_available
        ),

        location=_point_wkt(
            latitude,
            longitude
        )

    )

    db.add(hospital)

    db.commit()

    db.refresh(user)

    db.refresh(hospital)

    return hospital, user


def get_pending_hospitals(
    db
):

    return (
        db.query(Hospital, User)
        .join(
            User,
            Hospital.user_id
            ==
            User.user_id
        )
        .filter(
            User.is_verified
            ==
            False,

            User.role
            ==
            "HOSPITAL"
        )
        .all()
    )


def approve_hospital(
    db,
    hospital_id
):

    hospital = get_hospital_by_id(
        db,
        hospital_id
    )

    if hospital is None:
        return None

    user = get_user_by_id(
        db,
        hospital.user_id
    )

    if user is None:
        return None

    user.is_verified = True

    hospital.status = "READY"

    hospital.emergency_readiness = True

    hospital.updated_at = func.now()

    db.commit()

    db.refresh(hospital)

    return hospital


# ============================================================
# AMBULANCE CRUD
# ============================================================

def get_ambulance_by_id(
    db,
    ambulance_id
):

    ambulance_db_id = _safe_int(
        ambulance_id
    )

    if ambulance_db_id is not None:
        amb = (
            db.query(Ambulance)
            .filter(
                Ambulance.ambulance_id
                ==
                ambulance_db_id
            )
            .first()
        )
        if amb:
            return amb

    if ambulance_id:
        return (
            db.query(Ambulance)
            .filter(
                Ambulance.ambulance_number.ilike(
                    str(ambulance_id).strip()
                )
            )
            .first()
        )

    return None


def get_ambulance_by_number(
    db,
    ambulance_number
):

    if not ambulance_number:
        return None

    return (
        db.query(Ambulance)
        .filter(
            Ambulance.ambulance_number
            ==
            ambulance_number
        )
        .first()
    )


def register_ambulance(
    db,
    ambulance_number,
    driver_user_id=None
):

    existing = get_ambulance_by_number(
        db,
        ambulance_number
    )

    if existing:

        raise ValueError(
            "Ambulance number already exists."
        )

    driver_db_id = _safe_int(
        driver_user_id
    )

    ambulance = Ambulance(

        ambulance_number=(
            ambulance_number
        ),

        driver_user_id=(
            driver_db_id
            if driver_db_id is not None
            else None
        ),

        status="AVAILABLE",

        is_verified=False,

        is_active=True

    )

    db.add(ambulance)

    db.commit()

    db.refresh(ambulance)

    return ambulance


def get_available_ambulances(
    db
):

    return (
        db.query(Ambulance)
        .filter(
            Ambulance.status
            ==
            "AVAILABLE",

            Ambulance.is_verified
            ==
            True,

            Ambulance.is_active
            ==
            True
        )
        .all()
    )


def verify_ambulance(
    db,
    ambulance_id
):

    ambulance = get_ambulance_by_id(
        db,
        ambulance_id
    )

    if ambulance is None:
        return None

    ambulance.is_verified = True

    ambulance.updated_at = func.now()

    db.commit()

    db.refresh(ambulance)

    return ambulance


def activate_ambulance(
    db,
    ambulance_id
):

    ambulance = get_ambulance_by_id(
        db,
        ambulance_id
    )

    if ambulance is None:
        return None

    ambulance.status = "AVAILABLE"

    ambulance.is_active = True

    db.commit()

    db.refresh(ambulance)

    return ambulance


def deactivate_ambulance(
    db,
    ambulance_id
):

    ambulance = get_ambulance_by_id(
        db,
        ambulance_id
    )

    if ambulance is None:
        return None

    ambulance.status = "OFFLINE"

    ambulance.is_active = False

    db.commit()

    db.refresh(ambulance)

    return ambulance


# ============================================================
# OFFICER CRUD
# ============================================================

def get_officer_by_id(
    db,
    officer_id
):

    officer_db_id = _safe_int(
        officer_id
    )

    if officer_db_id is None:
        return None

    return (
        db.query(TrafficOfficer)
        .filter(
            TrafficOfficer.officer_id
            ==
            officer_db_id
        )
        .first()
    )


def get_available_officers_db(
    db
):

    return (
        db.query(
            TrafficOfficer,
            User
        )
        .join(
            User,
            TrafficOfficer.user_id
            ==
            User.user_id
        )
        .filter(
            TrafficOfficer.status
            ==
            "AVAILABLE",

            User.is_active
            ==
            True
        )
        .all()
    )


# ============================================================
# EMERGENCY CRUD
# ============================================================

def get_emergency_by_id(
    db,
    emergency_id
):

    emergency_db_id = _safe_int(
        emergency_id
    )

    if emergency_db_id is None:
        return None

    return (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            ==
            emergency_db_id
        )
        .first()
    )


def get_active_emergencies(
    db
):

    return (
        db.query(Emergency)
        .filter(
            Emergency.status.in_([
                "CREATED",
                "ACTIVE",
                "CORRIDOR_ACTIVE"
            ])
        )
        .all()
    )


def create_emergency(
    db,
    ambulance_id,
    hospital_id=None,
    officer_id=None,
    status="ACTIVE"
):

    ambulance_db_id = _safe_int(
        ambulance_id
    )

    if ambulance_db_id is None:

        raise ValueError(
            f"Invalid ambulance ID: "
            f"{ambulance_id}"
        )

    hospital_db_id = _safe_int(
        hospital_id
    )

    officer_db_id = _safe_int(
        officer_id
    )

    emergency = Emergency(

        ambulance_id=ambulance_db_id,

        hospital_id=hospital_db_id,

        officer_id=officer_db_id,

        status=status,

        started_at=func.now()

    )

    db.add(emergency)

    db.flush()

    return emergency


def update_emergency(
    db,
    emergency_id,
    status=None,
    hospital_id=None,
    officer_id=None
):

    emergency = get_emergency_by_id(
        db,
        emergency_id
    )

    if emergency is None:
        return None

    if status is not None:

        emergency.status = status

    if hospital_id is not None:

        emergency.hospital_id = (
            _safe_int(hospital_id)
        )

    if officer_id is not None:

        emergency.officer_id = (
            _safe_int(officer_id)
        )

    if status == "COMPLETED":

        from datetime import datetime

        emergency.completed_at = (
            datetime.utcnow()
        )

    db.commit()

    db.refresh(emergency)

    return emergency


# ============================================================
# AMBULANCE LOCATION UPDATE
# ============================================================

def update_ambulance_location(
    db,
    ambulance_id,
    latitude,
    longitude,
    status="ON_EMERGENCY"
):

    ambulance = get_ambulance_by_id(
        db,
        ambulance_id
    )

    if ambulance is None:

        raise ValueError(
            f"Ambulance '{ambulance_id}' "
            f"not found."
        )

    # ========================================================
    # IMPORTANT
    #
    # The ambulance table does NOT use EN_ROUTE.
    #
    # Valid emergency movement state:
    # ON_EMERGENCY
    # ========================================================

    allowed_statuses = {
        "AVAILABLE",
        "ON_EMERGENCY",
        "OFFLINE",
        "MAINTENANCE"
    }

    if status not in allowed_statuses:

        status = "ON_EMERGENCY"

    ambulance.current_location = (
        _point_wkt(
            latitude,
            longitude
        )
    )

    ambulance.status = status

    ambulance.updated_at = func.now()

    db.flush()

    return ambulance


# ============================================================
# TRACKING CRUD
# ============================================================

def create_tracking_record(
    db,
    ambulance_id,
    emergency_id,
    latitude,
    longitude,
    status="EN_ROUTE"
):

    ambulance_db_id = _safe_int(
        ambulance_id
    )

    if ambulance_db_id is None:

        raise ValueError(
            f"Invalid ambulance ID: "
            f"{ambulance_id}"
        )

    emergency_db_id = _safe_int(
        emergency_id
    )

    if emergency_db_id is None:

        raise ValueError(
            f"Invalid emergency ID: "
            f"{emergency_id}"
        )

    # ========================================================
    # UPDATE AMBULANCE MASTER RECORD
    #
    # Tracking uses EN_ROUTE/MOVING.
    # Ambulance master uses ON_EMERGENCY.
    # ========================================================

    update_ambulance_location(

        db=db,

        ambulance_id=ambulance_db_id,

        latitude=latitude,

        longitude=longitude,

        status="ON_EMERGENCY"

    )

    # ========================================================
    # CREATE TRACKING HISTORY RECORD
    # ========================================================

    tracking = AmbulanceTracking(

        ambulance_id=ambulance_db_id,

        emergency_id=emergency_db_id,

        location=_point_wkt(
            latitude,
            longitude
        ),

        status=status,

        recorded_at=func.now()

    )

    db.add(tracking)

    db.flush()

    return tracking


def get_tracking_by_ambulance(
    db,
    ambulance_id,
    limit=100
):

    ambulance_db_id = _safe_int(
        ambulance_id
    )

    if ambulance_db_id is None:
        return []

    return (
        db.query(AmbulanceTracking)
        .filter(
            AmbulanceTracking.ambulance_id
            ==
            ambulance_db_id
        )
        .order_by(
            AmbulanceTracking.recorded_at.desc()
        )
        .limit(limit)
        .all()
    )


def get_latest_tracking(
    db,
    ambulance_id
):

    ambulance_db_id = _safe_int(
        ambulance_id
    )

    if ambulance_db_id is None:
        return None

    return (
        db.query(AmbulanceTracking)
        .filter(
            AmbulanceTracking.ambulance_id
            ==
            ambulance_db_id
        )
        .order_by(
            AmbulanceTracking.recorded_at.desc()
        )
        .first()
    )


# ============================================================
# TRAFFIC OBSERVATION CRUD
# ============================================================

def create_traffic_observation(
    db,
    sensor_id,
    latitude,
    longitude,
    speed_kmh,
    free_flow_speed_kmh=None,
    confidence=None,
    road_closure=False
):

    observation = TrafficObservation(

        sensor_id=str(
            sensor_id
        ),

        location=_point_wkt(
            latitude,
            longitude
        ),

        observed_at=func.now(),

        speed_kmh=speed_kmh,

        free_flow_speed_kmh=(
            free_flow_speed_kmh
        ),

        confidence=confidence,

        road_closure=road_closure

    )

    db.add(observation)

    db.commit()

    db.refresh(observation)

    return observation


def get_traffic_observations(
    db,
    sensor_id=None,
    limit=100
):

    query = db.query(
        TrafficObservation
    )

    if sensor_id is not None:

        query = query.filter(
            TrafficObservation.sensor_id
            ==
            str(sensor_id)
        )

    return (
        query
        .order_by(
            TrafficObservation.observed_at.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# ROUTE CRUD
# ============================================================

def create_route(
    db,
    emergency_id,
    route_name,
    distance_km=None,
    estimated_duration_seconds=None,
    current_speed_kmh=None,
    predicted_speed_kmh=None,
    congestion=None,
    route_score=None,
    is_recommended=False,
    prediction_horizon_minutes=None,
    route_geometry=None
):

    emergency_db_id = _safe_int(
        emergency_id
    )

    if emergency_db_id is None:

        raise ValueError(
            f"Invalid emergency ID: "
            f"{emergency_id}"
        )

    route = Route(

        emergency_id=(
            emergency_db_id
        ),

        route_name=route_name,

        distance_km=distance_km,

        estimated_duration_seconds=(
            estimated_duration_seconds
        ),

        current_speed_kmh=(
            current_speed_kmh
        ),

        predicted_speed_kmh=(
            predicted_speed_kmh
        ),

        congestion=congestion,

        route_score=route_score,

        is_recommended=is_recommended,

        prediction_horizon_minutes=(
            prediction_horizon_minutes
        )

    )

    # --------------------------------------------------------
    # Spatial route geometry
    # --------------------------------------------------------

    if route_geometry:

        geometry_wkt = (
            _linestring_wkt_from_geometry(
                route_geometry
            )
        )

        if geometry_wkt:

            route.route_geometry = (
                WKTElement(
                    geometry_wkt,
                    srid=4326
                )
            )

    db.add(route)

    db.flush()

    return route


def get_routes_by_emergency(
    db,
    emergency_id
):

    emergency_db_id = _safe_int(
        emergency_id
    )

    if emergency_db_id is None:
        return []

    return (
        db.query(Route)
        .filter(
            Route.emergency_id
            ==
            emergency_db_id
        )
        .order_by(
            Route.route_id.asc()
        )
        .all()
    )


def get_recommended_route(
    db,
    emergency_id
):

    emergency_db_id = _safe_int(
        emergency_id
    )

    if emergency_db_id is None:
        return None

    return (
        db.query(Route)
        .filter(
            Route.emergency_id
            ==
            emergency_db_id,

            Route.is_recommended
            ==
            True
        )
        .first()
    )


def mark_recommended_route(
    db,
    emergency_id,
    route_id
):

    emergency_db_id = _safe_int(
        emergency_id
    )

    route_db_id = _safe_int(
        route_id
    )

    if (
        emergency_db_id is None
        or route_db_id is None
    ):

        return None

    (
        db.query(Route)
        .filter(
            Route.emergency_id
            ==
            emergency_db_id
        )
        .update(
            {
                Route.is_recommended:
                    False
            }
        )
    )

    route = (
        db.query(Route)
        .filter(
            Route.route_id
            ==
            route_db_id,

            Route.emergency_id
            ==
            emergency_db_id
        )
        .first()
    )

    if route is None:
        return None

    route.is_recommended = True

    db.commit()

    db.refresh(route)

    return route


# ============================================================
# ROUTE -> DICTIONARY
# ============================================================

def route_to_dict(
    route
):

    geometry = None

    try:

        geometry = (
            route.route_geometry
        )

    except Exception:
        geometry = None

    return {

        "route_id":
            route.route_id,

        "emergency_id":
            route.emergency_id,

        "route_name":
            route.route_name,

        "distance_km":
            route.distance_km,

        "estimated_duration_seconds":
            route.estimated_duration_seconds,

        "current_speed_kmh":
            route.current_speed_kmh,

        "predicted_speed_kmh":
            route.predicted_speed_kmh,

        "congestion":
            route.congestion,

        "route_score":
            route.route_score,

        "is_recommended":
            route.is_recommended,

        "prediction_horizon_minutes":
            route.prediction_horizon_minutes,

        "route_geometry":
            geometry

    }