
from sqlalchemy import text

from database.connection import SessionLocal
from database.models import Hospital, User


# ============================================================
# GET HOSPITAL GPS LOCATION FROM POSTGIS
# ============================================================

def _get_hospital_location(
    db,
    hospital_id
):
    """
    Read latitude and longitude from the PostGIS
    location column.
    """

    result = db.execute(
        text(
            """
            SELECT
                ST_Y(location::geometry) AS latitude,
                ST_X(location::geometry) AS longitude
            FROM hospitals
            WHERE hospital_id = :hospital_id
            """
        ),
        {
            "hospital_id": hospital_id
        }
    ).fetchone()

    if result is None:
        return None, None

    return result.latitude, result.longitude


# ============================================================
# CONVERT DATABASE HOSPITAL TO API FORMAT
# ============================================================

def _hospital_to_dict(
    db,
    hospital,
    user=None
):
    """
    Convert PostgreSQL hospital record into the response
    format expected by the existing application.
    """

    latitude, longitude = _get_hospital_location(
        db,
        hospital.hospital_id
    )

    return {
        # PostgreSQL-generated hospital ID
        "hospital_id": hospital.hospital_id,

        "hospital_name": hospital.hospital_name,

        "phone": hospital.phone,

        "latitude": latitude,

        "longitude": longitude,

        "emergency_ready": hospital.emergency_readiness,

        "icu_available": hospital.icu_available,

        "beds_available": hospital.beds_available,

        "status": hospital.status,

        "verification_status": (
            "VERIFIED"
            if user and user.is_verified
            else "PENDING"
        ),

        "is_active": (
            user.is_active
            if user
            else True
        )
    }


LEGACY_HOSPITAL_MAP = {
    "HOSP-001": "City Emergency Hospital",
    "HOSP-002": "Metro Care Hospital",
    "HOSP-003": "Central Medical Hospital"
}


def _resolve_hospital(db, hospital_id):
    if not hospital_id:
        return None

    # 1. Check numeric ID
    try:
        num_id = int(hospital_id)
        h = db.query(Hospital).filter(Hospital.hospital_id == num_id).first()
        if h:
            return h
    except (TypeError, ValueError):
        pass

    # 2. Check legacy map (HOSP-001, HOSP-002, etc.)
    h_str = str(hospital_id).strip()
    target_name = LEGACY_HOSPITAL_MAP.get(h_str.upper())
    if target_name:
        h = db.query(Hospital).filter(Hospital.hospital_name.ilike(f"%{target_name}%")).first()
        if h:
            return h

    # 3. Check hospital_name match
    h = db.query(Hospital).filter(Hospital.hospital_name.ilike(f"%{h_str}%")).first()
    if h:
        return h

    # 4. Fallback to any emergency-ready hospital
    return db.query(Hospital).filter(Hospital.emergency_readiness.is_(True)).first()


# ============================================================
# GET ONE HOSPITAL
# ============================================================

def get_hospital(
    hospital_id
):
    """
    Get a hospital supporting numeric IDs, legacy IDs (e.g. HOSP-001),
    or hospital names with graceful fallback.
    """

    db = SessionLocal()

    try:

        hospital = _resolve_hospital(db, hospital_id)

        if hospital is None:

            raise ValueError(
                f"Hospital '{hospital_id}' not found."
            )

        user = (
            db.query(User)
            .filter(
                User.user_id == hospital.user_id
            )
            .first()
        )

        return _hospital_to_dict(
            db,
            hospital,
            user
        )

    finally:

        db.close()



# ============================================================
# UPDATE HOSPITAL STATUS
# ============================================================

def update_hospital_status(
    hospital_id,
    emergency_ready,
    icu_available,
    beds_available
):
    """
    Update hospital emergency readiness and capacity
    directly in PostgreSQL.
    """

    db = SessionLocal()

    try:

        hospital = _resolve_hospital(db, hospital_id)

        if hospital is None:

            raise ValueError(
                f"Hospital '{hospital_id}' not found."
            )


        hospital.emergency_readiness = bool(
            emergency_ready
        )

        hospital.icu_available = max(
            0,
            int(icu_available)
        )

        hospital.beds_available = max(
            0,
            int(beds_available)
        )

        # ----------------------------------------------------
        # Determine current hospital status
        # ----------------------------------------------------

        if (
            hospital.emergency_readiness
            and hospital.icu_available > 0
        ):

            hospital.status = "READY"

        elif hospital.beds_available > 0:

            hospital.status = "BUSY"

        else:

            hospital.status = "NOT_READY"

        db.commit()

        db.refresh(hospital)

        user = (
            db.query(User)
            .filter(
                User.user_id == hospital.user_id
            )
            .first()
        )

        return _hospital_to_dict(
            db,
            hospital,
            user
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ============================================================
# GET READY HOSPITALS
# ============================================================

def get_ready_hospitals():
    """
    Return only hospitals that:

    1. Exist in PostgreSQL
    2. Have an active user account
    3. Are verified
    4. Are marked emergency-ready
    5. Have a READY status
    """

    db = SessionLocal()

    try:

        rows = (
            db.query(
                Hospital,
                User
            )
            .join(
                User,
                Hospital.user_id
                == User.user_id
            )
            .filter(
                Hospital.emergency_readiness.is_(True),
                Hospital.status == "READY",
                User.is_verified.is_(True),
                User.is_active.is_(True)
            )
            .order_by(
                Hospital.hospital_id
            )
            .all()
        )

        return [
            _hospital_to_dict(
                db,
                hospital,
                user
            )
            for hospital, user in rows
        ]

    finally:

        db.close()


# ============================================================
# CALCULATE HOSPITAL SCORE
# ============================================================

def calculate_hospital_score(
    hospital,
    travel_time_minutes
):
    """
    Lower score = better hospital.

    Travel time is the primary factor.
    ICU and bed availability improve the score.
    """

    if not hospital["emergency_ready"]:

        return float("inf")

    score = float(
        travel_time_minutes
    )

    score -= (
        hospital["icu_available"]
        * 0.5
    )

    score -= (
        hospital["beds_available"]
        * 0.1
    )

    return score


# ============================================================
# CHOOSE BEST HOSPITAL
# ============================================================

def choose_best_hospital(
    hospitals,
    estimated_travel_time
):
    """
    Choose the best hospital from a supplied hospital list.
    """

    ready_hospitals = [
        hospital
        for hospital in hospitals
        if hospital.get(
            "emergency_ready",
            False
        )
    ]

    if not ready_hospitals:

        return None

    return min(
        ready_hospitals,
        key=lambda hospital:
        calculate_hospital_score(
            hospital,
            estimated_travel_time
        )
    )
