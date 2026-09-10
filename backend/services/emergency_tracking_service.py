from datetime import datetime

from sqlalchemy import desc, text

from database.connection import SessionLocal
from database.models import (
    Ambulance,
    AmbulanceTracking,
    Emergency,
    Route
)
from database.crud import create_tracking_record, create_emergency



# ============================================================
# ACTIVE AMBULANCE TRACKING
# ============================================================

active_emergencies = {}


# ============================================================
# HELPER: CONVERT ID SAFELY
# ============================================================

def _safe_int(value):
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        pass

    try:
        db = SessionLocal()
        try:
            amb = db.query(Ambulance).filter(
                Ambulance.ambulance_number.ilike(str(value).strip())
            ).first()
            if amb:
                return amb.ambulance_id
        finally:
            db.close()
    except Exception:
        pass

    return None



# ============================================================
# HELPER: FIND ACTIVE EMERGENCY
# ============================================================

def _get_active_emergency(ambulance_id):

    db = SessionLocal()

    try:

        ambulance_db_id = _safe_int(
            ambulance_id
        )

        if ambulance_db_id is None:
            return None

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.ambulance_id
                ==
                ambulance_db_id,

                Emergency.status.in_([
                    "CREATED",
                    "ACTIVE",
                    "CORRIDOR_ACTIVE"
                ])
            )
            .order_by(
                desc(
                    Emergency.created_at
                )
            )
            .first()
        )

        return emergency

    except Exception as error:

        print(
            "[WARN] Could not find active "
            f"emergency for ambulance "
            f"{ambulance_id}: {error}"
        )

        return None

    finally:

        db.close()


# ============================================================
# HELPER: FIND ACTIVE EMERGENCY ID
# ============================================================

def _get_active_emergency_id(ambulance_id):

    emergency = _get_active_emergency(
        ambulance_id
    )

    if emergency is None:
        return None

    return emergency.emergency_id


# ============================================================
# HELPER: GET LATEST TRACKING RECORD
# ============================================================

def _get_latest_tracking_record(
    ambulance_id,
    emergency_id=None
):

    db = SessionLocal()

    try:

        ambulance_db_id = _safe_int(
            ambulance_id
        )

        if ambulance_db_id is None:
            return None

        query = (
            db.query(AmbulanceTracking)
            .filter(
                AmbulanceTracking.ambulance_id
                ==
                ambulance_db_id
            )
        )

        if emergency_id is not None:

            emergency_db_id = _safe_int(
                emergency_id
            )

            if emergency_db_id is not None:

                query = query.filter(
                    AmbulanceTracking.emergency_id
                    ==
                    emergency_db_id
                )

        return (
            query
            .order_by(
                AmbulanceTracking.recorded_at.desc()
            )
            .first()
        )

    except Exception as error:

        print(
            "[WARN] Could not get latest "
            f"tracking record for ambulance "
            f"{ambulance_id}: {error}"
        )

        return None

    finally:

        db.close()


# ============================================================
# HELPER: GET ROUTE INFORMATION
# ============================================================

def _get_route_information(
    emergency_id
):

    db = SessionLocal()

    try:

        emergency_db_id = _safe_int(
            emergency_id
        )

        if emergency_db_id is None:
            return None

        route = (
            db.query(Route)
            .filter(
                Route.emergency_id
                ==
                emergency_db_id,

                Route.is_recommended
                ==
                True
            )
            .first()
        )

        if route is None:

            route = (
                db.query(Route)
                .filter(
                    Route.emergency_id
                    ==
                    emergency_db_id
                )
                .order_by(
                    Route.route_id.asc()
                )
                .first()
            )

        if route is None:
            return None

        return {
            "route_id":
                route.route_name,

            "route_database_id":
                route.route_id
        }

    except Exception as error:

        print(
            "[WARN] Could not restore route "
            f"information: {error}"
        )

        return None

    finally:

        db.close()


# ============================================================
# HELPER: RESTORE TRACKING FROM POSTGRESQL
# ============================================================

