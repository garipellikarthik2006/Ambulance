from services.live_traffic_service import get_live_traffic


def analyze_route_traffic(route):
    traffic_points = route.get("traffic_points", [])

    if not traffic_points:
        return {
            "current_speed_kmh": None,
            "free_flow_speed_kmh": None,
            "congestion": "UNKNOWN",
            "traffic_points_checked": 0
        }

    speeds = []
    free_flow_speeds = []

    for point in traffic_points:

        try:
            traffic = get_live_traffic(
                point["latitude"],
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
                    float(current_speed)
                )

            if free_flow_speed is not None:
                free_flow_speeds.append(
                    float(free_flow_speed)
                )

        except Exception as error:
            print(
                f"Traffic lookup failed: {error}"
            )

    if not speeds:
        return {
            "current_speed_kmh": None,
            "free_flow_speed_kmh": None,
            "congestion": "UNKNOWN",
            "traffic_points_checked": 0
        }

    average_speed = sum(speeds) / len(speeds)

    average_free_flow = (
        sum(free_flow_speeds)
        / len(free_flow_speeds)
        if free_flow_speeds
        else None
    )

    if average_speed >= 40:
        congestion = "LOW"

    elif average_speed >= 20:
        congestion = "MODERATE"

    else:
        congestion = "HEAVY"

    return {
        "current_speed_kmh": round(
            average_speed,
            2
        ),
        "free_flow_speed_kmh": (
            round(average_free_flow, 2)
            if average_free_flow is not None
            else None
        ),
        "congestion": congestion,
        "traffic_points_checked": len(speeds)
    }