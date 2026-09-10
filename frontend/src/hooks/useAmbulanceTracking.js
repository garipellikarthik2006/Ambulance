import { useState, useEffect, useCallback } from "react";
import { getTracking } from "../services/api";

/**
 * Custom hook for polling ambulance live GPS coordinates.
 *
 * @param {string} ambulanceId - The ambulance identifier (e.g., "AMB-001")
 * @param {boolean} isEmergencyActive - Whether an emergency session is active
 * @returns {object} { ambulanceLocation, trackingStatus, lastUpdated, trackingError, refetchTracking }
 */
export function useAmbulanceTracking(ambulanceId, isEmergencyActive = true) {
  const [ambulanceLocation, setAmbulanceLocation] = useState(null);
  const [trackingStatus, setTrackingStatus] = useState("NOT_STARTED");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [trackingError, setTrackingError] = useState(null);

  const fetchTracking = useCallback(async () => {
    if (!ambulanceId || !isEmergencyActive) {
      setTrackingStatus("NOT_STARTED");
      setTrackingError(null);
      return;
    }

    try {
      const data = await getTracking(ambulanceId);

      // If backend returned null / 404 (not started)
      if (!data) {
        setTrackingStatus("NOT_STARTED");
        setTrackingError(null);
        return;
      }

      const latitude = Number(data.latitude);
      const longitude = Number(data.longitude);

      if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
        console.warn("Invalid ambulance coordinates received:", data);
        setTrackingStatus("UNAVAILABLE");
        setTrackingError("Received invalid coordinates from server.");
        return;
      }

      setAmbulanceLocation({ latitude, longitude });
      setTrackingStatus(data.status === "COMPLETED" ? "COMPLETED" : "LIVE");
      setLastUpdated(data.last_updated || new Date().toISOString());
      setTrackingError(null);
    } catch (err) {
      // Server down or network failure
      setTrackingStatus("UNAVAILABLE");
      setTrackingError(err.message || "Unable to reach tracking server.");
    }
  }, [ambulanceId, isEmergencyActive]);

  useEffect(() => {
    if (!ambulanceId || !isEmergencyActive) {
      setTrackingStatus("NOT_STARTED");
      setAmbulanceLocation(null);
      setTrackingError(null);
      return;
    }

    // Immediate initial fetch
    fetchTracking();

    // 5-second recurring polling
    const intervalId = setInterval(fetchTracking, 5000);

    return () => {
      clearInterval(intervalId);
    };
  }, [ambulanceId, isEmergencyActive, fetchTracking]);

  return {
    ambulanceLocation,
    trackingStatus,
    lastUpdated,
    trackingError,
    refetchTracking: fetchTracking
  };
}

export default useAmbulanceTracking;

