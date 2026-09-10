from prediction_service import predict_traffic

from services.traffic_database import (
    save_observation,
    get_recent_speeds,
    get_observation_count
)

from services.feature_builder import build_features


# ============================================================
# POSTGRESQL
# ============================================================

from database.connection import SessionLocal

from database.crud import (
    create_traffic_observation
)


# ============================================================
# SAVE TRAFFIC OBSERVATION TO POSTGRESQL
# ============================================================

def _save_traffic_to_postgresql(
    sensor_id,
    latitude,
    longitude,
    speed_kmh,
    free_flow_speed_kmh=None,
    confidence=None,
    road_closure=False
):
    """
    Save a live traffic observation to PostgreSQL.

    PostgreSQL persistence is intentionally separate from
    the existing SQLite traffic pipeline.

    If PostgreSQL fails, the existing SQLite/ML pipeline
    continues working.
    """

    db = SessionLocal()

    try:

        create_traffic_observation(

            db=db,

            sensor_id=str(
                sensor_id
            ),

            latitude=float(
                latitude
            ),

            longitude=float(
                longitude
            ),

            speed_kmh=(
                speed_kmh
            ),

            free_flow_speed_kmh=(
                free_flow_speed_kmh
            ),

            confidence=(
                confidence
            ),

            road_closure=(
                bool(road_closure)
            )

        )

        print(
            "[DATABASE] Traffic observation "
            "saved to PostgreSQL | "
            f"Sensor: {sensor_id} | "
            f"Speed: {speed_kmh} km/h | "
            f"Location: {latitude}, {longitude}"
        )

        return True

    except Exception as error:

        db.rollback()

        print(
            "[WARN] PostgreSQL traffic persistence "
            f"failed for sensor {sensor_id}: {error}"
        )

        return False

    finally:

        db.close()


# ============================================================
# MANUAL TRAFFIC OBSERVATION
# ============================================================

def add_traffic_observation(
    sensor_id,
    speed
):
    """
    Save a manually supplied traffic observation.

    Existing behavior is preserved:
    manual observations continue to use SQLite.
    """

    save_observation(

        sensor_id=sensor_id,

        speed_kmh=speed

    )


# ============================================================
# XGBOOST PREDICTION
# ============================================================

def predict_sensor(
    sensor_id
):
    """
    Generate a 15-minute traffic prediction
    using the XGBoost model.
    """

    history = get_recent_speeds(

        sensor_id,

        limit=12

    )

    observation_count = (
        get_observation_count(
            sensor_id
        )
    )

    if len(history) < 12:

        raise ValueError(

            f"ML warming up for sensor "
            f"{sensor_id}. "
            f"{observation_count}/12 "
            f"live observations collected."

        )

    features = build_features(
        history
    )

    result = predict_traffic(
        features
    )

    return {

        "sensor_id":
            sensor_id,

        "current_speed_kmh":
            history[-1],

        "predicted_speed_kmh":
            result[
                "predicted_speed"
            ],

        "prediction_horizon_minutes":
            15,

        "congestion_level":
            result[
                "congestion"
            ],

        "observations_used":
            len(history),

        "ml_status":
            "READY",

        "prediction_source":
            "XGBOOST_15_MIN_PREDICTION"

    }


# ============================================================
# LIVE TRAFFIC
# ============================================================

def add_live_traffic(
    sensor_id,
    latitude,
    longitude
):
    """
    Fetch live traffic from TomTom.

    The observation is saved to BOTH:

    1. SQLite
       - Existing traffic history
       - Existing XGBoost pipeline

    2. PostgreSQL
       - Persistent traffic observations
       - Database/history layer

    A PostgreSQL failure does NOT stop the existing
    SQLite/ML pipeline.
    """

    from services.live_traffic_service import (
        get_live_traffic
    )

    # ========================================================
    # GET LIVE TRAFFIC FROM TOMTOM
    # ========================================================

    traffic = get_live_traffic(

        latitude,

        longitude

    )

    current_speed = (
        traffic[
            "current_speed_kmh"
        ]
    )

    if current_speed is None:

        raise ValueError(
            "Traffic API did not return current speed."
        )

    # ========================================================
    # EXTRACT TRAFFIC DATA
    # ========================================================

    free_flow_speed = (
        traffic.get(
            "free_flow_speed_kmh"
        )
    )

    confidence = (
        traffic.get(
            "confidence"
        )
    )

    road_closure = (
        traffic.get(
            "road_closure"
        )
    )

    # ========================================================
    # SAVE TO EXISTING SQLITE DATABASE
    #
    # DO NOT REMOVE.
    #
    # XGBoost uses this history.
    # ========================================================

    save_observation(

        sensor_id=sensor_id,

        speed_kmh=current_speed,

        latitude=latitude,

        longitude=longitude,

        free_flow_speed_kmh=(
            free_flow_speed
        ),

        confidence=(
            confidence
        ),

        road_closure=(
            road_closure
        )

    )

    # ========================================================
    # SAVE TO POSTGRESQL
    #
    # Failure here must NOT break SQLite/ML.
    # ========================================================

    _save_traffic_to_postgresql(

        sensor_id=sensor_id,

        latitude=latitude,

        longitude=longitude,

        speed_kmh=current_speed,

        free_flow_speed_kmh=(
            free_flow_speed
        ),

        confidence=(
            confidence
        ),

        road_closure=(
            road_closure
        )

    )

    # ========================================================
    # CHECK ML HISTORY
    # ========================================================

    observation_count = (
        get_observation_count(
            sensor_id
        )
    )

    ml_prediction = None

    # ========================================================
    # RUN XGBOOST
    # ========================================================

    if observation_count >= 12:

        try:

            ml_prediction = predict_sensor(
                sensor_id
            )

        except Exception as error:

            print(
                f"ML prediction failed for "
                f"{sensor_id}: {error}"
            )

            ml_prediction = None

    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        **traffic,

        "sensor_id":
            sensor_id,

        "observations_collected":
            observation_count,

        "observations_required_for_ml":
            12,

        "ml_ready":
            observation_count >= 12,

        "ml_prediction":
            ml_prediction

    }


# ============================================================
# LIVE OR PREDICTED SPEED
# ============================================================

def get_live_or_predicted_speed(
    sensor_id,
    current_speed
):
    """
    Return XGBoost predicted speed when ML is ready.

    Otherwise return the current live traffic speed.
    """

    try:

        prediction = predict_sensor(
            sensor_id
        )

        return {

            "speed_kmh":
                prediction[
                    "predicted_speed_kmh"
                ],

            "source":
                "XGBOOST_15_MIN_PREDICTION",

            "ml_status":
                "READY",

            "observations_used":
                prediction[
                    "observations_used"
                ],

            "prediction_horizon_minutes":
                prediction[
                    "prediction_horizon_minutes"
                ]

        }

    except Exception:

        observation_count = (
            get_observation_count(
                sensor_id
            )
        )

        return {

            "speed_kmh":
                current_speed,

            "source":
                "LIVE_CURRENT_TRAFFIC",

            "ml_status":
                "WARMING_UP",

            "observations_used":
                observation_count,

            "prediction_horizon_minutes":
                15

        }