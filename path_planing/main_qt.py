# Qt 版 3D 演示入口。

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets


# 允许用户直接运行 python path_planing/main_qt.py。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from path_planing.ui.main_window import MainWindow


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
