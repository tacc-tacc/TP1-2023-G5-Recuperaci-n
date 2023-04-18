from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class CustomQLabel(QLabel):
  clicked=pyqtSignal()

  def mousePressEvent(self, ev):
    self.clicked.emit()