def _restore_tracking_from_database(
    ambulance_id
):

    db = SessionLocal()

    try:

        ambulance_db_id = _safe_int(
            ambulance_id
        )

        if ambulance_db_id is None:
            return None

        # ----------------------------------------------------
        # Find latest active emergency
        # ----------------------------------------------------

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.ambulance_id
                ==
                ambulance_db_id,

                Emergency.status.in_([
                    "CREATED",
                    "ACTIVE",
                    "CORRIDOR_ACTIVE"
                ])
            )
            .order_by(
                desc(
                    Emergency.created_at
                )
            )
            .first()
        )

        if emergency is None:

            print(
                "[WARN] No active PostgreSQL "
                f"emergency found for ambulance "
                f"{ambulance_id}"
            )

            return None

        # ----------------------------------------------------
        # Find latest tracking point
        # ----------------------------------------------------

        tracking = (
            db.query(AmbulanceTracking)
            .filter(
                AmbulanceTracking.ambulance_id
                ==
                ambulance_db_id,

                AmbulanceTracking.emergency_id
                ==
                emergency.emergency_id
            )
            .order_by(
                desc(
                    AmbulanceTracking.recorded_at
                )
            )
            .first()
        )

        if tracking is None:

            print(
                "[WARN] No PostgreSQL tracking "
                f"record found for ambulance "
                f"{ambulance_id}"
            )

            return None

        # ----------------------------------------------------
        # Read coordinates from PostGIS
        # ----------------------------------------------------

        coordinates = db.execute(
            text(
                """
                SELECT
                    ST_Y(location::geometry) AS latitude,
                    ST_X(location::geometry) AS longitude
                FROM ambulance_tracking
                WHERE tracking_id = :tracking_id
                """
            ),
            {
                "tracking_id":
                    tracking.tracking_id
            }
        ).fetchone()

        if coordinates is None:
            return None

        latitude = coordinates.latitude
        longitude = coordinates.longitude

        # ----------------------------------------------------
        # Restore recommended route
        # ----------------------------------------------------

        route = (
            db.query(Route)
            .filter(
                Route.emergency_id
                ==
                emergency.emergency_id,

                Route.is_recommended
                ==
                True
            )
            .first()
        )

        if route is None:

            route = (
                db.query(Route)
                .filter(
                    Route.emergency_id
                    ==
                    emergency.emergency_id
                )
                .order_by(
                    Route.route_id.asc()
                )
                .first()
            )

        route_id = None

        if route is not None:

            route_id = route.route_name

        # ----------------------------------------------------
        # Restore hospital
        # ----------------------------------------------------

        hospital_id = (
            emergency.hospital_id
        )

        # ----------------------------------------------------
        # Build tracking object
        # ----------------------------------------------------

        restored = {

            "ambulance_id":
                str(ambulance_id),

            "latitude":
                float(latitude),

            "longitude":
                float(longitude),

            "route_id":
                route_id,

            "hospital_id":
                (
                    str(hospital_id)
                    if hospital_id is not None
                    else None
                ),

            "route_geometry":
                None,

            "status":
                "EN_ROUTE",

            "last_updated":
                (
                    tracking.recorded_at.isoformat()
                    if tracking.recorded_at
                    else datetime.now().isoformat()
                )

        }

        # ----------------------------------------------------
        # Restore in memory
        # ----------------------------------------------------

        active_emergencies[ambulance_id] = (
            restored
        )

        print(
            "[TRACKING] Tracking state restored "
            f"from PostgreSQL for ambulance "
            f"{ambulance_id}"
        )

        return restored

    except Exception as error:

        print(
            "[WARN] Failed to restore tracking "
            f"from PostgreSQL: {error}"
        )

        return None

    finally:

        db.close()


# ============================================================
# HELPER: SAVE GPS TRACKING TO POSTGRESQL
# ============================================================

