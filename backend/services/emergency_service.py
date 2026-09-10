import json
from datetime import datetime

from geoalchemy2 import WKTElement

from services.traffic_service import (
    add_live_traffic,
    predict_sensor
)

from services.corridor_service import (
    choose_best_route
)

from services.hospital_service import (
    get_ready_hospitals
)

from services.officer_service import (
    find_nearest_officer,
    activate_corridor
)

# ============================================================
# POSTGRESQL DATABASE
# ============================================================

from database.connection import SessionLocal
from database.models import Emergency, Route, Ambulance, Hospital, TrafficOfficer


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _safe_int(value):
    """
    Convert a value to integer safely.

    Returns None when conversion is not possible.
    """

    if value is None:
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def _geometry_to_wkt(geometry):
    """
    Convert route geometry into a LINESTRING WKT.

    Supports:
    1. GeoJSON dictionary:
       {
           "type": "LineString",
           "coordinates": [
               [longitude, latitude],
               ...
           ]
       }

    2. JSON string containing the same structure.

    3. List of coordinate pairs:
       [
           [longitude, latitude],
           ...
       ]

    Returns None when geometry cannot be converted.
    """

    if geometry is None:
        return None

    # --------------------------------------------------------
    # Convert JSON string to Python object
    # --------------------------------------------------------

    if isinstance(geometry, str):

        geometry = geometry.strip()

        if not geometry:
            return None

        # Already WKT
        if geometry.upper().startswith("LINESTRING"):
            return geometry

        try:
            geometry = json.loads(geometry)

        except json.JSONDecodeError:
            return None

    # --------------------------------------------------------
    # GeoJSON dictionary
    # --------------------------------------------------------

    if isinstance(geometry, dict):

        coordinates = geometry.get("coordinates")

        if not coordinates:
            return None

    # --------------------------------------------------------
    # Direct coordinate list
    # --------------------------------------------------------

    elif isinstance(geometry, list):

        coordinates = geometry

    else:

        return None

    # --------------------------------------------------------
    # Build coordinate pairs
    # --------------------------------------------------------

    points = []

    for coordinate in coordinates:

        if not isinstance(coordinate, (list, tuple)):
            continue

        if len(coordinate) < 2:
            continue

        try:

            longitude = float(coordinate[0])
            latitude = float(coordinate[1])

            points.append(
                f"{longitude} {latitude}"
            )

        except (TypeError, ValueError):
            continue

    # --------------------------------------------------------
    # Need at least two points for a LineString
    # --------------------------------------------------------

    if len(points) < 2:
        return None

    return (
        "LINESTRING("
        +
        ", ".join(points)
        +
        ")"
    )


def _build_geometry_from_traffic_points(traffic_points):
    """
    Build a LINESTRING from traffic points when the original
    route geometry is not available.
    """

    if not traffic_points:
        return None

    points = []

    for point in traffic_points:

        if not isinstance(point, dict):
            continue

        latitude = point.get("latitude")
        longitude = point.get("longitude")

        if latitude is None or longitude is None:
            continue

        try:

            points.append(
                f"{float(longitude)} {float(latitude)}"
            )

        except (TypeError, ValueError):
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
# POSTGRESQL EMERGENCY PERSISTENCE
# ============================================================

