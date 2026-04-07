# Node 类：表示 A* 算法中的节点数据结构
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