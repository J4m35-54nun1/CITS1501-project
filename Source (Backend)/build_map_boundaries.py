"""Build GeoJSON from official ABS ASGS 2021 boundary zip files."""

import argparse
import json
from pathlib import Path
import struct
from zipfile import ZipFile


def _point_segment_distance_squared(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return (point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2

    position = max(
        0,
        min(
            1,
            ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy)
            / (dx * dx + dy * dy),
        ),
    )
    nearest = (start[0] + position * dx, start[1] + position * dy)
    return (point[0] - nearest[0]) ** 2 + (point[1] - nearest[1]) ** 2


def _simplify_open_ring(
    points: list[tuple[float, float]],
    tolerance_squared: float,
) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points

    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        start_index, end_index = pending.pop()
        furthest_index = -1
        furthest_distance = tolerance_squared
        for index in range(start_index + 1, end_index):
            distance = _point_segment_distance_squared(
                points[index],
                points[start_index],
                points[end_index],
            )
            if distance > furthest_distance:
                furthest_index = index
                furthest_distance = distance
        if furthest_index >= 0:
            keep.add(furthest_index)
            pending.append((start_index, furthest_index))
            pending.append((furthest_index, end_index))

    return [points[index] for index in sorted(keep)]


def _simplify_ring(
    ring: list[tuple[float, float]],
    tolerance: float,
) -> list[tuple[float, float]]:
    if len(ring) <= 4:
        return ring

    points = ring[:-1]
    pivot = max(
        range(1, len(points)),
        key=lambda index: _point_segment_distance_squared(
            points[index],
            points[0],
            points[0],
        ),
    )
    tolerance_squared = tolerance * tolerance
    first_half = _simplify_open_ring(points[: pivot + 1], tolerance_squared)
    second_path = points[pivot:] + points[:1]
    second_half = _simplify_open_ring(second_path, tolerance_squared)
    simplified = first_half + second_half[1:-1]
    if len(simplified) < 3:
        return ring
    simplified.append(simplified[0])
    return simplified


def _read_dbf(data: bytes, encoding: str) -> tuple[list[str], list[dict]]:
    record_count = struct.unpack_from("<I", data, 4)[0]
    header_length = struct.unpack_from("<H", data, 8)[0]
    record_length = struct.unpack_from("<H", data, 10)[0]

    fields = []
    position = 32
    while position < header_length and data[position] != 0x0D:
        descriptor = data[position : position + 32]
        name = descriptor[:11].split(b"\0", 1)[0].decode(encoding).strip()
        field_type = chr(descriptor[11])
        field_length = descriptor[16]
        decimal_count = descriptor[17]
        fields.append((name, field_type, field_length, decimal_count))
        position += 32

    records = []
    for index in range(record_count):
        position = header_length + index * record_length
        row = data[position : position + record_length]
        if not row or row[0:1] == b"*":
            continue
        offset = 1
        attributes = {}
        for name, field_type, field_length, decimal_count in fields:
            raw_value = row[offset : offset + field_length].strip()
            offset += field_length
            if not raw_value:
                value = None
            elif field_type in {"N", "F"}:
                text = raw_value.decode("ascii")
                value = float(text) if decimal_count else int(text)
            elif field_type == "L":
                value = raw_value.upper() in {b"Y", b"T"}
            else:
                value = raw_value.decode(encoding).strip()
            attributes[name] = value
        records.append(attributes)
    return [field[0] for field in fields], records


def _read_shapes(data: bytes) -> list[list[list[tuple[float, float]]]]:
    shapes = []
    position = 100
    while position + 8 <= len(data):
        content_length = struct.unpack_from(">I", data, position + 4)[0] * 2
        content_start = position + 8
        content_end = content_start + content_length
        if content_end > len(data):
            raise ValueError("Invalid or truncated shapefile record.")

        record = data[content_start:content_end]
        shape_type = struct.unpack_from("<I", record, 0)[0]
        if shape_type == 0:
            shapes.append([])
        elif shape_type in {5, 15, 25}:
            part_count, point_count = struct.unpack_from("<II", record, 36)
            part_start = 44
            part_indexes = list(
                struct.unpack_from(f"<{part_count}I", record, part_start)
            )
            point_start = part_start + part_count * 4
            points = [
                struct.unpack_from("<2d", record, point_start + index * 16)
                for index in range(point_count)
            ]
            part_indexes.append(point_count)
            shapes.append(
                [
                    points[part_indexes[index] : part_indexes[index + 1]]
                    for index in range(part_count)
                ]
            )
        else:
            raise ValueError(f"Unsupported shapefile geometry type: {shape_type}")
        position = content_end
    return shapes


def _ring_area(ring: list[tuple[float, float]]) -> float:
    return sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(ring, ring[1:])
    ) / 2