def _persist_emergency_to_database(
    ambulance_id,
    route_results,
    best_route,
    selected_hospital,
    selected_officer,
    corridor_status
):
    """
    Save the processed emergency and route results into
    PostgreSQL.

    This function deliberately does not control the main
    emergency logic. If database persistence fails, the
    emergency API can still return the existing result.
    """

    db = SessionLocal()

    try:

        # ====================================================
        # CONVERT PRIMARY KEYS
        # ====================================================

        ambulance_db_id = _safe_int(
            ambulance_id
        )

        if ambulance_db_id is None:
            amb_record = (
                db.query(Ambulance)
                .filter(Ambulance.ambulance_number.ilike(str(ambulance_id).strip()))
                .first()
            )
            if amb_record is not None:
                ambulance_db_id = amb_record.ambulance_id
            else:
                fallback_amb = db.query(Ambulance).filter(Ambulance.status == "AVAILABLE").first() or db.query(Ambulance).first()
                if fallback_amb is not None:
                    ambulance_db_id = fallback_amb.ambulance_id
                else:
                    new_amb = Ambulance(ambulance_number=str(ambulance_id or "AMB-001"), status="AVAILABLE")
                    db.add(new_amb)
                    db.flush()
                    ambulance_db_id = new_amb.ambulance_id

        hospital_db_id = None

        if selected_hospital:
            hospital_db_id = _safe_int(
                selected_hospital.get(
                    "hospital_id"
                )
            )
            if hospital_db_id is None:
                hosp_name = selected_hospital.get("hospital_name") or selected_hospital.get("name")
                if hosp_name:
                    hosp_record = db.query(Hospital).filter(Hospital.hospital_name.ilike(f"%{hosp_name.strip()}%")).first()
                    if hosp_record:
                        hospital_db_id = hosp_record.hospital_id
                if hospital_db_id is None:
                    first_hosp = db.query(Hospital).first()
                    if first_hosp:
                        hospital_db_id = first_hosp.hospital_id

        officer_db_id = None

        if selected_officer:
            officer_db_id = _safe_int(
                selected_officer.get(
                    "officer_id"
                )
            )
            if officer_db_id is None:
                first_off = db.query(TrafficOfficer).first()
                if first_off:
                    officer_db_id = first_off.officer_id

        # ====================================================
        # EMERGENCY STATUS
        # ====================================================

        if corridor_status == "CORRIDOR_ACTIVATED":

            emergency_status = (
                "CORRIDOR_ACTIVE"
            )

        else:

            emergency_status = "ACTIVE"

        # ====================================================
        # CREATE EMERGENCY
        # ====================================================

        emergency = Emergency(

            ambulance_id=ambulance_db_id,

            hospital_id=hospital_db_id,

            officer_id=officer_db_id,

            status=emergency_status,

            started_at=datetime.utcnow()

        )

        db.add(emergency)

        # Flush so PostgreSQL generates emergency_id
        db.flush()

        # ====================================================
        # SAVE ALL ROUTES
        # ====================================================

        for route_result in route_results:

            route_id = route_result.get(
                "route_id"
            )

            distance_km = route_result.get(
                "distance_km"
            )

            duration_minutes = route_result.get(
                "duration_minutes"
            )

            current_speed = route_result.get(
                "current_speed_kmh"
            )

            predicted_speed = route_result.get(
                "predicted_speed_kmh"
            )

            congestion = route_result.get(
                "congestion"
            )

            prediction_horizon = route_result.get(
                "prediction_horizon_minutes"
            )

            route_score = route_result.get(
                "route_score"
            )

            # ------------------------------------------------
            # Route geometry
            # ------------------------------------------------

            geometry = route_result.get(
                "geometry"
            )

            geometry_wkt = _geometry_to_wkt(
                geometry
            )

            # ------------------------------------------------
            # Fallback: build geometry from traffic points
            # ------------------------------------------------

            if geometry_wkt is None:

                geometry_wkt = (
                    _build_geometry_from_traffic_points(
                        route_result.get(
                            "traffic_points",
                            []
                        )
                    )
                )

            # ------------------------------------------------
            # Convert duration to seconds
            # ------------------------------------------------

            estimated_duration_seconds = None

            if duration_minutes is not None:

                try:

                    estimated_duration_seconds = (
                        float(duration_minutes)
                        *
                        60
                    )

                except (TypeError, ValueError):

                    estimated_duration_seconds = None

            # ------------------------------------------------
            # Recommended route?
            # ------------------------------------------------

            is_recommended = False

            if best_route:

                is_recommended = (

                    route_id
                    ==
                    best_route.get(
                        "route_id"
                    )

                )

            # ------------------------------------------------
            # Create database route
            # ------------------------------------------------

            route_record = Route(

                emergency_id=emergency.emergency_id,

                route_name=(
                    str(route_id)
                    if route_id is not None
                    else "Unnamed Route"
                ),

                distance_km=distance_km,

                estimated_duration_seconds=(
                    estimated_duration_seconds
                ),

                current_speed_kmh=current_speed,

                predicted_speed_kmh=predicted_speed,

                congestion=congestion,

                route_score=route_score,

                is_recommended=is_recommended,

                prediction_horizon_minutes=(
                    prediction_horizon
                )

            )

            # ------------------------------------------------
            # Add spatial geometry when available
            # ------------------------------------------------

            if geometry_wkt:

                route_record.route_geometry = (
                    WKTElement(
                        geometry_wkt,
                        srid=4326
                    )
                )

            db.add(route_record)

        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()

        print(
            "\n======================================="
        )

        print(
            "[DATABASE] Emergency persisted"
        )

        print(
            f"Emergency ID: "
            f"{emergency.emergency_id}"
        )

        print(
            f"Ambulance ID: "
            f"{ambulance_db_id}"
        )

        print(
            f"Routes saved: "
            f"{len(route_results)}"
        )

        print(
            f"Hospital ID: "
            f"{hospital_db_id}"
        )

        print(
            f"Officer ID: "
            f"{officer_db_id}"
        )

        print(
            f"Emergency status: "
            f"{emergency_status}"
        )

        print(
            "=======================================\n"
        )

        return emergency.emergency_id

    except Exception as error:

        db.rollback()

        print(
            "\n[WARN] PostgreSQL emergency persistence "
            f"failed: {error}\n"
        )

        return None

    finally:

        db.close()


