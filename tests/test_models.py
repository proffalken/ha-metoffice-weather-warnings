"""Tests for GeoJSON -> Warning parsing."""

from datetime import UTC, datetime

from custom_components.metoffice_warnings.models import Warning, warnings_from_geojson


def test_warnings_from_geojson_empty(issued_empty: dict) -> None:
    assert warnings_from_geojson(issued_empty) == []


def test_warnings_from_geojson_active(issued_active: dict) -> None:
    warnings = warnings_from_geojson(issued_active)

    assert len(warnings) == 2
    first = warnings[0]
    assert isinstance(first, Warning)
    assert first.warning_id == "11111111-1111-1111-1111-111111111111"
    assert first.version == "1.0"
    assert first.level == "amber"
    assert first.weather_types == ["THUNDERSTORM"]
    assert first.headline == "Thunderstorms may cause disruption Tuesday"
    assert first.what_should_i_do == (
        "Avoid driving through flood water and keep an eye on local weather updates."
    )
    assert first.status == "ISSUED"
    assert first.region_names == ["London & South East England"]
    assert first.valid_from == datetime(2026, 8, 26, 2, 0, tzinfo=UTC)
    assert first.valid_to == datetime(2026, 8, 26, 21, 0, tzinfo=UTC)
    assert first.likelihood == 70
    assert first.impact == 3
    assert first.update_description is None

    second = warnings[1]
    assert second.level == "yellow"
    assert second.region_names == ["West Midlands"]
    assert second.update_description == "Valid period extended by six hours."


def test_warning_as_dict_is_jsonable(issued_active: dict) -> None:
    warning = warnings_from_geojson(issued_active)[0]
    data = warning.as_dict()

    assert data["id"] == warning.warning_id
    assert data["level"] == "amber"
    assert data["valid_from"] == "2026-08-26T02:00:00+00:00"
    assert data["areas"] == ["London & South East England"]
    # Every warning in the list carries its further details (issue #3).
    assert data["further_details"] == warning.further_details
