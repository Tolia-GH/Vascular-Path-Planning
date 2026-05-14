# 规划路径渲染辅助。

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pyvista as pv

from path_planing.engine import Node3D


FEASIBILITY_COLORS = {
    "green": "#00cc66",
    "yellow": "#ffcc00",
    "orange": "#ff8800",
    "red": "#cc0000",
}


def build_path_polyline(path: Sequence[Node3D] | np.ndarray) -> pv.PolyData:
    # 将路径点序列构造成一条连续 PolyData 折线。
    points = np.asarray(path, dtype=np.float64)
    if points.size == 0:
        return pv.PolyData()
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Path points must have shape (N, 3), got {points.shape}")

    polyline = pv.PolyData()
    polyline.points = points
    polyline.lines = np.hstack([[len(points)], np.arange(len(points), dtype=np.int64)])
    return polyline


class PathRenderer:
    # 管理规划路径、起点 marker 和终点 marker 三类 actor。
    def __init__(self) -> None:
        self._polyline: pv.PolyData | None = None
        self._path_actor: Any | None = None
        self._start_actor: Any | None = None
        self._goal_actor: Any | None = None
        self._feasibility = "green"
        self._visible = True

    def set_path(
        self,
        path: Sequence[Node3D] | np.ndarray,
        feasibility: str = "green",
    ) -> pv.PolyData:
        self._polyline = build_path_polyline(path)
        self._feasibility = feasibility
        return self._polyline

    @property
    def polyline(self) -> pv.PolyData | None:
        return self._polyline

    @property
    def path_actor(self) -> Any | None:
        return self._path_actor

    @property
    def start_actor(self) -> Any | None:
        return self._start_actor

    @property
    def goal_actor(self) -> Any | None:
        return self._goal_actor

    @property
    def is_set(self) -> bool:
        return self._polyline is not None and self._polyline.n_points >= 2

    def add_to_plotter(self, plotter: Any, **kwargs: Any) -> Any | None:
        # 添加路径线和起终点 marker；三者分开管理，便于后续统一清除。
        if self._polyline is None or self._polyline.n_points < 2:
            return None

        self.remove_from_plotter(plotter)

        defaults = {
            "color": FEASIBILITY_COLORS.get(self._feasibility, FEASIBILITY_COLORS["green"]),
            "line_width": 5.0,
            "pickable": False,
            "reset_camera": False,
            "render_lines_as_tubes": True,
            "name": "planned_path",
        }
        defaults.update(kwargs)
        self._path_actor = plotter.add_mesh(self._polyline, **defaults)

        # 起终点 marker 跟路径 actor 分开管理，后续清除/替换路径时可以一次性移除。
        start_point = self._polyline.points[0]
        goal_point = self._polyline.points[-1]
        self._start_actor = plotter.add_points(
            start_point,
            color="blue",
            point_size=16,
            render_points_as_spheres=True,
            pickable=False,
            reset_camera=False,
            name="path_start_marker",
        )
        self._goal_actor = plotter.add_points(
            goal_point,
            color="limegreen",
            point_size=16,
            render_points_as_spheres=True,
            pickable=False,
            reset_camera=False,
            name="path_goal_marker",
        )
        self.set_visible(self._visible)
        return self._path_actor

    def show_path(
        self,
        plotter: Any,
        path: Sequence[Node3D] | np.ndarray,
        feasibility: str = "green",
        **kwargs: Any,
    ) -> Any | None:
        self.set_path(path, feasibility=feasibility)
        return self.add_to_plotter(plotter, **kwargs)

    def remove_from_plotter(self, plotter: Any) -> None:
        for actor in (self._path_actor, self._start_actor, self._goal_actor):
            if actor is not None:
                plotter.remove_actor(actor, reset_camera=False)
        self._path_actor = None
        self._start_actor = None
        self._goal_actor = None

    def clear(self, plotter: Any | None = None) -> None:
        if plotter is not None:
            self.remove_from_plotter(plotter)
        self._polyline = None

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        for actor in (self._path_actor, self._start_actor, self._goal_actor):
            if actor is not None:
                actor.SetVisibility(visible)
