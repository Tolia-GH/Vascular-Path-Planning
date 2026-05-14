# 中心线分段、渲染与高亮辅助。

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyvista as pv


@dataclass(frozen=True)
class CenterlineSegment:
    # 保存一个可渲染线段及其在源 VTK 中对应的点索引。
    index: int
    point_ids: list[int]
    polyline: pv.PolyData

    @property
    def point_count(self) -> int:
        return len(self.point_ids)


def split_polydata_lines(lines: np.ndarray) -> list[list[int]]:
    # 将 VTK 压缩 line-cell 数组拆成每段中心线的点索引列表。
    segments: list[list[int]] = []
    index = 0
    line_values = np.asarray(lines, dtype=np.int64)

    while index < len(line_values):
        point_count = int(line_values[index])
        start = index + 1
        stop = start + point_count
        if point_count <= 0 or stop > len(line_values):
            raise ValueError("Invalid compressed PolyData.lines structure")
        segments.append([int(value) for value in line_values[start:stop]])
        index = stop

    return segments


def build_polyline_from_points(points: np.ndarray) -> pv.PolyData:
    # 从 N×3 坐标数组构造单条 PolyData 折线。
    point_array = np.asarray(points, dtype=np.float64)
    if point_array.ndim != 2 or point_array.shape[1] != 3:
        raise ValueError(f"Polyline points must have shape (N, 3), got {point_array.shape}")

    polyline = pv.PolyData()
    polyline.points = point_array
    point_count = polyline.n_points
    if point_count:
        polyline.lines = np.hstack([[point_count], np.arange(point_count, dtype=np.int64)])
    return polyline


class CenterlineRenderer:
    # 管理中心线 VTK 的加载、分段 actor 创建以及线段高亮状态。
    def __init__(self, vtk_path: str | Path | None = None) -> None:
        self._polydata: pv.PolyData | None = None
        self._segments: list[CenterlineSegment] = []
        self._actors: list[Any] = []
        self._highlight_actor: Any | None = None
        self._selected_index: int | None = None
        self._base_line_width = 1.5
        self._highlight_line_width = 4.0

        if vtk_path is not None:
            self.load(vtk_path)

    def load(self, vtk_path: str | Path) -> pv.PolyData:
        path = Path(vtk_path)
        if not path.is_file():
            raise FileNotFoundError(f"Centerline VTK file not found: {path}")

        polydata = pv.read(path)
        if not isinstance(polydata, pv.PolyData):
            raise TypeError(f"Centerline must be PolyData, got {type(polydata).__name__}")
        if len(polydata.lines) == 0:
            raise ValueError("Centerline PolyData has no line cells")

        segment_ids = split_polydata_lines(polydata.lines)
        segments: list[CenterlineSegment] = []
        for index, point_ids in enumerate(segment_ids):
            # 中心线列表和高亮都依赖这里的段索引，因此加载阶段就固定 segment -> PolyData 映射。
            points = polydata.points[np.asarray(point_ids, dtype=np.int64)]
            segments.append(
                CenterlineSegment(
                    index=index,
                    point_ids=point_ids,
                    polyline=build_polyline_from_points(points),
                )
            )

        self._polydata = polydata
        self._segments = segments
        self._actors = []
        self._highlight_actor = None
        self._selected_index = None
        return polydata

    @property
    def polydata(self) -> pv.PolyData | None:
        return self._polydata

    @property
    def segments(self) -> list[CenterlineSegment]:
        return self._segments

    @property
    def segment_polylines(self) -> list[pv.PolyData]:
        return [segment.polyline for segment in self._segments]

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    @property
    def actors(self) -> list[Any]:
        return self._actors

    @property
    def selected_index(self) -> int | None:
        return self._selected_index

    @property
    def is_loaded(self) -> bool:
        return self._polydata is not None

    @property
    def points(self) -> np.ndarray:
        if self._polydata is None:
            return np.empty((0, 3), dtype=np.float64)
        return self._polydata.points

    def add_to_plotter(self, plotter: Any, **kwargs: Any) -> list[Any]:
        # 把每段中心线分别添加为 actor，方便后续列表选择时单独高亮。
        self.remove_from_plotter(plotter)
        if not self._segments:
            return []

        defaults = {
            "color": "black",
            "line_width": self._base_line_width,
            "opacity": 1.0,
            "pickable": True,
            "reset_camera": False,
            "render_lines_as_tubes": True,
        }
        defaults.update(kwargs)

        self._actors = [
            plotter.add_mesh(
                segment.polyline,
                name=f"centerline_segment_{segment.index}",
                **defaults,
            )
            for segment in self._segments
        ]
        return self._actors

    def highlight_segment(self, plotter: Any, segment_index: int | None) -> Any | None:
        # 高亮一个中心线段，同时恢复上一次被选中的段。
        if segment_index is None:
            self.clear_highlight(plotter)
            return None
        if segment_index < 0 or segment_index >= len(self._segments):
            raise IndexError(f"Segment index out of range: {segment_index}")

        if self._selected_index is not None and self._selected_index < len(self._actors):
            self._actors[self._selected_index].SetVisibility(True)

        if self._highlight_actor is not None:
            plotter.remove_actor(self._highlight_actor, reset_camera=False)
            self._highlight_actor = None

        if segment_index < len(self._actors):
            # 高亮时隐藏原黑色底线，只显示红色层，避免两条线重叠造成视觉噪声。
            self._actors[segment_index].SetVisibility(False)

        self._highlight_actor = plotter.add_mesh(
            self._segments[segment_index].polyline,
            color="red",
            line_width=self._highlight_line_width,
            opacity=1.0,
            pickable=True,
            reset_camera=False,
            render_lines_as_tubes=True,
            name="centerline_highlight",
        )
        self._selected_index = segment_index
        plotter.render()
        return self._highlight_actor

    def clear_highlight(self, plotter: Any) -> None:
        if self._selected_index is not None and self._selected_index < len(self._actors):
            self._actors[self._selected_index].SetVisibility(True)
        if self._highlight_actor is not None:
            plotter.remove_actor(self._highlight_actor, reset_camera=False)
            self._highlight_actor = None
        self._selected_index = None
        plotter.render()

    def remove_from_plotter(self, plotter: Any) -> None:
        self.clear_highlight(plotter)
        for actor in self._actors:
            plotter.remove_actor(actor, reset_camera=False)
        self._actors = []
