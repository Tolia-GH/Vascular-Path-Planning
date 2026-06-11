from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import heapq
import math
import time
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pyvista as pv

try:
    from scipy.spatial import cKDTree
except Exception:  # pragma: no cover - fallback for environments without scipy
    cKDTree = None


Point3D = Tuple[float, float, float]


@dataclass(frozen=True)
class GraphEdge:
    neighbor_id: int
    distance: float


@dataclass
class GraphNode:
    node_id: int
    coord: Point3D
    neighbors: List[GraphEdge] = field(default_factory=list)
    component_id: int = -1


@dataclass
class ConnectedComponent:
    component_id: int
    node_ids: List[int]

    @property
    def size(self) -> int:
        return len(self.node_ids)


@dataclass
class PathPlanningResult:
    reachable: bool
    start_node_id: int
    end_node_id: int
    path_node_ids: List[int] = field(default_factory=list)
    path_coordinates: List[Point3D] = field(default_factory=list)
    total_length: float = 0.0
    elapsed_ms: float = 0.0
    control_node_count: int = 0
    error_message: Optional[str] = None


def euclidean_distance(point_a: Point3D, point_b: Point3D) -> float:
    return math.sqrt(
        (point_b[0] - point_a[0]) ** 2
        + (point_b[1] - point_a[1]) ** 2
        + (point_b[2] - point_a[2]) ** 2
    )


def iter_polyline_point_ids(polydata: pv.PolyData) -> Iterable[List[int]]:
    lines = np.asarray(polydata.lines, dtype=np.int64)
    index = 0
    n_total = int(lines.shape[0])
    while index < n_total:
        n_points = int(lines[index])
        index += 1
        if n_points <= 0:
            continue
        point_ids = lines[index:index + n_points]
        if int(point_ids.shape[0]) != n_points:
            raise ValueError("PolyData.lines 编码不完整，无法解析中心线拓扑。")
        index += n_points
        yield point_ids.tolist()


class _UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            self.parent[root_left] = root_right
            return
        if self.rank[root_left] > self.rank[root_right]:
            self.parent[root_right] = root_left
            return
        self.parent[root_right] = root_left
        self.rank[root_left] += 1


