import sys
import XInput

from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QGroupBox
)


# =========================
# 标准 XInput Bitmask（关键修复）
# =========================
XBOX_MASK = {
    "A": 0x1000,
    "B": 0x2000,
    "X": 0x4000,
    "Y": 0x8000,

    "LB": 0x0100,
    "RB": 0x0200,

    "LS": 0x0040,
    "RS": 0x0080,

    "BACK": 0x0020,
    "START": 0x0010,

    "DPAD_UP": 0x0001,
    "DPAD_DOWN": 0x0002,
    "DPAD_LEFT": 0x0004,
    "DPAD_RIGHT": 0x0008
}


def normalize(value):
    return max(-1.0, min(1.0, value / 32767.0))


# =========================
# 摇杆组件
# =========================
class StickWidget(QWidget):

    def __init__(self, title):
        super().__init__()

        self.x = 0.0
        self.y = 0.0
        self.title = title

        self.setMinimumSize(250, 250)

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        center_x = width / 2
        center_y = height / 2

        radius = min(width, height) / 2 - 25

        painter.setPen(QPen(QColor(30, 30, 30), 3))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        painter.setPen(QPen(Qt.lightGray, 1))
        painter.drawLine(int(center_x), int(center_y - radius), int(center_x), int(center_y + radius))
        painter.drawLine(int(center_x - radius), int(center_y), int(center_x + radius), int(center_y))

        dot_x = center_x + self.x * radius
        dot_y = center_y - self.y * radius

        painter.setBrush(QColor(255, 50, 50))
        painter.setPen(Qt.NoPen)

        painter.drawEllipse(QPointF(dot_x, dot_y), 10, 10)

        painter.setPen(Qt.black)

        painter.drawText(10, 20, self.title)
        painter.drawText(10, 40, f"X: {self.x:.2f}")
        painter.drawText(10, 60, f"Y: {self.y:.2f}")


# =========================
# 按键指示器
# =========================
class ButtonIndicator(QPushButton):

    def __init__(self, text):
        super().__init__(text)

        self.setFixedSize(70, 70)

        self.off_style()
        self.setEnabled(False)

    def on_style(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border-radius: 35px;
                border: 2px solid black;
            }
        """)

    def off_style(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: #d0d0d0;
                color: black;
                font-weight: bold;
                border-radius: 35px;
                border: 2px solid black;
            }
        """)

    def set_pressed(self, pressed):
        if pressed:
            self.on_style()
        else:
            self.off_style()


