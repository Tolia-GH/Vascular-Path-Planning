import argparse
import json
import os
import re
from typing import Iterable, List, Optional, Tuple


def _extract_index_from_filename(path: str) -> Tuple[int, str]:
    name = os.path.basename(path)
    m = re.search(r"\((\d+)\)", name)
    if m:
        return int(m.group(1)), name
    return 10**9, name


def _load_curve_points_from_mrk_json(path: str) -> Optional[List[List[float]]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    markups = data.get("markups", [])
    if not markups:
        return None

    curve = None
    for item in markups:
        if item.get("type") == "Curve":
            curve = item
            break
    if curve is None:
        curve = markups[0]

    control_points = curve.get("controlPoints") or curve.get("points") or []
    if not control_points:
        return None

    positions: List[List[float]] = []
    for cp in control_points:
        pos = cp.get("position")
        if pos is None:
            continue
        if len(pos) != 3:
            continue
        positions.append([float(pos[0]), float(pos[1]), float(pos[2])])

    if len(positions) < 2:
        return None
    return positions


def build_centerline_points_and_lines_from_mrk_files(
    paths: Iterable[str],
) -> Tuple[List[List[float]], List[List[int]]]:
    points: List[List[float]] = []
    lines: List[List[int]] = []

    for p in paths:
        pts = _load_curve_points_from_mrk_json(p)
        if pts is None:
            continue

        start = len(points)
        points.extend(pts)
        lines.append(list(range(start, start + len(pts))))

    return points, lines


def build_centerline_points_and_lines_from_mrk_dir(
    mrk_dir: str,
) -> Tuple[List[List[float]], List[List[int]]]:
    mrk_dir = os.path.abspath(mrk_dir)
    paths = [
        os.path.join(mrk_dir, f)
        for f in os.listdir(mrk_dir)
        if f.lower().endswith(".mrk.json")
    ]
    paths.sort(key=_extract_index_from_filename)
    return build_centerline_points_and_lines_from_mrk_files(paths)


def export_polydata_to_vtk(points: List[List[float]], lines: List[List[int]], output_vtk_path: str) -> str:
    output_vtk_path = os.path.abspath(output_vtk_path)
    out_dir = os.path.dirname(output_vtk_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    line_index_count = sum(len(line) + 1 for line in lines)
    with open(output_vtk_path, "w", encoding="utf-8") as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("centerline merged from slicer markups curve\n")
        f.write("ASCII\n")
        f.write("DATASET POLYDATA\n")
        f.write(f"POINTS {len(points)} float\n")
        for x, y, z in points:
            f.write(f"{x} {y} {z}\n")
        f.write(f"LINES {len(lines)} {line_index_count}\n")
        for line in lines:
            f.write(f"{len(line)} " + " ".join(str(i) for i in line) + "\n")

    return output_vtk_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mrk-dir",
        default=os.path.join("..", "source", "mrk"),
        help="包含 Slicer Centerline curve (*.mrk.json) 的目录",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("..", "source", "vtk", "Centerline_curves_merged.vtk"),
        help="输出 vtk 文件路径",
    )
    args = parser.parse_args(argv)

    points, lines = build_centerline_points_and_lines_from_mrk_dir(args.mrk_dir)
    if not points or not lines:
        raise RuntimeError(f"未从目录读取到有效曲线：{os.path.abspath(args.mrk_dir)}")

    out = export_polydata_to_vtk(points, lines, args.output)
    print(f"saved: {out}")
    print(f"points: {len(points)}, cells(lines): {len(lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