def _save_tracking_to_database(
    ambulance_id,
    latitude,
    longitude,
    status
):

    db = SessionLocal()

    try:

        ambulance_db_id = _safe_int(
            ambulance_id
        )

        if ambulance_db_id is None:

            print(
                "[WARN] PostgreSQL tracking skipped: "
                f"invalid ambulance ID "
                f"{ambulance_id}"
            )

            return False

        # ----------------------------------------------------
        # Find active emergency
        # ----------------------------------------------------

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.ambulance_id
                ==
                ambulance_db_id,

                Emergency.status.in_([
                    "CREATED",
                    "ACTIVE",
                    "CORRIDOR_ACTIVE"
                ])
            )
            .order_by(
                desc(
                    Emergency.created_at
                )
            )
            .first()
        )

        if emergency is None:
            try:
                emergency = create_emergency(
                    db=db,
                    ambulance_id=ambulance_db_id,
                    status="ACTIVE"
                )
                db.commit()
                db.refresh(emergency)
                print(
                    f"[DATABASE] Created active emergency {emergency.emergency_id} "
                    f"for ambulance {ambulance_db_id}"
                )
            except Exception as e:
                print(f"[WARN] Could not auto-create emergency: {e}")
                return False


        # ----------------------------------------------------
        # Create tracking history
        # ----------------------------------------------------

        tracking_record = create_tracking_record(

            db=db,

            ambulance_id=ambulance_db_id,

            emergency_id=emergency.emergency_id,

            latitude=float(latitude),

            longitude=float(longitude),

            status=status

        )

        db.commit()

        print(
            "[DATABASE] Tracking point saved | "
            f"Ambulance: {ambulance_db_id} | "
            f"Emergency: {emergency.emergency_id} | "
            f"Location: {latitude}, {longitude}"
        )

        return tracking_record is not None

    except Exception as error:

        db.rollback()

        print(
            "[WARN] PostgreSQL tracking save failed: "
            f"{error}"
        )

        return False

    finally:

        db.close()


# ============================================================
# START TRACKING
# ============================================================

def start_tracking(
    ambulance_id,
    latitude,
    longitude,
    route_id=None,
    hospital_id=None,
    route_geometry=None
):

    latitude = float(latitude)

    longitude = float(longitude)

    timestamp = datetime.now().isoformat()

    active_emergencies[ambulance_id] = {

        "ambulance_id":
            ambulance_id,

        "latitude":
            latitude,

        "longitude":
            longitude,

        "route_id":
            route_id,

        "hospital_id":
            hospital_id,

        "route_geometry":
            route_geometry,

        "status":
            "EN_ROUTE",

        "last_updated":
            timestamp

    }

    # ========================================================
    # SAVE INITIAL GPS POSITION
    # ========================================================

    _save_tracking_to_database(

        ambulance_id=ambulance_id,

        latitude=latitude,

        longitude=longitude,

        status="EN_ROUTE"

    )

    print(
        f"[TRACKING] Tracking started for {ambulance_id}"
    )

    return active_emergencies[ambulance_id]


# ============================================================
# UPDATE LOCATION
# ============================================================

def update_location(
    ambulance_id,
    latitude,
    longitude
):

    # ========================================================
    # RECOVER AFTER SERVER RESTART
    # ========================================================

    if ambulance_id not in active_emergencies:

        restored = (
            _restore_tracking_from_database(
                ambulance_id
            )
        )

        if restored is None:

            raise ValueError(
                f"Ambulance '{ambulance_id}' "
                f"is not being tracked."
            )

    latitude = float(latitude)

    longitude = float(longitude)

    timestamp = datetime.now().isoformat()

    # ========================================================
    # UPDATE IN-MEMORY STATE
    # ========================================================

    active_emergencies[ambulance_id][
        "latitude"
    ] = latitude

    active_emergencies[ambulance_id][
        "longitude"
    ] = longitude

    active_emergencies[ambulance_id][
        "last_updated"
    ] = timestamp

    # ========================================================
    # SAVE GPS UPDATE TO POSTGRESQL
    # ========================================================

    _save_tracking_to_database(

        ambulance_id=ambulance_id,

        latitude=latitude,

        longitude=longitude,

        status="EN_ROUTE"

    )

    return active_emergencies[ambulance_id]


# ============================================================
# GET ONE AMBULANCE
# ============================================================

def get_tracking(
    ambulance_id
):

    tracking = active_emergencies.get(
        ambulance_id
    )

    if tracking is not None:

        return tracking

    return _restore_tracking_from_database(
        ambulance_id
    )


# ============================================================
# GET ALL ACTIVE AMBULANCES
# ============================================================