# =========================
# 主窗口
# =========================
class XboxMonitor(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Xbox Controller Real-time Monitor")
        self.resize(1400, 800)

        self.build_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller)
        self.timer.start(16)

    # =========================
    # 创建扳机
    # =========================
    def create_trigger_bar(self, title):

        box = QVBoxLayout()

        label = QLabel(title)

        progress = QProgressBar()
        progress.setRange(0, 255)
        progress.setOrientation(Qt.Vertical)
        progress.setMinimumHeight(300)

        box.addWidget(label)
        box.addWidget(progress)

        container = QWidget()
        container.setLayout(box)

        return container, progress

    # =========================
    # UI布局
    # =========================
    def build_ui(self):

        main_layout = QHBoxLayout(self)

        lt_widget, self.lt_bar = self.create_trigger_bar("LT")
        self.left_stick = StickWidget("LEFT STICK")

        center_box = QVBoxLayout()

        self.btn_lb = ButtonIndicator("LB")
        self.btn_rb = ButtonIndicator("RB")

        self.btn_ls = ButtonIndicator("LS")
        self.btn_rs = ButtonIndicator("RS")

        self.btn_back = ButtonIndicator("BACK")
        self.btn_start = ButtonIndicator("START")

        self.btn_up = ButtonIndicator("↑")
        self.btn_down = ButtonIndicator("↓")
        self.btn_left = ButtonIndicator("←")
        self.btn_right = ButtonIndicator("→")

        self.btn_a = ButtonIndicator("A")
        self.btn_b = ButtonIndicator("B")
        self.btn_x = ButtonIndicator("X")
        self.btn_y = ButtonIndicator("Y")

        shoulder_layout = QHBoxLayout()
        shoulder_layout.addWidget(self.btn_lb)
        shoulder_layout.addStretch()
        shoulder_layout.addWidget(self.btn_rb)

        center_box.addLayout(shoulder_layout)
        center_box.addSpacing(30)

        middle_buttons = QHBoxLayout()
        middle_buttons.addWidget(self.btn_back)
        middle_buttons.addWidget(self.btn_start)

        center_box.addLayout(middle_buttons)
        center_box.addSpacing(40)

        dpad_grid = QGridLayout()
        dpad_grid.addWidget(self.btn_up, 0, 1)
        dpad_grid.addWidget(self.btn_left, 1, 0)
        dpad_grid.addWidget(self.btn_right, 1, 2)
        dpad_grid.addWidget(self.btn_down, 2, 1)

        dpad_group = QGroupBox("D-Pad")
        dpad_group.setLayout(dpad_grid)

        center_box.addWidget(dpad_group)
        center_box.addSpacing(30)

        abxy_grid = QGridLayout()
        abxy_grid.addWidget(self.btn_y, 0, 1)
        abxy_grid.addWidget(self.btn_x, 1, 0)
        abxy_grid.addWidget(self.btn_b, 1, 2)
        abxy_grid.addWidget(self.btn_a, 2, 1)

        abxy_group = QGroupBox("ABXY")
        abxy_group.setLayout(abxy_grid)

        center_box.addWidget(abxy_group)

        center_container = QWidget()
        center_container.setLayout(center_box)

        self.right_stick = StickWidget("RIGHT STICK")
        rt_widget, self.rt_bar = self.create_trigger_bar("RT")

        main_layout.addWidget(lt_widget)
        main_layout.addWidget(self.left_stick)
        main_layout.addWidget(self.btn_ls)
        main_layout.addWidget(center_container)
        main_layout.addWidget(self.right_stick)
        main_layout.addWidget(self.btn_rs)
        main_layout.addWidget(rt_widget)

    # =========================
    # 按键设置（修复版）
    # =========================
    def set_button(self, button, mask, buttons_value):
        pressed = (buttons_value & mask) != 0
        button.set_pressed(pressed)

    # =========================
    # 更新逻辑
    # =========================
    def update_controller(self):

        try:
            state = XInput.get_state(0)
            pad = state.Gamepad
            buttons = pad.wButtons

            # 摇杆
            self.left_stick.set_position(
                normalize(pad.sThumbLX),
                normalize(pad.sThumbLY)
            )

            self.right_stick.set_position(
                normalize(pad.sThumbRX),
                normalize(pad.sThumbRY)
            )

            # 扳机
            self.lt_bar.setValue(pad.bLeftTrigger)
            self.rt_bar.setValue(pad.bRightTrigger)

            # =========================
            # 按键（统一mask修复）
            # =========================
            self.set_button(self.btn_a, XBOX_MASK["A"], buttons)
            self.set_button(self.btn_b, XBOX_MASK["B"], buttons)
            self.set_button(self.btn_x, XBOX_MASK["X"], buttons)
            self.set_button(self.btn_y, XBOX_MASK["Y"], buttons)

            self.set_button(self.btn_lb, XBOX_MASK["LB"], buttons)
            self.set_button(self.btn_rb, XBOX_MASK["RB"], buttons)

            self.set_button(self.btn_ls, XBOX_MASK["LS"], buttons)
            self.set_button(self.btn_rs, XBOX_MASK["RS"], buttons)

            self.set_button(self.btn_back, XBOX_MASK["BACK"], buttons)
            self.set_button(self.btn_start, XBOX_MASK["START"], buttons)

            self.set_button(self.btn_up, XBOX_MASK["DPAD_UP"], buttons)
            self.set_button(self.btn_down, XBOX_MASK["DPAD_DOWN"], buttons)
            self.set_button(self.btn_left, XBOX_MASK["DPAD_LEFT"], buttons)
            self.set_button(self.btn_right, XBOX_MASK["DPAD_RIGHT"], buttons)

        except Exception as e:
            print("Controller error:", e)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = XboxMonitor()
    window.show()

    sys.exit(app.exec_())