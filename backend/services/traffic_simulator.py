from services.traffic_service import add_live_traffic


def collect_traffic_sample(
    sensor_id,
    latitude,
    longitude
):

    traffic = add_live_traffic(
        sensor_id,
        latitude,
        longitude
    )

    return {
        "sensor_id": sensor_id,
        "current_speed_kmh": traffic[
            "current_speed_kmh"
        ],
        "free_flow_speed_kmh": traffic[
            "free_flow_speed_kmh"
        ]
    }