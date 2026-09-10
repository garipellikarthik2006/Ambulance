import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.abspath(os.path.join(BASE_DIR, "..", "traffic_history.db"))


def get_connection():
    return sqlite3.connect(
        DATABASE_NAME,
        check_same_thread=False
    )


def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traffic_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            speed_kmh REAL NOT NULL,
            latitude REAL,
            longitude REAL,
            free_flow_speed_kmh REAL,
            confidence REAL,
            road_closure INTEGER
        )
    """)

    connection.commit()
    connection.close()


def save_observation(
    sensor_id,
    speed_kmh,
    latitude=None,
    longitude=None,
    free_flow_speed_kmh=None,
    confidence=None,
    road_closure=None
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO traffic_observations (
            sensor_id,
            timestamp,
            speed_kmh,
            latitude,
            longitude,
            free_flow_speed_kmh,
            confidence,
            road_closure
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sensor_id,
        datetime.now().isoformat(),
        speed_kmh,
        latitude,
        longitude,
        free_flow_speed_kmh,
        confidence,
        int(road_closure) if road_closure is not None else None
    ))

    connection.commit()
    connection.close()


def get_recent_speeds(sensor_id, limit=12):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT speed_kmh
        FROM traffic_observations
        WHERE sensor_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (
        sensor_id,
        limit
    ))

    rows = cursor.fetchall()

    connection.close()

    speeds = [
        row[0]
        for row in rows
    ]

    speeds.reverse()

    return speeds


def get_observation_count(sensor_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM traffic_observations
        WHERE sensor_id = ?
    """, (sensor_id,))

    count = cursor.fetchone()[0]

    connection.close()

    return count