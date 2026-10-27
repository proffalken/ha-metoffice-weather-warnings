"""Tests for optional home-coordinate warning filtering."""

from unittest.mock import AsyncMock

from custom_components.metoffice_warnings.const import AREA_ALL
from custom_components.metoffice_warnings.coordinator import (
    MetOfficeWarningsCoordinator,
)
from custom_components.metoffice_warnings.geometry import (
    geometry_covers,
    valid_coordinates,
)
from custom_components.metoffice_warnings.models import warnings_from_geojson


def _square(x1, y1, x2, y2):
    return {"type": "Polygon", "coordinates": [[
        [x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1],
    ]]}


def test_geometry_inside_outside_boundary_and_invalid():
    geometry = _square(-2, 50, 0, 52)
    assert geometry_covers(geometry, 51, -1) is True
    assert geometry_covers(geometry, 51, 1) is False
    assert geometry_covers(geometry, 50, -1) is True
    assert geometry_covers(None, 51, -1) is None
    assert not valid_coordinates(None, -1)


def test_multipolygon_and_hole():
    hole = [[-1.5, 50.5], [-0.5, 50.5], [-0.5, 51.5],
            [-1.5, 51.5], [-1.5, 50.5]]
    polygon = _square(-2, 50, 0, 52)["coordinates"] + [hole]
    assert geometry_covers({"type": "Polygon", "coordinates": polygon}, 51, -1) is False
    assert geometry_covers({"type": "MultiPolygon", "coordinates": [
        _square(-5, 53, -4, 54)["coordinates"], _square(-2, 50, 0, 52)["coordinates"]
    ]}, 51, -1) is True


async def test_polygon_filter_overrides_regions(hass, issued_active):
    warnings = warnings_from_geojson(issued_active)
    for warning in warnings:
        object.__setattr__(warning, "geometry", _square(-2, 50, 0, 52))
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings
    hass.config.latitude = 51
    hass.config.longitude = -1
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=["Scotland"], use_home_location=True
    )
    result = await coordinator._async_update_data()
    assert len(result.warnings) == len(warnings)
    assert result.filter_method == "polygon"


async def test_missing_geometry_uses_region_fallback(hass, issued_active):
    client = AsyncMock()
    warnings = warnings_from_geojson(issued_active)
    for warning in warnings:
        object.__setattr__(warning, "geometry", None)
    client.async_get_active_warnings.return_value = warnings
    hass.config.latitude = 51
    hass.config.longitude = -1
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=[AREA_ALL], use_home_location=True
    )
    result = await coordinator._async_update_data()
    assert len(result.warnings) == 2
    assert result.filter_method == "polygon_with_region_fallback"


def test_invalid_coordinates_and_malformed_geometry():
    geometry = _square(-2, 50, 0, 52)
    for latitude, longitude in [
        (None, -1), (91, -1), (51, -181), (float("nan"), -1),
        (51, float("inf")), (True, -1),
    ]:
        assert not valid_coordinates(latitude, longitude)
        assert geometry_covers(geometry, latitude, longitude) is None

    for malformed in [
        None,
        {},
        {"type": "Point", "coordinates": [-1, 51]},
        {"type": "Polygon", "coordinates": []},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1]]]},
        {"type": "Polygon", "coordinates": [[
            [0, 0], [1, 0], ["bad", 1], [0, 0],
        ]]},
        {"type": "MultiPolygon", "coordinates": []},
    ]:
        assert geometry_covers(malformed, 51, -1) is None


async def test_invalid_home_coordinates_fall_back_to_regions(hass, issued_active):
    warnings = warnings_from_geojson(issued_active)
    for warning in warnings:
        object.__setattr__(warning, "geometry", _square(-2, 50, 0, 52))
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings
    hass.config.latitude = 91
    hass.config.longitude = -1
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=[AREA_ALL], use_home_location=True
    )
    result = await coordinator._async_update_data()
    assert len(result.warnings) == len(warnings)
    assert result.filter_method == "region_fallback"


async def test_malformed_geometry_falls_back_to_regions(hass, issued_active):
    warnings = warnings_from_geojson(issued_active)
    for warning in warnings:
        object.__setattr__(
            warning, "geometry", {"type": "Polygon", "coordinates": []}
        )
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings
    hass.config.latitude = 51
    hass.config.longitude = -1
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=[AREA_ALL], use_home_location=True
    )
    result = await coordinator._async_update_data()
    assert len(result.warnings) == len(warnings)
    assert result.filter_method == "polygon_with_region_fallback"


async def test_location_filter_disabled_uses_regions(hass, issued_active):
    warnings = warnings_from_geojson(issued_active)
    for warning in warnings:
        object.__setattr__(warning, "geometry", _square(-2, 50, 0, 52))
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings
    hass.config.latitude = 51
    hass.config.longitude = -1
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=[AREA_ALL], use_home_location=False
    )
    result = await coordinator._async_update_data()
    assert len(result.warnings) == len(warnings)
    assert result.filter_method == "region"


async def test_diagnostics_exports_all_polygons_and_match_decisions(
    hass, issued_active
):
    from types import SimpleNamespace

    from custom_components.metoffice_warnings.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    warnings = warnings_from_geojson(issued_active)
    object.__setattr__(warnings[0], "geometry", _square(-2, 50, 0, 52))
    object.__setattr__(warnings[1], "geometry", _square(2, 50, 3, 52))
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings
    hass.config.latitude = 51
    hass.config.longitude = -1
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=[AREA_ALL], use_home_location=True
    )
    coordinator.async_set_updated_data(await coordinator._async_update_data())
    entry = SimpleNamespace(
        data={"api_key": "secret", "areas": [AREA_ALL]},
        options={"use_home_location": True},
        runtime_data=coordinator,
    )
    result = await async_get_config_entry_diagnostics(hass, entry)
    records = result["geometry_diagnostics"]["warnings"]
    assert len(records) == 2
    assert records[0]["included"] is True
    assert records[0]["polygon_match"] is True
    assert records[1]["included"] is False
    assert records[1]["polygon_match"] is False
    assert records[0]["geometry"]["type"] == "Polygon"
    assert "secret" not in str(result)
    assert "51," not in str(result)
