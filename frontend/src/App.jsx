import { useState } from "react";
import MapView from "./components/MapView";
import { startEmergency as apiStartEmergency } from "./services/api";
import { useAmbulanceTracking } from "./hooks/useAmbulanceTracking";



// ============================================================
// APP
// ============================================================

function App() {

  // ==========================================================
  // STATE (With Session Persistence for Mid-Emergency Refresh)
  // ==========================================================

  const [ambulanceId, setAmbulanceId] = useState(() => {
    return sessionStorage.getItem("emergency_ambulanceId") || "AMB-001";
  });

  const [startLatitude, setStartLatitude] = useState(() => {
    return sessionStorage.getItem("emergency_startLat") || "";
  });

  const [startLongitude, setStartLongitude] = useState(() => {
    return sessionStorage.getItem("emergency_startLng") || "";
  });

  const [hospitalId, setHospitalId] = useState(() => {
    return sessionStorage.getItem("emergency_hospitalId") || "HOSP-001";
  });

  const [result, setResult] = useState(() => {
    try {
      const saved = sessionStorage.getItem("emergency_result");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Save values to sessionStorage for refresh tolerance
  const saveSession = (newResult, ambId, lat, lng, hospId) => {
    if (newResult) {
      sessionStorage.setItem("emergency_result", JSON.stringify(newResult));
      sessionStorage.setItem("emergency_ambulanceId", ambId);
      sessionStorage.setItem("emergency_startLat", lat);
      sessionStorage.setItem("emergency_startLng", lng);
      sessionStorage.setItem("emergency_hospitalId", hospId);
    } else {
      sessionStorage.removeItem("emergency_result");
    }
  };

  const resetEmergency = () => {
    setResult(null);
    setError("");
    sessionStorage.removeItem("emergency_result");
  };

  // ==========================================================
  // GET CURRENT LOCATION
  // ==========================================================

  const useCurrentLocation = () => {
    setError("");

    if (!navigator.geolocation) {
      setError("Geolocation is not supported by this browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude.toFixed(6);
        const lng = position.coords.longitude.toFixed(6);
        setStartLatitude(lat);
        setStartLongitude(lng);
        sessionStorage.setItem("emergency_startLat", lat);
        sessionStorage.setItem("emergency_startLng", lng);
      },
      (locationError) => {
        console.error("Location error:", locationError);
        setError(
          "Unable to get your current location. Please enter coordinates manually."
        );
      }
    );
  };

  // ==========================================================
  // AMBULANCE TRACKING HOOK
  // ==========================================================

  const { ambulanceLocation, trackingStatus, trackingError } = useAmbulanceTracking(
    ambulanceId,
    Boolean(result)
  );

  // ==========================================================
  // START EMERGENCY
  // ==========================================================

  const startEmergency = async () => {
    setError("");

    if (!startLatitude || !startLongitude) {
      setError("Please enter the ambulance starting location.");
      return;
    }

    const latitude = Number(startLatitude);
    const longitude = Number(startLongitude);

    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      setError("Latitude and longitude must be valid numbers.");
      return;
    }

    setLoading(true);

    try {
      const data = await apiStartEmergency({
        ambulance_id: ambulanceId,
        ambulance_latitude: latitude,
        ambulance_longitude: longitude,
        destination_hospital_id: hospitalId
      });

      console.log("Emergency response:", data);
      setResult(data);
      saveSession(data, ambulanceId, startLatitude, startLongitude, hospitalId);
    } catch (err) {
      console.error("Emergency start failed:", err);
      const friendlyMsg =
        err.message === "Failed to fetch" || err.message?.includes("Unable to reach server")
          ? "Unable to reach server. Please ensure the backend is running at http://127.0.0.1:8000."
          : (err.message || "Unable to process emergency request.");
      setError(friendlyMsg);
    } finally {
      setLoading(false);
    }
  };



  // ==========================================================
  // BACKEND DATA
  // ==========================================================

  const hospital =
    result?.destination_hospital ||
    result?.selected_hospital ||
    null;

  const routes =
    result?.routes_analyzed ||
    result?.routes ||
    [];

  const recommendedRoute =
    result?.recommended_route ||
    null;

  const assignedOfficer =
    result?.assigned_officer ||
    null;

  const assignedTrafficPoint =
    assignedOfficer?.assigned_traffic_point ||
    null;


  // ==========================================================
  // MAP CENTER
  // ==========================================================

  const mapCenter =

    ambulanceLocation

      ? [
          ambulanceLocation.latitude,
          ambulanceLocation.longitude
        ]

      : (
          startLatitude &&
          startLongitude
        )

        ? [
            Number(startLatitude),
            Number(startLongitude)
          ]

        : [
            17.3850,
            78.4867
          ];


  // ==========================================================
  // ROUTE COLOR
  // ==========================================================

  const getRouteColor = (
    congestion
  ) => {

    switch (congestion) {

      case "LOW":
        return "green";

      case "MODERATE":
        return "orange";

      case "HEAVY":
        return "red";

      default:
        return "gray";

    }

  };


  // ==========================================================
  // ML STATUS
  // ==========================================================

  const getMLStatus = (
    route
  ) => {

    if (
      route?.ml_status === "READY"
    ) {

      return "READY";

    }

    return (
      route?.ml_status ||
      "WARMING_UP"
    );

  };


  // ==========================================================
  // PREDICTION SOURCE
  // ==========================================================

  const getPredictionSource = (
    route
  ) => {

    return (
      route?.prediction_source ||
      "LIVE_CURRENT_TRAFFIC"
    );

  };


  // ==========================================================
  // ROUTE DECISION
  // ==========================================================

  const getRouteDecision = (
    route
  ) => {

    if (
      route?.route_decision
    ) {

      return route.route_decision;

    }

    if (
      recommendedRoute?.route_id ===
      route?.route_id
    ) {

      return "SELECTED";

    }

    return "ALTERNATIVE";

  };


  // ==========================================================
  // MAIN UI
  // ==========================================================

  return (

    <div className="app">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="header">

        <div>

          <h1>
            🚑 Ambulance Corridor AI
          </h1>

          <p>
            Dynamic emergency routing and
            traffic intelligence
          </p>

        </div>

      </header>


      {/* ======================================================
          MAIN DASHBOARD
      ====================================================== */}

      <main className="dashboard">


        {/* ====================================================
            AMBULANCE CONTROL PANEL
        ==================================================== */}

        <section className="control-panel">

          <h2>
            Ambulance Emergency
          </h2>


          <label>
            Ambulance ID
          </label>

          <input
            value={
              ambulanceId
            }
            onChange={(e) =>
              setAmbulanceId(
                e.target.value
              )
            }
            placeholder="AMB-001"
          />


          <label>
            Starting Latitude
          </label>

          <input
            value={
              startLatitude
            }
            onChange={(e) =>
              setStartLatitude(
                e.target.value
              )
            }
            placeholder="17.4400"
          />


          <label>
            Starting Longitude
          </label>

          <input
            value={
              startLongitude
            }
            onChange={(e) =>
              setStartLongitude(
                e.target.value
              )
            }
            placeholder="78.3489"
          />


          <button
            onClick={
              useCurrentLocation
            }
            className="location-button"
          >

            📍 Use My Current Location

          </button>


          <label>
            Destination Hospital
          </label>

          <select
            value={
              hospitalId
            }
            onChange={(e) =>
              setHospitalId(
                e.target.value
              )
            }
          >

            <option value="HOSP-001">
              City Emergency Hospital
            </option>

            <option value="HOSP-002">
              Metro Care Hospital
            </option>

            <option value="HOSP-003">
              Central Medical Hospital
            </option>

          </select>


          <button
            onClick={
              startEmergency
            }
            className="emergency-button"
            disabled={
              loading
            }
          >

            {
              loading

                ? "Finding Best Route..."

                : "🚨 Start Emergency"
            }

          </button>


          {result && (
            <button
              onClick={resetEmergency}
              style={{
                marginTop: "12px",
                width: "100%",
                padding: "10px",
                background: "#f3f4f6",
                color: "#4b5563",
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                fontWeight: 600,
                cursor: "pointer"
              }}
            >
              🔄 Reset Emergency Session
            </button>
          )}

          {error && (
            <div className="error">
              {error}
            </div>
          )}

        </section>


        {/* ====================================================
            MAP
        ==================================================== */}

        <section className="map-panel">
          <h2>
            Live Emergency Route
          </h2>

          <MapView
            ambulanceId={ambulanceId}
            ambulanceLocation={ambulanceLocation}
            hospital={hospital}
            officer={assignedOfficer}
            recommendedRoute={recommendedRoute}
            alternativeRoutes={routes.filter(
              (r) => r.route_id !== recommendedRoute?.route_id
            )}
            trackingStatus={trackingStatus}
            startLatitude={startLatitude}
            startLongitude={startLongitude}
          />
        </section>


      </main>


      {/* ======================================================
          RESULTS
      ====================================================== */}

      {result && (

        <section className="results">

          <h2>
            🤖 AI Emergency Decision
          </h2>


          {/* ==================================================
              AI ROUTE DECISION
          ================================================== */}

          {recommendedRoute && (

            <div className="ai-decision-panel">

              <h2>
                🏆 AI Route Decision
              </h2>

              <div className="ai-decision-main">

                <div>

                  <div className="ai-decision-label">
                    SELECTED ROUTE
                  </div>

                  <div className="ai-decision-route">

                    {
                      recommendedRoute.route_id
                    }

                  </div>

                </div>


                <div>

                  <div className="ai-decision-label">
                    ROUTE SCORE
                  </div>

                  <div className="ai-decision-score">

                    {
                      recommendedRoute.score != null
                        ? Number(
                            recommendedRoute.score
                          ).toFixed(2)
                        : "N/A"
                    }

                  </div>

                </div>

              </div>


              <div className="ai-decision-grid">

                <div>

                  <strong>
                    🚗 Live Speed
                  </strong>

                  <span>

                    {
                      recommendedRoute.current_speed_kmh ??
                      "N/A"
                    }
                    {" "}km/h

                  </span>

                </div>


                <div>

                  <strong>
                    🧠 Predicted Speed
                  </strong>

                  <span>

                    {
                      recommendedRoute.predicted_speed_kmh ??
                      "N/A"
                    }
                    {" "}km/h

                  </span>

                </div>


                <div>

                  <strong>
                    🚦 Congestion
                  </strong>

                  <span>

                    {
                      recommendedRoute.congestion ||
                      "UNKNOWN"
                    }

                  </span>

                </div>


                <div>

                  <strong>
                    ⏱️ Estimated Travel Time
                  </strong>

                  <span>

                    {
                      recommendedRoute
                        .estimated_travel_time_minutes != null

                        ? Number(
                            recommendedRoute
                              .estimated_travel_time_minutes
                          ).toFixed(2)

                        : "N/A"
                    }
                    {" "}minutes

                  </span>

                </div>


                <div>

                  <strong>
                    ⚠️ Congestion Penalty
                  </strong>

                  <span>

                    {
                      recommendedRoute
                        .congestion_penalty ??
                      "N/A"
                    }

                  </span>

                </div>


                <div>

                  <strong>
                    🤖 Prediction Source
                  </strong>

                  <span>

                    {
                      getPredictionSource(
                        recommendedRoute
                      )
                    }

                  </span>

                </div>

              </div>


              <div className="ai-decision-reason">

                <strong>
                  💡 Why was this route selected?
                </strong>

                <p>

                  {
                    recommendedRoute
                      .decision_reason ||

                    "This route has the lowest traffic-adjusted score."
                  }

                </p>

              </div>

            </div>

          )}


          {/* ==================================================
              SUMMARY CARDS
          ================================================== */}

          <div className="cards">


            {/* =================================================
                RECOMMENDED ROUTE
            ================================================= */}

            <div className="card">

              <h3>
                ⭐ Recommended Route
              </h3>

              <strong>

                {
                  recommendedRoute?.route_id ||
                  "No route available"
                }

              </strong>


              {recommendedRoute && (

                <>

                  <p>

                    📏 Distance:
                    {" "}
                    {
                      recommendedRoute.distance_km
                    }
                    {" "}km

                  </p>


                  <p>

                    🚦 Traffic:
                    {" "}
                    {
                      recommendedRoute.congestion ||
                      "UNKNOWN"
                    }

                  </p>


                  <p>

                    🚗 Current Speed:
                    {" "}
                    {
                      recommendedRoute.current_speed_kmh ??
                      "N/A"
                    }
                    {" "}km/h

                  </p>


                  <p>

                    🧠 ML Predicted Speed:
                    {" "}
                    {
                      recommendedRoute.predicted_speed_kmh ??
                      "N/A"
                    }
                    {" "}km/h

                  </p>


                  <p>

                    ⏱️ Prediction Horizon:
                    {" "}
                    {
                      recommendedRoute.prediction_horizon_minutes ??
                      15
                    }
                    {" "}minutes

                  </p>


                  <p>

                    🤖 Prediction Source:
                    {" "}
                    {
                      getPredictionSource(
                        recommendedRoute
                      )
                    }

                  </p>


                  <p>

                    🧠 ML Status:
                    {" "}
                    {
                      getMLStatus(
                        recommendedRoute
                      )
                    }

                  </p>

                </>

              )}

            </div>


            {/* =================================================
                HOSPITAL
            ================================================= */}

            <div className="card">

              <h3>
                🏥 Hospital
              </h3>

              <strong>

                {
                  hospital?.hospital_name ||
                  "Not selected"
                }

              </strong>

              <p>

                Status:
                {" "}

                {
                  result.hospital_status ||
                  "UNKNOWN"
                }

              </p>

            </div>


            {/* =================================================
                TRAFFIC
            ================================================= */}

            <div className="card">

              <h3>
                🚦 Traffic
              </h3>

              <strong>

                {
                  result.traffic_source ||
                  "LIVE_DYNAMIC_TRAFFIC"
                }

              </strong>

              <p>

                Live traffic points
                analyzed for routes.

              </p>

            </div>


            {/* =================================================
                TRAFFIC OFFICER
            ================================================= */}

            <div className="card">

              <h3>
                👮 Traffic Officer
              </h3>

              <strong>

                {
                  assignedOfficer?.officer_id ||
                  "Waiting"
                }

              </strong>


              {assignedOfficer && (

                <>

                  <p>

                    Officer:
                    {" "}
                    {
                      assignedOfficer.name
                    }

                  </p>


                  <p>

                    Junction:
                    {" "}
                    {
                      assignedOfficer.location
                    }

                  </p>


                  <p>

                    Distance:
                    {" "}
                    {
                      assignedOfficer
                        .distance_to_route_km ??
                      "N/A"
                    }
                    {" "}km

                  </p>


                  <p>

                    🚦 Green Corridor:
                    {" "}

                    {
                      assignedOfficer.corridor_active
                        ? "ACTIVE"
                        : "INACTIVE"
                    }

                  </p>

                </>

              )}


              <p>

                {
                  result.corridor_status ||
                  "WAITING"
                }

              </p>

            </div>

          </div>


          {/* ==================================================
              AMBULANCE TRACKING
          ================================================== */}

          <div className="system-status">

            <h3>
              🚑 Ambulance Tracking
            </h3>

            <p>

              Ambulance ID:
              {" "}
              {ambulanceId}

            </p>

            <p>

              Status:
              {" "}

              {
                ambulanceLocation
                  ? "🟢 TRACKING ACTIVE"
                  : "🔴 NOT TRACKING"
              }

            </p>


            {ambulanceLocation && (

              <>

                <p>

                  Latitude:
                  {" "}
                  {
                    ambulanceLocation.latitude
                  }

                </p>

                <p>

                  Longitude:
                  {" "}
                  {
                    ambulanceLocation.longitude
                  }

                </p>

              </>

            )}


            <p>

              🔄 Location updates:
              {" "}
              Every 5 seconds

            </p>

          </div>


          {/* ==================================================
              ROUTES ANALYZED
          ================================================== */}

          <h3>
            🛣️ Routes Analyzed
          </h3>


          <div className="route-list">

            {
              routes.map(
                (route) => {

                  const isRecommended =

                    recommendedRoute?.route_id ===
                    route.route_id;

                  const routeDecision =
                    getRouteDecision(
                      route
                    );


                  return (

                    <div

                      className={

                        isRecommended

                          ? "route-card recommended-route"

                          : "route-card"

                      }

                      key={
                        route.route_id
                      }

                    >

                      <div className="route-header">

                        <strong>

                          {route.route_id}

                        </strong>


                        {isRecommended && (

                          <span className="recommended-badge">

                            ⭐ AI RECOMMENDED

                          </span>

                        )}

                      </div>


                      <span>

                        🏷️ Decision:
                        {" "}
                        {routeDecision}

                      </span>


                      <span>

                        📏 Distance:
                        {" "}
                        {route.distance_km}
                        {" "}km

                      </span>


                      <span>

                        🗺️ OSRM Duration:
                        {" "}
                        {
                          route.duration_minutes ??
                          "N/A"
                        }
                        {" "}minutes

                      </span>


                      <span>

                        🚗 Current Speed:
                        {" "}
                        {
                          route.current_speed_kmh ??
                          "N/A"
                        }
                        {" "}km/h

                      </span>


                      <span>

                        🧠 ML Predicted Speed:
                        {" "}
                        {
                          route.predicted_speed_kmh ??
                          "N/A"
                        }
                        {" "}km/h

                      </span>


                      <span>

                        ⏱️ Prediction Horizon:
                        {" "}
                        {
                          route.prediction_horizon_minutes ??
                          15
                        }
                        {" "}minutes

                      </span>


                      <span>

                        🤖 Prediction Source:
                        {" "}
                        {
                          getPredictionSource(
                            route
                          )
                        }

                      </span>


                      <span>

                        🧠 ML Status:
                        {" "}
                        {
                          getMLStatus(
                            route
                          )
                        }

                      </span>


                      <span>

                        🚦 Congestion:
                        {" "}
                        {
                          route.congestion ??
                          "UNKNOWN"
                        }

                      </span>


                      <span>

                        ⏱️ Estimated Travel Time:
                        {" "}
                        {
                          route
                            .estimated_travel_time_minutes != null

                            ? Number(
                                route
                                  .estimated_travel_time_minutes
                              ).toFixed(2)

                            : "N/A"
                        }
                        {" "}minutes

                      </span>


                      <span>

                        ⚠️ Congestion Penalty:
                        {" "}
                        {
                          route.congestion_penalty ??
                          "N/A"
                        }

                      </span>


                      <span>

                        ⭐ Route Score:
                        {" "}
                        {
                          route.score != null
                            ? Number(
                                route.score
                              ).toFixed(2)
                            : "N/A"
                        }

                      </span>


                      <span>

                        📍 Traffic Points Checked:
                        {" "}
                        {
                          route.traffic_points_checked ??
                          route.traffic_points?.length ??
                          0
                        }

                      </span>


                      {route.decision_reason && (

                        <div className="route-reason">

                          💡{" "}
                          {
                            route.decision_reason
                          }

                        </div>

                      )}

                    </div>

                  );

                }

              )

            }

          </div>


          {/* ==================================================
              GREEN CORRIDOR
          ================================================== */}

          {assignedOfficer && (

            <div className="system-status">

              <h3>
                🚦 Green Corridor Status
              </h3>


              <p>

                👮 Assigned Officer:
                {" "}
                {
                  assignedOfficer.officer_id
                }

              </p>


              <p>

                📍 Junction:
                {" "}
                {
                  assignedOfficer.location
                }

              </p>


              <p>

                📏 Distance to Route:
                {" "}
                {
                  assignedOfficer
                    .distance_to_route_km ??
                  "N/A"
                }
                {" "}km

              </p>


              <p>

                🚦 Corridor:

                {" "}

                {
                  assignedOfficer.corridor_active
                    ? "🟢 ACTIVE"
                    : "🔴 INACTIVE"
                }

              </p>


              {assignedTrafficPoint && (

                <p>

                  📍 Assigned Traffic Point:
                  {" "}

                  {
                    Number(
                      assignedTrafficPoint.latitude
                    ).toFixed(5)
                  }

                  {", "}

                  {
                    Number(
                      assignedTrafficPoint.longitude
                    ).toFixed(5)
                  }

                </p>

              )}

            </div>

          )}


          {/* ==================================================
              SYSTEM STATUS
          ================================================== */}

          <div className="system-status">

            <h3>
              System Status
            </h3>


            <p>

              🚑 Ambulance:
              {" "}
              {
                ambulanceLocation
                  ? "TRACKING ACTIVE"
                  : "ACTIVE"
              }

            </p>


            <p>

              🚦 Traffic:
              LIVE

            </p>


            <p>

              🧠 AI Decision Engine:
              ACTIVE

            </p>


            <p>

              🤖 ML Prediction:
              {" "}

              {
                recommendedRoute?.ml_status ||
                "WARMING_UP"
              }

            </p>


            <p>

              👮 Corridor:
              {" "}

              {
                result.corridor_status ||
                "WAITING"
              }

            </p>


            <p>

              🏥 Hospital:
              {" "}

              {
                result.hospital_status ||
                "UNKNOWN"
              }

            </p>

          </div>

        </section>

      )}

    </div>

  );

}


export default App;