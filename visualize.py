import matplotlib.pyplot as plt
import mplcursors
from mpl_toolkits.mplot3d import Axes3D

def visualization(vessel_net, path=None):
    """
    可视化三维血管网络和路径
    vessel_net: 加权邻接表，表示血管网络
    path: 可选，表示A*算法计算的路径（一个由节点组成的列表）
    """
    # 创建一个3D图形
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # 用于存储所有节点的坐标
    nodes = list(vessel_net.keys())

    # 存储节点的散点图
    scatters = []


    # 绘制节点
    for node in nodes:
        scatter = ax.scatter(node[0], node[1], node[2], color='k', marker='.', s=30)  # 绘制节点
        scatters.append(scatter)

    # 绘制边（血管段）
    for node, neighbors in vessel_net.items():
        for neighbor, weight in neighbors:
            ax.plot(
                [node[0], neighbor[0]],
                [node[1], neighbor[1]],
                [node[2], neighbor[2]],
                color='k', linewidth=1)  # 绘制连接的边（绿色）

        # 如果路径存在，绘制路径
    if path:
        # 提取路径中的节点坐标
        path_nodes = [vessel_net[node] for node in path]
        x_path = [node[0] for node in path]
        y_path = [node[1] for node in path]
        z_path = [node[2] for node in path]
        ax.plot(x_path, y_path, z_path,
                color='r', linewidth=3)  # 绘制路径（红色）

        # 标记起点
        start = path[0]
        ax.scatter(
            start[0], start[1], start[2],
            color='b', s=60, marker='.', label='起点'
        )
        ax.text(
            start[0], start[1], start[2],
            'S', fontsize=12, verticalalignment='bottom'
        )

        # 标记终点
        end = path[-1]
        ax.scatter(
            end[0], end[1], end[2],
            color='b', s=60, marker='*', label='终点'
        )
        ax.text(
            end[0], end[1], end[2],
            'E', fontsize=12, verticalalignment='bottom'
        )

    # 设置坐标轴标签ppython
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # 使用 mplcursors 添加交互功能
    cursor = mplcursors.cursor(scatters, hover=True)

    # 鼠标悬停显示坐标
    cursor.connect(
        "add",
        lambda sel: sel.annotation.set_text(f'({sel.artist._offsets3d[0][sel.index]}, '
                                            f'{sel.artist._offsets3d[1][sel.index]}, '
                                            f'{sel.artist._offsets3d[2][sel.index]})')
    )

    # 显示图形
    plt.show()

