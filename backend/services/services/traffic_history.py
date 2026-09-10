from collections import defaultdict, deque


MAX_HISTORY = 12

traffic_history = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY)
)


def add_speed(sensor_id, speed):

    traffic_history[sensor_id].append(
        float(speed)
    )


def get_history(sensor_id):

    return list(
        traffic_history[sensor_id]
    )


def clear_history(sensor_id):

    traffic_history[sensor_id].clear()