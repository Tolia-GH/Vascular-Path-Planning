# KDTree 最近邻吸附工具，用于将 3D 点选坐标映射到最近图节点。

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from path_planing.engine.graph_loader import Node3D


class KDTreeSnapper:
    # 基于 scipy cKDTree 实现 O(log N) 最近邻查询。
    def __init__(self, nodes: list[Node3D] | None = None) -> None:
        self._tree: cKDTree | None = None
        self._nodes: list[Node3D] = []
        self._node_indices: dict[Node3D, int] = {}

        if nodes is not None:
            self.build(nodes)

    @property
    def is_ready(self) -> bool:
        return self._tree is not None

    def build(self, nodes: list[Node3D]) -> None:
        # 用图的所有节点构建 KDTree，同时缓存节点→索引映射。
        if not nodes:
            raise ValueError("Node list must not be empty")

        self._nodes = nodes
        self._node_indices = {node: i for i, node in enumerate(nodes)}
        points = np.array(nodes, dtype=np.float64)
        self._tree = cKDTree(points)

    def find_nearest(
        self, query: tuple[float, float, float]
    ) -> tuple[Node3D, float]:
        # 返回 (最近图节点, 距离_mm)。
        if self._tree is None:
            raise RuntimeError("KDTree not built; call build() first")

        distance, index = self._tree.query(query)
        return self._nodes[int(index)], float(distance)


def find_nearest_node(
    query_xyz: tuple[float, float, float],
    nodes: list[Node3D],
) -> tuple[Node3D, float]:
    # 一次性查询的便捷入口。
    return KDTreeSnapper(nodes).find_nearest(query_xyz)