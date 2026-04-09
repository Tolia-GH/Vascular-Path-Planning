import heapq
import math

from .node import Node


def euclidean_distance(p1, p2):
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2)


def a_star(start, goal, graph, heuristic=None):
    if heuristic is None:
        heuristic = euclidean_distance

    best_g = {start: 0.0}
    open_heap = []

    start_node = Node(start)
    start_node.g = 0.0
    start_node.h = float(heuristic(start, goal))
    start_node.f = start_node.g + start_node.h
    heapq.heappush(open_heap, start_node)

    while open_heap:
        current = heapq.heappop(open_heap)

        if current.g != best_g.get(current.position, float("inf")):
            continue

        if current.position == goal:
            path = []
            node = current
            while node is not None:
                path.append(node.position)
                node = node.parent
            return path[::-1]

        for neighbor, weight in graph.get(current.position, []):
            tentative_g = current.g + float(weight)
            if tentative_g >= best_g.get(neighbor, float("inf")):
                continue

            best_g[neighbor] = tentative_g
            neighbor_node = Node(neighbor, parent=current)
            neighbor_node.g = tentative_g
            neighbor_node.h = float(heuristic(neighbor, goal))
            neighbor_node.f = neighbor_node.g + neighbor_node.h
            heapq.heappush(open_heap, neighbor_node)

    return None

