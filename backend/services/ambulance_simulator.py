import asyncio

from services.emergency_tracking_service import (
    update_location,
    get_tracking
)


# ============================================================
# AMBULANCE ROUTE SIMULATOR
# ============================================================

async def simulate_ambulance_movement(
    ambulance_id,
    route_geometry,
    interval_seconds=5
):

    if not route_geometry:

        print(
            f"[WARN] No route geometry for {ambulance_id}"
        )

        return


    coordinates = route_geometry.get(
        "coordinates",
        []
    )


    if not coordinates:

        print(
            f"[WARN] No route coordinates for {ambulance_id}"
        )

        return


    print()
    print("=" * 60)
    print(
        f"[SIM] Starting ambulance simulation: {ambulance_id}"
    )
    print(
        f"[ROUTE] Route points available: {len(coordinates)}"
    )
    print("=" * 60)


    # --------------------------------------------------------
    # MOVE THROUGH ROUTE
    # --------------------------------------------------------

    for coordinate in coordinates:

        # OSRM format:
        # [longitude, latitude]

        if len(coordinate) < 2:
            continue


        longitude = coordinate[0]

        latitude = coordinate[1]


        # ----------------------------------------------------
        # CHECK WHETHER AMBULANCE STILL EXISTS
        # ----------------------------------------------------

        tracking = get_tracking(
            ambulance_id
        )


        if tracking is None:

            print(
                f"[WARN] Tracking stopped for {ambulance_id}"
            )

            return


        # ----------------------------------------------------
        # UPDATE LOCATION
        # ----------------------------------------------------

        update_location(

            ambulance_id=ambulance_id,

            latitude=latitude,

            longitude=longitude

        )


        print(
            f"[AMBULANCE] {ambulance_id} -> "
            f"Lat: {latitude:.6f}, "
            f"Lon: {longitude:.6f}"
        )


        # ----------------------------------------------------
        # WAIT BEFORE NEXT POSITION
        # ----------------------------------------------------

        await asyncio.sleep(
            interval_seconds
        )


    # ========================================================
    # ROUTE COMPLETED
    # ========================================================

    tracking = get_tracking(
        ambulance_id
    )


    if tracking:

        tracking["status"] = "ARRIVED"


    print()
    print("=" * 60)
    print(
        f"[DESTINATION] {ambulance_id} reached destination."
    )
    print("=" * 60)