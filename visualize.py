import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def visualization(vessel_net, path=None):
    """
    可视化三维血管网络和路径
    vessel_net: 加权邻接表，表示血管网络
    path: 可选，表示A*算法计算的路径（一个由节点组成的列表）
    """
    # 创建一个3D图形
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # 用于存储所有节点的坐标
    nodes = list(vessel_net.keys())

    # 绘制节点
    for node in nodes:
        ax.scatter(node[0], node[1], node[2], color='b', s=50)  # 绘制节点（蓝色）

    # 绘制边（血管段）
    for node, neighbors in vessel_net.items():
        for neighbor, weight in neighbors:
            ax.plot([node[0], neighbor[0]], [node[1], neighbor[1]], [node[2], neighbor[2]], color='g', linewidth=1)  # 绘制连接的边（绿色）

    # 如果路径存在，绘制路径
    if path:
        # 提取路径中的节点坐标
        path_nodes = [vessel_net[node] for node in path]
        x_path = [node[0] for node in path]
        y_path = [node[1] for node in path]
        z_path = [node[2] for node in path]
        ax.plot(x_path, y_path, z_path, color='r', linewidth=4, marker='o')  # 绘制路径（红色）

    # 设置坐标轴标签
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # 显示图形
    plt.show()

vessel_net = {
    (0, 0, 0): [((1, 0, 0), 5), ((0, 1, 0), 7)],  # 从 (0,0,0) 到 (1,0,0) 的权重为 5， 到 (0,1,0) 的权重为 7
    (1, 0, 0): [((0, 0, 0), 5), ((1, 1, 0), 6)],  # 从 (1,0,0) 到 (0,0,0) 的权重为 5， 到 (1,1,0) 的权重为 6
    (0, 1, 0): [((0, 0, 0), 7), ((1, 1, 0), 3)],  # 从 (0,1,0) 到 (0,0,0) 的权重为 7， 到 (1,1,0) 的权重为 3
    (1, 1, 0): [((1, 0, 0), 6), ((0, 1, 0), 3)]   # 从 (1,1,0) 到 (1,0,0) 的权重为 6， 到 (0,1,0) 的权重为 3
}

# 示例路径
path = [(0, 0, 0), (1, 0, 0), (1, 1, 0)]

# 调用可视化函数
visualization(vessel_net, path)