from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import asyncio
from contextlib import asynccontextmanager

from services.traffic_database import initialize_database

from services.traffic_collector import traffic_collection_loop

from services.traffic_service import (
    add_traffic_observation,
    predict_sensor,
    add_live_traffic
)

from services.corridor_service import choose_best_route

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

from services.emergency_service import start_emergency

from services.routing_service import get_routes

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

    # Start live traffic collection
    collector_task = asyncio.create_task(
        traffic_collection_loop()
    )

    yield

    # Stop collector when application shuts down
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
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# DATABASE
# ============================================================

initialize_database()


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
        "service": "Ambulance Corridor AI",
        "ml_prediction": "15-minute traffic forecasting",
        "traffic_source": "Dynamic live traffic"
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
        "status": "observation_added",
        "sensor_id": data.sensor_id,
        "speed_kmh": data.speed_kmh
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
        "status": "live_traffic_added",
        "sensor_id": sensor_id,
        "latitude": latitude,
        "longitude": longitude,
        "traffic": traffic
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
        "status": "corridor_selected",
        "recommended_route": best_route
    }


# ============================================================
# HOSPITAL
# ============================================================

@app.get("/hospitals/{hospital_id}")
def hospital_details(
    hospital_id: str
):

    hospital = get_hospital(
        hospital_id
    )

    if hospital is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital not found."
        )

    return hospital


