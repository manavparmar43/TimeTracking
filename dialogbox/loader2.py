import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import dialogbox.send_data as send_data
class Loader(QWidget):
    success_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)

        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        self.timer.start(15)  # Update angle every 15 milliseconds

        # Remove minimize, maximize, and close buttons
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Set initial size for the widget
        self.setFixedSize(280, 280)  # Adjust the size as needed

        # Create vertical layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Add QLabel to display image
        self.image_label = QLabel(self)
        pixmap = QPixmap(
                # os.path.join(os.getcwd(), "resource/logo.png")
                 os.path.join(self.exe_dir, "_internal", "resource" ,"logo.png")         
                         )
        self.image_label.setPixmap(pixmap.scaled(170, 170, Qt.KeepAspectRatio))
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Add QLabel to display text
        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

        # Set text
        self.message_label.setText("Kindly hold on as your information \n is being transmitted to the server.")
        self.message_label.setStyleSheet("color:red;")

        self.success_signal.connect(self.close)

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        radius = int(side / 2 - 10)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw outer circle
        painter.setPen(QPen(QColor(200, 200, 200), 3))
        painter.drawEllipse(int(self.width() / 2 - radius), int(self.height() / 2 - radius), 2 * radius, 2 * radius)

        # Draw loading arc
        painter.setPen(QPen(QColor(0, 120, 215), 3))
        painter.drawArc(int(self.width() / 2 - radius), int(self.height() / 2 - radius), 2 * radius, 2 * radius,
                        90 * 16, self.angle * 16)

    def update_angle(self):
        self.angle = (self.angle + 1) % 360
        self.update()

        if self.angle == 0:
            self.timer.stop()
            self.success_signal.emit()
            self.show_success_message()

    def moveEvent(self, event):
        # Center the widget on the screen
        screen_geometry = QApplication.desktop().availableGeometry()
        self.move((screen_geometry.width() - self.width()) // 2,
                  (screen_geometry.height() - self.height()) // 2)
        
    def show_success_message(self):
        success_dialog = send_data.Send_data()
        success_dialog.exec_()    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    video_loader = Loader()
    video_loader.show()
    sys.exit(app.exec_())