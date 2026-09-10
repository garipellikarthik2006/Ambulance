from services.routing_service import get_routes
from services.route_traffic_service import (
    analyze_route_traffic
)


routes = get_routes(
    start_latitude=17.4400,
    start_longitude=78.3489,
    destination_latitude=17.3850,
    destination_longitude=78.4867
)


print("\n==============================")
print("ROUTE TRAFFIC ANALYSIS")
print("==============================")


for route in routes:

    traffic = analyze_route_traffic(
        route
    )

    print("\n", route["route_id"])

    print(
        "Distance:",
        route["distance_km"],
        "km"
    )

    print(
        "Current Speed:",
        traffic["current_speed_kmh"],
        "km/h"
    )

    print(
        "Free Flow:",
        traffic["free_flow_speed_kmh"],
        "km/h"
    )

    print(
        "Congestion:",
        traffic["congestion"]
    )

    print(
        "Traffic Points:",
        traffic["traffic_points_checked"]
    )