from services.officer_service import (
    get_available_officers,
    find_nearest_officer
)


print("\n==============================")
print("AVAILABLE OFFICERS")
print("==============================")


officers = get_available_officers()

for officer in officers:

    print(
        officer["officer_id"],
        "-",
        officer["name"],
        "-",
        officer["location"]
    )


print("\n==============================")
print("NEAREST OFFICER")
print("==============================")


nearest = find_nearest_officer(
    latitude=17.4000,
    longitude=78.4800
)


print(nearest)