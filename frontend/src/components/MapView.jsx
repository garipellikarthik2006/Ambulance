import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  CircleMarker,
  useMap
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// ============================================================
// CUSTOM EMOJI DIVICONS
// ============================================================
const createEmojiIcon = (emoji, borderColor) => {
  return L.divIcon({
    className: "custom-emoji-icon",
    html: `<div style="
      font-size: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background: #ffffff;
      border-radius: 50%;
      border: 3px solid ${borderColor};
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
    ">${emoji}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18]
  });
};

const ambulanceIcon = createEmojiIcon("🚑", "#dc2626"); // Red accent
const hospitalIcon = createEmojiIcon("🏥", "#2563eb");  // Blue accent
const officerIcon = createEmojiIcon("👮", "#059669");   // Green accent

// ============================================================
// CONGESTION COLOR HELPER
// ============================================================
const getCongestionColor = (congestion) => {
  switch (congestion) {
    case "LOW":
      return "#10b981"; // Green
    case "MODERATE":
      return "#f59e0b"; // Yellow / Orange
    case "HEAVY":
      return "#ef4444"; // Red
    case "UNKNOWN":
    default:
      return "#6b7280"; // Gray fallback
  }
};

// ============================================================
// SMART MAP FOLLOWER (Preserves Zoom & Handles Manual Panning)
// ============================================================
function MapFollower({ ambulanceLocation }) {
  const map = useMap();
  const isUserInteracting = useRef(false);

  useEffect(() => {
    const handleDragStart = () => {
      isUserInteracting.current = true;
    };

    map.on("dragstart", handleDragStart);

    return () => {
      map.off("dragstart", handleDragStart);
    };
  }, [map]);

  useEffect(() => {
    if (!ambulanceLocation) {
      return;
    }

    const latitude = Number(ambulanceLocation.latitude);
    const longitude = Number(ambulanceLocation.longitude);

    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      return;
    }

    const currentBounds = map.getBounds();
    const isVisible = currentBounds && currentBounds.contains([latitude, longitude]);

    // If ambulance goes outside the visible viewport or user hasn't dragged away,
    // smoothly pan to the new position without resetting the user's zoom level.
    if (!isVisible || !isUserInteracting.current) {
      map.panTo([latitude, longitude], {
        animate: true,
        duration: 0.8
      });
    }
  }, [ambulanceLocation, map]);

  return null;
}

// ============================================================
// MAP VIEW COMPONENT
// ============================================================
export default function MapView({
  ambulanceId = "AMB-001",
  ambulanceLocation,
  hospital,
  officer,
  recommendedRoute,
  alternativeRoutes = [],
  trackingStatus = "NOT_STARTED",
  startLatitude,
  startLongitude
}) {
  // Determine Map Center
  const mapCenter = ambulanceLocation
    ? [ambulanceLocation.latitude, ambulanceLocation.longitude]
    : startLatitude && startLongitude
    ? [Number(startLatitude), Number(startLongitude)]
    : [17.3850, 78.4867];

  const assignedTrafficPoint =
    officer?.assigned_traffic_point ||
    (officer?.latitude && officer?.longitude
      ? { latitude: officer.latitude, longitude: officer.longitude }
      : null);

  // Combine routes for rendering
  const allRoutes = [];
  if (recommendedRoute) {
    allRoutes.push(recommendedRoute);
  }
  if (Array.isArray(alternativeRoutes)) {
    alternativeRoutes.forEach((route) => {
      if (
        !recommendedRoute ||
        route.route_id !== recommendedRoute.route_id
      ) {
        allRoutes.push(route);
      }
    });
  }

  // Render tracking status badge overlay
  const renderStatusBadge = () => {
    switch (trackingStatus) {
      case "LIVE":
        return (
          <span style={{
            padding: "6px 14px",
            borderRadius: "20px",
            background: "#ecfdf5",
            color: "#047857",
            border: "1px solid #a7f3d0",
            fontWeight: 600,
            fontSize: "13px",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            boxShadow: "0 2px 6px rgba(0,0,0,0.08)"
          }}>
            🟢 LIVE TRACKING
          </span>
        );
      case "UNAVAILABLE":
        return (
          <span style={{
            padding: "6px 14px",
            borderRadius: "20px",
            background: "#fef2f2",
            color: "#b91c1c",
            border: "1px solid #fecaca",
            fontWeight: 600,
            fontSize: "13px",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            boxShadow: "0 2px 6px rgba(0,0,0,0.08)"
          }}>
            🔴 TRACKING UNAVAILABLE
          </span>
        );
      case "NOT_STARTED":
      default:
        return (
          <span style={{
            padding: "6px 14px",
            borderRadius: "20px",
            background: "#f3f4f6",
            color: "#4b5563",
            border: "1px solid #e5e7eb",
            fontWeight: 600,
            fontSize: "13px",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            boxShadow: "0 2px 6px rgba(0,0,0,0.08)"
          }}>
            ⚪ TRACKING NOT STARTED
          </span>
        );
    }
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      {/* MAP OVERLAY STATUS BADGE (Top-Right) */}
      <div style={{
        position: "absolute",
        top: "12px",
        right: "12px",
        zIndex: 1000
      }}>
        {renderStatusBadge()}
      </div>

      {/* MAP OVERLAY LEGEND (Bottom-Left) */}
      <div style={{
        position: "absolute",
        bottom: "16px",
        left: "16px",
        zIndex: 1000,
        background: "rgba(255, 255, 255, 0.95)",
        backdropFilter: "blur(6px)",
        padding: "10px 14px",
        borderRadius: "8px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        border: "1px solid #e5e7eb",
        fontSize: "12px",
        fontFamily: "sans-serif",
        color: "#1f2937",
        maxWidth: "280px"
      }}>
        <div style={{
          fontWeight: 700,
          marginBottom: "6px",
          fontSize: "12px",
          color: "#111827",
          borderBottom: "1px solid #e5e7eb",
          paddingBottom: "4px"
        }}>
          🗺️ Map Legend
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🚑</span> Ambulance
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🏥</span> Hospital
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>👮</span> Officer
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "#2563eb", fontWeight: 700 }}>⭐</span> Recommended
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "#6b7280" }}>🛣️</span> Alternative
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🟢</span> Low Traffic
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🟡</span> Moderate
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🔴</span> Heavy Traffic
          </div>
        </div>
      </div>

      <MapContainer
        center={mapCenter}
        zoom={12}
        style={{
          height: "550px",
          width: "100%",
          borderRadius: "8px"
        }}
      >
        <MapFollower ambulanceLocation={ambulanceLocation} />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* AMBULANCE MARKER (LIVE) */}
        {ambulanceLocation && (
          <Marker
            position={[ambulanceLocation.latitude, ambulanceLocation.longitude]}
            icon={ambulanceIcon}
          >
            <Popup>
              <div style={{ minWidth: "180px", fontFamily: "sans-serif" }}>
                <div style={{ marginBottom: "6px" }}>
                  {trackingStatus === "LIVE" ? (
                    <span style={{ background: "#ecfdf5", color: "#047857", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                      🟢 LIVE TRACKING
                    </span>
                  ) : trackingStatus === "UNAVAILABLE" ? (
                    <span style={{ background: "#fef2f2", color: "#b91c1c", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                      🔴 TRACKING UNAVAILABLE
                    </span>
                  ) : (
                    <span style={{ background: "#f3f4f6", color: "#4b5563", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600 }}>
                      ⚪ NOT STARTED
                    </span>
                  )}
                </div>
                <h4 style={{ margin: "2px 0 6px 0", fontSize: "14px", color: "#111827" }}>
                  🚑 Ambulance ({ambulanceId})
                </h4>
                <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#374151" }}>
                  <strong>Status:</strong> EN_ROUTE
                  <br />
                  <strong>Latitude:</strong> {ambulanceLocation.latitude}
                  <br />
                  <strong>Longitude:</strong> {ambulanceLocation.longitude}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* AMBULANCE MARKER (STARTING LOCATION FALLBACK) */}
        {!ambulanceLocation && startLatitude && startLongitude && (
          <Marker
            position={[Number(startLatitude), Number(startLongitude)]}
            icon={ambulanceIcon}
          >
            <Popup>
              <div style={{ minWidth: "170px", fontFamily: "sans-serif" }}>
                <div style={{ marginBottom: "6px" }}>
                  <span style={{ background: "#f3f4f6", color: "#4b5563", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600 }}>
                    ⚪ NOT STARTED
                  </span>
                </div>
                <h4 style={{ margin: "2px 0 6px 0", fontSize: "14px", color: "#111827" }}>
                  🚑 Ambulance ({ambulanceId})
                </h4>
                <div style={{ fontSize: "12px", color: "#374151" }}>
                  Tracking will start when emergency begins.
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* HOSPITAL MARKER */}
        {hospital && hospital.latitude != null && hospital.longitude != null && (
          <Marker
            position={[Number(hospital.latitude), Number(hospital.longitude)]}
            icon={hospitalIcon}
          >
            <Popup>
              <div style={{ minWidth: "185px", fontFamily: "sans-serif" }}>
                <div style={{ marginBottom: "6px" }}>
                  {hospital.status === "READY" || (hospital.emergency_ready && hospital.status !== "BUSY") ? (
                    <span style={{
                      background: "#ecfdf5",
                      color: "#047857",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 700
                    }}>
                      🟢 READY
                    </span>
                  ) : hospital.status === "BUSY" || hospital.status === "LIMITED" ? (
                    <span style={{
                      background: "#fffbeb",
                      color: "#b45309",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 700
                    }}>
                      🟡 {hospital.status || "BUSY"}
                    </span>
                  ) : (
                    <span style={{
                      background: "#fef2f2",
                      color: "#b91c1c",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 700
                    }}>
                      🔴 {hospital.status || "NOT READY"}
                    </span>
                  )}
                </div>
                <h4 style={{ margin: "2px 0 6px 0", fontSize: "14px", color: "#111827" }}>
                  🏥 {hospital.hospital_name || "Destination Hospital"}
                </h4>
                <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#374151" }}>
                  <strong>Hospital ID:</strong> {hospital.hospital_id || "N/A"}
                  <br />
                  <strong>Status:</strong> {hospital.status || (hospital.emergency_ready ? "READY" : "NOT READY")}
                  <br />
                  <strong>ICU Available:</strong> {hospital.icu_available ?? "N/A"}
                  <br />
                  <strong>Beds Available:</strong> {hospital.beds_available ?? "N/A"}
                  <br />
                  <strong>Emergency Ready:</strong> {hospital.emergency_ready ? "YES" : "NO"}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* TRAFFIC OFFICER MARKER */}
        {assignedTrafficPoint && assignedTrafficPoint.latitude != null && assignedTrafficPoint.longitude != null && (
          <Marker
            position={[
              Number(assignedTrafficPoint.latitude),
              Number(assignedTrafficPoint.longitude)
            ]}
            icon={officerIcon}
          >
            <Popup>
              <div style={{ minWidth: "185px", fontFamily: "sans-serif" }}>
                <div style={{ marginBottom: "6px" }}>
                  {officer?.corridor_active ? (
                    <span style={{
                      background: "#ecfdf5",
                      color: "#047857",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 700
                    }}>
                      🟢 CORRIDOR ACTIVE
                    </span>
                  ) : (
                    <span style={{
                      background: "#f3f4f6",
                      color: "#4b5563",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 600
                    }}>
                      ⚪ CORRIDOR INACTIVE
                    </span>
                  )}
                </div>
                <h4 style={{ margin: "2px 0 6px 0", fontSize: "14px", color: "#111827" }}>
                  👮 {officer?.name || "Traffic Officer"}
                </h4>
                <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#374151" }}>
                  <strong>Officer ID:</strong> {officer?.officer_id || "N/A"}
                  <br />
                  <strong>Junction:</strong> {officer?.location || "Assigned Point"}
                  <br />
                  <strong>Officer Status:</strong> {officer?.status || "ASSIGNED"}
                  <br />
                  <strong>Green Corridor:</strong> {officer?.corridor_active ? "ACTIVE" : "INACTIVE"}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* TRAFFIC SAMPLING POINTS (RECOMMENDED ROUTE ONLY) */}
        {recommendedRoute?.traffic_points && Array.isArray(recommendedRoute.traffic_points) && (
          recommendedRoute.traffic_points
            .slice(0, 15) // Cap at max 15 points to avoid clutter
            .map((point, ptIdx) => {
              if (point.latitude == null || point.longitude == null) return null;

              const pointCongestion = point.congestion || recommendedRoute.congestion || "UNKNOWN";
              const pointColor = getCongestionColor(pointCongestion);
              const pointSpeed = point.current_speed_kmh ?? recommendedRoute.current_speed_kmh;
              const pointFreeFlow = point.free_flow_speed_kmh ?? recommendedRoute.free_flow_speed_kmh;

              return (
                <CircleMarker
                  key={`traffic-point-${ptIdx}`}
                  center={[Number(point.latitude), Number(point.longitude)]}
                  radius={6}
                  pathOptions={{
                    color: pointColor,
                    fillColor: pointColor,
                    fillOpacity: 0.85,
                    weight: 2
                  }}
                >
                  <Popup>
                    <div style={{ minWidth: "175px", fontFamily: "sans-serif" }}>
                      <div style={{ marginBottom: "6px" }}>
                        <span style={{
                          background: pointColor === "#10b981" ? "#ecfdf5" : pointColor === "#f59e0b" ? "#fffbeb" : pointColor === "#ef4444" ? "#fef2f2" : "#f3f4f6",
                          color: pointColor === "#10b981" ? "#047857" : pointColor === "#f59e0b" ? "#b45309" : pointColor === "#ef4444" ? "#b91c1c" : "#4b5563",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 700
                        }}>
                          🚦 TRAFFIC CHECKPOINT #{ptIdx + 1}
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#374151" }}>
                        <strong>Congestion:</strong> {pointCongestion}
                        <br />
                        <strong>Live Speed:</strong> {pointSpeed != null ? `${pointSpeed} km/h` : "N/A"}
                        <br />
                        <strong>Free-Flow Speed:</strong> {pointFreeFlow != null ? `${pointFreeFlow} km/h` : "N/A"}
                        <br />
                        <strong>Predicted ({recommendedRoute.prediction_source || "XGBOOST_15_MIN_PREDICTION"}):</strong> {recommendedRoute.predicted_speed_kmh != null ? `${recommendedRoute.predicted_speed_kmh} km/h` : "N/A"}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })
        )}

        {/* ROUTES (POLYLINES) */}
        {allRoutes.map((route, index) => {
          if (!route.geometry || !route.geometry.coordinates) {
            return null;
          }

          // Flipped GeoJSON coordinates [lng, lat] -> Leaflet [lat, lng]
          const positions = route.geometry.coordinates.map((coordinate) => [
            coordinate[1],
            coordinate[0]
          ]);

          // Decision Authority: Backend route_decision === "SELECTED" or recommendedRoute prop match or single route
          const isRecommended =
            route.route_decision === "SELECTED" ||
            recommendedRoute?.route_id === route.route_id ||
            allRoutes.length === 1;

          return (
            <Polyline
              key={route.route_id || `route-${index}`}
              positions={positions}
              pathOptions={{
                color: isRecommended ? "#2563eb" : "#6b7280",
                weight: isRecommended ? 8 : 4,
                opacity: isRecommended ? 1.0 : 0.65,
                dashArray: isRecommended ? null : "6, 8"
              }}
            >
              <Popup>
                <div style={{ minWidth: "190px", fontFamily: "sans-serif" }}>
                  {isRecommended ? (
                    <span style={{
                      background: "#dbeafe",
                      color: "#1e40af",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 700,
                      display: "inline-block",
                      marginBottom: "6px"
                    }}>
                      ⭐ RECOMMENDED CORRIDOR
                    </span>
                  ) : (
                    <span style={{
                      background: "#f3f4f6",
                      color: "#4b5563",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: 600,
                      display: "inline-block",
                      marginBottom: "6px"
                    }}>
                      ALTERNATIVE ROUTE
                    </span>
                  )}
                  <h4 style={{ margin: "4px 0 6px 0", fontSize: "14px", color: "#111827" }}>
                    🛣️ Route {route.route_id}
                  </h4>
                  <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#374151" }}>
                    <strong>Distance:</strong> {route.distance_km != null ? `${Number(route.distance_km).toFixed(2)} km` : "N/A"}
                    <br />
                    <strong>Est. Time:</strong> {route.estimated_travel_time_minutes != null ? `${Number(route.estimated_travel_time_minutes).toFixed(1)} mins` : "N/A"}
                    <br />
                    <strong>Live Speed:</strong> {route.current_speed_kmh != null ? `${route.current_speed_kmh} km/h` : "N/A"}
                    <br />
                    <strong>Predicted ({route.prediction_source || "XGBOOST_15_MIN_PREDICTION"}):</strong> {route.predicted_speed_kmh != null ? `${route.predicted_speed_kmh} km/h` : "N/A"}
                    <br />
                    <strong>Congestion:</strong> {route.congestion || "UNKNOWN"}
                    <br />
                    <strong>Route Score:</strong> {route.score != null ? Number(route.score).toFixed(2) : "N/A"}
                  </div>
                </div>
              </Popup>
            </Polyline>
          );
        })}
      </MapContainer>
    </div>
  );
}
