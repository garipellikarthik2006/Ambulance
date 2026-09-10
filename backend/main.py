import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        pass


from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from contextlib import asynccontextmanager

import asyncio


# ============================================================
# POSTGRESQL / SQLALCHEMY
# ============================================================

from database.models import Ambulance
from database.connection import get_db

from database.crud import (
    get_user_by_email,
    get_ambulance_by_id,
    get_ambulance_by_number,
    get_ready_hospitals_db,
    get_available_officers_db,
    get_emergency_by_id,
    get_tracking_by_ambulance,
    get_routes_by_emergency,
    get_recommended_route,
)


# ============================================================
# EXISTING TRAFFIC / ML SERVICES
# ============================================================

from services.traffic_database import initialize_database

from services.traffic_collector import (
    traffic_collection_loop
)

from services.traffic_service import (
    add_traffic_observation,
    predict_sensor,
    add_live_traffic
)

from services.corridor_service import (
    choose_best_route
)

from services.hospital_service import (
    get_hospital,
    get_ready_hospitals,
    update_hospital_status
)

from services.officer_service import (
    get_available_officers,
    activate_corridor,
    deactivate_corridor
)

from services.emergency_service import (
    start_emergency
)

from services.routing_service import (
    get_routes
)

from services.emergency_tracking_service import (
    start_tracking,
    update_location,
    get_tracking,
    get_all_active_emergencies,
    complete_emergency
)

from services.ambulance_simulator import (
    simulate_ambulance_movement
)

from services.route_traffic_service import (
    analyze_route_traffic
)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    collector_task = asyncio.create_task(
        traffic_collection_loop()
    )

    yield

    collector_task.cancel()

    try:
        await collector_task
    except asyncio.CancelledError:
        pass


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Ambulance Corridor AI",
    description=(
        "AI-powered traffic prediction and "
        "ambulance corridor decision support"
    ),
    version="1.0",
    lifespan=lifespan
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# HTTP EXCEPTION HANDLER
#
# Keep the actual HTTP status code instead of converting
# HTTP errors into 500.
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        }
    )


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc)
        },
        headers={
            "Access-Control-Allow-Origin": "*"
        }
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()


# ============================================================
# DATABASE HEALTH
# ============================================================

@app.get("/database/health")
def database_health():

    from sqlalchemy import text

    db = next(get_db())

    try:

        result = db.execute(
            text(
                "SELECT current_database(), current_schema()"
            )
        ).fetchone()

        return {
            "status": "CONNECTED",
            "database": result[0],
            "schema": result[1]
        }

    finally:

        db.close()


# ============================================================
# DATABASE TEST DATA
# ============================================================

@app.get("/database/test-data")
def database_test_data():

    db = next(get_db())

    try:

        user = get_user_by_email(
            db,
            "test.driver@ambulance.local"
        )

        ambulance = get_ambulance_by_number(
            db,
            "TEST-AMB-001"
        )

        hospitals = get_ready_hospitals_db(
            db
        )

        officers = get_available_officers_db(
            db
        )

        emergency = get_emergency_by_id(
            db,
            1
        )

        tracking = get_tracking_by_ambulance(
            db,
            1
        )

        routes = get_routes_by_emergency(
            db,
            1
        )

        recommended_route = get_recommended_route(
            db,
            1
        )

        return {

            "status": "SUCCESS",

            "user": (
                user.full_name
                if user
                else None
            ),

            "ambulance": (
                ambulance.ambulance_number
                if ambulance
                else None
            ),

            "ready_hospitals":
                len(hospitals),

            "available_officers":
                len(officers),

            "emergency": (
                emergency.status
                if emergency
                else None
            ),

            "tracking_records":
                len(tracking),

            "routes":
                len(routes),

            "recommended_route": (
                recommended_route.route_name
                if recommended_route
                else None
            )
        }

    finally:

        db.close()


# ============================================================
# REQUEST MODELS
# ============================================================

class TrafficObservation(BaseModel):

    sensor_id: str
    speed_kmh: float


class RouteOption(BaseModel):

    route_id: str
    distance_km: float
    predicted_speed_kmh: float
    congestion: str


class HospitalStatusUpdate(BaseModel):

    emergency_ready: bool
    icu_available: int
    beds_available: int


class HospitalRegistrationRequest(BaseModel):

    hospital_name: str
    email: str
    phone: str
    password: str
    latitude: float
    longitude: float
    icu_available: int = 0
    beds_available: int = 0