@app.get("/hospitals/ready")
def ready_hospitals():

    return {
        "hospitals": get_ready_hospitals()
    }


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
        "officers": get_available_officers()
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

    # --------------------------------------------------------
    # 1. GET DESTINATION HOSPITAL
    # --------------------------------------------------------

    hospital = get_hospital(
        data.destination_hospital_id
    )

    if hospital is None:

        raise HTTPException(
            status_code=404,
            detail="Destination hospital not found."
        )


    # --------------------------------------------------------
    # 2. GET ROUTES FROM OSRM
    # --------------------------------------------------------

    try:

        routes = get_routes(
            start_latitude=data.ambulance_latitude,
            start_longitude=data.ambulance_longitude,
            destination_latitude=hospital["latitude"],
            destination_longitude=hospital["longitude"]
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Routing service failed: {error}"
        )


    if not routes:

        raise HTTPException(
            status_code=500,
            detail="No route returned by routing service."
        )


    # --------------------------------------------------------
    # 3. GET XGBOOST PREDICTION
    # --------------------------------------------------------
    #
    # The current XGBoost model was trained using
    # METR-LA sensor 773869.
    #
    # TomTom remains the source of live traffic.
    # XGBoost provides the 15-minute prototype prediction.
    #
    # --------------------------------------------------------

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
            "🤖 XGBoost 15-minute prediction"
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
            "\n⚠️ XGBoost prediction unavailable:"
        )

        print(
            str(error)
        )


    # --------------------------------------------------------
    # 4. ANALYZE LIVE TRAFFIC FOR EACH ROUTE
    # --------------------------------------------------------

    emergency_routes = []


    for route in routes:

        # ----------------------------------------------------
        # GET LIVE TOMTOM TRAFFIC
        # ----------------------------------------------------

        try:

            traffic = analyze_route_traffic(
                route
            )

        except Exception as error:

            traffic = {
                "current_speed_kmh": None,
                "free_flow_speed_kmh": None,
                "congestion": "UNKNOWN",
                "traffic_points_checked": 0,
                "error": str(error)
            }


        # ----------------------------------------------------
        # CURRENT LIVE SPEED
        # ----------------------------------------------------

        current_speed = traffic.get(
            "current_speed_kmh"
        )


        # ----------------------------------------------------
        # SAFETY FALLBACK
        # ----------------------------------------------------

        if current_speed is None:

            current_speed = 20.0


        # ----------------------------------------------------
        # LIVE CONGESTION
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # XGBOOST PREDICTED SPEED
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # CREATE ROUTE INFORMATION
        # ----------------------------------------------------

        emergency_routes.append({

            **route,

            "current_speed_kmh": round(
                float(current_speed),
                2
            ),

            "predicted_speed_kmh": round(
                float(predicted_speed),
                2
            ),

            "congestion": congestion,

            "traffic_points_checked": traffic.get(
                "traffic_points_checked",
                0
            ),

            "free_flow_speed_kmh": traffic.get(
                "free_flow_speed_kmh"
            ),

            "prediction_source": prediction_source,

            "prediction_horizon_minutes": 15

        })


    # --------------------------------------------------------
    # 5. AI SELECTS BEST ROUTE
    # --------------------------------------------------------

    try:

        result = start_emergency(
            ambulance_id=data.ambulance_id,
            routes=emergency_routes,
            destination_hospital=hospital
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Emergency decision failed: {error}"
        )


    result["destination_hospital"] = hospital


    # --------------------------------------------------------
    # 6. GET RECOMMENDED ROUTE
    # --------------------------------------------------------

    recommended_route = result.get(
        "recommended_route"
    )


    # --------------------------------------------------------
    # SAFETY FALLBACK
    # --------------------------------------------------------

    if recommended_route is None:

        if len(emergency_routes) > 0:

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


    # --------------------------------------------------------
    # 7. GET ROUTE GEOMETRY
    # --------------------------------------------------------

    route_geometry = recommended_route.get(
        "geometry"
    )


    # --------------------------------------------------------
    # 8. START AMBULANCE TRACKING
    # --------------------------------------------------------

    try:

        tracking = start_tracking(
            ambulance_id=data.ambulance_id,
            latitude=data.ambulance_latitude,
            longitude=data.ambulance_longitude,
            route_id=recommended_route.get(
                "route_id"
            ),
            hospital_id=data.destination_hospital_id,
            route_geometry=route_geometry
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Tracking failed: {error}"
        )


    result["tracking"] = tracking


    # --------------------------------------------------------
    # 9. START AUTOMATIC AMBULANCE MOVEMENT
    # --------------------------------------------------------

    if route_geometry:

        asyncio.create_task(
            simulate_ambulance_movement(
                ambulance_id=data.ambulance_id,
                route_geometry=route_geometry,
                interval_seconds=5
            )
        )

        result["simulation"] = {
            "status": "STARTED",
            "interval_seconds": 5
        }

    else:

        result["simulation"] = {
            "status": "NOT_STARTED",
            "reason": "Route geometry unavailable."
        }


    # --------------------------------------------------------
    # 10. RETURN COMPLETE RESULT
    # --------------------------------------------------------

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
        "sensor_id": sensor_id,
        "observations_collected": count,
        "observations_required": 12,
        "ml_ready": count >= 12,
        "recent_speeds": history
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

            "sensor_id": sensor_id,

            "current_speed_kmh": (
                history[-1]
                if history
                else None
            ),

            "observations_collected": count,

            "ml_ready": count >= 12

        })


    return {

        "system_status": "ONLINE",

        "traffic_source": "LIVE_DYNAMIC_TRAFFIC",

        "traffic": traffic,

        "available_officers":
            get_available_officers(),

        "ready_hospitals":
            get_ready_hospitals()

    }


# ============================================================
# EMERGENCY TRACKING
# ============================================================

@app.post("/tracking/start")
def tracking_start(
    data: TrackingStartRequest
):

    try:

        return start_tracking(
            ambulance_id=data.ambulance_id,
            latitude=data.latitude,
            longitude=data.longitude,
            route_id=data.route_id,
            hospital_id=data.hospital_id,
            route_geometry=data.route_geometry
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
            ambulance_id=data.ambulance_id,
            latitude=data.latitude,
            longitude=data.longitude
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

    try:

        tracking = get_tracking(
            ambulance_id
        )

    except ValueError:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Ambulance '{ambulance_id}' "
                f"is not currently being tracked. "
                f"Start an emergency first."
            )
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