import os
import xgboost as xgb
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ambulance_traffic_model.json")
METADATA_PATH = os.path.join(BASE_DIR, "traffic_model_metadata.pkl")


# Create XGBoost model
model = xgb.XGBRegressor()

# Load native XGBoost model
model.load_model(MODEL_PATH)

# Load metadata
metadata = joblib.load(METADATA_PATH)

feature_columns = metadata["feature_columns"]


def classify_congestion(speed):

    if speed >= 40:
        return "LOW"

    elif speed >= 20:
        return "MODERATE"

    else:
        return "HEAVY"


def predict_traffic(features):

    input_df = pd.DataFrame([features])

    input_df = input_df[feature_columns]

    predicted_speed = model.predict(input_df)[0]

    return {
        "predicted_speed": round(float(predicted_speed), 2),
        "prediction_horizon_minutes": 15,
        "congestion": classify_congestion(predicted_speed)
    }