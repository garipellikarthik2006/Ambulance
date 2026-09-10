from services.routing_service import get_routes


routes = get_routes(

    start_latitude=17.4400,

    start_longitude=78.3489,

    destination_latitude=17.3850,

    destination_longitude=78.4867

)


print("\n==============================")
print("DYNAMIC ROUTES")
print("==============================")


for route in routes:

    print("\nRoute:", route["route_id"])

    print(
        "Distance:",
        route["distance_km"],
        "km"
    )

    print(
        "Duration:",
        route["duration_minutes"],
        "minutes"
    )

    print(
        "Representative Latitude:",
        route["latitude"]
    )

    print(
        "Representative Longitude:",
        route["longitude"]
    )

    print(
        "Traffic Points:",
        len(
            route["traffic_points"]
        )
    )

    for point in route["traffic_points"]:

        print(
            "   Traffic Point:",
            point["latitude"],
            point["longitude"]
        )