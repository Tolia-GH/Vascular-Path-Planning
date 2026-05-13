# 对现有 A* 实现的轻量封装。

from __future__ import annotations

from collections.abc import Callable

from vascular_path_planning.planning.a_star import a_star

from .graph_loader import Graph, Node3D

Heuristic = Callable[[Node3D, Node3D], float]


class PathPlanner:
    # 持有血管图引用，并把搜索委托给公共 A* 函数。
    def __init__(self, graph: Graph | None = None) -> None:
        self._graph: Graph = graph if graph is not None else {}

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def is_ready(self) -> bool:
        return bool(self._graph)

    def set_graph(self, graph: Graph) -> None:
        if not graph:
            raise ValueError("Graph must not be empty")
        self._graph = graph

    def plan(
        self,
        start: Node3D,
        goal: Node3D,
        heuristic: Heuristic | None = None,
    ) -> list[Node3D] | None:
        # 返回从起点到终点的有序路径；无路可达时返回 None。
        self._validate_node("start", start)
        self._validate_node("goal", goal)
        # 搜索行为保持和已验证的 vascular_path_planning 实现一致；本封装只负责数据就绪校验。
        return a_star(start, goal, self._graph, heuristic=heuristic)

    def _validate_node(self, label: str, node: Node3D) -> None:
        if not self._graph:
            raise RuntimeError("Graph not loaded")
        if node not in self._graph:
            raise ValueError(f"{label.capitalize()} node is not in graph: {node!r}")


Planner = PathPlanner
