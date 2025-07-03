# ✅ 完整修改后的脚本，用于构建以 .fcsv 端点为节点的血管邻接图

from collections import defaultdict
import numpy as np
import pandas as pd
import pyvista as pv
from scipy.spatial import KDTree
import heapq

# -----------------------------
# 第0步：路径配置（不变）
vtk_path = "D:/SIAT/slicer_files/Centerline/Centerline_model.vtk"
fcsv_path = "D:/SIAT/slicer_files/Centerline/Points/Endpoints.fcsv"

# -----------------------------
# 第一步：读取中心线.vtk文件
mesh = pv.read(vtk_path)
centerline_points = mesh.points                         # shape: (N, 3)
lines_raw = mesh.lines.reshape((-1, 3))      # 每行 [2, i1, i2]

# ✅【修改位置 #1】构造完整图（用索引为 key）
full_graph = defaultdict(list)
for line in lines_raw:
    _, i1, i2 = line
    dist = np.linalg.norm(centerline_points[i1] - centerline_points[i2])
    full_graph[i1].append((i2, dist))
    full_graph[i2].append((i1, dist))

# -----------------------------
# 第二步：读取端点坐标（.fcsv）
df = pd.read_csv(fcsv_path, skiprows=3, header=None)
endpoints_xyz = df.iloc[:, [1, 2, 3]].values

# ✅【修改位置 #2】用 KDTree 匹配最近中心线点索引
kdtree = KDTree(centerline_points)
endpoint_indices = kdtree.query(endpoints_xyz)[1]

# ✅ 修复：直接获取所有端点对应坐标
endpoint_coords = [tuple(centerline_points[i]) for i in endpoint_indices]

print("端点匹配到中心线的索引为：", endpoint_indices)

# -----------------------------
# 第三步：定义 Dijkstra 算法

def dijkstra(graph, start_idx):
    dist = {}
    prev = {}
    heap = [(0, start_idx)]
    while heap:
        d, node = heapq.heappop(heap)
        if node in dist:
            continue
        dist[node] = d
        for neighbor, w in graph[node]:
            if neighbor not in dist:
                heapq.heappush(heap, (d + w, neighbor))
                prev[neighbor] = node
    return dist, prev

# -----------------------------
# 第四步：构造 vessel_net（只保留端点为节点）

# ✅【修改位置 #3】构造以端点为节点的邻接表（使用浮点坐标）
vessel_net = defaultdict(list)

for i, start in enumerate(endpoint_indices):
    dist_map, _ = dijkstra(full_graph, start)
    for j, end in enumerate(endpoint_indices):
        if i != j and end in dist_map:
            p1 = endpoint_coords[i]
            p2 = endpoint_coords[j]
            vessel_net[p1].append((p2, round(dist_map[end], 2)))

vessel_net = dict(vessel_net)

print(vessel_net)
# -----------------------------
# 输出部分
print(f"\n最终邻接图节点数: {len(vessel_net)}")
for i, (node, edges) in enumerate(vessel_net.items()):
    print(f"{node} → {edges}")
    if i >= 4:
        break

# 可视化（可选）
# visualization(vessel_net)