class CenterlineGraph:
    def __init__(
        self,
        nodes: Dict[int, GraphNode],
        components: List[ConnectedComponent],
        raw_point_to_node_id: Dict[int, int],
        merge_tolerance: float,
    ):
        self.nodes = nodes
        self.components = components
        self.raw_point_to_node_id = raw_point_to_node_id
        self.merge_tolerance = float(merge_tolerance)

        self._coordinates = np.asarray([self.nodes[node_id].coord for node_id in sorted(self.nodes)], dtype=float)
        self._node_ids = np.asarray(sorted(self.nodes), dtype=np.int64)
        self._kdtree = cKDTree(self._coordinates) if cKDTree is not None and len(self._coordinates) else None

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(node.neighbors) for node in self.nodes.values()) // 2

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def coordinates(self) -> np.ndarray:
        return self._coordinates

    def get_node(self, node_id: int) -> GraphNode:
        return self.nodes[node_id]

    def same_component(self, start_node_id: int, end_node_id: int) -> bool:
        return self.nodes[start_node_id].component_id == self.nodes[end_node_id].component_id

    def nearest_node(self, point: Point3D) -> Tuple[int, float]:
        point_array = np.asarray(point, dtype=float)
        if self._kdtree is not None:
            distance, index = self._kdtree.query(point_array)
            node_id = int(self._node_ids[int(index)])
            return node_id, float(distance)

        if self._coordinates.size == 0:
            raise ValueError("中心线图为空，无法执行最近点查询。")

        deltas = self._coordinates - point_array
        distances = np.linalg.norm(deltas, axis=1)
        index = int(np.argmin(distances))
        return int(self._node_ids[index]), float(distances[index])

    def to_adjacency_list(self) -> Dict[int, Dict[str, object]]:
        adjacency: Dict[int, Dict[str, object]] = {}
        for node_id, node in self.nodes.items():
            adjacency[node_id] = {
                "id": node_id,
                "coord": node.coord,
                "component_id": node.component_id,
                "neighbors": [
                    {"id": edge.neighbor_id, "distance": edge.distance}
                    for edge in node.neighbors
                ],
            }
        return adjacency

    @classmethod
    def from_polydata(
        cls,
        polydata: pv.PolyData,
        merge_tolerance: float = 1e-3,
    ) -> "CenterlineGraph":
        if not isinstance(polydata, pv.PolyData):
            raise TypeError("中心线数据必须是 PolyData。")
        if polydata.n_points <= 0:
            raise ValueError("中心线数据不包含有效点。")
        if polydata.lines is None or len(polydata.lines) == 0:
            raise ValueError("中心线数据不包含 lines，无法构建图结构。")

        points = np.asarray(polydata.points, dtype=float)
        raw_point_to_node_id, node_coords = cls._merge_points(points, merge_tolerance)

        edge_weights: Dict[Tuple[int, int], float] = {}
        for point_ids in iter_polyline_point_ids(polydata):
            if len(point_ids) < 2:
                continue
            for left_raw, right_raw in zip(point_ids[:-1], point_ids[1:]):
                left_node_id = raw_point_to_node_id[int(left_raw)]
                right_node_id = raw_point_to_node_id[int(right_raw)]
                if left_node_id == right_node_id:
                    continue
                left_coord = node_coords[left_node_id]
                right_coord = node_coords[right_node_id]
                distance = euclidean_distance(left_coord, right_coord)
                edge_key = (min(left_node_id, right_node_id), max(left_node_id, right_node_id))
                best_distance = edge_weights.get(edge_key)
                if best_distance is None or distance < best_distance:
                    edge_weights[edge_key] = distance

        nodes = {
            node_id: GraphNode(node_id=node_id, coord=coord)
            for node_id, coord in node_coords.items()
        }
        for (left_node_id, right_node_id), distance in edge_weights.items():
            nodes[left_node_id].neighbors.append(GraphEdge(neighbor_id=right_node_id, distance=distance))
            nodes[right_node_id].neighbors.append(GraphEdge(neighbor_id=left_node_id, distance=distance))

        components = cls._compute_connected_components(nodes)
        return cls(
            nodes=nodes,
            components=components,
            raw_point_to_node_id=raw_point_to_node_id,
            merge_tolerance=merge_tolerance,
        )

    @staticmethod
    def _merge_points(points: np.ndarray, merge_tolerance: float) -> Tuple[Dict[int, int], Dict[int, Point3D]]:
        if points.shape[0] == 0:
            return {}, {}

        union_find = _UnionFind(points.shape[0])
        tolerance = max(0.0, float(merge_tolerance))

        if tolerance > 0.0 and cKDTree is not None:
            kdtree = cKDTree(points)
            for left_idx, right_idx in kdtree.query_pairs(r=tolerance):
                union_find.union(int(left_idx), int(right_idx))
        elif tolerance > 0.0:
            rounded_to_index: Dict[Tuple[int, int, int], int] = {}
            scale = 1.0 / tolerance
            for idx, point in enumerate(points):
                rounded_key = tuple(int(round(coord * scale)) for coord in point)
                previous = rounded_to_index.get(rounded_key)
                if previous is not None:
                    union_find.union(previous, idx)
                else:
                    rounded_to_index[rounded_key] = idx

        root_to_members: Dict[int, List[int]] = {}
        for raw_index in range(points.shape[0]):
            root = union_find.find(raw_index)
            root_to_members.setdefault(root, []).append(raw_index)

        root_to_node_id: Dict[int, int] = {}
        node_coords: Dict[int, Point3D] = {}
        raw_point_to_node_id: Dict[int, int] = {}

        for node_id, root in enumerate(sorted(root_to_members)):
            members = root_to_members[root]
            coord = tuple(np.mean(points[members], axis=0).tolist())
            root_to_node_id[root] = node_id
            node_coords[node_id] = coord
            for member in members:
                raw_point_to_node_id[member] = node_id

        return raw_point_to_node_id, node_coords

    @staticmethod
    def _compute_connected_components(nodes: Dict[int, GraphNode]) -> List[ConnectedComponent]:
        components: List[ConnectedComponent] = []
        visited = set()

        for node_id in sorted(nodes):
            if node_id in visited:
                continue

            queue = deque([node_id])
            component_node_ids: List[int] = []
            component_id = len(components)

            while queue:
                current_id = queue.popleft()
                if current_id in visited:
                    continue
                visited.add(current_id)
                component_node_ids.append(current_id)
                nodes[current_id].component_id = component_id
                for edge in nodes[current_id].neighbors:
                    if edge.neighbor_id not in visited:
                        queue.append(edge.neighbor_id)

            components.append(
                ConnectedComponent(component_id=component_id, node_ids=component_node_ids)
            )

        return components


