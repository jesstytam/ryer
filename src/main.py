import sys

from PyQt6.QtWidgets import QApplication, QWidget

#classes

class Window(QWidget):
    #create window
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("App")
        self.show()

#run

if __name__=="__main__":
    app = QApplication(sys.argv)
    window = Window()
    app.exec()