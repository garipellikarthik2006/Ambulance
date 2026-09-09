# ============================================================
# CORRIDOR / ROUTE DECISION SERVICE
# ============================================================


# ------------------------------------------------------------
# CONGESTION PENALTY
# ------------------------------------------------------------

def congestion_penalty(congestion):

    penalties = {
        "LOW": 0,
        "MODERATE": 5,
        "HEAVY": 15,
        "UNKNOWN": 10
    }

    return penalties.get(
        congestion,
        10
    )


# ------------------------------------------------------------
# CALCULATE ROUTE SCORE
# ------------------------------------------------------------

def calculate_route_score(
    distance_km,
    predicted_speed_kmh,
    congestion
):

    # Invalid speed means this route cannot be used.
    if (
        predicted_speed_kmh is None
        or predicted_speed_kmh <= 0
    ):

        return {
            "score": float("inf"),
            "estimated_travel_time_minutes": None,
            "congestion_penalty": 999
        }

    # --------------------------------------------------------
    # Calculate predicted travel time
    # --------------------------------------------------------

    predicted_time = (
        distance_km
        / predicted_speed_kmh
    ) * 60

    # --------------------------------------------------------
    # Calculate congestion penalty
    # --------------------------------------------------------

    penalty = congestion_penalty(
        congestion
    )

    # --------------------------------------------------------
    # Final route score
    #
    # Lower score = better route
    # --------------------------------------------------------

    score = (
        predicted_time
        + penalty
    )

    return {
        "score": round(
            score,
            2
        ),

        "estimated_travel_time_minutes": round(
            predicted_time,
            2
        ),

        "congestion_penalty": penalty
    }


# ------------------------------------------------------------
# CHOOSE BEST ROUTE
# ------------------------------------------------------------

def choose_best_route(routes):

    if not routes:
        return None

    # --------------------------------------------------------
    # Calculate score for every route
    # --------------------------------------------------------

    for route in routes:

        score_data = calculate_route_score(

            distance_km=route[
                "distance_km"
            ],

            predicted_speed_kmh=route[
                "predicted_speed_kmh"
            ],

            congestion=route[
                "congestion"
            ]

        )

        # Add decision information to route
        route[
            "score"
        ] = score_data[
            "score"
        ]

        route[
            "estimated_travel_time_minutes"
        ] = score_data[
            "estimated_travel_time_minutes"
        ]

        route[
            "congestion_penalty"
        ] = score_data[
            "congestion_penalty"
        ]

    # --------------------------------------------------------
    # Select route with lowest score
    # --------------------------------------------------------

    best_route = min(
        routes,
        key=lambda route: route[
            "score"
        ]
    )

    # --------------------------------------------------------
    # Add decision explanation
    # --------------------------------------------------------

    best_route[
        "route_decision"
    ] = "SELECTED"

    best_route[
        "decision_reason"
    ] = (
        "Selected because it has "
        "the lowest traffic-adjusted "
        "route score."
    )

    # --------------------------------------------------------
    # Mark the other routes
    # --------------------------------------------------------

    for route in routes:

        if route[
            "route_id"
        ] != best_route[
            "route_id"
        ]:

            route[
                "route_decision"
            ] = "ALTERNATIVE"

            route[
                "decision_reason"
            ] = (
                "Not selected because "
                "another route has a "
                "lower traffic-adjusted "
                "score."
            )

    return best_route