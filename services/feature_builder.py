import math
from datetime import datetime


def build_features(history):
    if len(history) < 12:
        raise ValueError("At least 12 traffic observations are required.")

    now = datetime.now()

    hour = now.hour + now.minute / 60
    day_of_week = now.weekday()

    features = {
        "speed_lag_1": history[-1],
        "speed_lag_2": history[-2],
        "speed_lag_3": history[-3],
        "speed_lag_4": history[-4],
        "speed_lag_5": history[-5],
        "speed_lag_6": history[-6],
        "speed_lag_12": history[-12],

        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),

        "dow_sin": math.sin(2 * math.pi * day_of_week / 7),
        "dow_cos": math.cos(2 * math.pi * day_of_week / 7),

        "is_weekend": int(day_of_week >= 5)
    }

    return features