"""Dependency-free GeoJSON point containment for Home Assistant warning areas."""
import math


def valid_coordinates(latitude, longitude):
    """Check latitude/longitude existence, numeric type and legal ranges."""
    return (
        type(latitude) in (int, float)
        and type(longitude) in (int, float)
        and math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _ring_contains(ring, x, y):
    """Return (inside, boundary); malformed rings raise ValueError."""
    if not isinstance(ring, (list, tuple)) or len(ring) < 4:
        raise ValueError("Invalid ring")
    pts = []
    for coord in ring:
        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
            raise ValueError("Invalid vertex")
        px, py = coord[:2]
        if not valid_coordinates(py, px):
            raise ValueError("Invalid coordinate")
        pts.append((px, py))
    if pts[0] != pts[-1]:
        raise ValueError("Unclosed ring")
    inside = False
    for (ax, ay), (bx, by) in zip(pts, pts[1:], strict=False):
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if (
            abs(cross) <= 1e-10
            and min(ax, bx) - 1e-10 <= x <= max(ax, bx) + 1e-10
            and min(ay, by) - 1e-10 <= y <= max(ay, by) + 1e-10
        ):
            return True, True
        if (ay > y) != (by > y):
            x_intersect = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < x_intersect:
                inside = not inside
    return inside, False


def _polygon_contains(rings, longitude, latitude):
    if not isinstance(rings, list) or not rings:
        raise ValueError("Invalid polygon")
    outer, boundary = _ring_contains(rings[0], longitude, latitude)
    if boundary:
        return True
    if not outer:
        return False
    for hole in rings[1:]:
        in_hole, on_hole_boundary = _ring_contains(hole, longitude, latitude)
        if on_hole_boundary:
            return True
        if in_hole:
            return False
    return True


def geometry_covers(geometry, latitude, longitude):
    """True if home covered, False if not, None if geometry is unusable."""
    if not valid_coordinates(latitude, longitude) or not isinstance(geometry, dict):
        return None
    try:
        kind = geometry.get("type")
        coords = geometry.get("coordinates")
        if kind == "Polygon":
            return _polygon_contains(coords, longitude, latitude)
        if kind == "MultiPolygon":
            if not isinstance(coords, list) or not coords:
                return None
            # Validate every polygon even if one already contains the point.
            return any(
                [_polygon_contains(poly, longitude, latitude) for poly in coords]
            )
        return None
    except (ValueError, TypeError, IndexError, OverflowError):
        return None
