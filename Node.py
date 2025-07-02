import heapq
import math
import visualize

# 启发式函数：计算两点之间的欧几里得距离
def euclidean_distance(node1, node2):
    return math.sqrt((node2[0] - node1[0]) ** 2 + (node2[1] - node1[1]) ** 2 + (node2[2] - node1[2]) ** 2)


# Node 类：表示 A* 算法中的节点
class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = float('inf')  # 从起点到当前节点的实际代价
        self.h = 0  # 启发式代价
        self.f = float('inf')  # 总代价 f(n) = g(n) + h(n)

    def __lt__(self, other):
        # 用于 heapq 排序节点，根据 f 值排序
        return self.f < other.f

    def __repr__(self):
        return f"Node({self.position}, f={self.f})"


# A* 算法
def a_star(start, goal, graph):
    open_list = []  # 开放列表，用于存储待处理的节点
    closed_list = []  # 封闭列表，用于存储已处理的节点

    # 初始化起始节点
    start_node = Node(start)
    start_node.g = 0
    start_node.h = euclidean_distance(start, goal)
    start_node.f = start_node.g + start_node.h

    # 将起始节点加入开放列表
    heapq.heappush(open_list, start_node)

    while open_list:
        # 从开放列表中选择 f 值最小的节点
        current_node = heapq.heappop(open_list)

        # 如果当前节点是目标节点，则构造路径
        if current_node.position == goal:
            path = []
            while current_node:
                path.append(current_node.position)
                current_node = current_node.parent
            return path[::-1]  # 返回反向路径

        # 将当前节点加入封闭列表
        closed_list.append(current_node.position)

        # 遍历当前节点的所有相邻节点
        for neighbor, weight in graph[current_node.position]:
            if neighbor in closed_list:
                continue  # 如果相邻节点已经在封闭列表中，跳过

            # 计算从起点到邻居的代价
            tentative_g = current_node.g + weight

            # 如果邻居节点不在开放列表中，或者找到了一条更优的路径
            neighbor_node = Node(neighbor, current_node)
            if tentative_g < neighbor_node.g:
                neighbor_node.g = tentative_g
                neighbor_node.h = euclidean_distance(neighbor, goal)
                neighbor_node.f = neighbor_node.g + neighbor_node.h

                # 将邻居节点加入开放列表
                heapq.heappush(open_list, neighbor_node)

    return None  # 如果没有路径，返回None


# 示例：血管网络和路径规划
vessel_net = {
    # 主主动脉 (Aortic Arch)
    (0.0, 0.0, 0.0): [  # 起始点，坐标为 (x, y, z)
        ((1.0, 2.0, 0.0), 5.0),  # 连接到左锁骨下动脉，权重5.0（单位：cm）
        ((1.0, -2.0, 0.0), 5.0), # 连接到右锁骨下动脉，权重5.0
        ((0.5, 0.5, -2.0), 10.0), # 连接到头臂动脉，权重10.0
        ((0.5, 1.5, -4.0), 15.0), # 连接到腹主动脉，权重15.0
    ],

    # 左锁骨下动脉
    (1.0, 2.0, 0.0): [
        ((0.0, 0.0, 0.0), 5.0),  # 返回主主动脉，权重5.0
        ((1.5, 2.5, -1.0), 8.0),  # 连接到左肾动脉，权重8.0
    ],

    # 右锁骨下动脉
    (1.0, -2.0, 0.0): [
        ((0.0, 0.0, 0.0), 5.0),  # 返回主主动脉，权重5.0
        ((1.5, -2.5, -1.0), 8.0), # 连接到右肾动脉，权重8.0
    ],

    # 头臂动脉
    (0.5, 0.5, -2.0): [
        ((0.0, 0.0, 0.0), 10.0),  # 返回主主动脉，权重10.0
        ((0.8, 0.8, -3.0), 6.0),  # 连接到头部血管，权重6.0
    ],

    # 腹主动脉
    (0.5, 1.5, -4.0): [
        ((0.0, 0.0, 0.0), 15.0),  # 返回主主动脉，权重15.0
        ((0.8, 1.8, -5.0), 12.0), # 连接到左肾动脉，权重12.0
        ((1.2, 1.8, -5.0), 12.0), # 连接到右肾动脉，权重12.0
    ],

    # 左肾动脉
    (1.5, 2.5, -1.0): [
        ((1.0, 2.0, 0.0), 8.0),  # 返回左锁骨下动脉，权重8.0
        ((0.8, 2.5, -2.0), 6.0),  # 连接到左肾，权重6.0
    ],

    # 右肾动脉
    (1.5, -2.5, -1.0): [
        ((1.0, -2.0, 0.0), 8.0),  # 返回右锁骨下动脉，权重8.0
        ((1.2, -2.5, -2.0), 6.0),  # 连接到右肾，权重6.0
    ],

    # 其他肾脏血管、骨盆动脉等可以继续扩展
}


if __name__ == '__main__':

    # 定义起点和目标点
    start = (1.0, -2, 0.0)
    goal = (1.5, 2.5, -1.0)

    # 运行 A* 算法
    path = a_star(start, goal, vessel_net)

    visualize.visualization(vessel_net, path)

    if path:
        print("最短路径:", path)
    else:
        print("没有找到路径")
