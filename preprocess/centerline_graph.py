from __future__ import annotations

import json
import math
import os
import pickle
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


Point3 = Tuple[float, float, float]
WeightedAdjacency = Dict[Point3, List[Tuple[Point3, float]]]


@dataclass(frozen=True)
class CurveData:
    points: List[Point3]
    radius: Optional[List[float]]
    coordinate_system: Optional[str]
    coordinate_units: Optional[str]


def _euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    dx = float(b[0]) - float(a[0])
    dy = float(b[1]) - float(a[1])
    dz = float(b[2]) - float(a[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def load_slicer_curve_mrk_json(path: str) -> CurveData:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    markups = data.get("markups") or []
    if not markups:
        raise ValueError(f"No 'markups' found in: {path}")

    m = markups[0]
    if m.get("type") not in (None, "Curve"):
        raise ValueError(f"Unsupported markup type {m.get('type')!r} in: {path}")

    points: List[Point3] = []
    for cp in m.get("controlPoints") or []:
        if cp.get("positionStatus") not in (None, "defined"):
            continue
        pos = cp.get("position")
        if not (isinstance(pos, list) and len(pos) == 3):
            continue
        points.append((float(pos[0]), float(pos[1]), float(pos[2])))

    if len(points) < 2:
        raise ValueError(f"Not enough points ({len(points)}) in: {path}")

    radius: Optional[List[float]] = None
    for meas in m.get("measurements") or []:
        if meas.get("name") != "Radius":
            continue
        vals = meas.get("controlPointValues")
        if isinstance(vals, list) and len(vals) == len(points):
            radius = [float(v) for v in vals]
        break

    return CurveData(
        points=points,
        radius=radius,
        coordinate_system=m.get("coordinateSystem"),
        coordinate_units=m.get("coordinateUnits"),
    )


def iter_curve_files(input_path: str) -> List[str]:
    input_path = os.path.abspath(input_path)
    if os.path.isfile(input_path):
        return [input_path]

    if not os.path.isdir(input_path):
        raise FileNotFoundError(input_path)

    curve_paths: List[str] = []
    for name in os.listdir(input_path):
        if name.lower().endswith(".mrk.json"):
            curve_paths.append(os.path.join(input_path, name))
    curve_paths.sort()
    return curve_paths


def _quantize_point(p: Point3, tol: float) -> Tuple[int, int, int]:
    if tol <= 0:
        raise ValueError("merge_tol must be > 0")
    return (
        int(round(p[0] / tol)),
        int(round(p[1] / tol)),
        int(round(p[2] / tol)),
    )


def build_weighted_graph_from_curves(
    curve_paths: Iterable[str],
    merge_tol: float = 0.01,
    undirected: bool = True,
) -> WeightedAdjacency:
    key_to_point: Dict[Tuple[int, int, int], Point3] = {}
    key_to_index: Dict[Tuple[int, int, int], int] = {}
    index_to_point: List[Point3] = []
    adjacency: Dict[int, Dict[int, float]] = {}

    def get_node_index(p: Point3) -> int:
        key = _quantize_point(p, merge_tol)
        idx = key_to_index.get(key)
        if idx is not None:
            return idx
        idx = len(index_to_point)
        key_to_index[key] = idx
        key_to_point[key] = p
        index_to_point.append(p)
        adjacency[idx] = {}
        return idx

    def add_edge(u: int, v: int, w: float) -> None:
        prev = adjacency[u].get(v)
        if prev is None or w < prev:
            adjacency[u][v] = w

    for curve_path in curve_paths:
        curve = load_slicer_curve_mrk_json(curve_path)
        pts = curve.points
        for i in range(len(pts) - 1):
            a = pts[i]
            b = pts[i + 1]
            u = get_node_index(a)
            v = get_node_index(b)
            if u == v:
                continue
            w = _euclidean(a, b)
            add_edge(u, v, w)
            if undirected:
                add_edge(v, u, w)

    vessel_net: WeightedAdjacency = {}
    for u, neighbors in adjacency.items():
        u_point = index_to_point[u]
        vessel_net[u_point] = [(index_to_point[v], float(w)) for v, w in neighbors.items()]

    return vessel_net


def save_pickle(obj: Any, path: str) -> str:
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    return path


def save_json_vessel_net(vessel_net: WeightedAdjacency, path: str) -> str:
    def key(p: Point3) -> str:
        return f"{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}"

    payload = {
        key(src): [(key(dst), float(w)) for dst, w in neighbors]
        for src, neighbors in vessel_net.items()
    }
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path

