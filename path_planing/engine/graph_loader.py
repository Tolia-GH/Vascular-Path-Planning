# 中心线血管图加载器。

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

Node3D = tuple[float, float, float]
Graph = dict[Node3D, list[tuple[Node3D, float]]]


class GraphLoadError(ValueError):
    pass


@dataclass(frozen=True)
class GraphStats:
    # 供状态栏和验证逻辑使用的图规模统计。
    node_count: int
    edge_count: int
    min_weight: float | None
    max_weight: float | None


class GraphLoader:
    # 将 centerline_vessel_net.json 转成 A* 可直接使用的数值邻接表。
    # 源 JSON 结构是 "x,y,z" -> [["邻居x,邻居y,邻居z", 权重], ...]。
    # 规划器需要数值 tuple 节点，因此这里统一完成坐标转换和邻居校验。
    def __init__(self, graph_path: str | Path | None = None) -> None:
        self._path: Path | None = None
        self._graph: Graph = {}
        self._nodes: list[Node3D] = []
        self._key_to_node: dict[str, Node3D] = {}
        self._node_to_key: dict[Node3D, str] = {}
        self._stats = GraphStats(0, 0, None, None)

        if graph_path is not None:
            self.load(graph_path)

    def load(self, graph_path: str | Path) -> Graph:
        # 加载图 JSON，并返回转换后的邻接表。
        path = Path(graph_path)
        if not path.is_file():
            raise FileNotFoundError(f"Graph file not found: {path}")

        with path.open("r", encoding="utf-8") as file_obj:
            raw = json.load(file_obj)

        if not isinstance(raw, dict):
            raise GraphLoadError("Graph JSON must be an object adjacency map")

        key_to_node: dict[str, Node3D] = {}
        node_to_key: dict[Node3D, str] = {}
        nodes: list[Node3D] = []

        # 第一遍先把所有坐标 key 规范化为数值节点；第二遍构边时就能校验邻居是否真实存在。
        for key in raw:
            if not isinstance(key, str):
                raise GraphLoadError(f"Graph node key must be a string: {key!r}")
            node = self.parse_node(key)
            if node in node_to_key:
                raise GraphLoadError(
                    f"Duplicate node coordinates: {key!r} and {node_to_key[node]!r}"
                )
            key_to_node[key] = node
            node_to_key[node] = key
            nodes.append(node)

        graph: Graph = {}
        weights: list[float] = []

        # 第二遍把邻接项转换为“数值节点 + 浮点权重”，保留源图的加权邻接结构。
        for key, neighbors in raw.items():
            if not isinstance(neighbors, list):
                raise GraphLoadError(f"Neighbors for {key!r} must be a list")

            node = key_to_node[key]
            adjacency: list[tuple[Node3D, float]] = []

            for item in neighbors:
                target_key, weight = self._parse_edge_item(key, item)
                if target_key not in key_to_node:
                    raise GraphLoadError(
                        f"Neighbor {target_key!r} referenced by {key!r} is missing"
                    )

                weight_value = float(weight)
                if weight_value < 0:
                    raise GraphLoadError(
                        f"Negative edge weight from {key!r} to {target_key!r}: "
                        f"{weight_value}"
                    )

                adjacency.append((key_to_node[target_key], weight_value))
                weights.append(weight_value)

            graph[node] = adjacency

        self._path = path
        self._graph = graph
        self._nodes = nodes
        self._key_to_node = key_to_node
        self._node_to_key = node_to_key
        self._stats = GraphStats(
            node_count=len(nodes),
            edge_count=sum(len(edges) for edges in graph.values()),
            min_weight=min(weights) if weights else None,
            max_weight=max(weights) if weights else None,
        )

        return self._graph

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def nodes(self) -> list[Node3D]:
        return self._nodes

    @property
    def node_count(self) -> int:
        return self._stats.node_count

    @property
    def edge_count(self) -> int:
        return self._stats.edge_count

    @property
    def stats(self) -> GraphStats:
        return self._stats

    @property
    def is_loaded(self) -> bool:
        return bool(self._graph)

    def key_for_node(self, node: Node3D) -> str:
        # 根据数值节点找回原始 JSON 坐标 key。
        try:
            return self._node_to_key[node]
        except KeyError as exc:
            raise KeyError(f"Node is not in the loaded graph: {node!r}") from exc

    def node_for_key(self, key: str) -> Node3D:
        # 根据原始 JSON 坐标 key 找到数值节点。
        try:
            return self._key_to_node[key]
        except KeyError as exc:
            raise KeyError(f"Node key is not in the loaded graph: {key!r}") from exc

    @staticmethod
    def parse_node(value: str | Sequence[float]) -> Node3D:
        # 把坐标字符串或三元数值序列统一转换成 3D 节点 tuple。
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
        else:
            parts = list(value)

        if len(parts) != 3:
            raise GraphLoadError(f"Node must contain exactly 3 coordinates: {value!r}")

        try:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
        except (TypeError, ValueError) as exc:
            raise GraphLoadError(f"Invalid node coordinates: {value!r}") from exc

    @staticmethod
    def format_node(node: Node3D) -> str:
        # 按源 JSON 的坐标 key 格式输出节点。
        return f"{node[0]:.6f},{node[1]:.6f},{node[2]:.6f}"

    @staticmethod
    def _parse_edge_item(source_key: str, item: Any) -> tuple[str, float]:
        if not isinstance(item, list) or len(item) < 2:
            raise GraphLoadError(
                f"Edge entry for {source_key!r} must be [target_key, weight]: "
                f"{item!r}"
            )

        target_key, weight = item[0], item[1]
        if not isinstance(target_key, str):
            raise GraphLoadError(
                f"Edge target for {source_key!r} must be a string: {target_key!r}"
            )

        try:
            weight_value = float(weight)
        except (TypeError, ValueError) as exc:
            raise GraphLoadError(
                f"Edge weight for {source_key!r} -> {target_key!r} is invalid: "
                f"{weight!r}"
            ) from exc

        return target_key, weight_value


def load_graph(graph_path: str | Path) -> Graph:
    # 一次性加载图文件的便捷入口。
    return GraphLoader(graph_path).graph
