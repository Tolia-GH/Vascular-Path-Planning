import numpy as np
from scipy import interpolate
import pyvista as pv


class CenterlineBSplineSmoother:
    def __init__(self, smoothing_factor=0.0, degree=3):
        self.s = smoothing_factor
        self.k = degree

    def fit(self, points):
        self.points = np.array(points)

        if self.points.shape[0] < 4:
            raise ValueError("至少需要4个点")

        x, y, z = self.points[:, 0], self.points[:, 1], self.points[:, 2]

        self.tck, self.u = interpolate.splprep(
            [x, y, z],
            s=self.s,
            k=self.k
        )

        return self

    def evaluate(self, num=300):
        u_new = np.linspace(0, 1, num)
        x, y, z = interpolate.splev(u_new, self.tck)
        return np.vstack([x, y, z]).T, u_new

    # ========= 关键：方向计算 =========

    def tangent(self, u):
        dx, dy, dz = interpolate.splev(u, self.tck, der=1)
        v = np.array([dx, dy, dz])
        return v / np.linalg.norm(v)

    def normal(self, u):
        d1 = np.array(interpolate.splev(u, self.tck, der=1))
        d2 = np.array(interpolate.splev(u, self.tck, der=2))

        T = d1 / np.linalg.norm(d1)

        N = d2 - np.dot(d2, T) * T
        return N / np.linalg.norm(N)


# ===========================
# PyVista交互可视化
# ===========================
class CenterlineViewer:
    def __init__(self, smoother, smooth_curve, u_values):
        self.smoother = smoother
        self.curve = smooth_curve
        self.u_values = u_values

        self.plotter = pv.Plotter()
        self.arrow_actor = None
        self.text_actor = None

    def build_scene(self):
        # 原始点
        orig = pv.PolyData(self.smoother.points)
        self.plotter.add_mesh(orig, color="red", point_size=10, render_points_as_spheres=True)

        # ========= 原始折线（新增）=========
        raw_line = pv.lines_from_points(self.smoother.points)
        self.plotter.add_mesh(
            raw_line,
            color="black",
            line_width=2,
            label="Original Polyline"
        )
        # 平滑曲线
        line = pv.lines_from_points(self.curve)
        self.plotter.add_mesh(line, color="blue", line_width=3)

        # 开启拾取
        self.plotter.enable_point_picking(
            callback=self.on_pick,
            use_picker=True,
            show_message=False,
            show_point=True
        )

    def on_pick(self, picked_point, picker):
        picked_point = np.array(picked_point)

        # 找最近点对应u
        idx = np.argmin(np.linalg.norm(self.curve - picked_point, axis=1))
        u = self.u_values[idx]

        # 计算方向
        T = self.smoother.tangent(u)
        N = self.smoother.normal(u)

        # 清理旧对象
        if self.arrow_actor:
            self.plotter.remove_actor(self.arrow_actor)
        if self.text_actor:
            self.plotter.remove_actor(self.text_actor)

        # 切向量（绿色）
        self.arrow_actor = self.plotter.add_arrows(
            picked_point.reshape(1, 3),
            T.reshape(1, 3),
            mag=0.5,
            color="green"
        )

        # 法向量（橙色）
        self.plotter.add_arrows(
            picked_point.reshape(1, 3),
            N.reshape(1, 3),
            mag=0.5,
            color="orange"
        )

        # 文本输出
        info = f"Tangent: {np.round(T, 3)}\nNormal: {np.round(N, 3)}"
        self.text_actor = self.plotter.add_text(info, font_size=10)

        print("Picked point:", picked_point)
        print("T:", T)
        print("N:", N)

    def show(self):
        self.build_scene()
        self.plotter.show()


# ===========================
# 示例
# ===========================
if __name__ == "__main__":

    centerline_points = np.array([
        [0, 0, 0],
        [1, 0.2, 0.1],
        [2, 0.5, 0.4],
        [3, 1.2, 0.9],
        [4, 2.0, 1.5],
        [5, 3.0, 2.0],
        [6, 4.0, 2.2],
        [7, 5.0, 2.1],
    ])

    smoother = CenterlineBSplineSmoother(
        smoothing_factor=2.0,
        degree=3
    ).fit(centerline_points)

    curve, u_vals = smoother.evaluate(num=300)

    viewer = CenterlineViewer(smoother, curve, u_vals)
    viewer.show()