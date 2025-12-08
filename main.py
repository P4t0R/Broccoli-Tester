import sys
import signal
from PySide6.QtWidgets import QApplication
from ui import MainWindow


def main():
    # permitir cerrar con Ctrl+C desde terminal
    signal.signal(signal.SIGINT, lambda *args: QApplication.quit())

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    try:
        return_code = app.exec()
    except Exception as e:
        print("Error en la aplicación:", e)
        return_code = 1
    sys.exit(return_code)


if __name__ == "__main__":
    main()
