from services.traffic_service import (
    add_live_traffic,
    get_live_or_predicted_speed,
    predict_sensor
)

from services.corridor_service import (
    choose_best_route
)

from services.hospital_service import (
    get_ready_hospitals
)

from services.officer_service import (
    get_available_officers,
    find_nearest_officer,
    activate_corridor
)


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

    ratio = current_speed / free_flow_speed

    if ratio >= 0.75:
        return "LOW"

    elif ratio >= 0.45:
        return "MODERATE"

    else:
        return "HEAVY"


# ============================================================
# START EMERGENCY
# ============================================================

def start_emergency(
    ambulance_id,
    routes,
    destination_hospital=None
):

    route_results = []

    # --------------------------------------------------------
    # Process every route
    # --------------------------------------------------------

    for route in routes:

        traffic_points = route.get(
            "traffic_points",
            []
        )

        # If OSRM did not provide traffic points,
        # use the route's middle point.
        if not traffic_points:

            traffic_points = [{
                "latitude": route["latitude"],
                "longitude": route["longitude"]
            }]

        speeds = []
        free_flow_speeds = []
        checked_points = []

        # ----------------------------------------------------
        # Get LIVE TomTom traffic for every route point
        # ----------------------------------------------------

        for index, point in enumerate(
            traffic_points
        ):

            try:

                traffic = add_live_traffic(
                    sensor_id=(
                        f"{route['route_id']}"
                        f"-P{index + 1}"
                    ),
                    latitude=point["latitude"],
                    longitude=point["longitude"]
                )

                current_speed = traffic[
                    "current_speed_kmh"
                ]

                free_flow_speed = traffic[
                    "free_flow_speed_kmh"
                ]

                if current_speed is not None:

                    speeds.append(
                        float(current_speed)
                    )

                if free_flow_speed is not None:

                    free_flow_speeds.append(
                        float(free_flow_speed)
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

                checked_points.append({

                    "latitude":
                        point["latitude"],

                    "longitude":
                        point["longitude"],

                    "error":
                        str(error)

                })

        # ----------------------------------------------------
        # Calculate average LIVE traffic
        # ----------------------------------------------------

        if speeds:

            average_speed = (
                sum(speeds) / len(speeds)
            )

        else:

            average_speed = None

        if free_flow_speeds:

            average_free_flow = (
                sum(free_flow_speeds)
                / len(free_flow_speeds)
            )

        else:

            average_free_flow = None

        # ----------------------------------------------------
        # Classify LIVE congestion
        # ----------------------------------------------------

        congestion = classify_live_congestion(
            average_speed,
            average_free_flow
        )

        # ====================================================
        # XGBOOST 15-MINUTE PREDICTION
        # ====================================================

        predicted_speed = average_speed

        prediction_source = (
            "LIVE_CURRENT_TRAFFIC"
        )

        prediction_horizon = 0

        ml_status = "WARMING_UP"

        try:

            # Prototype ML sensor.
            #
            # The current XGBoost model was trained
            # using METR-LA sensor 773869.
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
                "\n----------------------------------------"
            )

            print(
                f"🤖 Route {route['route_id']} "
                "XGBoost prediction"
            )

            print(
                f"Current route speed: "
                f"{average_speed} km/h"
            )

            print(
                f"Predicted speed in 15 minutes: "
                f"{predicted_speed} km/h"
            )

            print(
                f"Congestion: {congestion}"
            )

            print(
                "----------------------------------------"
            )

        except Exception as error:

            print(
                f"⚠️ XGBoost prediction unavailable "
                f"for {route['route_id']}: "
                f"{error}"
            )

            # If ML is unavailable, use live traffic.
            predicted_speed = average_speed

            prediction_source = (
                "LIVE_CURRENT_TRAFFIC"
            )

            prediction_horizon = 0

            ml_status = "WARMING_UP"

        # ----------------------------------------------------
        # Add route result
        # ----------------------------------------------------

        route_results.append({

            "route_id":
                route["route_id"],

            "distance_km":
                route["distance_km"],

            "duration_minutes":
                route.get(
                    "duration_minutes"
                ),

            "latitude":
                route["latitude"],

            "longitude":
                route["longitude"],

            # LIVE traffic
            "current_speed_kmh": (
                round(
                    average_speed,
                    2
                )
                if average_speed is not None
                else None
            ),

            # Free-flow traffic
            "free_flow_speed_kmh": (
                round(
                    average_free_flow,
                    2
                )
                if average_free_flow is not None
                else None
            ),

            # ML prediction
            "predicted_speed_kmh": (
                round(
                    predicted_speed,
                    2
                )
                if predicted_speed is not None
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
                len(checked_points),

            "traffic_points":
                checked_points,

            "geometry":
                route.get(
                    "geometry"
                )

        })

    # ========================================================
    # SELECT BEST ROUTE
    # ========================================================

    valid_routes = [

        route

        for route in route_results

        if route[
            "predicted_speed_kmh"
        ] > 0

    ]

    if valid_routes:

        best_route = choose_best_route(
            valid_routes
        )

    else:

        best_route = None

    # ========================================================
    # HOSPITAL SELECTION
    # ========================================================

    if destination_hospital:

        selected_hospital = (
            destination_hospital
        )

        if destination_hospital[
            "emergency_ready"
        ]:

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
    # TRAFFIC OFFICER SELECTION
    # ========================================================

    selected_officer = None

    if best_route:

        route_points = best_route.get(
            "traffic_points",
            []
        )

        for point in route_points:

            officer = find_nearest_officer(
                point["latitude"],
                point["longitude"]
            )

            if officer:

                if (
                    selected_officer is None
                    or
                    officer[
                        "distance_to_route_km"
                    ]
                    <
                    selected_officer[
                        "distance_to_route_km"
                    ]
                ):

                    selected_officer = (
                        officer
                    )

    # ========================================================
    # ACTIVATE GREEN CORRIDOR
    # ========================================================

    if selected_officer:

        officer_status = activate_corridor(
            selected_officer[
                "officer_id"
            ]
        )

        officer_status[
            "assigned_traffic_point"
        ] = {

            "latitude":
                best_route[
                    "latitude"
                ],

            "longitude":
                best_route[
                    "longitude"
                ]

        }

        officer_status[
            "distance_to_route_km"
        ] = selected_officer[
            "distance_to_route_km"
        ]

        corridor_status = (
            "CORRIDOR_ACTIVATED"
        )

    else:

        officer_status = None

        corridor_status = (
            "WAITING_FOR_TRAFFIC_OFFICER"
        )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {

        "ambulance_id":
            ambulance_id,

        "status":
            "EMERGENCY_PROCESSED",

        "traffic_source":
            "LIVE_DYNAMIC_TRAFFIC",

        "ml_status":
            (
                "READY"
                if any(
                    route[
                        "ml_status"
                    ] == "READY"
                    for route in route_results
                )
                else "WARMING_UP"
            ),

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
            corridor_status

    }