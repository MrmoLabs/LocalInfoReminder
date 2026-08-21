from PyQt6.QtCore import Qt
try:
    print(f"TopEdge type: {type(Qt.Edge.TopEdge)}")
    print(f"Top | Left: {Qt.Edge.TopEdge | Qt.Edge.LeftEdge}")
    print("OR operation successful")
except Exception as e:
    print(f"OR operation failed: {e}")

try:
    val = int(Qt.Edge.TopEdge) | int(Qt.Edge.LeftEdge)
    edge = Qt.Edge(val)
    print(f"Cast from int {val} successful: {edge}")
except Exception as e:
    print(f"Cast from int failed: {e}")
