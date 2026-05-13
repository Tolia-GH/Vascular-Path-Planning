# 集成测试：KDTree + Viewer3D + MainWindow 规划闭环（离屏）
import sys

# ---- 1. 导入 ----
print("=== 1. 导入检查 ===")
from path_planing.utils.kd_tree import KDTreeSnapper
from path_planing.ui.viewer_3d import Viewer3D
from path_planing.ui.main_window import MainWindow
from path_planing.ui.control_panel import ControlPanel
from path_planing.ui.path_info_panel import PathInfoPanel
from path_planing.ui import __all__ as ui_all
from path_planing.engine import GraphLoader, PathPlanner, PathAnalyzer
print(f"ui.__all__ = {ui_all}")
print("IMPORTS_OK")

# ---- 2. KDTree 单元测试 ----
print("\n=== 2. KDTree 单元测试 ===")
nodes = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (10.0, 10.0, 0.0), (5.0, 5.0, 5.0)]
kd = KDTreeSnapper()
kd.build(nodes)
node, dist = kd.find_nearest((5.1, 5.2, 4.9))
print(f"query=(5.1,5.2,4.9) -> node={node} dist_mm={dist:.4f}")
assert dist < 1.0, f"KDTree dist too large: {dist}"
print("KDTREE_OK")

# ---- 3. 管线集成 ----
print("\n=== 3. 数据加载 + 规划管线 ===")
from pathlib import Path

root = Path(__file__).resolve().parent
graph_path = root / "source" / "graphs" / "centerline_vessel_net.json"
assert graph_path.exists(), f"Graph not found: {graph_path}"

loader = GraphLoader()
loader.load(graph_path)
print(f"graph_nodes={loader.node_count} edges={loader.edge_count}")

planner = PathPlanner()
planner.set_graph(loader.graph)

analyzer = PathAnalyzer()

kd_tree = KDTreeSnapper()
kd_tree.build(loader.nodes)

# 取一对端点测试
nodes_list = list(loader.nodes)
start = tuple(float(x) for x in nodes_list[1000])
goal = tuple(float(x) for x in nodes_list[5000])
print(f"start={start}")
print(f"goal={goal}")

import time
t0 = time.perf_counter()
path = planner.plan(start, goal)
elapsed_ms = (time.perf_counter() - t0) * 1000.0
assert path is not None and len(path) >= 2, "Path is None or too short"
print(f"path_nodes={len(path)} elapsed_ms={elapsed_ms:.2f}")

result = analyzer.analyze(path)
print(f"length_mm={result.total_length_mm:.2f} feasibility={result.feasibility}")

# ---- 4. 面板测试 ----
print("\n=== 4. 面板测试 ===")
from PyQt5 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

cp = ControlPanel()
assert cp.mode == "idle"
assert cp.start_node is None
assert cp.goal_node is None
assert not cp.is_ready_to_plan
print("ControlPanel initial state OK")

cp.set_mode_start()
assert cp.mode == "start"
cp.set_pick_result(
    coords=(10.1, 20.2, 30.3),
    snapped_node=(10.0, 20.0, 30.0),
    snap_distance_mm=1.5,
)
assert cp.mode == "idle", f"Expected idle after pick, got {cp.mode}"
assert cp.start_node == (10.0, 20.0, 30.0)
assert not cp.is_ready_to_plan  # 还缺终点
print("ControlPanel start pick OK")

cp.set_mode_goal()
cp.set_pick_result(
    coords=(40.1, 50.2, 60.3),
    snapped_node=(40.0, 50.0, 60.0),
    snap_distance_mm=0.8,
)
assert cp.mode == "idle"
assert cp.goal_node == (40.0, 50.0, 60.0)
assert cp.is_ready_to_plan
print("ControlPanel goal pick OK")

cp.clear_all()
assert cp.start_node is None and cp.goal_node is None
assert not cp.is_ready_to_plan
print("ControlPanel clear OK")

pi = PathInfoPanel()
pi.update_from_summary(result.summary, elapsed_ms=elapsed_ms)
print(f"PathInfoPanel: length={pi._length_value.text()} feasibility={pi._feasibility_value.text()}")
assert pi._length_value.text() != "--"
print("PathInfoPanel OK")

# ---- 5. Viewer3D 点选模拟 ----
print("\n=== 5. Viewer3D 点选回调验证 ===")
# 用 viewer_3d.point_picked 信号触发 -- 之前已确认 viewer_3d 可以构造
viewer = Viewer3D(off_screen=True)
print(f"Viewer3D created, signals=[{', '.join(s.decode() if isinstance(s, bytes) else s for s in dir(viewer) if 'pick' in s.lower())}]")
# 连接信号虚拟槽
picked_received = []
def on_pick(coords):
    picked_received.append(coords)
viewer.point_picked.connect(on_pick)
# 模拟 pick callback -- 内部 _on_pick 预留给 PyVista pick_callback
# 当前 Viewer3D 的 point_picked 信号由 enable_picking 里的追踪器触发，
# 这里仅验证信号连接有效
viewer.point_picked.emit((100.0, 200.0, 300.0))
assert len(picked_received) == 1
assert picked_received[0] == (100.0, 200.0, 300.0)
print(f"Viewer3D pick signal OK: received={picked_received}")

viewer.close()

print("\n=== ALL TESTS PASSED ===")