class EmergencyRequest(BaseModel):

    ambulance_id: str
    ambulance_latitude: float
    ambulance_longitude: float
    destination_hospital_id: str


class TrackingStartRequest(BaseModel):

    ambulance_id: str
    latitude: float
    longitude: float
    route_id: str | None = None
    hospital_id: str | None = None
    route_geometry: dict | None = None


class TrackingLocationRequest(BaseModel):

    ambulance_id: str
    latitude: float
    longitude: float


# ============================================================
# SYSTEM
# ============================================================

@app.get("/")
def home():

    return {

        "status": "online",

        "service":
            "Ambulance Corridor AI",

        "ml_prediction":
            "15-minute traffic forecasting",

        "traffic_source":
            "Dynamic live traffic"

    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# ============================================================
# TRAFFIC
# ============================================================

@app.post("/traffic/observation")
def traffic_observation(
    data: TrafficObservation
):

    add_traffic_observation(
        data.sensor_id,
        data.speed_kmh
    )

    return {

        "status":
            "observation_added",

        "sensor_id":
            data.sensor_id,

        "speed_kmh":
            data.speed_kmh

    }


@app.get("/traffic/predict/{sensor_id}")
def traffic_prediction(
    sensor_id: str
):

    try:

        return predict_sensor(
            sensor_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# ============================================================
# LIVE TRAFFIC
# ============================================================

@app.post("/traffic/live")
def live_traffic(
    sensor_id: str,
    latitude: float,
    longitude: float
):

    try:

        traffic = add_live_traffic(
            sensor_id,
            latitude,
            longitude
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    return {

        "status":
            "live_traffic_added",

        "sensor_id":
            sensor_id,

        "latitude":
            latitude,

        "longitude":
            longitude,

        "traffic":
            traffic

    }


# ============================================================
# CORRIDOR
# ============================================================

@app.post("/corridor/choose")
def choose_corridor(
    routes: list[RouteOption]
):

    route_data = [

        route.model_dump()

        for route in routes

    ]

    best_route = choose_best_route(
        route_data
    )

    return {

        "status":
            "corridor_selected",

        "recommended_route":
            best_route

    }


# ============================================================
# HOSPITAL
# ============================================================

@app.get("/hospitals/ready")
def ready_hospitals():

    return {

        "hospitals":
            get_ready_hospitals()

    }


@app.get("/hospitals/{hospital_id}")
def hospital_details(
    hospital_id: str
):

    try:

        hospital = get_hospital(
            hospital_id
        )

    except Exception:

        hospital = None

    if hospital is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Hospital '{hospital_id}' "
                f"not found."
            )
        )

    return hospital


@app.put("/hospitals/{hospital_id}/status")
def hospital_status_update(
    hospital_id: str,
    data: HospitalStatusUpdate
):

    try:

        return update_hospital_status(
            hospital_id,
            data.emergency_ready,
            data.icu_available,
            data.beds_available
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ============================================================
# TRAFFIC OFFICERS
# ============================================================

@app.get("/officers/available")
def available_officers():

    return {

        "officers":
            get_available_officers()

    }


@app.post("/officers/{officer_id}/activate")
def officer_activate(
    officer_id: str
):

    try:

        return activate_corridor(
            officer_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


@app.post("/officers/{officer_id}/deactivate")
def officer_deactivate(
    officer_id: str
):

    try:

        return deactivate_corridor(
            officer_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ============================================================
# EMERGENCY
# ============================================================

@app.post("/emergency/start")
async def emergency_start(
    data: EmergencyRequest
):

    # ========================================================
    # 1. VALIDATE AMBULANCE (WITH FALLBACK IF NOT FOUND / BUSY)
    # ========================================================

    db = next(get_db())

    try:

        ambulance = get_ambulance_by_id(
            db,
            data.ambulance_id
        )

        # If requested ambulance is not found or not available, use another available ambulance
        if ambulance is None or ambulance.status != "AVAILABLE":

            fallback_ambulance = (
                db.query(Ambulance)
                .filter(Ambulance.status == "AVAILABLE")
                .first()
            )

            if fallback_ambulance is not None:

                print(
                    f"[AMBULANCE] Requested '{data.ambulance_id}' not available/found. "
                    f"Using available ambulance '{fallback_ambulance.ambulance_number}' (ID: {fallback_ambulance.ambulance_id})"
                )

                ambulance = fallback_ambulance

            elif ambulance is not None:

                # Ambulance exists; reset to AVAILABLE to unblock emergency
                ambulance.status = "AVAILABLE"
                db.commit()
                db.refresh(ambulance)

            else:

                # Auto-provision requested ambulance
                ambulance = Ambulance(
                    ambulance_number=data.ambulance_id or "AMB-001",
                    status="AVAILABLE"
                )
                db.add(ambulance)
                db.commit()
                db.refresh(ambulance)

    finally:

        db.close()

    if ambulance is not None:
        data.ambulance_id = ambulance.ambulance_number or str(ambulance.ambulance_id)

    # ========================================================
    # 2. VALIDATE HOSPITAL
    # ========================================================

    try:

        hospital = get_hospital(
            data.destination_hospital_id
        )

    except Exception:

        hospital = None

    if hospital is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Hospital "
                f"'{data.destination_hospital_id}' "
                f"not found."
            )
        )

    if not hospital.get(
        "emergency_ready",
        False
    ):

        raise HTTPException(
            status_code=409,
            detail=(
                f"Hospital "
                f"'{data.destination_hospital_id}' "
                f"is not ready for emergency admission."
            )
        )

    # ========================================================
    # 3. GET ROUTES
    # ========================================================

    try:

        routes = get_routes(

            start_latitude=
                data.ambulance_latitude,

            start_longitude=
                data.ambulance_longitude,

            destination_latitude=
                hospital["latitude"],

            destination_longitude=
                hospital["longitude"]

        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Routing service failed: "
                f"{error}"
            )
        )

    if not routes:

        raise HTTPException(
            status_code=500,
            detail=(
                "No route returned by "
                "routing service."
            )
        )

    # ========================================================
    # 4. XGBOOST
    # ========================================================

    ML_SENSOR_ID = "773869"

    ml_prediction = None

    try:

        ml_prediction = predict_sensor(
            ML_SENSOR_ID
        )

        print(
            "\n========================================"
        )

        print(
            "[AI] XGBoost 15-minute prediction"
        )

        print(
            "========================================"
        )

        print(
            f"Current speed: "
            f"{ml_prediction['current_speed_kmh']} km/h"
        )

        print(
            f"Predicted speed: "
            f"{ml_prediction['predicted_speed_kmh']} km/h"
        )

        print(
            f"Congestion: "
            f"{ml_prediction['congestion_level']}"
        )

        print(
            "========================================"
        )

    except Exception as error:

        print(
            "\n[WARN] XGBoost prediction unavailable:"
        )

        print(
            str(error)
        )

    # ========================================================
    # 5. ANALYZE ROUTES
    # ========================================================

    emergency_routes = []

    for route in routes:

        try:

            traffic = analyze_route_traffic(
                route
            )

        except Exception as error:

            traffic = {

                "current_speed_kmh":
                    None,

                "free_flow_speed_kmh":
                    None,

                "congestion":
                    "UNKNOWN",

                "traffic_points_checked":
                    0,

                "error":
                    str(error)

            }

        current_speed = traffic.get(
            "current_speed_kmh"
        )

        if current_speed is None:

            current_speed = 20.0

        congestion = traffic.get(
            "congestion",
            "UNKNOWN"
        )

        if congestion == "UNKNOWN":

            if current_speed >= 40:

                congestion = "LOW"

            elif current_speed >= 20:

                congestion = "MODERATE"

            else:

                congestion = "HEAVY"

        predicted_speed = current_speed

        prediction_source = (
            "LIVE_CURRENT_TRAFFIC"
        )

        if ml_prediction is not None:

            predicted_speed = (
                ml_prediction[
                    "predicted_speed_kmh"
                ]
            )

            prediction_source = (
                "XGBOOST_15_MIN_PREDICTION"
            )

        emergency_routes.append({

            **route,

            "current_speed_kmh":
                round(
                    float(current_speed),
                    2
                ),

            "predicted_speed_kmh":
                round(
                    float(predicted_speed),
                    2
                ),

            "congestion":
                congestion,

            "traffic_points_checked":
                traffic.get(
                    "traffic_points_checked",
                    0
                ),

            "free_flow_speed_kmh":
                traffic.get(
                    "free_flow_speed_kmh"
                ),

            "prediction_source":
                prediction_source,

            "prediction_horizon_minutes":
                15

        })

    # ========================================================
    # 6. EMERGENCY DECISION
    # ========================================================

    try:

        result = start_emergency(

            ambulance_id=
                data.ambulance_id,

            routes=
                emergency_routes,

            destination_hospital=
                hospital

        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Emergency decision failed: "
                f"{error}"
            )
        )

    result["destination_hospital"] = (
        hospital
    )

    # ========================================================
    # 7. RECOMMENDED ROUTE
    # ========================================================

    recommended_route = result.get(
        "recommended_route"
    )

    if recommended_route is None:

        if emergency_routes:

            recommended_route = (
                emergency_routes[0]
            )

            result["recommended_route"] = (
                recommended_route
            )

        else:

            raise HTTPException(
                status_code=500,
                detail=(
                    "No route available "
                    "for ambulance tracking."
                )
            )

    # ========================================================
    # 8. ROUTE GEOMETRY
    # ========================================================

    route_geometry = (
        recommended_route.get(
            "geometry"
        )
    )

    # ========================================================
    # 9. START TRACKING
    # ========================================================

    try:

        tracking = start_tracking(

            ambulance_id=
                data.ambulance_id,

            latitude=
                data.ambulance_latitude,

            longitude=
                data.ambulance_longitude,

            route_id=
                recommended_route.get(
                    "route_id"
                ),

            hospital_id=
                data.destination_hospital_id,

            route_geometry=
                route_geometry

        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Tracking failed: "
                f"{error}"
            )
        )

    result["tracking"] = tracking

    # ========================================================
    # 10. START SIMULATION
    # ========================================================

    if route_geometry:

        asyncio.create_task(

            simulate_ambulance_movement(

                ambulance_id=
                    data.ambulance_id,

                route_geometry=
                    route_geometry,

                interval_seconds=5

            )

        )

        result["simulation"] = {

            "status":
                "STARTED",

            "interval_seconds":
                5

        }

    else:

        result["simulation"] = {

            "status":
                "NOT_STARTED",

            "reason":
                "Route geometry unavailable."

        }

    # ========================================================
    # 11. RETURN
    # ========================================================

    return result


