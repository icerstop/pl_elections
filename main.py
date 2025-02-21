from PySide6.QtWidgets import QApplication
import sys
from gui import ElectionApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ElectionApp()
    window.show()
    sys.exit(app.exec())