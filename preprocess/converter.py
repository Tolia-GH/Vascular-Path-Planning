# 你的 Node 类
class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = float('inf')
        self.h = 0
        self.f = float('inf')

    def __lt__(self, other):
        return self.f < other.f

    def __repr__(self):
        return f"Node({self.position}, f={self.f})"

# 原始血管邻接表
vessel_net = {
    (0.0, 0.0, 0.0): [((1.0, 2.0, 0.0), 5.0), ((1.0, -2.0, 0.0), 5.0), ((0.5, 0.5, -2.0), 10.0), ((0.5, 1.5, -4.0), 15.0)],
    (1.0, 2.0, 0.0): [((0.0, 0.0, 0.0), 5.0), ((1.5, 2.5, -1.0), 8.0)],
    (1.0, -2.0, 0.0): [((0.0, 0.0, 0.0), 5.0), ((1.5, -2.5, -1.0), 8.0)],
    (0.5, 0.5, -2.0): [((0.0, 0.0, 0.0), 10.0), ((0.8, 0.8, -3.0), 6.0)],
    (0.5, 1.5, -4.0): [((0.0, 0.0, 0.0), 15.0), ((0.8, 1.8, -5.0), 12.0), ((1.2, 1.8, -5.0), 12.0)],
    (1.5, 2.5, -1.0): [((1.0, 2.0, 0.0), 8.0), ((0.8, 2.5, -2.0), 6.0)],
    (1.5, -2.5, -1.0): [((1.0, -2.0, 0.0), 8.0), ((1.2, -2.5, -2.0), 6.0)],
}

# 第一步：收集所有唯一坐标
all_positions = set(vessel_net.keys())
for neighbors in vessel_net.values():
    for pos, weight in neighbors:
        all_positions.add(pos)

# 第二步：为每个坐标创建 Node，并按列表顺序存储
vessel_nodes = []
position_to_index = {}

for idx, pos in enumerate(all_positions):
    vessel_nodes.append(Node(pos))
    position_to_index[pos] = idx

# 第三步：用 Node 索引重新构建邻接表
vessel_edges = {}

for src_pos, neighbors in vessel_net.items():
    src_idx = position_to_index[src_pos]
    vessel_edges[src_idx] = []
    for tgt_pos, weight in neighbors:
        tgt_idx = position_to_index[tgt_pos]
        vessel_edges[src_idx].append((tgt_idx, weight))

print(vessel_nodes)
print(vessel_edges)
# # 打印结果示例
# print("vessel_nodes 列表:")
# for i, node in enumerate(vessel_nodes):
#     print(f"Index: {i}, Node: {node}")
#
# print("\n邻接表（索引形式）:")
# for src_idx, neighbors in vessel_edges.items():
#     print(f"{src_idx} -> {neighbors}")