# ============================================================
# TRAFFIC STATUS
# ============================================================

@app.get("/traffic/status/{sensor_id}")
def traffic_status(
    sensor_id: str
):

    from services.traffic_database import (
        get_observation_count,
        get_recent_speeds
    )

    count = get_observation_count(
        sensor_id
    )

    history = get_recent_speeds(
        sensor_id,
        limit=12
    )

    return {

        "sensor_id":
            sensor_id,

        "observations_collected":
            count,

        "observations_required":
            12,

        "ml_ready":
            count >= 12,

        "recent_speeds":
            history

    }


# ============================================================
# DASHBOARD STATUS
# ============================================================

@app.get("/dashboard/status")
def dashboard_status():

    from services.traffic_database import (
        get_observation_count,
        get_recent_speeds
    )

    sensor_ids = [
        "773869",
        "773870",
        "773871"
    ]

    traffic = []

    for sensor_id in sensor_ids:

        count = get_observation_count(
            sensor_id
        )

        history = get_recent_speeds(
            sensor_id,
            limit=1
        )

        traffic.append({

            "sensor_id":
                sensor_id,

            "current_speed_kmh":
                (
                    history[-1]
                    if history
                    else None
                ),

            "observations_collected":
                count,

            "ml_ready":
                count >= 12

        })

    return {

        "system_status":
            "ONLINE",

        "traffic_source":
            "LIVE_DYNAMIC_TRAFFIC",

        "traffic":
            traffic,

        "available_officers":
            get_available_officers(),

        "ready_hospitals":
            get_ready_hospitals()

    }


# ============================================================
# TRACKING
# ============================================================

@app.post("/tracking/start")
def tracking_start(
    data: TrackingStartRequest
):

    try:

        return start_tracking(

            ambulance_id=
                data.ambulance_id,

            latitude=
                data.latitude,

            longitude=
                data.longitude,

            route_id=
                data.route_id,

            hospital_id=
                data.hospital_id,

            route_geometry=
                data.route_geometry

        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.put("/tracking/location")
def tracking_location(
    data: TrackingLocationRequest
):

    try:

        return update_location(

            ambulance_id=
                data.ambulance_id,

            latitude=
                data.latitude,

            longitude=
                data.longitude

        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


@app.get("/tracking")
def all_tracking():

    return {

        "active_emergencies":
            get_all_active_emergencies()

    }


@app.get("/tracking/{ambulance_id}")
def tracking_status(
    ambulance_id: str
):

    tracking = get_tracking(
        ambulance_id
    )

    if tracking is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Ambulance '{ambulance_id}' "
                f"is not currently being tracked. "
                f"Start an emergency first."
            )
        )

    return tracking


@app.post("/tracking/{ambulance_id}/complete")
def tracking_complete(
    ambulance_id: str
):

    try:

        return complete_emergency(
            ambulance_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )