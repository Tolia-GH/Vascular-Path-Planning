import numpy as np
from scipy import interpolate
import pyvista as pv


class CenterlineBSplineSmoother:
    """基于 SciPy B-spline 的三维中心线平滑器。

    该类负责将离散中心线点拟合为参数曲线，并提供曲线重采样、
    切向量与法向量计算能力。
    """

    def __init__(self, smoothing_factor=0.0, degree=3):
        """初始化平滑器参数。

        Args:
            smoothing_factor: 样条平滑因子，值越大通常越平滑。
            degree: B 样条阶数，常用 3（立方样条）。
        """
        self.s = smoothing_factor
        self.k = degree

    def fit(self, points):
        """拟合输入三维点序列。

        Args:
            points: 形如 (N, 3) 的点集，N 至少为 4。

        Returns:
            CenterlineBSplineSmoother: 返回自身，便于链式调用。
        """
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
        """对已拟合样条进行重采样。

        Args:
            num: 采样点数量。

        Returns:
            tuple[np.ndarray, np.ndarray]:
                - 平滑曲线点坐标，形如 (num, 3)
                - 参数 u 的采样序列，范围 [0, 1]
        """
        u_new = np.linspace(0, 1, num)
        x, y, z = interpolate.splev(u_new, self.tck)
        return np.vstack([x, y, z]).T, u_new

    # ========= 关键：方向计算 =========

    def tangent(self, u):
        """计算参数位置 u 处的单位切向量。

        Args:
            u: 曲线参数，通常在 [0, 1]。

        Returns:
            np.ndarray: 归一化后的切向量，形如 (3,)。
        """
        dx, dy, dz = interpolate.splev(u, self.tck, der=1)
        v = np.array([dx, dy, dz])
        return v / np.linalg.norm(v)

    def normal(self, u):
        """计算参数位置 u 处的单位法向量。

        Args:
            u: 曲线参数，通常在 [0, 1]。

        Returns:
            np.ndarray: 归一化后的法向量，形如 (3,)。
        """
        d1 = np.array(interpolate.splev(u, self.tck, der=1))
        d2 = np.array(interpolate.splev(u, self.tck, der=2))

        T = d1 / np.linalg.norm(d1)

        N = d2 - np.dot(d2, T) * T
        return N / np.linalg.norm(N)


def iter_polydata_polyline_point_ids(polydata: pv.PolyData):
    """迭代 PolyData 中每条折线对应的点索引列表。

    Args:
        polydata: 包含 lines 编码的一维数组结构的 PolyData。

    Yields:
        list[int]: 单条折线的点索引序列。
    """
    lines = np.asarray(polydata.lines, dtype=np.int64)
    i = 0
    n_total = int(lines.shape[0])
    while i < n_total:
        n = int(lines[i])
        i += 1
        if n <= 0:
            continue
        ids = lines[i:i + n]
        i += n
        yield ids.tolist()


