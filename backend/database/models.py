from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Boolean,
    Float,
    Text,
    ForeignKey,
    CheckConstraint,
    DateTime,
)
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geography
from datetime import datetime


Base = declarative_base()


# =========================
# USERS
# =========================

class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    password_hash = Column(Text, nullable=False)
    role = Column(String(30), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN', 'AMBULANCE_DRIVER', 'POLICE_OFFICER', 'HOSPITAL')",
            name="users_role_check",
        ),
    )


# =========================
# HOSPITALS
# =========================

class Hospital(Base):
    __tablename__ = "hospitals"

    hospital_id = Column(BigInteger, primary_key=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id"),
        unique=True,
    )

    hospital_name = Column(String(200), nullable=False)
    phone = Column(String(20))

    status = Column(String(30), nullable=False)
    emergency_readiness = Column(Boolean, default=False)

    icu_available = Column(Integer, default=0)
    beds_available = Column(Integer, default=0)

    location = Column(
        Geography(geometry_type="POINT", srid=4326)
    )

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('READY', 'BUSY', 'NOT_READY')",
            name="hospitals_status_check",
        ),
    )


# =========================
# AMBULANCES
# =========================

class Ambulance(Base):
    __tablename__ = "ambulances"

    ambulance_id = Column(BigInteger, primary_key=True)

    ambulance_number = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    driver_user_id = Column(
        BigInteger,
        ForeignKey("users.user_id"),
    )

    status = Column(String(30), nullable=False)

    current_location = Column(
        Geography(geometry_type="POINT", srid=4326)
    )

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'ON_EMERGENCY', 'OFFLINE', 'MAINTENANCE')",
            name="ambulances_status_check",
        ),
    )


# =========================
# TRAFFIC OFFICERS
# =========================

class TrafficOfficer(Base):
    __tablename__ = "traffic_officers"

    officer_id = Column(BigInteger, primary_key=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id"),
        unique=True,
    )

    badge_number = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    status = Column(String(30), nullable=False)

    current_location = Column(
        Geography(geometry_type="POINT", srid=4326)
    )

    corridor_status = Column(String(30), default="INACTIVE")

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'BUSY', 'OFFLINE')",
            name="traffic_officers_status_check",
        ),
    )


# =========================
# EMERGENCIES
# =========================

class Emergency(Base):
    __tablename__ = "emergencies"

    emergency_id = Column(BigInteger, primary_key=True)

    ambulance_id = Column(
        BigInteger,
        ForeignKey("ambulances.ambulance_id"),
        nullable=False,
    )

    hospital_id = Column(
        BigInteger,
        ForeignKey("hospitals.hospital_id"),
    )

    officer_id = Column(
        BigInteger,
        ForeignKey("traffic_officers.officer_id"),
    )

    status = Column(String(30), nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'ACTIVE', 'CORRIDOR_ACTIVE', 'COMPLETED', 'CANCELLED')",
            name="emergencies_status_check",
        ),
    )


# =========================
# AMBULANCE TRACKING
# =========================

class AmbulanceTracking(Base):
    __tablename__ = "ambulance_tracking"

    tracking_id = Column(BigInteger, primary_key=True)

    ambulance_id = Column(
        BigInteger,
        ForeignKey("ambulances.ambulance_id"),
        nullable=False,
    )

    emergency_id = Column(
        BigInteger,
        ForeignKey("emergencies.emergency_id"),
        nullable=False,
    )

    location = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    status = Column(String(30))

    recorded_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )


# =========================
# TRAFFIC OBSERVATIONS
# =========================

class TrafficObservation(Base):
    __tablename__ = "traffic_observations"

    observation_id = Column(BigInteger, primary_key=True)

    sensor_id = Column(String(100), nullable=False)

    location = Column(
        Geography(geometry_type="POINT", srid=4326)
    )

    observed_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    speed_kmh = Column(Float, nullable=False)
    free_flow_speed_kmh = Column(Float)
    confidence = Column(Float)
    road_closure = Column(Boolean)


# =========================
# ROUTES
# =========================

class Route(Base):
    __tablename__ = "routes"

    route_id = Column(BigInteger, primary_key=True)

    emergency_id = Column(
        BigInteger,
        ForeignKey("emergencies.emergency_id"),
        nullable=False,
    )

    route_name = Column(String(150), nullable=False)

    route_geometry = Column(
        Geography(geometry_type="LINESTRING", srid=4326)
    )

    distance_km = Column(Float)
    estimated_duration_seconds = Column(Integer)

    current_speed_kmh = Column(Float)
    predicted_speed_kmh = Column(Float)

    congestion = Column(String(30))
    route_score = Column(Float)

    is_recommended = Column(Boolean, default=False)

    prediction_horizon_minutes = Column(Integer)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )