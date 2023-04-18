# Python modules
import sys
from PyQt5 import QtWidgets

# Project modules
from src.ui.inputwindow import Ui_InputDialog

import numpy as np
import scipy.signal as signal

sin = np.sin
cos = np.cos
exp = np.exp
square = signal.square
sawtooth = signal.sawtooth
delta = signal.unit_impulse
heaviside = np.heaviside
gausspulse = signal.gausspulse
chirp = signal.chirp
pi = np.pi
e = np.e
gamma = np.euler_gamma

class InputDialog(QtWidgets.QDialog, Ui_InputDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.input_txt.setEnabled(True)
        self.input_txt.textChanged.connect(self.enableInputFunction)
        self.check_btn.clicked.connect(self.processInputValues)
        self.input_func = None
        self.fs = self.fs_box.value()
        self.dsh = self.dsh_box.value()/100
        self.dla = self.dla_box.value()/100
        self.time = []

    def getInputTitle(self):
        return self.resp_name_txt.text()

    def getInputExpression(self):
        return self.input_txt.text()

    def enableInputFunction(self, txt):
        if txt != '':
            self.input_txt.setEnabled(True)
    
    def validateInput(self):
        try:
            self.fs = self.fs_box.value()
            self.dsh = self.dsh_box.value()/100
            self.dla = self.dla_box.value()/100
            if (self.minbox.value() < 0 or self.maxbox.value() < 0 or self.minbox.value() >= self.maxbox.value()):
                return False
            self.time = np.arange(self.minbox.value(), self.maxbox.value(), 1/(100*self.fs))
            t = self.time #necesario para el eval()
            self.input_func = eval(self.input_txt.text())
        except Exception:
            return False
        return True

    def processInputValues(self):
        if self.validateInput():
            self.error_label.clear()
            self.accept()
        else:
            self.error_label.setText("La expresión y/o los límites no son válidos")