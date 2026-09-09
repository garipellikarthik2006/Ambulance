from prediction_service import predict_traffic

from services.traffic_database import (
    save_observation,
    get_recent_speeds,
    get_observation_count
)

from services.feature_builder import build_features


def add_traffic_observation(sensor_id, speed):
    """
    Save a manually supplied traffic observation.
    """

    save_observation(
        sensor_id=sensor_id,
        speed_kmh=speed
    )


def predict_sensor(sensor_id):
    """
    Generate a 15-minute traffic prediction
    using the XGBoost model.
    """

    history = get_recent_speeds(
        sensor_id,
        limit=12
    )

    observation_count = get_observation_count(
        sensor_id
    )

    if len(history) < 12:

        raise ValueError(
            f"ML warming up for sensor {sensor_id}. "
            f"{observation_count}/12 live observations collected."
        )

    features = build_features(history)

    result = predict_traffic(features)

    return {
        "sensor_id": sensor_id,

        "current_speed_kmh":
            history[-1],

        "predicted_speed_kmh":
            result["predicted_speed"],

        "prediction_horizon_minutes":
            15,

        "congestion_level":
            result["congestion"],

        "observations_used":
            len(history),

        "ml_status":
            "READY",

        "prediction_source":
            "XGBOOST_15_MIN_PREDICTION"
    }


def add_live_traffic(
    sensor_id,
    latitude,
    longitude
):
    """
    Fetch live traffic from TomTom,
    save it to SQLite,
    and use XGBoost when enough
    observations are available.
    """

    from services.live_traffic_service import (
        get_live_traffic
    )

    traffic = get_live_traffic(
        latitude,
        longitude
    )

    current_speed = (
        traffic["current_speed_kmh"]
    )

    if current_speed is None:

        raise ValueError(
            "Traffic API did not return current speed."
        )


    # ==========================================
    # SAVE LIVE TRAFFIC
    # ==========================================

    save_observation(

        sensor_id=sensor_id,

        speed_kmh=current_speed,

        latitude=latitude,

        longitude=longitude,

        free_flow_speed_kmh=
            traffic.get(
                "free_flow_speed_kmh"
            ),

        confidence=
            traffic.get(
                "confidence"
            ),

        road_closure=
            traffic.get(
                "road_closure"
            )

    )


    # ==========================================
    # CHECK ML HISTORY
    # ==========================================

    observation_count = (
        get_observation_count(
            sensor_id
        )
    )


    ml_prediction = None


    # ==========================================
    # RUN XGBOOST
    # ==========================================

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


    # ==========================================
    # RESPONSE
    # ==========================================

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

def get_live_or_predicted_speed(sensor_id, current_speed):
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
                prediction["predicted_speed_kmh"],

            "source":
                "XGBOOST_15_MIN_PREDICTION",

            "ml_status":
                "READY",

            "observations_used":
                prediction["observations_used"],

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