def _point_in_ring(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for first, second in zip(ring, ring[1:]):
        if (first[1] > y) != (second[1] > y):
            cross_x = (second[0] - first[0]) * (y - first[1]) / (
                second[1] - first[1]
            ) + first[0]
            if x < cross_x:
                inside = not inside
    return inside


def _polygon_coordinates(
    rings: list[list[tuple[float, float]]],
) -> list[list[list[list[float]]]]:
    polygons: list[list[list[tuple[float, float]]]] = []
    holes = []
    for ring in rings:
        if len(ring) < 4:
            continue
        if _ring_area(ring) < 0:
            polygons.append([ring])
        else:
            holes.append(ring)

    for hole in holes:
        containing = [
            polygon
            for polygon in polygons
            if _point_in_ring(hole[0], polygon[0])
        ]
        if containing:
            min(containing, key=lambda polygon: abs(_ring_area(polygon[0]))).append(
                hole
            )

    return [
        [
            [[round(coordinate, 5) for coordinate in point] for point in ring]
            for ring in polygon
        ]
        for polygon in polygons
    ]


def _read_geojson(archive_path: Path, layer_name: str, tolerance: float) -> dict:
    with ZipFile(archive_path) as archive:
        components = {
            Path(name).suffix.lower(): archive.read(name)
            for name in archive.namelist()
            if Path(name).stem.lower() == layer_name.lower()
        }
    if ".shp" not in components or ".dbf" not in components:
        raise ValueError(f"{archive_path} is missing its .shp or .dbf file.")

    cpg = components.get(".cpg", b"utf-8").decode("ascii", errors="ignore").strip()
    encoding = cpg or "utf-8"
    _, records = _read_dbf(components[".dbf"], encoding)
    shapes = _read_shapes(components[".shp"])
    if len(records) != len(shapes):
        raise ValueError(
            f"Geometry/attribute count mismatch in '{archive_path.name}'."
        )

    features = []
    if layer_name.startswith("STE_"):
        property_fields = ("STE_CODE21", "STE_NAME21")
    else:
        property_fields = (
            "LGA_CODE21",
            "LGA_NAME21",
            "STE_CODE21",
            "STE_NAME21",
        )

    for properties, rings in zip(records, shapes):
        properties = {
            field: properties[field]
            for field in property_fields
            if field in properties
        }
        rings = [_simplify_ring(ring, tolerance) for ring in rings]
        polygons = _polygon_coordinates(rings)
        if not polygons:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": polygons,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lga-zip", type=Path, required=True)
    parser.add_argument("--state-zip", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "Interface (Frontend)"
        / "assets"
        / "australia_boundaries_2021.json",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.005,
        help="Boundary simplification tolerance in degrees (default: 0.005).",
    )
    args = parser.parse_args()

    if args.tolerance < 0:
        parser.error("--tolerance cannot be negative.")
    boundary_data = {
        "states": _read_geojson(
            args.state_zip,
            "STE_2021_AUST_GDA2020",
            args.tolerance,
        ),
        "lgas": _read_geojson(
            args.lga_zip,
            "LGA_2021_AUST_GDA2020",
            args.tolerance,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(boundary_data, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(boundary_data['states']['features'])} state/territory "
        f"features and {len(boundary_data['lgas']['features'])} LGA features "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
