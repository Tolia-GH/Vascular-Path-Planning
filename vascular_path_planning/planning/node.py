class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = float("inf")
        self.h = 0.0
        self.f = float("inf")

    def __lt__(self, other):
        return self.f < other.f

    def __repr__(self):
        return f"Node({self.position}, f={self.f})"

