from math import atan2, cos, radians, sin, sqrt

from rest_framework import serializers


JKUAT_CENTER = (-1.1017, 37.0143)
JKUAT_SERVICE_RADIUS_KM = 12
JKUAT_BLOCK_RADIUS_KM = 15
EARTH_RADIUS_KM = 6371

LANDMARK_COORDINATES = {
    "Main Gate": (-1.1017, 37.0143),
    "Back Gate": (-1.0948, 37.0121),
    "Library": (-1.0999, 37.0129),
    "Administration Block": (-1.1011, 37.0132),
    "Engineering Block": (-1.1026, 37.0165),
    "ICT Centre": (-1.1006, 37.0154),
    "Health Centre": (-1.1031, 37.0122),
    "Hostels Block A": (-1.0968, 37.0168),
    "Hostels Block B": (-1.0974, 37.0175),
    "Hostels Block C": (-1.0982, 37.0181),
    "Hostels Block D": (-1.099, 37.0186),
    "Mess/Dining Hall": (-1.1001, 37.017),
    "Sports Ground": (-1.1045, 37.0158),
    "JKUAT Town Stage": (-1.106, 37.0108),
    "Other (specify in notes)": JKUAT_CENTER,
}


def distance_from_jkuat_km(latitude, longitude):
    lat = float(latitude)
    lng = float(longitude)
    center_lat, center_lng = JKUAT_CENTER
    delta_lat = radians(lat - center_lat)
    delta_lng = radians(lng - center_lng)
    a = (
        sin(delta_lat / 2) ** 2
        + cos(radians(center_lat))
        * cos(radians(lat))
        * sin(delta_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))


def get_landmark_coordinates(name):
    return LANDMARK_COORDINATES.get(name, JKUAT_CENTER)


def validate_within_hard_geofence(latitude, longitude, field_name="location"):
    if latitude is None or longitude is None:
        return

    try:
        distance_km = distance_from_jkuat_km(latitude, longitude)
    except (TypeError, ValueError):
        raise serializers.ValidationError(
            {field_name: "Latitude and longitude must be valid numbers."}
        )
    if distance_km >= JKUAT_BLOCK_RADIUS_KM:
        raise serializers.ValidationError(
            {
                field_name: (
                    f"This location is {distance_km:.1f}km from JKUAT. "
                    f"TaskiT blocks posting and accepting from "
                    f"{JKUAT_BLOCK_RADIUS_KM}km and beyond."
                )
            }
        )
