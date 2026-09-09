import requests


OSRM_URL = (
    "https://router.project-osrm.org/"
    "route/v1/driving"
)


def get_routes(
    start_latitude,
    start_longitude,
    destination_latitude,
    destination_longitude
):

    # ============================================
    # BUILD OSRM REQUEST
    # ============================================

    coordinates = (
        f"{start_longitude},{start_latitude};"
        f"{destination_longitude},{destination_latitude}"
    )

    url = f"{OSRM_URL}/{coordinates}"

    params = {
        "alternatives": "true",
        "steps": "true",
        "geometries": "geojson",
        "overview": "full"
    }


    # ============================================
    # CALL OSRM
    # ============================================

    response = requests.get(
        url,
        params=params,
        timeout=30
    )


    # ============================================
    # HANDLE OSRM ERRORS
    # ============================================

    if not response.ok:

        raise ValueError(
            f"OSRM routing failed: "
            f"{response.status_code} - "
            f"{response.text}"
        )


    data = response.json()


    if data.get("code") != "Ok":

        raise ValueError(
            f"OSRM routing failed: "
            f"{data.get('code')}"
        )


    routes = []


    # ============================================
    # PROCESS ROUTES
    # ============================================

    for index, route in enumerate(
        data.get("routes", [])
    ):

        geometry = route.get(
            "geometry"
        )

        coordinates = []

        if geometry:

            coordinates = geometry.get(
                "coordinates",
                []
            )


        # ========================================
        # CREATE TRAFFIC POINTS
        # ========================================

        traffic_points = []


        if coordinates:

            total_points = len(
                coordinates
            )


            if total_points >= 3:

                indexes = [

                    int(
                        total_points * 0.25
                    ),

                    int(
                        total_points * 0.50
                    ),

                    int(
                        total_points * 0.75
                    )

                ]


                for point_index in indexes:

                    point_index = min(
                        point_index,
                        total_points - 1
                    )


                    longitude, latitude = (
                        coordinates[
                            point_index
                        ]
                    )


                    traffic_points.append({

                        "latitude":
                            latitude,

                        "longitude":
                            longitude

                    })


            else:

                for coordinate in coordinates:

                    longitude, latitude = (
                        coordinate
                    )


                    traffic_points.append({

                        "latitude":
                            latitude,

                        "longitude":
                            longitude

                    })


        # ========================================
        # REPRESENTATIVE ROUTE POINT
        # ========================================

        if coordinates:

            middle_index = (
                len(coordinates) // 2
            )

            longitude, latitude = (
                coordinates[middle_index]
            )

        else:

            latitude = start_latitude
            longitude = start_longitude


        # ========================================
        # SAVE ROUTE
        # ========================================

        routes.append({

            "route_id":
                f"ROUTE-{index + 1}",

            "distance_km":
                round(
                    route["distance"] / 1000,
                    2
                ),

            "duration_minutes":
                round(
                    route["duration"] / 60,
                    1
                ),

            # Representative route location
            "latitude":
                latitude,

            "longitude":
                longitude,

            # Complete route geometry
            "geometry":
                geometry,

            # Points used for live traffic
            "traffic_points":
                traffic_points

        })


    # ============================================
    # NO ROUTES
    # ============================================

    if not routes:

        raise ValueError(
            "OSRM returned no routes."
        )


    return routes