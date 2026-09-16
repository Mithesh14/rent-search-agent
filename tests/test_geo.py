from rentsearch import geo

GUINDY = {"name": "Guindy", "lat": 13.0092746, "lon": 80.2130846}
ALANDUR = {"name": "Alandur", "lat": 13.0042558, "lon": 80.2014525}
STATIONS = [GUINDY, ALANDUR]


def test_haversine_zero_for_same_point():
    assert geo.haversine_km(13.0, 80.2, 13.0, 80.2) == 0


def test_haversine_matches_known_distance():
    # Guindy <-> Alandur is a real, short, well-known hop on the Chennai Metro Blue Line.
    distance = geo.haversine_km(GUINDY["lat"], GUINDY["lon"], ALANDUR["lat"], ALANDUR["lon"])
    assert 1.0 < distance < 2.0


def test_nearest_metro_station_picks_closest():
    station, distance = geo.nearest_metro_station(13.0086685, 80.2126063, STATIONS)
    assert station["name"] == "Guindy"
    assert distance < 0.5


def test_nearest_metro_station_empty_list_returns_none():
    assert geo.nearest_metro_station(13.0, 80.2, []) is None


def test_find_area_matches_substring_case_insensitively():
    areas = [{"name": "Guindy", "lat": 13.0, "lon": 80.2, "flood_notes": "note"}]
    assert geo.find_area("Flat in GUINDY near main road", areas)["name"] == "Guindy"


def test_find_area_no_match_returns_none():
    areas = [{"name": "Guindy", "lat": 13.0, "lon": 80.2, "flood_notes": "note"}]
    assert geo.find_area("Flat in Velachery", areas) is None
