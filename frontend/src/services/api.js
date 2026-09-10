const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Helper to catch network-level failures (e.g. server down / CORS / offline)
 */
async function safeFetch(url, options = {}) {
  try {
    const response = await fetch(url, options);
    return response;
  } catch (error) {
    if (error.name === "TypeError" || error.message === "Failed to fetch") {
      throw new Error("Unable to reach server. Please check if the backend is running.");
    }
    throw error;
  }
}

// ============================================================
// EMERGENCY START
// ============================================================
export async function startEmergency(payload) {
  const response = await safeFetch(`${API_URL}/emergency/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = "Emergency request failed.";
    try {
      const errorData = JSON.parse(errorText);
      errorMessage = errorData.detail || errorMessage;
    } catch {
      errorMessage = errorText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return await response.json();
}

// ============================================================
// AMBULANCE TRACKING
// ============================================================
export async function getTracking(ambulanceId) {
  if (!ambulanceId) return null;

  try {
    const response = await safeFetch(`${API_URL}/tracking/${ambulanceId}`);

    if (response.status === 404) {
      // 404 means emergency tracking hasn't been started yet for this ID
      return null;
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Failed to fetch ambulance tracking.");
    }

    return await response.json();
  } catch (err) {
    // If backend is unreachable or returns an error during polling
    throw err;
  }
}

// ============================================================
// HOSPITAL DETAILS
// ============================================================
export async function getHospital(hospitalId) {
  const response = await safeFetch(`${API_URL}/hospitals/${hospitalId}`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Hospital '${hospitalId}' not found.`);
  }

  return await response.json();
}

// ============================================================
// AVAILABLE TRAFFIC OFFICERS
// ============================================================
export async function getAvailableOfficers() {
  const response = await safeFetch(`${API_URL}/officers/available`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to fetch available officers.");
  }

  return await response.json();
}

// ============================================================
// TRAFFIC PREDICTION
// ============================================================
export async function getTrafficPrediction(sensorId) {
  const response = await safeFetch(`${API_URL}/traffic/predict/${sensorId}`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to fetch prediction for sensor ${sensorId}`);
  }

  return await response.json();
}

