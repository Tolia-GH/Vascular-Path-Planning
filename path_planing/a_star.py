import math
import heapq
from node import Node

# 启发式函数：计算两点之间的欧几里得距离
def euclidean_distance(node1, node2):
    return math.sqrt((node2[0] - node1[0]) ** 2 + (node2[1] - node1[1]) ** 2 + (node2[2] - node1[2]) ** 2)


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