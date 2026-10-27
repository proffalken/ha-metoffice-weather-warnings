"""Data models for NSWWS warnings.

Field names were confirmed against a live `/objects/issued` response. Note
`warningVersion` comes back as a string (e.g. "1.0"), not a number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .const import WARNING_LEVEL_AMBER, WARNING_LEVEL_RED, WARNING_LEVEL_YELLOW

_LEVEL_MAP = {
    "YELLOW": WARNING_LEVEL_YELLOW,
    "AMBER": WARNING_LEVEL_AMBER,
    "RED": WARNING_LEVEL_RED,
}


@dataclass(frozen=True, slots=True)
class Warning:
    """A single active NSWWS warning."""

    warning_id: str
    version: str
    level: str
    likelihood: int | None
    impact: int | None
    weather_types: list[str]
    headline: str
    what_to_expect: list[str]
    what_should_i_do: str | None
    further_details: str | None
    status: str
    update_description: str | None
    region_names: list[str]
    region_codes: list[str]
    valid_from: datetime
    valid_to: datetime
    issued: datetime
    modified: datetime
    geometry: dict | None = None

    def as_dict(self) -> dict:
        """Return a JSON-serialisable representation for entity attributes."""
        return {
            "id": self.warning_id,
            "level": self.level,
            "weather_types": self.weather_types,
            "headline": self.headline,
            "what_to_expect": self.what_to_expect,
            "what_should_i_do": self.what_should_i_do,
            "further_details": self.further_details,
            "areas": self.region_names,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat(),
            "likelihood": self.likelihood,
            "impact": self.impact,
            "status": self.status,
        }


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _warning_from_feature(feature: dict) -> Warning:
    props = feature["properties"]
    areas = props.get("affectedAreas", [])

    return Warning(
        warning_id=props["warningId"],
        version=props.get("warningVersion", "1.0"),
        level=_LEVEL_MAP.get(props["warningLevel"], props["warningLevel"].lower()),
        likelihood=props.get("warningLikelihood"),
        impact=props.get("warningImpact"),
        weather_types=list(props.get("weatherType", [])),
        headline=props.get("warningHeadline", ""),
        what_to_expect=list(props.get("whatToExpect", [])),
        what_should_i_do=props.get("whatShouldIDo"),
        further_details=props.get("warningFurtherDetails"),
        status=props.get("warningStatus", "ISSUED"),
        update_description=props.get("warningUpdateDescription"),
        region_names=[a.get("regionName", "") for a in areas],
        region_codes=[a.get("regionCode", "") for a in areas],
        valid_from=_parse_datetime(props["validFromDate"]),
        valid_to=_parse_datetime(props["validToDate"]),
        issued=_parse_datetime(props["issuedDate"]),
        modified=_parse_datetime(props["modifiedDate"]),
        geometry=feature.get("geometry"),
    )


def warnings_from_geojson(payload: dict) -> list[Warning]:
    """Parse a `/objects/issued` GeoJSON FeatureCollection into Warning objects."""
    features = payload.get("features", [])
    return [_warning_from_feature(feature) for feature in features]
