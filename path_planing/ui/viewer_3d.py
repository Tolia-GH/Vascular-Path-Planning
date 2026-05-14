# 3D 视图组件，封装 PyVista QtInteractor。

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PyQt5 import QtCore, QtWidgets
from pyvistaqt import QtInteractor
from vtkmodules.vtkRenderingCore import vtkCellPicker

from path_planing.engine import Node3D
from path_planing.render import CenterlineRenderer, PathRenderer, VesselRenderer


class Viewer3D(QtWidgets.QWidget):
    point_picked = QtCore.pyqtSignal(tuple)
    pick_missed = QtCore.pyqtSignal(str)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        off_screen: bool | None = None,
    ) -> None:
        super().__init__(parent)

        self.plotter = QtInteractor(self, off_screen=off_screen)
        self.vessel_renderer = VesselRenderer()
        self.centerline_renderer = CenterlineRenderer()
        self.path_renderer = PathRenderer()
        self._screen_pick_radius_px = 24.0

        # 选点临时 marker（起点/终点球），规划前独立显示，规划/清除时移除
        self._pick_start_actor = None
        self._pick_goal_actor = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.plotter)

        self._configure_scene()

    def _configure_scene(self) -> None:
        self.plotter.set_background("white")
        self.plotter.add_axes()

    def load_vessel(self, vtk_path: str | Path) -> None:
        self.vessel_renderer.load(vtk_path)
        self.vessel_renderer.add_to_plotter(self.plotter)

    def load_centerline(self, vtk_path: str | Path) -> None:
        self.centerline_renderer.load(vtk_path)
        self.centerline_renderer.add_to_plotter(self.plotter)

    def load_static_scene(
        self,
        vessel_path: str | Path | None = None,
        centerline_path: str | Path | None = None,
    ) -> None:
        # 血管和中心线分开加载，后续可以独立刷新某一层而不重建整个场景。
        if vessel_path is not None:
            self.load_vessel(vessel_path)
        if centerline_path is not None:
            self.load_centerline(centerline_path)
        self.reset_camera()

    def show_path(
        self,
        path: Sequence[Node3D],
        feasibility: str = "green",
        **kwargs: Any,
    ) -> None:
        self.path_renderer.show_path(self.plotter, path, feasibility=feasibility, **kwargs)
        self.plotter.render()

    def clear_path(self) -> None:
        self.path_renderer.clear(self.plotter)
        self.plotter.render()

    def highlight_segment(self, segment_index: int | None) -> None:
        self.centerline_renderer.highlight_segment(self.plotter, segment_index)

    def show_pick_marker(self, coords, marker_type: str) -> None:
        # 在 3D 视图中绘制选点标记球；起点=蓝色，终点=绿色。
        color = "#0088ff" if marker_type == "start" else "#33cc33"
        name = f"_pick_{marker_type}_marker"

        # 先移除旧的同类型 marker 避免叠加
        old = self._pick_start_actor if marker_type == "start" else self._pick_goal_actor
        if old is not None:
            self.plotter.remove_actor(old, reset_camera=False)

        actor = self.plotter.add_points(
            np.array(coords, dtype=np.float64).reshape(1, 3),
            color=color,
            point_size=18.0,
            render_points_as_spheres=True,
            pickable=False,
            reset_camera=False,
            name=name,
        )
        if marker_type == "start":
            self._pick_start_actor = actor
        else:
            self._pick_goal_actor = actor
        self.plotter.render()

    def clear_pick_markers(self) -> None:
        # 清除选点阶段的临时 marker，规划前/清除时调用。
        for actor in (self._pick_start_actor, self._pick_goal_actor):
            if actor is not None:
                self.plotter.remove_actor(actor, reset_camera=False)
        self._pick_start_actor = None
        self._pick_goal_actor = None
        self.plotter.render()

    def enable_picking(self, enabled: bool = True) -> None:
        # 启用或禁用 3D 点选功能。
        if enabled:
            self.plotter.untrack_click_position(side="left")
            self.plotter.track_click_position(
                callback=self._on_left_click_position,
                side="left",
                viewport=True,
            )
        else:
            self.plotter.untrack_click_position(side="left")
            self.plotter.disable_picking()

    def _on_left_click_position(self, click_pos) -> None:
        # 优先按屏幕距离选择中心线点，避免窗口点选的深度误差把点吸附到远处。
        coords = self._pick_centerline_by_screen(click_pos)
        if coords is None:
            coords = self._pick_model_surface(click_pos)
        if coords is None:
            self.pick_missed.emit("未命中血管或中心线，请靠近中心线重新点击。")
            return

        self.point_picked.emit(coords)

    def _pick_centerline_by_screen(self, click_pos) -> tuple[float, float, float] | None:
        points = self.centerline_renderer.points
        if points.size == 0:
            return None

        try:
            click_x, click_y = float(click_pos[0]), float(click_pos[1])
        except (TypeError, ValueError, IndexError):
            return None

        renderer = self.plotter.renderer
        best_index: int | None = None
        best_dist2 = self._screen_pick_radius_px * self._screen_pick_radius_px

        for index, point in enumerate(np.asarray(points, dtype=np.float64)):
            renderer.SetWorldPoint(float(point[0]), float(point[1]), float(point[2]), 1.0)
            renderer.WorldToDisplay()
            display_x, display_y, display_z = renderer.GetDisplayPoint()
            if display_z < 0.0 or display_z > 1.0:
                continue

            dist2 = (display_x - click_x) ** 2 + (display_y - click_y) ** 2
            if dist2 <= best_dist2:
                best_dist2 = dist2
                best_index = index

        if best_index is None:
            return None

        picked = points[best_index]
        return (float(picked[0]), float(picked[1]), float(picked[2]))

    def _pick_model_surface(self, click_pos) -> tuple[float, float, float] | None:
        try:
            click_x, click_y = float(click_pos[0]), float(click_pos[1])
        except (TypeError, ValueError, IndexError):
            return None

        picker = vtkCellPicker()
        picker.SetTolerance(0.03)
        hit = picker.Pick(click_x, click_y, 0, self.plotter.renderer)
        if not hit:
            return None
        if hasattr(picker, "GetDataSet") and picker.GetDataSet() is None:
            return None

        picked = picker.GetPickPosition()
        return (float(picked[0]), float(picked[1]), float(picked[2]))

    def _on_point_picked(self, world_pos) -> None:
        # PyVista 没有命中点时可能返回空值，直接忽略即可。
        if world_pos is None:
            return

        try:
            # 这里只需要前三个世界坐标，后续由 KDTree 吸附到最近中心线节点。
            coords = tuple(float(c) for c in world_pos[:3])
        except (TypeError, ValueError, IndexError):
            return

        if len(coords) != 3:
            return

        self.point_picked.emit(coords)

    def reset_camera(self) -> None:
        self.plotter.reset_camera()
        self.plotter.render()

    def view_top(self) -> None:
        self.plotter.view_xy()
        self.reset_camera()

    def view_front(self) -> None:
        self.plotter.view_xz()
        self.reset_camera()

    def view_side(self) -> None:
        self.plotter.view_yz()
        self.reset_camera()

    def close(self) -> bool:
        try:
            self.plotter.close()
        finally:
            return super().close()