# ============================================================
# LIVE TRAFFIC CONGESTION CLASSIFICATION
# ============================================================

def classify_live_congestion(
    current_speed,
    free_flow_speed
):

    if current_speed is None:

        return "UNKNOWN"

    if (
        free_flow_speed is None
        or free_flow_speed <= 0
    ):

        if current_speed >= 40:

            return "LOW"

        elif current_speed >= 20:

            return "MODERATE"

        else:

            return "HEAVY"

    ratio = (
        current_speed
        /
        free_flow_speed
    )

    if ratio >= 0.75:

        return "LOW"

    elif ratio >= 0.45:

        return "MODERATE"

    else:

        return "HEAVY"


# ============================================================
# START EMERGENCY
#
# main.py MUST call:
#
# start_emergency(
#     ambulance_id,
#     routes,
#     destination_hospital
# )
# ============================================================

def start_emergency(
    ambulance_id,
    routes,
    destination_hospital=None
):

    route_results = []

    # ========================================================
    # PROCESS EACH ROUTE
    # ========================================================

    for route in routes:

        traffic_points = route.get(
            "traffic_points",
            []
        )

        # ----------------------------------------------------
        # FALLBACK TRAFFIC POINT
        # ----------------------------------------------------

        if not traffic_points:

            traffic_points = [{

                "latitude":
                    route.get(
                        "latitude"
                    ),

                "longitude":
                    route.get(
                        "longitude"
                    )

            }]

        speeds = []

        free_flow_speeds = []

        checked_points = []

        # ====================================================
        # GET LIVE TOMTOM TRAFFIC
        # ====================================================

        for index, point in enumerate(
            traffic_points
        ):

            try:

                traffic = add_live_traffic(

                    sensor_id=(
                        f"{route['route_id']}"
                        f"-P{index + 1}"
                    ),

                    latitude=
                        point["latitude"],

                    longitude=
                        point["longitude"]

                )

                current_speed = traffic.get(
                    "current_speed_kmh"
                )

                free_flow_speed = traffic.get(
                    "free_flow_speed_kmh"
                )

                if current_speed is not None:

                    speeds.append(
                        float(
                            current_speed
                        )
                    )

                if free_flow_speed is not None:

                    free_flow_speeds.append(
                        float(
                            free_flow_speed
                        )
                    )

                checked_points.append({

                    "latitude":
                        point["latitude"],

                    "longitude":
                        point["longitude"],

                    "current_speed_kmh":
                        current_speed,

                    "free_flow_speed_kmh":
                        free_flow_speed

                })

            except Exception as error:

                print(

                    "[WARN] Live traffic failed "
                    f"for route "
                    f"{route.get('route_id')}: "
                    f"{error}"

                )

                checked_points.append({

                    "latitude":
                        point["latitude"],

                    "longitude":
                        point["longitude"],

                    "error":
                        str(error)

                })

        # ====================================================
        # AVERAGE CURRENT SPEED
        # ====================================================

        if speeds:

            average_speed = (
                sum(speeds)
                /
                len(speeds)
            )

        else:

            average_speed = None

        # ====================================================
        # AVERAGE FREE-FLOW SPEED
        # ====================================================

        if free_flow_speeds:

            average_free_flow = (

                sum(
                    free_flow_speeds
                )
                /
                len(
                    free_flow_speeds
                )

            )

        else:

            average_free_flow = None

        # ====================================================
        # LIVE CONGESTION
        # ====================================================

        congestion = classify_live_congestion(

            average_speed,

            average_free_flow

        )

        # ====================================================
        # XGBOOST PREDICTION
        # ====================================================

        predicted_speed = (
            average_speed
        )

        prediction_source = (
            "LIVE_CURRENT_TRAFFIC"
        )

        prediction_horizon = 0

        ml_status = "WARMING_UP"

        try:

            # ------------------------------------------------
            # Current prototype ML sensor
            # ------------------------------------------------

            ml_prediction = predict_sensor(
                "773869"
            )

            predicted_speed = (
                ml_prediction[
                    "predicted_speed_kmh"
                ]
            )

            prediction_source = (
                "XGBOOST_15_MIN_PREDICTION"
            )

            prediction_horizon = 15

            ml_status = "READY"

            print(
                "\n======================================="
            )

            print(
                "[AI] XGBoost traffic prediction"
            )

            print(
                f"Route: "
                f"{route.get('route_id')}"
            )

            print(
                f"Current speed: "
                f"{average_speed} km/h"
            )

            print(
                f"Predicted speed: "
                f"{predicted_speed} km/h"
            )

            print(
                f"Congestion: "
                f"{congestion}"
            )

            print(
                "Prediction horizon: 15 minutes"
            )

            print(
                "======================================="
            )

        except Exception as error:

            print(

                "[WARN] XGBoost prediction "
                f"unavailable: {error}"

            )

            # ------------------------------------------------
            # Graceful fallback
            # ------------------------------------------------

            predicted_speed = (
                average_speed
            )

            prediction_source = (
                "LIVE_CURRENT_TRAFFIC"
            )

            prediction_horizon = 0

            ml_status = "WARMING_UP"

        # ====================================================
        # ROUTE RESULT
        # ====================================================

        route_results.append({

            "route_id":
                route.get(
                    "route_id"
                ),

            "distance_km":
                route.get(
                    "distance_km"
                ),

            "duration_minutes":
                route.get(
                    "duration_minutes"
                ),

            "latitude":
                route.get(
                    "latitude"
                ),

            "longitude":
                route.get(
                    "longitude"
                ),

            "current_speed_kmh":
                (
                    round(
                        average_speed,
                        2
                    )
                    if average_speed
                    is not None
                    else None
                ),

            "free_flow_speed_kmh":
                (
                    round(
                        average_free_flow,
                        2
                    )
                    if average_free_flow
                    is not None
                    else None
                ),

            "predicted_speed_kmh":
                (
                    round(
                        predicted_speed,
                        2
                    )
                    if predicted_speed
                    is not None
                    else 0
                ),

            "prediction_horizon_minutes":
                prediction_horizon,

            "prediction_source":
                prediction_source,

            "ml_status":
                ml_status,

            "congestion":
                congestion,

            "traffic_points_checked":
                len(
                    checked_points
                ),

            "traffic_points":
                checked_points,

            "geometry":
                route.get(
                    "geometry"
                )

        })

    # ========================================================
    # VALID ROUTES
    # ========================================================

    valid_routes = [

        route

        for route in route_results

        if route.get(
            "predicted_speed_kmh",
            0
        ) > 0

    ]

    # ========================================================
    # BEST ROUTE
    # ========================================================

    if valid_routes:

        best_route = choose_best_route(
            valid_routes
        )

    elif route_results:

        # ----------------------------------------------------
        # Fallback:
        # choose first route if ML/live traffic is unavailable
        # ----------------------------------------------------

        best_route = route_results[0]

    else:

        best_route = None

    # ========================================================
    # HOSPITAL
    # ========================================================

    if destination_hospital:

        selected_hospital = (
            destination_hospital
        )

        if destination_hospital.get(
            "emergency_ready",
            False
        ):

            hospital_status = (
                "HOSPITAL_SELECTED"
            )

        else:

            hospital_status = (
                "HOSPITAL_NOT_READY"
            )

    else:

        hospitals = get_ready_hospitals()

        if hospitals:

            selected_hospital = (
                hospitals[0]
            )

            hospital_status = (
                "HOSPITAL_SELECTED"
            )

        else:

            selected_hospital = None

            hospital_status = (
                "NO_READY_HOSPITAL"
            )

    # ========================================================
    # TRAFFIC OFFICER
    # ========================================================

    selected_officer = None

    if best_route:

        route_points = best_route.get(
            "traffic_points",
            []
        )

        for point in route_points:

            try:

                officer = find_nearest_officer(

                    point["latitude"],

                    point["longitude"]

                )

            except Exception as error:

                print(

                    "[WARN] Officer lookup failed: "
                    f"{error}"

                )

                officer = None

            if officer:

                if selected_officer is None:

                    selected_officer = (
                        officer
                    )

                else:

                    current_distance = (
                        selected_officer.get(
                            "distance_to_route_km",
                            float("inf")
                        )
                    )

                    new_distance = (
                        officer.get(
                            "distance_to_route_km",
                            float("inf")
                        )
                    )

                    if new_distance < current_distance:

                        selected_officer = (
                            officer
                        )

    # ========================================================
    # ACTIVATE CORRIDOR
    # ========================================================

    officer_status = None

    if selected_officer:

        try:

            officer_status = activate_corridor(

                selected_officer[
                    "officer_id"
                ]

            )

            if officer_status is None:

                officer_status = (
                    selected_officer
                )

            officer_status[
                "assigned_traffic_point"
            ] = {

                "latitude":
                    best_route.get(
                        "latitude"
                    ),

                "longitude":
                    best_route.get(
                        "longitude"
                    )

            }

            if (
                "distance_to_route_km"
                in selected_officer
            ):

                officer_status[
                    "distance_to_route_km"
                ] = selected_officer[
                    "distance_to_route_km"
                ]

            corridor_status = (
                "CORRIDOR_ACTIVATED"
            )

        except Exception as error:

            print(

                "[WARN] Corridor activation "
                f"failed: {error}"

            )

            corridor_status = (
                "CORRIDOR_ACTIVATION_FAILED"
            )

    else:

        corridor_status = (
            "WAITING_FOR_TRAFFIC_OFFICER"
        )

    # ========================================================
    # ML STATUS
    # ========================================================

    final_ml_status = (

        "READY"

        if any(

            route.get(
                "ml_status"
            ) == "READY"

            for route in route_results

        )

        else "WARMING_UP"

    )

    # ========================================================
    # POSTGRESQL PERSISTENCE
    #
    # Existing emergency logic has already completed.
    # Now save the emergency + route decisions.
    # ========================================================

    database_emergency_id = (
        _persist_emergency_to_database(

            ambulance_id=ambulance_id,

            route_results=route_results,

            best_route=best_route,

            selected_hospital=selected_hospital,

            selected_officer=officer_status,

            corridor_status=corridor_status

        )
    )

    # ========================================================
    # FINAL RESPONSE
    #
    # Existing response fields are preserved.
    # One additional field tells the frontend/demo whether
    # PostgreSQL persistence succeeded.
    # ========================================================

    return {

        "ambulance_id":
            ambulance_id,

        "status":
            "EMERGENCY_PROCESSED",

        "traffic_source":
            "LIVE_DYNAMIC_TRAFFIC",

        "ml_status":
            final_ml_status,

        "routes_analyzed":
            route_results,

        "recommended_route":
            best_route,

        "selected_hospital":
            selected_hospital,

        "hospital_status":
            hospital_status,

        "assigned_officer":
            officer_status,

        "corridor_status":
            corridor_status,

        "database_emergency_id":
            database_emergency_id,

        "database_persistence":
            (
                "SAVED"
                if database_emergency_id is not None
                else "FAILED"
            )

    }