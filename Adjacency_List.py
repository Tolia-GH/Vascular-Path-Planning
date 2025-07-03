from collections import defaultdict
from visualize import visualization
import numpy as np
import pandas as pd
import pyvista as pv
from scipy.spatial import KDTree

# 路径配置（修改为你本地的路径）
vtk_path = "D:/SIAT/slicer_files/Centerline/Centerline_model.vtk"       # 中心线路径
fcsv_path = "D:/SIAT/slicer_files/Centerline/Points/Endpoints.fcsv"      # 端点坐标

# ---------------------------------------
# 第一步：读取中心线.vtk文件
mesh = pv.read(vtk_path)
centerline_points = mesh.points                         # shape: (N, 3)
lines_raw = mesh.lines.reshape((-1, 3))      # 每行 [2, i1, i2]

# 构造边列表，节点为三维坐标
edges = []
for line in lines_raw:
    _, i1, i2 = line
    p1 = tuple(centerline_points[i1])
    p2 = tuple(centerline_points[i2])
    dist = np.linalg.norm(centerline_points[i1] - centerline_points[i2])
    edges.append((p1, p2, round(dist, 2)))


# ---------------------------------------
# 第二步：读取端点坐标（.fcsv）
df = pd.read_csv(fcsv_path, skiprows=3, header=None)
# 提取第2、3、4列（索引为1, 2, 3），分别为 x, y, z 坐标
endpoints_xyz = df.iloc[:, [1, 2, 3]].values

# 打印结果确认
print("端点坐标（x, y, z）：\n", endpoints_xyz)
print("shape：", endpoints_xyz.shape)
# ---------------------------------------
# 第三步：将端点匹配到最近的中心线点索引
tree = KDTree(centerline_points)
endpoint_indices = tree.query(endpoints_xyz)[1]  # 返回最近点的索引列表
endpoint_coords = [tuple(centerline_points[i]) for i in endpoint_indices]   # 构造 endpoint_indices 映射后的节点坐标
endpoint_set = set(endpoint_indices)


print("端点匹配到中心线的索引为：", endpoint_indices)

# 可选：设置方向（从 endpoint_indices[0] 指向 endpoint_indices[1]）

# ---------------------------------------
# 第四步：构造符合要求的邻接表 vessel_net（以坐标为 key）
vessel_net = defaultdict(list)

for line in lines_raw:
    _, i1, i2 = line
    if i1 in endpoint_set and i2 in endpoint_set:
        p1 = tuple(centerline_points[i1])
        p2 = tuple(centerline_points[i2])
        dist = np.linalg.norm(centerline_points[i1] - centerline_points[i2])
        vessel_net[p1].append((p2, round(dist, 2)))

# 可选转为普通字典
vessel_net = dict(vessel_net)

print("邻接表结构为：", vessel_net)

# visualization(vessel_net)
