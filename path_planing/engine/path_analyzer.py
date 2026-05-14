# 规划路径指标分析与可行性评分。

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .graph_loader import Node3D


@dataclass(frozen=True)
class PlanResult:
    # 单条规划路径的计算结果，供信息面板和渲染层消费。
    path_xyz: np.ndarray
    total_length_mm: float
    total_cost: float
    peak_curvature: float
    mean_curvature: float
    min_radius_mm: float | None
    feasibility: str
    node_count: int

    @property
    def summary(self) -> dict[str, float | int | str | None]:
        return {
            "length_mm": round(self.total_length_mm, 2),
            "total_cost": round(self.total_cost, 2),
            "node_count": self.node_count,
            "curvature_max_per_mm": round(self.peak_curvature, 6),
            "curvature_mean_per_mm": round(self.mean_curvature, 6),
            "min_radius_mm": (
                round(self.min_radius_mm, 2)
                if self.min_radius_mm is not None
                else None
            ),
            "feasibility": self.feasibility,
        }


class PathAnalyzer:
    # 计算长度、曲率、转弯半径和可行性等级。
    def __init__(
        self,
        curvature_yellow: float = 0.002,
        curvature_orange: float = 0.005,
        curvature_red: float = 0.010,
        radius_yellow_mm: float = 500.0,
        radius_orange_mm: float = 200.0,
        radius_red_mm: float = 100.0,
    ) -> None:
        self.curvature_yellow = curvature_yellow
        self.curvature_orange = curvature_orange
        self.curvature_red = curvature_red
        self.radius_yellow_mm = radius_yellow_mm
        self.radius_orange_mm = radius_orange_mm
        self.radius_red_mm = radius_red_mm
        self._last_result: PlanResult | None = None

    @property
    def last_result(self) -> PlanResult | None:
        return self._last_result

    def analyze(
        self,
        path: Sequence[Node3D] | np.ndarray,
        centerline_attrs: Mapping[str, Any] | None = None,
        total_cost: float | None = None,
    ) -> PlanResult:
        # centerline_attrs 预留给后续中心线半径/曲率属性；Phase 1 先用几何折线计算。
        points = as_points(path)
        # Phase 1 还没有接入逐节点血管半径属性，因此展示指标先由规划中心线折线几何推导。
        lengths = segment_lengths(points)
        total_length = float(np.sum(lengths)) if len(lengths) else 0.0
        curvatures = path_curvatures(points)
        peak_curvature = float(np.max(curvatures)) if len(curvatures) else 0.0
        mean_curvature = float(np.mean(curvatures)) if len(curvatures) else 0.0
        min_radius = min_turning_radius(curvatures)

        result = PlanResult(
            path_xyz=points,
            total_length_mm=total_length,
            total_cost=float(total_cost) if total_cost is not None else total_length,
            peak_curvature=peak_curvature,
            mean_curvature=mean_curvature,
            min_radius_mm=min_radius,
            feasibility=self.score_feasibility(peak_curvature, min_radius),
            node_count=int(len(points)),
        )
        self._last_result = result
        return result

    def set_path(
        self,
        path: Sequence[Node3D] | np.ndarray,
        centerline_attrs: Mapping[str, Any] | None = None,
        total_cost: float | None = None,
    ) -> PlanResult:
        # 兼容 UI 中“设置路径并刷新状态”的调用方式。
        return self.analyze(path, centerline_attrs=centerline_attrs, total_cost=total_cost)

    @property
    def summary(self) -> dict[str, float | int | str | None]:
        if self._last_result is None:
            return PlanResult(
                path_xyz=np.empty((0, 3), dtype=np.float64),
                total_length_mm=0.0,
                total_cost=0.0,
                peak_curvature=0.0,
                mean_curvature=0.0,
                min_radius_mm=None,
                feasibility="green",
                node_count=0,
            ).summary
        return self._last_result.summary

    def score_feasibility(
        self,
        peak_curvature: float,
        min_radius_mm: float | None,
    ) -> str:
        # 根据峰值曲率和最小转弯半径给出 green/yellow/orange/red 等级。
        # 这里是演示阶段默认阈值；集中在分析器里，后续接入真实器械约束时不需要改 UI。
        if peak_curvature >= self.curvature_red:
            return "red"
        if min_radius_mm is not None and min_radius_mm < self.radius_red_mm:
            return "red"
        if peak_curvature >= self.curvature_orange:
            return "orange"
        if min_radius_mm is not None and min_radius_mm < self.radius_orange_mm:
            return "orange"
        if peak_curvature >= self.curvature_yellow:
            return "yellow"
        if min_radius_mm is not None and min_radius_mm < self.radius_yellow_mm:
            return "yellow"
        return "green"


def analyze_path(
    path_points: Sequence[Node3D] | np.ndarray,
    centerline_attrs: Mapping[str, Any] | None = None,
    total_cost: float | None = None,
) -> PlanResult:
    # 使用默认演示阈值分析一条路径。
    return PathAnalyzer().analyze(
        path_points,
        centerline_attrs=centerline_attrs,
        total_cost=total_cost,
    )


def as_points(path: Sequence[Node3D] | np.ndarray) -> np.ndarray:
    points = np.asarray(path, dtype=np.float64)
    if points.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Path points must have shape (N, 3), got {points.shape}")
    return points


def segment_lengths(points: np.ndarray) -> np.ndarray:
    if len(points) < 2:
        return np.empty((0,), dtype=np.float64)
    return np.linalg.norm(np.diff(points, axis=0), axis=1)


def path_curvatures(points: np.ndarray) -> np.ndarray:
    # 按每三个连续点的外接圆估计逐点曲率，单位为 1/mm。
    # 曲率公式为 k = 4A/(abc)。
    count = len(points)
    curvatures = np.zeros(count, dtype=np.float64)
    if count < 3:
        return curvatures

    for index in range(1, count - 1):
        p0 = points[index - 1]
        p1 = points[index]
        p2 = points[index + 1]

        side_a = float(np.linalg.norm(p1 - p0))
        side_b = float(np.linalg.norm(p2 - p1))
        side_c = float(np.linalg.norm(p2 - p0))
        denom = side_a * side_b * side_c
        if denom <= 1e-12:
            continue

        # 等价于 k = 4A/(abc)；这里的 cross_norm 是三角形面积的两倍。
        cross_norm = float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))
        curvatures[index] = 2.0 * cross_norm / denom

    return curvatures


def min_turning_radius(curvatures: np.ndarray) -> float | None:
    valid = curvatures[curvatures > 1e-12]
    if len(valid) == 0:
        return None
    return float(1.0 / np.max(valid))
