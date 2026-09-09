import { useEffect, useState } from "react";

import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap
} from "react-leaflet";

import "leaflet/dist/leaflet.css";


const API_URL = "http://127.0.0.1:8000";


// ============================================================
// MAP FOLLOWER
// ============================================================

function MapFollower({ ambulanceLocation }) {

  const map = useMap();

  useEffect(() => {

    if (!ambulanceLocation) {
      return;
    }

    const latitude =
      Number(ambulanceLocation.latitude);

    const longitude =
      Number(ambulanceLocation.longitude);

    if (
      Number.isNaN(latitude) ||
      Number.isNaN(longitude)
    ) {
      return;
    }

    map.panTo(
      [
        latitude,
        longitude
      ],
      {
        animate: true,
        duration: 0.8
      }
    );

  }, [
    ambulanceLocation,
    map
  ]);

  return null;
}


// ============================================================
// APP
// ============================================================

function App() {

  // ==========================================================
  // STATE
  // ==========================================================

  const [ambulanceId, setAmbulanceId] =
    useState("AMB-001");

  const [startLatitude, setStartLatitude] =
    useState("");

  const [startLongitude, setStartLongitude] =
    useState("");

  const [hospitalId, setHospitalId] =
    useState("HOSP-001");

  const [result, setResult] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [ambulanceLocation, setAmbulanceLocation] =
    useState(null);


  // ==========================================================
  // GET CURRENT LOCATION
  // ==========================================================

  const useCurrentLocation = () => {

    setError("");

    if (!navigator.geolocation) {

      setError(
        "Geolocation is not supported by this browser."
      );

      return;
    }

    navigator.geolocation.getCurrentPosition(

      (position) => {

        setStartLatitude(
          position.coords.latitude.toFixed(6)
        );

        setStartLongitude(
          position.coords.longitude.toFixed(6)
        );

      },

      (locationError) => {

        console.error(
          "Location error:",
          locationError
        );

        setError(
          "Unable to get your current location. Please enter the coordinates manually."
        );

      }

    );

  };


  // ==========================================================
  // FETCH AMBULANCE TRACKING
  // ==========================================================

  const fetchAmbulanceTracking = async (
    currentAmbulanceId
  ) => {

    if (!currentAmbulanceId) {
      return;
    }

    try {

      const response = await fetch(
        `${API_URL}/tracking/${currentAmbulanceId}`
      );

      if (response.status === 404) {

        console.log(
          `Tracking not started for ${currentAmbulanceId}`
        );

        return;
      }

      if (!response.ok) {

        const errorText =
          await response.text();

        throw new Error(
          errorText ||
          "Failed to fetch ambulance tracking."
        );

      }

      const data =
        await response.json();

      console.log(
        "Ambulance tracking:",
        data
      );

      const latitude =
        Number(data.latitude);

      const longitude =
        Number(data.longitude);

      if (
        Number.isNaN(latitude) ||
        Number.isNaN(longitude)
      ) {

        console.error(
          "Invalid ambulance coordinates:",
          data
        );

        return;
      }

      setAmbulanceLocation({

        latitude:
          latitude,

        longitude:
          longitude

      });

    }

    catch (trackingError) {

      console.error(
        "Ambulance tracking error:",
        trackingError
      );

    }

  };


  // ==========================================================
  // AUTOMATIC AMBULANCE TRACKING
  // ==========================================================

  useEffect(() => {

    if (!result) {
      return;
    }

    if (!ambulanceId) {
      return;
    }

    console.log(
      `Automatic tracking started for ${ambulanceId}`
    );

    fetchAmbulanceTracking(
      ambulanceId
    );

    const trackingInterval =
      setInterval(() => {

        fetchAmbulanceTracking(
          ambulanceId
        );

      }, 5000);

    return () => {

      console.log(
        `Automatic tracking stopped for ${ambulanceId}`
      );

      clearInterval(
        trackingInterval
      );

    };

  }, [
    result,
    ambulanceId
  ]);


  // ==========================================================
  // START EMERGENCY
  // ==========================================================

  const startEmergency = async () => {

    setError("");

    setResult(null);

    setAmbulanceLocation(null);

    if (
      !startLatitude ||
      !startLongitude
    ) {

      setError(
        "Please enter the ambulance starting location."
      );

      return;
    }

    const latitude =
      Number(startLatitude);

    const longitude =
      Number(startLongitude);

    if (
      Number.isNaN(latitude) ||
      Number.isNaN(longitude)
    ) {

      setError(
        "Latitude and longitude must be valid numbers."
      );

      return;
    }

    setLoading(true);

    try {

      const response = await fetch(
        `${API_URL}/emergency/start`,
        {

          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({

            ambulance_id:
              ambulanceId,

            ambulance_latitude:
              latitude,

            ambulance_longitude:
              longitude,

            destination_hospital_id:
              hospitalId

          })

        }
      );

      if (!response.ok) {

        const errorText =
          await response.text();

        let errorMessage =
          "Emergency request failed.";

        try {

          const errorData =
            JSON.parse(errorText);

          errorMessage =
            errorData.detail ||
            errorMessage;

        }

        catch {

          errorMessage =
            errorText ||
            errorMessage;

        }

        throw new Error(
          errorMessage
        );

      }

      const data =
        await response.json();

      console.log(
        "Emergency response:",
        data
      );

      setResult(data);

      await fetchAmbulanceTracking(
        ambulanceId
      );

    }

    catch (error) {

      console.error(
        "Emergency error:",
        error
      );

      setError(
        error.message ||
        "Unable to process emergency."
      );

    }

    finally {

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

          <MapContainer

            center={
              mapCenter
            }

            zoom={12}

            style={{
              height: "550px",
              width: "100%"
            }}

          >

            <MapFollower
              ambulanceLocation={
                ambulanceLocation
              }
            />


            <TileLayer

              attribution='&copy; OpenStreetMap contributors'

              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

            />


            {/* ==================================================
                AMBULANCE
            ================================================== */}

            {ambulanceLocation && (

              <Marker

                position={[

                  ambulanceLocation.latitude,

                  ambulanceLocation.longitude

                ]}

              >

                <Popup>

                  🚑 <strong>
                    Ambulance
                  </strong>

                  <br />

                  ID:
                  {" "}
                  {ambulanceId}

                  <br />

                  Status:
                  {" "}
                  EN ROUTE

                  <br />

                  Latitude:
                  {" "}
                  {ambulanceLocation.latitude}

                  <br />

                  Longitude:
                  {" "}
                  {ambulanceLocation.longitude}

                </Popup>

              </Marker>

            )}


            {/* ==================================================
                STARTING LOCATION
            ================================================== */}

            {!ambulanceLocation &&
              startLatitude &&
              startLongitude && (

                <Marker

                  position={[

                    Number(
                      startLatitude
                    ),

                    Number(
                      startLongitude
                    )

                  ]}

                >

                  <Popup>

                    🚑 <strong>
                      Ambulance
                    </strong>

                    <br />

                    ID:
                    {" "}
                    {ambulanceId}

                    <br />

                    Tracking:
                    {" "}
                    NOT STARTED

                  </Popup>

                </Marker>

              )
            }


            {/* ==================================================
                HOSPITAL
            ================================================== */}

            {hospital && (

              <Marker

                position={[

                  Number(
                    hospital.latitude
                  ),

                  Number(
                    hospital.longitude
                  )

                ]}

              >

                <Popup>

                  🏥 <strong>

                    {
                      hospital.hospital_name
                    }

                  </strong>

                  <br />

                  Status:
                  {" "}

                  {
                    hospital.emergency_ready
                      ? "READY"
                      : "NOT READY"
                  }

                </Popup>

              </Marker>

            )}


            {/* ==================================================
                TRAFFIC OFFICER
            ================================================== */}

            {assignedTrafficPoint && (

              <Marker

                position={[

                  Number(
                    assignedTrafficPoint.latitude
                  ),

                  Number(
                    assignedTrafficPoint.longitude
                  )

                ]}

              >

                <Popup>

                  👮 <strong>
                    Traffic Officer
                  </strong>

                  <br />

                  Officer:
                  {" "}
                  {
                    assignedOfficer.name
                  }

                  <br />

                  Junction:
                  {" "}
                  {
                    assignedOfficer.location
                  }

                  <br />

                  🚦 Green Corridor:
                  {" "}

                  {
                    assignedOfficer.corridor_active
                      ? "ACTIVE"
                      : "INACTIVE"
                  }

                </Popup>

              </Marker>

            )}


            {/* ==================================================
                ROUTES
            ================================================== */}

            {
              routes.map(
                (route) => {

                  if (
                    !route.geometry ||
                    !route.geometry.coordinates
                  ) {

                    return null;

                  }

                  const positions =
                    route.geometry.coordinates.map(
                      (coordinate) => [

                        coordinate[1],

                        coordinate[0]

                      ]
                    );

                  const isRecommended =

                    recommendedRoute?.route_id ===
                    route.route_id;

                  const routeColor =
                    getRouteColor(
                      route.congestion
                    );

                  return (

                    <Polyline

                      key={
                        route.route_id
                      }

                      positions={
                        positions
                      }

                      pathOptions={{

                        color:

                          isRecommended
                            ? "blue"
                            : routeColor,

                        weight:

                          isRecommended
                            ? 9
                            : 5,

                        opacity:

                          isRecommended
                            ? 1
                            : 0.7

                      }}

                    />

                  );

                }

              )

            }

          </MapContainer>


          {/* ==================================================
              MAP LEGEND
          ================================================== */}

          <div className="map-legend">

            <div className="legend-title">
              Traffic Conditions
            </div>

            <div>

              <span className="legend-line green">
              </span>

              Low Traffic

            </div>

            <div>

              <span className="legend-line orange">
              </span>

              Moderate Traffic

            </div>

            <div>

              <span className="legend-line red">
              </span>

              Heavy Traffic

            </div>

            <div>

              <span className="legend-line recommended">
              </span>

              AI Recommended

            </div>

          </div>

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