class AStarPathPlanner:
    def __init__(self, graph: CenterlineGraph):
        self.graph = graph

    def plan(self, start_node_id: int, end_node_id: int) -> PathPlanningResult:
        if start_node_id not in self.graph.nodes:
            return PathPlanningResult(
                reachable=False,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                error_message="起点节点不存在，请重新选择。",
            )
        if end_node_id not in self.graph.nodes:
            return PathPlanningResult(
                reachable=False,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                error_message="终点节点不存在，请重新选择。",
            )
        if not self.graph.same_component(start_node_id, end_node_id):
            return PathPlanningResult(
                reachable=False,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                error_message="起点与终点无法连通，请重新选择。",
            )

        start_time = time.perf_counter()
        open_heap: List[Tuple[float, float, int]] = []
        start_coord = self.graph.get_node(start_node_id).coord
        goal_coord = self.graph.get_node(end_node_id).coord
        start_h = euclidean_distance(start_coord, goal_coord)
        heapq.heappush(open_heap, (start_h, 0.0, start_node_id))

        came_from: Dict[int, int] = {}
        g_score: Dict[int, float] = {start_node_id: 0.0}
        closed_set = set()

        while open_heap:
            _, current_g, current_id = heapq.heappop(open_heap)
            if current_id in closed_set:
                continue
            if current_id == end_node_id:
                break

            closed_set.add(current_id)
            current_node = self.graph.get_node(current_id)
            for edge in current_node.neighbors:
                neighbor_id = edge.neighbor_id
                if neighbor_id in closed_set:
                    continue

                tentative_g = current_g + edge.distance
                if tentative_g >= g_score.get(neighbor_id, float("inf")):
                    continue

                came_from[neighbor_id] = current_id
                g_score[neighbor_id] = tentative_g
                neighbor_coord = self.graph.get_node(neighbor_id).coord
                heuristic = euclidean_distance(neighbor_coord, goal_coord)
                heapq.heappush(open_heap, (tentative_g + heuristic, tentative_g, neighbor_id))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        if end_node_id not in g_score:
            return PathPlanningResult(
                reachable=False,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                elapsed_ms=elapsed_ms,
                error_message="起点与终点无法连通，请重新选择。",
            )

        path_node_ids = self._reconstruct_path(came_from, start_node_id, end_node_id)
        path_coordinates = [self.graph.get_node(node_id).coord for node_id in path_node_ids]
        return PathPlanningResult(
            reachable=True,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            path_node_ids=path_node_ids,
            path_coordinates=path_coordinates,
            total_length=float(g_score[end_node_id]),
            elapsed_ms=elapsed_ms,
            control_node_count=len(path_node_ids),
        )

    @staticmethod
    def _reconstruct_path(
        came_from: Dict[int, int],
        start_node_id: int,
        end_node_id: int,
    ) -> List[int]:
        path = [end_node_id]
        current_id = end_node_id
        while current_id != start_node_id:
            current_id = came_from[current_id]
            path.append(current_id)
        path.reverse()
        return path