def smooth_centerline_polydata_bspline(
    centerline,
    smoothing_factor: float = 0.0000001,
    degree: int = 3,
    num_samples: int = 300,
    enforce_endpoints: bool = True,
    method: str = "constrained",
    n_control_points: int | None = None,
    tangent_weight: float | None = None,
    curvature_weight: float | None = None,
):
    """对中心线 PolyData 按线段执行 B 样条平滑并重建输出 PolyData。

    支持两种平滑模式：
    - ``splprep``: 直接调用 SciPy 样条拟合。
    - ``constrained``: 采用端点约束与平滑正则的约束样条求解。

    Args:
        centerline: 输入中心线，需可转换为 ``pv.PolyData`` 且包含 lines。
        smoothing_factor: 平滑强度参数。
        degree: 样条阶数。
        num_samples: 每条线段重采样点数。
        enforce_endpoints: 是否强制保持每段首末点不变。
        method: 平滑算法，``"constrained"`` 或 ``"splprep"``。
        n_control_points: 约束样条控制点数，``None`` 时自动估计。
        tangent_weight: 端点切向约束权重，``None`` 时自动估计。
        curvature_weight: 端点曲率约束权重，``None`` 时自动估计。

    Returns:
        vtk.vtkPolyData: 平滑后的中心线 PolyData。
    """
    import vtk

    centerline_dataset = pv.wrap(centerline)
    if isinstance(centerline_dataset, pv.PolyData):
        centerline_poly = centerline_dataset
    else:
        if hasattr(centerline_dataset, "extract_geometry"):
            centerline_poly = centerline_dataset.extract_geometry()
        else:
            raise TypeError("centerline 需要是包含折线的 PolyData，或可提取几何的 PyVista 数据对象")

    if not isinstance(centerline_poly, pv.PolyData):
        raise TypeError("centerline 需要是 PolyData（包含 lines/points）")
    if not hasattr(centerline_poly, "lines") or centerline_poly.lines is None:
        raise ValueError("输入数据不包含 lines，无法按线段进行平滑")

    def _chord_length_u(points: np.ndarray):
        """按弦长参数化生成归一化 u 序列。"""
        d = np.linalg.norm(np.diff(points, axis=0), axis=1)
        d = np.where(np.isfinite(d), d, 0.0)
        s = np.concatenate([[0.0], np.cumsum(d)])
        total = float(s[-1])
        if total <= 0.0:
            return np.linspace(0.0, 1.0, points.shape[0])
        u = s / total
        u[0] = 0.0
        u[-1] = 1.0
        return u

    def _open_uniform_knots(n_ctrl: int, k: int):
        """生成开区间均匀节点向量。"""
        n_internal = n_ctrl - k - 1
        if n_internal <= 0:
            return np.array([0.0] * (k + 1) + [1.0] * (k + 1), dtype=float)
        internal = np.linspace(0.0, 1.0, n_internal + 2)[1:-1]
        return np.concatenate(
            [np.zeros(k + 1, dtype=float), internal.astype(float), np.ones(k + 1, dtype=float)]
        )

    def _design_matrix(u: np.ndarray, knots: np.ndarray, k: int, deriv: int = 0):
        """构建 B 样条基函数设计矩阵（可选导数阶）。"""
        from scipy.interpolate import BSpline

        if deriv == 0 and hasattr(BSpline, "design_matrix"):
            m = BSpline.design_matrix(u, knots, k, extrapolate=False)
            return m.toarray()

        n_ctrl = int(len(knots) - k - 1)
        a = np.zeros((u.shape[0], n_ctrl), dtype=float)
        for j in range(n_ctrl):
            c = np.zeros(n_ctrl, dtype=float)
            c[j] = 1.0
            b = BSpline(knots, c, k, extrapolate=False)
            if deriv > 0:
                b = b.derivative(deriv)
            a[:, j] = b(u)
        return a

    def _constrained_bspline_points(points: np.ndarray):
        """基于端点约束和正则项求解平滑曲线点集。"""
        from scipy.interpolate import BSpline

        pts = np.asarray(points, dtype=float)
        if pts.shape[0] < 2:
            return pts

        k = int(degree)
        if pts.shape[0] <= k:
            k = max(1, int(pts.shape[0] - 1))

        if pts.shape[0] < 4 or k < 2:
            return pts

        n_ctrl = n_control_points
        if n_ctrl is None:
            n_ctrl = max(k + 1, min(int(pts.shape[0]), max(8, int(pts.shape[0] // 3))))
        n_ctrl = int(n_ctrl)
        n_ctrl = max(k + 1, min(n_ctrl, int(pts.shape[0])))

        u = _chord_length_u(pts)
        knots = _open_uniform_knots(n_ctrl, k)

        b0 = _design_matrix(u, knots, k, deriv=0)
        a = b0[:, 1:-1]
        y = pts.copy()
        p0 = pts[0]
        p1 = pts[-1]
        y -= b0[:, [0]] * p0
        y -= b0[:, [-1]] * p1

        lam = float(smoothing_factor)
        d2 = np.zeros((n_ctrl - 2, n_ctrl), dtype=float)
        for r in range(n_ctrl - 2):
            d2[r, r] = 1.0
            d2[r, r + 1] = -2.0
            d2[r, r + 2] = 1.0
        d2_inner = d2[:, 1:-1]

        gtg = a.T @ a
        rhs = a.T @ y

        if lam > 0.0:
            gtg = gtg + lam * (d2_inner.T @ d2_inner)

        tw = tangent_weight
        cw = curvature_weight
        if tw is None:
            tw = 10.0 * lam if lam > 0.0 else 1.0
        if cw is None:
            cw = 1.0 * lam if lam > 0.0 else 0.1

        u_eps = 1e-8
        u0 = np.array([0.0 + u_eps], dtype=float)
        u1 = np.array([1.0 - u_eps], dtype=float)

        d1_0 = _design_matrix(u0, knots, k, deriv=1).reshape(-1)
        d1_1 = _design_matrix(u1, knots, k, deriv=1).reshape(-1)
        d2_0 = _design_matrix(u0, knots, k, deriv=2).reshape(-1)
        d2_1 = _design_matrix(u1, knots, k, deriv=2).reshape(-1)

        def _endpoint_tangent(pts_local: np.ndarray, start: bool):
            """估计线段起点或终点处的离散切向量。"""
            if pts_local.shape[0] < 3:
                v = pts_local[-1] - pts_local[0]
                return v
            if start:
                i = min(3, pts_local.shape[0] - 1)
                du = float(u[i] - u[0])
                if du <= 0.0:
                    return pts_local[i] - pts_local[0]
                return (pts_local[i] - pts_local[0]) / du
            j = max(pts_local.shape[0] - 4, 0)
            du = float(u[-1] - u[j])
            if du <= 0.0:
                return pts_local[-1] - pts_local[j]
            return (pts_local[-1] - pts_local[j]) / du

        if tw and tw > 0.0:
            t0 = _endpoint_tangent(pts, start=True)
            t1 = _endpoint_tangent(pts, start=False)

            d1_0_inner = d1_0[1:-1]
            d1_1_inner = d1_1[1:-1]

            r0 = t0 - (d1_0[0] * p0 + d1_0[-1] * p1)
            r1 = t1 - (d1_1[0] * p0 + d1_1[-1] * p1)

            gtg = gtg + tw * (np.outer(d1_0_inner, d1_0_inner) + np.outer(d1_1_inner, d1_1_inner))
            rhs = rhs + tw * (np.outer(d1_0_inner, r0) + np.outer(d1_1_inner, r1))

        if cw and cw > 0.0:
            d2_0_inner = d2_0[1:-1]
            d2_1_inner = d2_1[1:-1]

            r0 = - (d2_0[0] * p0 + d2_0[-1] * p1)
            r1 = - (d2_1[0] * p0 + d2_1[-1] * p1)

            gtg = gtg + cw * (np.outer(d2_0_inner, d2_0_inner) + np.outer(d2_1_inner, d2_1_inner))
            rhs = rhs + cw * (np.outer(d2_0_inner, r0) + np.outer(d2_1_inner, r1))

        p_inner = np.linalg.solve(gtg, rhs)
        ctrl = np.empty((n_ctrl, 3), dtype=float)
        ctrl[0] = p0
        ctrl[-1] = p1
        ctrl[1:-1] = p_inner

        u_new = np.linspace(0.0, 1.0, int(num_samples))
        spl_x = BSpline(knots, ctrl[:, 0], k, extrapolate=False)
        spl_y = BSpline(knots, ctrl[:, 1], k, extrapolate=False)
        spl_z = BSpline(knots, ctrl[:, 2], k, extrapolate=False)
        curve = np.vstack([spl_x(u_new), spl_y(u_new), spl_z(u_new)]).T
        curve[0] = p0
        curve[-1] = p1
        return curve

    points_out = vtk.vtkPoints()
    lines_out = vtk.vtkCellArray()

    for ids in iter_polydata_polyline_point_ids(centerline_poly):
        segment_points = np.asarray(centerline_poly.points[np.asarray(ids, dtype=np.int64)], dtype=float)
        if segment_points.shape[0] < 2:
            continue

        k = int(degree)
        if segment_points.shape[0] <= k:
            k = max(1, int(segment_points.shape[0] - 1))

        if segment_points.shape[0] < 4 or k < 2:
            smoothed_points = segment_points
        else:
            if method == "splprep":
                smoother = CenterlineBSplineSmoother(
                    smoothing_factor=float(smoothing_factor),
                    degree=int(k),
                ).fit(segment_points)
                smoothed_points, _ = smoother.evaluate(num=int(num_samples))
            else:
                smoothed_points = _constrained_bspline_points(segment_points)

        if (
            enforce_endpoints
            and smoothed_points is not segment_points
            and isinstance(smoothed_points, np.ndarray)
            and smoothed_points.shape[0] >= 2
        ):
            smoothed_points[0] = segment_points[0]
            smoothed_points[-1] = segment_points[-1]

        point_ids = vtk.vtkIdList()
        for p in smoothed_points:
            pid = points_out.InsertNextPoint(float(p[0]), float(p[1]), float(p[2]))
            point_ids.InsertNextId(pid)

        lines_out.InsertNextCell(point_ids)

    poly_out = vtk.vtkPolyData()
    poly_out.SetPoints(points_out)
    poly_out.SetLines(lines_out)
    poly_out.Modified()
    return poly_out


# ===========================
# PyVista交互可视化
# ===========================
class CenterlineViewer:
    """用于展示原始点、原始折线与平滑曲线的交互式可视化器。"""

    def __init__(self, smoother, smooth_curve, u_values):
        """初始化可视化状态。

        Args:
            smoother: 已拟合的 ``CenterlineBSplineSmoother`` 实例。
            smooth_curve: 平滑后的曲线点。
            u_values: 与平滑曲线点对应的参数序列。
        """
        self.smoother = smoother
        self.curve = smooth_curve
        self.u_values = u_values

        self.plotter = pv.Plotter()
        self.arrow_actor = None
        self.text_actor = None

    def build_scene(self):
        """构建可视化场景并启用点拾取回调。"""
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
        """点拾取回调：显示拾取点的切向量、法向量及文本信息。

        Args:
            picked_point: 被拾取点坐标。
            picker: PyVista/VTK 拾取器对象（当前未直接使用）。
        """
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
        """显示交互式可视化窗口。"""
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
