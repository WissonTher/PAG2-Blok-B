from gui import Ui_Form
from PyQt5 import QtWidgets, QtCore
import sys

class InterfaceWidget(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = InterfaceWidget()
    window.show()
    sys.exit(app.exec_())