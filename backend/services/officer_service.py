import math

from sqlalchemy import text

from database.connection import SessionLocal
from database.models import TrafficOfficer, User


# ============================================================
# DISTANCE CALCULATION
# ============================================================

def calculate_distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.
    """

    earth_radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


# ============================================================
# GET OFFICER GPS LOCATION FROM POSTGIS
# ============================================================

def _get_officer_location(
    db,
    officer_id
):
    """
    Read latitude and longitude from the PostGIS
    current_location column.
    """

    result = db.execute(
        text(
            """
            SELECT
                ST_Y(current_location::geometry) AS latitude,
                ST_X(current_location::geometry) AS longitude
            FROM traffic_officers
            WHERE officer_id = :officer_id
            """
        ),
        {
            "officer_id": officer_id
        }
    ).fetchone()

    if result is None:
        return None, None

    return result.latitude, result.longitude


# ============================================================
# CONVERT DATABASE OFFICER TO API FORMAT
# ============================================================

def _officer_to_dict(
    db,
    officer,
    user,
    distance_to_route_km=None
):
    """
    Convert SQLAlchemy/PostgreSQL officer data to the
    application response format.
    """

    latitude, longitude = _get_officer_location(
        db,
        officer.officer_id
    )

    result = {
        # PostgreSQL-generated primary key
        "officer_id": officer.officer_id,

        # Registration/badge identifier
        "badge_number": officer.badge_number,

        # User registration data
        "name": (
            user.full_name
            if user
            else None
        ),

        # Kept for compatibility with old frontend
        "location": (
            "GPS Location"
            if latitude is not None
            else None
        ),

        "latitude": latitude,

        "longitude": longitude,

        "status": officer.status,

        "corridor_active": (
            officer.corridor_status == "ACTIVE"
        )
    }

    if distance_to_route_km is not None:

        result["distance_to_route_km"] = round(
            distance_to_route_km,
            2
        )

    return result


# ============================================================
# GET AVAILABLE OFFICERS
# ============================================================

def get_available_officers():
    """
    Get all available traffic officers from PostgreSQL.

    No static officer dictionary is used.
    """

    db = SessionLocal()

    try:

        rows = (
            db.query(
                TrafficOfficer,
                User
            )
            .join(
                User,
                TrafficOfficer.user_id
                == User.user_id
            )
            .filter(
                TrafficOfficer.status == "AVAILABLE",
                TrafficOfficer.corridor_status == "INACTIVE",
                User.is_active.is_(True)
            )
            .order_by(
                TrafficOfficer.officer_id
            )
            .all()
        )

        result = []

        for officer, user in rows:

            result.append(
                _officer_to_dict(
                    db,
                    officer,
                    user
                )
            )

        return result

    finally:

        db.close()


# ============================================================
# FIND NEAREST AVAILABLE OFFICER
# ============================================================

def find_nearest_officer(
    latitude,
    longitude
):
    """
    Find the nearest available officer using
    PostgreSQL/PostGIS stored GPS coordinates.

    The returned officer_id is the actual
    PostgreSQL-generated officer_id.
    """

    db = SessionLocal()

    try:

        rows = (
            db.query(
                TrafficOfficer,
                User
            )
            .join(
                User,
                TrafficOfficer.user_id
                == User.user_id
            )
            .filter(
                TrafficOfficer.status == "AVAILABLE",
                TrafficOfficer.corridor_status == "INACTIVE",
                User.is_active.is_(True)
            )
            .all()
        )

        if not rows:
            return None

        nearest = None
        nearest_distance = float("inf")

        for officer, user in rows:

            officer_latitude, officer_longitude = (
                _get_officer_location(
                    db,
                    officer.officer_id
                )
            )

            if (
                officer_latitude is None
                or officer_longitude is None
            ):
                continue

            distance = calculate_distance_km(
                latitude,
                longitude,
                officer_latitude,
                officer_longitude
            )

            if distance < nearest_distance:

                nearest_distance = distance

                nearest = _officer_to_dict(
                    db,
                    officer,
                    user,
                    distance
                )

        return nearest

    finally:

        db.close()


# ============================================================
# ACTIVATE GREEN CORRIDOR
# ============================================================

def activate_corridor(
    officer_id
):
    """
    Activate the officer using the PostgreSQL-generated
    numeric officer_id.
    """

    db = SessionLocal()

    try:

        try:
            officer_id = int(officer_id)
        except (TypeError, ValueError):

            raise ValueError(
                f"Invalid officer ID '{officer_id}'. "
                f"Expected PostgreSQL-generated numeric officer_id."
            )

        officer = (
            db.query(TrafficOfficer)
            .filter(
                TrafficOfficer.officer_id
                == officer_id
            )
            .first()
        )

        if officer is None:

            raise ValueError(
                f"Officer '{officer_id}' not found."
            )

        user = (
            db.query(User)
            .filter(
                User.user_id
                == officer.user_id
            )
            .first()
        )

        if officer.status == "OFFLINE":

            raise ValueError(
                f"Officer '{officer_id}' is currently OFFLINE."
            )

        officer.status = "BUSY"
        officer.corridor_status = "ACTIVE"

        db.commit()
        db.refresh(officer)

        return _officer_to_dict(
            db,
            officer,
            user
        )

    except Exception:
        db.rollback()
        raise

    finally:

        db.close()


# ============================================================
# DEACTIVATE GREEN CORRIDOR
# ============================================================

def deactivate_corridor(
    officer_id
):
    """
    Deactivate the officer using the PostgreSQL-generated
    numeric officer_id.
    """

    db = SessionLocal()

    try:

        try:
            officer_id = int(officer_id)
        except (TypeError, ValueError):

            raise ValueError(
                f"Invalid officer ID '{officer_id}'. "
                f"Expected PostgreSQL-generated numeric officer_id."
            )

        officer = (
            db.query(TrafficOfficer)
            .filter(
                TrafficOfficer.officer_id
                == officer_id
            )
            .first()
        )

        if officer is None:

            raise ValueError(
                f"Officer '{officer_id}' not found."
            )

        user = (
            db.query(User)
            .filter(
                User.user_id
                == officer.user_id
            )
            .first()
        )

        officer.status = "AVAILABLE"
        officer.corridor_status = "INACTIVE"

        db.commit()
        db.refresh(officer)

        return _officer_to_dict(
            db,
            officer,
            user
        )

    except Exception:
        db.rollback()
        raise

    finally:

        db.close()