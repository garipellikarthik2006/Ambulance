from route_decision import choose_best_route


routes = [
    {
        "name": "Route A",
        "distance_km": 8,
        "predicted_speed_kmh": 18,
        "congestion": "HEAVY"
    },
    {
        "name": "Route B",
        "distance_km": 10,
        "predicted_speed_kmh": 35,
        "congestion": "LOW"
    },
    {
        "name": "Route C",
        "distance_km": 7,
        "predicted_speed_kmh": 22,
        "congestion": "MODERATE"
    }
]


best = choose_best_route(routes)


print("Route evaluation:")
print()

for route in routes:
    print(
        route["name"],
        "Score:",
        round(route["score"], 2)
    )

print()
print("Recommended route:")
print(best["name"])