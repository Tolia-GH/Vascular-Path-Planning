# 血管表面模型的加载与渲染辅助。

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyvista as pv


class VesselRenderer:
    # 负责维护单个血管网格及其 PyVista actor，供 Qt 视图反复添加/移除。
    def __init__(self, vtk_path: str | Path | None = None) -> None:
        self._mesh: pv.PolyData | None = None
        self._actor: Any | None = None
        self._visible = True

        if vtk_path is not None:
            self.load(vtk_path)

    def load(self, vtk_path: str | Path) -> pv.PolyData:
        path = Path(vtk_path)
        if not path.is_file():
            raise FileNotFoundError(f"Vessel VTK file not found: {path}")

        mesh = pv.read(path)
        if not isinstance(mesh, pv.PolyData):
            raise TypeError(f"Vessel mesh must be PolyData, got {type(mesh).__name__}")

        self._mesh = mesh
        return mesh

    @property
    def mesh(self) -> pv.PolyData | None:
        return self._mesh

    @property
    def actor(self) -> Any | None:
        return self._actor

    @property
    def is_loaded(self) -> bool:
        return self._mesh is not None

    @property
    def is_visible(self) -> bool:
        return self._visible

    def add_to_plotter(self, plotter: Any, **kwargs: Any) -> Any | None:
        # 将已加载血管网格添加到 PyVista/QtInteractor 渲染器。
        if self._mesh is None:
            return None

        defaults = {
            "color": "lightcoral",
            "opacity": 0.25,
            "specular": 0.1,
            "smooth_shading": True,
            "pickable": True,
            "reset_camera": False,
            "name": "vessel_mesh",
        }
        defaults.update(kwargs)

        self.remove_from_plotter(plotter)
        self._actor = plotter.add_mesh(self._mesh, **defaults)
        self.set_visible(self._visible)
        return self._actor

    def remove_from_plotter(self, plotter: Any) -> None:
        if self._actor is not None:
            plotter.remove_actor(self._actor, reset_camera=False)
            self._actor = None

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        if self._actor is not None:
            self._actor.SetVisibility(visible)
