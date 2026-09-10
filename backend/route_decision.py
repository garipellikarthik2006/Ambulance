def congestion_penalty(congestion):

    penalties = {
        "LOW": 0,
        "MODERATE": 5,
        "HEAVY": 15
    }

    return penalties.get(congestion, 10)


def calculate_route_score(
    distance_km,
    predicted_speed_kmh,
    congestion
):

    if predicted_speed_kmh <= 0:
        return float("inf")

    predicted_time = (
        distance_km / predicted_speed_kmh
    ) * 60

    penalty = congestion_penalty(congestion)

    return predicted_time + penalty


def choose_best_route(routes):

    for route in routes:

        route["score"] = calculate_route_score(
            route["distance_km"],
            route["predicted_speed_kmh"],
            route["congestion"]
        )

    return min(
        routes,
        key=lambda route: route["score"]
    )