import asyncio

from services.traffic_service import add_live_traffic


# ============================================================
# ROUTE LOCATIONS
# ============================================================
# IMPORTANT:
# Replace these example coordinates with the actual
# Hyderabad road/junction locations used in your demo.
# ============================================================

TRAFFIC_POINTS = {
    "773869": {
        "latitude": 17.3850,
        "longitude": 78.4867
    },

    "773870": {
        "latitude": 17.4000,
        "longitude": 78.4800
    },

    "773871": {
        "latitude": 17.3700,
        "longitude": 78.5000
    }
}


# ============================================================
# COLLECT ONE LIVE OBSERVATION
# ============================================================

def collect_all_traffic():

    results = []

    for sensor_id, location in TRAFFIC_POINTS.items():

        try:

            traffic = add_live_traffic(
                sensor_id=sensor_id,
                latitude=location["latitude"],
                longitude=location["longitude"]
            )

            results.append({
                "sensor_id": sensor_id,
                "status": "SUCCESS",
                "current_speed_kmh": traffic["current_speed_kmh"],
                "observations_collected": traffic[
                    "observations_collected"
                ]
            })

        except Exception as error:

            results.append({
                "sensor_id": sensor_id,
                "status": "FAILED",
                "error": str(error)
            })

    return results


# ============================================================
# BACKGROUND COLLECTOR
# ============================================================

async def traffic_collection_loop():

    while True:

        print("\n========================================")
        print("Collecting live traffic...")
        print("========================================")

        results = collect_all_traffic()

        for result in results:
            print(result)

        print("Next collection in 5 minutes.")

        await asyncio.sleep(300)