def get_all_active_emergencies():

    results = list(
        active_emergencies.values()
    )

    db = SessionLocal()

    try:

        emergencies = (
            db.query(Emergency)
            .filter(
                Emergency.status.in_([
                    "CREATED",
                    "ACTIVE",
                    "CORRIDOR_ACTIVE"
                ])
            )
            .all()
        )

        for emergency in emergencies:

            ambulance_id = (
                emergency.ambulance_id
            )

            if ambulance_id in active_emergencies:
                continue

            restored = (
                _restore_tracking_from_database(
                    ambulance_id
                )
            )

            if restored is not None:

                results.append(
                    restored
                )

    except Exception as error:

        print(
            "[WARN] Could not restore all "
            f"active tracking records: {error}"
        )

    finally:

        db.close()

    return results


# ============================================================
# COMPLETE EMERGENCY
# ============================================================

def complete_emergency(
    ambulance_id
):

    # ========================================================
    # RECOVER AFTER SERVER RESTART
    # ========================================================

    if ambulance_id not in active_emergencies:

        restored = (
            _restore_tracking_from_database(
                ambulance_id
            )
        )

        if restored is None:

            return {

                "status":
                    "NOT_FOUND",

                "message": (
                    f"Ambulance '{ambulance_id}' "
                    f"is not currently tracked."
                )

            }

    # ========================================================
    # GET FINAL GPS POSITION
    # ========================================================

    current_latitude = (
        active_emergencies[ambulance_id][
            "latitude"
        ]
    )

    current_longitude = (
        active_emergencies[ambulance_id][
            "longitude"
        ]
    )

    # ========================================================
    # SAVE FINAL TRACKING POINT
    #
    # IMPORTANT:
    # Do this BEFORE setting the emergency to COMPLETED,
    # because _save_tracking_to_database() searches for
    # an active emergency.
    # ========================================================

    _save_tracking_to_database(

        ambulance_id=ambulance_id,

        latitude=current_latitude,

        longitude=current_longitude,

        status="COMPLETED"

    )

    # ========================================================
    # UPDATE IN-MEMORY STATUS
    # ========================================================

    active_emergencies[ambulance_id][
        "status"
    ] = "COMPLETED"

    active_emergencies[ambulance_id][
        "last_updated"
    ] = datetime.now().isoformat()

    # ========================================================
    # UPDATE DATABASE
    # ========================================================

    db = SessionLocal()

    try:

        ambulance_db_id = _safe_int(
            ambulance_id
        )

        if ambulance_db_id is None:

            return active_emergencies[
                ambulance_id
            ]

        # ----------------------------------------------------
        # Find active emergency
        # ----------------------------------------------------

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.ambulance_id
                ==
                ambulance_db_id,

                Emergency.status.in_([
                    "CREATED",
                    "ACTIVE",
                    "CORRIDOR_ACTIVE"
                ])
            )
            .order_by(
                desc(
                    Emergency.created_at
                )
            )
            .first()
        )

        # ----------------------------------------------------
        # Complete emergency
        # ----------------------------------------------------

        if emergency:

            emergency.status = (
                "COMPLETED"
            )

            emergency.completed_at = (
                datetime.utcnow()
            )

            print(
                "[DATABASE] Emergency marked "
                f"COMPLETED | "
                f"Emergency: "
                f"{emergency.emergency_id}"
            )

        # ----------------------------------------------------
        # Release ambulance
        # ----------------------------------------------------

        ambulance = (
            db.query(Ambulance)
            .filter(
                Ambulance.ambulance_id
                ==
                ambulance_db_id
            )
            .first()
        )

        if ambulance:

            ambulance.status = (
                "AVAILABLE"
            )

            ambulance.updated_at = (
                datetime.utcnow()
            )

            print(
                "[DATABASE] Ambulance released | "
                f"Ambulance: "
                f"{ambulance_db_id} "
                f"→ AVAILABLE"
            )

        # ----------------------------------------------------
        # Commit both changes
        # ----------------------------------------------------

        db.commit()

    except Exception as error:

        db.rollback()

        print(
            "[WARN] Failed to complete "
            f"emergency/release ambulance: "
            f"{error}"
        )

    finally:

        db.close()

    return active_emergencies[ambulance_id]