# PyQt5 modules
from math import inf
from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QColorDialog, QFileDialog, QDialog, QStyle
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QBrush, QColorConstants, QPalette

# Project modules
from src.ui.mainwindow import Ui_MainWindow
from src.package.Dataset import Dataset
from src.package.Dataline import Dataline
import src.package.Filter as Filter
import src.package.transfer_function as TF
from src.package.Sampler import Sampler
from src.package.Filter import AnalogFilter
from src.widgets.input_dialog import InputDialog

import scipy.signal as signal
import matplotlib.ticker as ticker
from mplcursors import cursor, Selection

import numpy as np
from pyparsing.exceptions import ParseSyntaxException

MARKER_STYLES = {'None': '', 'Point': '.',  'Pixel': ',',  'Circle': 'o',  'Triangle down': 'v',  'Triangle up': '^',  'Triangle left': '<',  'Triangle right': '>',  'Tri down': '1',  'Tri up': '2',  'Tri left': '3',  'Tri right': '4',
                 'Octagon': '8',  'Square': 's',  'Pentagon': 'p',  'Plus (filled)': 'P',  'Star': '*',  'Hexagon': 'h',  'Hexagon alt.': 'H',  'Plus': '+',  'x': 'x',  'x (filled)': 'X',  'Diamond': 'D',  'Diamond (thin)': 'd',  'Vline': '|',  'Hline': '_'}
LINE_STYLES = {'None': '', 'Solid': '-',
               'Dashed': '--', 'Dash-dot': '-.', 'Dotted': ':'}

POLE_COLOR = '#FF0000'
POLE_SEL_COLOR = '#00FF00'
ZERO_COLOR = '#0000FF'
ZERO_SEL_COLOR = '#00FF00'

TEMPLATE_FACE_COLOR = '#ffcccb'
TEMPLATE_EDGE_COLOR = '#ef9a9a'
ADD_TEMPLATE_FACE_COLOR = '#c8e6c9'
ADD_TEMPLATE_EDGE_COLOR = '#a5d6a7'

SHOW_PZ_IN_HZ = True
PZ_XLABEL = f'$\sigma$ [1/s]' if SHOW_PZ_IN_HZ else '$\sigma$ ($rad/s$)'
PZ_YLABEL = f'$jf$ [Hz]' if SHOW_PZ_IN_HZ else '$j\omega$ ($rad/s$)'
F_TO_W = 2*np.pi
W_TO_F = 1/F_TO_W
SING_B_TO_F = W_TO_F if SHOW_PZ_IN_HZ else 1
SING_F_TO_B = F_TO_W if SHOW_PZ_IN_HZ else 1

ENTRADA, FAA, SH, LLA, FR = range(5)
FILTER_INDEXES = [FAA, FR]
SAMPLER_INDEXES = [ENTRADA, SH, LLA]


tb = QBrush(QColorConstants.Transparent)
TRANSPARENTE = QPalette(tb, tb, tb, tb, tb, tb, tb, tb, tb)
NO_TRANSPARENTE = QPalette()

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.datasets = []
        self.datalines = []

        self.selected_dataset_data = {}
        self.selected_dataline_data = {}

        self.dataline_list.currentItemChanged.connect(
            self.populateSelectedDatalineDetails)
        self.dl_transform_cb.activated.connect(self.updateSelectedDataline)
        self.dl_xdata_cb.activated.connect(self.updateSelectedDataline)
        self.dl_xscale_sb.valueChanged.connect(self.updateSelectedDataline)
        self.dl_xoffset_sb.valueChanged.connect(self.updateSelectedDataline)
        self.dl_ydata_cb.activated.connect(self.updateSelectedDataline)
        self.dl_yscale_sb.valueChanged.connect(self.updateSelectedDataline)
        self.dl_yoffset_sb.valueChanged.connect(self.updateSelectedDataline)
        self.dl_color_edit.textEdited.connect(self.updateSelectedDataline)
        self.dl_style_cb.activated.connect(self.updateSelectedDataline)
        self.dl_linewidth_sb.valueChanged.connect(self.updateSelectedDataline)
        self.dl_marker_cb.activated.connect(self.updateSelectedDataline)
        self.dl_markersize_sb.valueChanged.connect(self.updateSelectedDataline)

        self.dl_color_pickerbtn.clicked.connect(self.openColorPicker)

        self.respd = InputDialog()
        self.chg_input.clicked.connect(self.openInputDialog)
        self.respd.accepted.connect(self.processInputValues)

        self.plt_labelsize_sb.valueChanged.connect(self.updatePlot)
        self.plt_legendsize_sb.valueChanged.connect(self.updatePlot)
        self.plt_ticksize_sb.valueChanged.connect(self.updatePlot)
        self.plt_titlesize_sb.valueChanged.connect(self.updatePlot)
        self.plt_autoscale.clicked.connect(self.autoscalePlots)
        self.plt_legendpos.activated.connect(self.updatePlot)
        self.plt_grid.stateChanged.connect(self.updatePlot)

        self.sdis_faa.setVisible(False)
        self.sdis_sh.setVisible(False)
        self.sdis_lla.setVisible(False)
        self.sdis_fr.setVisible(False)

        self.sdis_faa.clicked.connect(self.toggleEnableFAA)
        self.sen_faa.clicked.connect(self.toggleEnableFAA)
        self.sdis_sh.clicked.connect(self.toggleEnableSH)
        self.sen_sh.clicked.connect(self.toggleEnableSH)
        self.sdis_lla.clicked.connect(self.toggleEnableLLA)
        self.sen_lla.clicked.connect(self.toggleEnableLLA)
        self.sdis_fr.clicked.connect(self.toggleEnableFR)
        self.sen_fr.clicked.connect(self.toggleEnableFR)

        self.chk_faa.clicked.connect(self.updateEnables)
        self.chk_sh.clicked.connect(self.updateEnables)
        self.chk_lla.clicked.connect(self.updateEnables)
        self.chk_fr.clicked.connect(self.updateEnables)

        self.plots_canvases = [
            [self.plot_vi_t, self.plot_vi_f],
            [self.plot_va_t, self.plot_va_f],
            [self.plot_vb_t, self.plot_vb_f],
            [self.plot_vc_t, self.plot_vc_f],
            [self.plot_vo_t, self.plot_vo_f],
            [self.plot_vovi_t, self.plot_vovi_f]
        ]

        self.dl_titles = [
            ['Vi(t)', 'Vi(f)'],
            ['Va(t)', 'Ha(f)'],
            ['Vb(t)', 'Vb(f)'],
            ['Vc(t)', 'Vc(t)'],
            ['Vo(t)', 'Ho(f)'],
            ['Vi(t)', 'Vi(f)'],
            ['Vo(t)', 'Vo(f)']
        ]

        self.filsamplers = []
        self.enabled = [True, True, True, True, True]

        self.input = None
        self.t = None
        self.f = None

        self.chg_filter_btn.clicked.connect(self.changeSelectedFilter)
        self.addSampler('No')
        self.addFilter('Anti-alias')
        self.addSampler('SH')
        self.addSampler('Llave')
        self.addFilter('Recuperador')
        self.updateSamplers(noPlot=True)
        self.createDatasets()
        self.createDatalines()
        self.openInputDialog()

    # Vuelve a plotear
    # iteramos con la señal intermedia, si está activado la pasamos por el bloque
    # después se generan los dataset con los dataline y se manda a plotear

    def rePlotAll(self):
        intermediateSignal = self.input

        for i in range(5):
            self.datasets[i].origin = self.filsamplers[i-i]
            if not self.enabled[i]:
                if i-1 in SAMPLER_INDEXES:
                    self.datasets[i].parse_from_sampler(self.filsamplers[i-1])
                else:
                    self.datasets[i].parse_from_tf(self.filsamplers[i-1].tf, self.f)
            else:
                self.datasets[i].origin = self.filsamplers[i]
                if i in SAMPLER_INDEXES:
                    intermediateSignal = self.filsamplers[i].Sample(intermediateSignal, self.t)
                    self.datasets[i].parse_from_sampler(self.filsamplers[i])
                    if i == 0:
                        self.f = self.filsamplers[i].f
                else:
                    intermediateSignal = self.filsamplers[i].tf.simulateInputSignal(intermediateSignal, self.t)
                    self.datasets[i].parse_from_tf(self.filsamplers[i].tf, self.f)
                    self.datasets[i].data[0]['xf'] = abs(self.filsamplers[i].tf.getFFT(intermediateSignal))

            #necesario para los filtros
            self.datasets[i].data[0]['t'] = self.t
            self.datasets[i].data[0]['x'] = intermediateSignal

        self.updatePlots()

    def updateSamplers(self, noPlot=False):
        self.filsamplers[SH].fs = self.respd.fs
        self.filsamplers[SH].dc = self.respd.dsh
        self.filsamplers[LLA].fs = self.respd.fs
        self.filsamplers[LLA].dc = self.respd.dla
        
    def createDatasets(self):
        self.datasets = []
        for i in range(5):
            self.datasets.append(Dataset(origin=self.filsamplers[i]))
            if i in FILTER_INDEXES:
                self.datasets[i].fields.append('t')
                self.datasets[i].fields.append('x')

    def createDatalines(self):
        self.dataline_list.clear()
        self.datalines = []
        for i in range(5):
            dlt = self.datasets[i].create_dataline()
            dlt.plots = self.plots_canvases[i][0]
            dlt.name = self.dl_titles[i][0]
            dlt.xsource = 't'
            dlt.ysource = 'x'
            dlf = self.datasets[i].create_dataline()
            dlf.plots = self.plots_canvases[i][1]
            dlf.name = self.dl_titles[i][1]
            qlwt1 = QListWidgetItem()
            qlwt1.setText(dlt.name)
            qlwt2 = QListWidgetItem()
            qlwt2.setText(dlf.name)
            self.dataline_list.insertItem(2*i, qlwt1)
            self.dataline_list.insertItem(2*i+1, qlwt2)
            self.datalines.append(dlt)
            self.datalines.append(dlf)

        dlt = self.datasets[0].create_dataline()
        dlt.plots = self.plots_canvases[5][0]
        dlt.name = self.dl_titles[5][0]
        dlt.xsource = 't'
        dlt.ysource = 'x'
        dlf = self.datasets[0].create_dataline()
        dlf.plots = self.plots_canvases[5][1]
        dlf.name = self.dl_titles[5][1]
        qlwt1 = QListWidgetItem()
        qlwt1.setText(dlt.name)
        qlwt2 = QListWidgetItem()
        qlwt2.setText(dlf.name)
        self.dataline_list.insertItem(10, qlwt1)
        self.dataline_list.insertItem(11, qlwt2)
        self.datalines.append(dlt)
        self.datalines.append(dlf)

        dlt = self.datasets[4].create_dataline()
        dlt.plots = self.plots_canvases[5][0]
        dlt.name = self.dl_titles[6][0]
        dlt.xsource = 't'
        dlt.ysource = 'x'
        dlf = self.datasets[4].create_dataline()
        dlf.plots = self.plots_canvases[5][1]
        dlf.name = self.dl_titles[6][1]
        dlf.xsource = 'f'
        dlf.ysource = 'xf'
        qlwt1 = QListWidgetItem()
        qlwt1.setText(dlt.name)
        qlwt2 = QListWidgetItem()
        qlwt2.setText(dlf.name)
        self.dataline_list.insertItem(12, qlwt1)
        self.dataline_list.insertItem(13, qlwt2)
        self.datalines.append(dlt)
        self.datalines.append(dlf)

    def openInputDialog(self):
        self.respd.open()
        self.respd.input_txt.setFocus()

    def processInputValues(self):        
        self.t = self.respd.time
        self.input = self.respd.input_func
        self.inp_lbl.setText(self.respd.getInputExpression())
        self.updateSamplers()
        self.rePlotAll()

    def addSampler(self, newName=''):
        stype = 0 if newName == 'SH' else (1 if newName == 'Llave' else 2)
        duty = self.respd.dsh if newName == 'SH' else self.respd.dla
        sampler = Sampler(self.respd.fs, duty, stype)
        self.filsamplers.append(sampler)

    def buildFilterFromParams(self, name):
        if self.tipo_box.currentIndex() in [Filter.BAND_PASS, Filter.BAND_REJECT]:
            wa = [F_TO_W * self.fa_min_box.value(), F_TO_W *
                  self.fa_max_box.value()]
            wp = [F_TO_W * self.fp_min_box.value(), F_TO_W *
                  self.fp_max_box.value()]
        else:
            wa = F_TO_W * self.fa_box.value()
            wp = F_TO_W * self.fp_box.value()

        params = {
            "name": name,
            "filter_type": self.tipo_box.currentIndex(),
            "approx_type": self.aprox_box.currentIndex(),
            "helper_approx": 0,
            "helper_N": 0,
            "is_helper": False,
            "define_with": 0,
            "N_min": 1,
            "N_max": 25,
            "gain": self.gain_box.value(),
            "denorm": self.denorm_box.value(),
            "aa_dB": self.aa_box.value(),
            "ap_dB": self.ap_box.value(),
            "wa": wa,
            "wp": wp,
            "w0": 1000,
            "bw": 100,
            "gamma": 100,
            "tau0": 1,
            "wrg": 100,
        }
        return AnalogFilter(**params)

    def addFilter(self, name):
        newFilter = self.buildFilterFromParams(name)
        valid, msg = newFilter.validate()
        if not valid:
            self.statusbar.showMessage('ERROR: revise la plantilla del filtro', 10000)
            return
        self.selfil_cb.addItem(name, '')
        self.filsamplers.append(newFilter)

    def changeSelectedFilter(self):
        name = self.selfil_cb.currentText()
        newFilter = self.buildFilterFromParams(name)
        valid, msg = newFilter.validate()
        if not valid:
            self.statusbar.showMessage('ERROR: revise la plantilla del filtro', 10000)
            return
        index = FAA if self.selfil_cb.currentIndex() == 0 else FR
        self.filsamplers[index] = newFilter
        self.rePlotAll()

    def toggleEnableFAA(self):
        self.chk_faa.setCheckState(not self.chk_faa.isChecked())
        self.updateEnables()

    def toggleEnableSH(self):
        self.chk_sh.setCheckState(not self.chk_sh.isChecked())
        self.updateEnables()

    def toggleEnableLLA(self):
        self.chk_lla.setCheckState(not self.chk_lla.isChecked())
        self.updateEnables()

    def toggleEnableFR(self):
        self.chk_fr.setCheckState(not self.chk_fr.isChecked())
        self.updateEnables()

    def updateEnables(self):
        self.sen_faa.setVisible(not self.chk_faa.isChecked())
        self.sdis_faa.setVisible(self.chk_faa.isChecked())
        self.sen_sh.setVisible(not self.chk_sh.isChecked())
        self.sdis_sh.setVisible(self.chk_sh.isChecked())
        self.sen_lla.setVisible(not self.chk_lla.isChecked())
        self.sdis_lla.setVisible(self.chk_lla.isChecked())
        self.sen_fr.setVisible(not self.chk_fr.isChecked())
        self.sdis_fr.setVisible(self.chk_fr.isChecked())
        self.enabled[FAA] = not self.chk_faa.isChecked()
        self.enabled[SH] = not self.chk_sh.isChecked()
        self.enabled[LLA] = not self.chk_lla.isChecked()
        self.enabled[FR] = not self.chk_fr.isChecked()
        self.rePlotAll()
        pass
        
    def condition_canvas(self, canvas, xlabel, ylabel, xscale='linear', yscale='linear', grid=True):
        canvas.ax.clear()
        canvas.ax.grid(grid, which="both", linestyle=':')
        canvas.ax.set_xlabel(xlabel)
        canvas.ax.set_ylabel(ylabel)
        canvas.ax.set_xscale(xscale)
        canvas.ax.set_yscale(yscale)
        canvas.ax.xaxis.label.set_size(self.plt_labelsize_sb.value())
        canvas.ax.yaxis.label.set_size(self.plt_labelsize_sb.value())
        for label in (canvas.ax.get_xticklabels() + canvas.ax.get_yticklabels()):
            label.set_fontsize(self.plt_ticksize_sb.value())

    def populateSelectedFilterDetails(self, index=-2):
        if (index == -2):
            for i, fds in enumerate(self.filsamplers):
                if (fds.origin == self.selected_dataset_data.origin):
                    self.selfil_cb.blockSignals(True)
                    self.stages_selfil_cb.blockSignals(True)
                    self.selfil_cb.setCurrentIndex(i)
                    self.stages_selfil_cb.setCurrentIndex(i)
                    self.selfil_cb.blockSignals(False)
                    self.stages_selfil_cb.blockSignals(False)
                    break
        elif (index != -1):
            if (index == self.selfil_cb.currentIndex()):
                filtds = self.selfil_cb.currentData()
                self.stages_selfil_cb.blockSignals(True)
                self.stages_selfil_cb.setCurrentIndex(index)
                self.stages_selfil_cb.blockSignals(False)
            else:
                filtds = self.stages_selfil_cb.currentData()
                self.selfil_cb.blockSignals(True)
                self.selfil_cb.setCurrentIndex(index)
                self.selfil_cb.blockSignals(False)
        else:
            return
        self.filtername_box.setText(self.selected_dataset_data.title)
        self.tipo_box.setCurrentIndex(
            self.selected_dataset_data.origin.filter_type)
        self.aprox_box.setCurrentIndex(
            self.selected_dataset_data.origin.approx_type)
        self.compareapprox_cb.setCurrentIndexes(
            self.selected_dataset_data.origin.helper_approx)
        self.comp_N_box.setValue(self.selected_dataset_data.origin.helper_N)
        self.gain_box.setValue(self.selected_dataset_data.origin.gain)
        self.aa_box.setValue(self.selected_dataset_data.origin.aa_dB)
        self.ap_box.setValue(self.selected_dataset_data.origin.ap_dB)
        self.N_label.setText(str(self.selected_dataset_data.origin.N))
        self.N_min_box.setValue(self.selected_dataset_data.origin.N_min)
        self.N_max_box.setValue(self.selected_dataset_data.origin.N_max)
        Qs = [self.calcQ(p)
              for p in self.selected_dataset_data.origin.tf.getZP()[1]]
        self.max_Q_label.setText("{:.2f}".format(max(Qs)))
        self.drloss_label.setText("{:.2f} dB".format(
            self.selected_dataset_data.origin.getDynamicRangeLoss()))
        self.define_with_box.setCurrentIndex(
            self.selected_dataset_data.origin.define_with)
        if self.selected_dataset_data.origin.filter_type in [Filter.BAND_PASS, Filter.BAND_REJECT]:
            self.fp_box.setValue(0)
            self.fa_box.setValue(0)
            fa = []
            fp = []
            if (self.selected_dataset_data.origin.filter_type == Filter.BAND_PASS):
                fp = [w * W_TO_F for w in self.selected_dataset_data.origin.wp]
                fa = [w * W_TO_F for w in self.selected_dataset_data.origin.reqwa]
            else:
                fp = [w * W_TO_F for w in self.selected_dataset_data.origin.reqwp]
                fa = [w * W_TO_F for w in self.selected_dataset_data.origin.wa]
            self.fa_min_box.setValue(fa[0])
            self.fa_max_box.setValue(fa[1])
            self.fp_min_box.setValue(fp[0])
            self.fp_max_box.setValue(fp[1])
            self.bw_max_box.setValue(
                self.selected_dataset_data.origin.bw[1] * W_TO_F)
            self.bw_min_box.setValue(
                self.selected_dataset_data.origin.bw[0] * W_TO_F)
            self.f0_box.setValue(self.selected_dataset_data.origin.w0 * W_TO_F)
        elif self.selected_dataset_data.origin.filter_type in [Filter.LOW_PASS, Filter.HIGH_PASS]:
            self.fp_box.setValue(self.selected_dataset_data.origin.wp * W_TO_F)
            self.fa_box.setValue(self.selected_dataset_data.origin.wa * W_TO_F)
            self.fa_min_box.setValue(0)
            self.fa_max_box.setValue(0)
            self.fp_min_box.setValue(0)
            self.fp_max_box.setValue(0)
        else:
            self.fp_box.setValue(0)
            self.fa_box.setValue(0)
            self.fa_min_box.setValue(0)
            self.fa_max_box.setValue(0)
            self.fp_min_box.setValue(0)
            self.fp_max_box.setValue(0)

    def populateSelectedDatalineDetails(self, listitemwidget, qlistwidget):
        i = self.dataline_list.currentIndex().row()
        if not i in range(len(self.datalines)):
            self.setDatalineControlsStatus(False)
            return
        
        self.selected_dataline_data = self.datalines[i]
        self.setDatalineControlsStatus(True)
        self.dl_xscale_sb.blockSignals(True)
        self.dl_yscale_sb.blockSignals(True)
        self.dl_xoffset_sb.blockSignals(True)
        self.dl_yoffset_sb.blockSignals(True)
        self.dl_linewidth_sb.blockSignals(True)
        self.dl_markersize_sb.blockSignals(True)


        self.dl_xdata_cb.clear()
        self.dl_ydata_cb.clear()
        self.dl_xdata_cb.addItems(self.selected_dataline_data.dataset.fields)
        self.dl_ydata_cb.addItems(self.selected_dataline_data.dataset.fields)

        self.dl_transform_cb.setCurrentIndex(
            self.selected_dataline_data.transform)
        self.dl_xdata_cb.setCurrentText(self.selected_dataline_data.xsource)
        self.dl_xscale_sb.setValue(self.selected_dataline_data.xscale)
        self.dl_xoffset_sb.setValue(self.selected_dataline_data.xoffset)
        self.dl_ydata_cb.setCurrentText(self.selected_dataline_data.ysource)
        self.dl_yscale_sb.setValue(self.selected_dataline_data.yscale)
        self.dl_yoffset_sb.setValue(self.selected_dataline_data.yoffset)
        self.dl_color_edit.setText(self.selected_dataline_data.color)
        self.dl_style_cb.setCurrentText(self.selected_dataline_data.linestyle)
        self.dl_linewidth_sb.setValue(self.selected_dataline_data.linewidth)
        self.dl_marker_cb.setCurrentText(
            self.selected_dataline_data.markerstyle)
        self.dl_markersize_sb.setValue(self.selected_dataline_data.markersize)
        self.dl_color_label.setStyleSheet(
            f'background-color: {self.selected_dataline_data.color}')

        self.dl_xscale_sb.blockSignals(False)
        self.dl_yscale_sb.blockSignals(False)
        self.dl_xoffset_sb.blockSignals(False)
        self.dl_yoffset_sb.blockSignals(False)
        self.dl_linewidth_sb.blockSignals(False)
        self.dl_markersize_sb.blockSignals(False)

    def updateSelectedDataline(self):
        self.selected_dataline_data.transform = self.dl_transform_cb.currentIndex()
        self.selected_dataline_data.xsource = self.dl_xdata_cb.currentText()
        self.selected_dataline_data.xscale = self.dl_xscale_sb.value()
        self.selected_dataline_data.xoffset = self.dl_xoffset_sb.value()
        self.selected_dataline_data.ysource = self.dl_ydata_cb.currentText()
        self.selected_dataline_data.yscale = self.dl_yscale_sb.value()
        self.selected_dataline_data.yoffset = self.dl_yoffset_sb.value()
        self.selected_dataline_data.color = self.dl_color_edit.text()
        self.selected_dataline_data.linestyle = self.dl_style_cb.currentText()
        self.selected_dataline_data.linewidth = self.dl_linewidth_sb.value()
        self.selected_dataline_data.markerstyle = self.dl_marker_cb.currentText()
        self.selected_dataline_data.markersize = self.dl_markersize_sb.value()
        self.updatePlot(self.selected_dataline_data)

    def openColorPicker(self):
        dialog = QColorDialog(self)
        dialog.setCurrentColor(Qt.red)
        dialog.setOption(QColorDialog.ShowAlphaChannel)
        dialog.open()
        dialog.currentColorChanged.connect(self.updateDatalineColor)

    def updateDatalineColor(self, color):
        self.dl_color_edit.setText(color.name())
        self.dl_color_label.setStyleSheet(f'background-color: {color.name()}')
        self.selected_dataline_data.color = color.name()
        self.updatePlot(self.selected_dataline_data)

    def setDatalineControlsStatus(self, enabled=True):
        self.dl_transform_cb.setEnabled(enabled)
        self.dl_xdata_cb.setEnabled(enabled)
        self.dl_xscale_sb.setEnabled(enabled)
        self.dl_xoffset_sb.setEnabled(enabled)
        self.dl_ydata_cb.setEnabled(enabled)
        self.dl_yscale_sb.setEnabled(enabled)
        self.dl_yoffset_sb.setEnabled(enabled)
        self.dl_color_edit.setEnabled(enabled)
        self.dl_color_pickerbtn.setEnabled(enabled)
        self.dl_style_cb.setEnabled(enabled)
        self.dl_linewidth_sb.setEnabled(enabled)
        self.dl_marker_cb.setEnabled(enabled)
        self.dl_markersize_sb.setEnabled(enabled)

    def autoscalePlots(self):
        for dl in self.datalines:
            canvas = dl.plots.canvas
            canvas.ax.margins(self.plt_marginx.value(),
                              self.plt_marginy.value())
            canvas.ax.relim()
            canvas.ax.autoscale()
            canvas.draw()

    def updatePlot(self, dl):
        if not isinstance(dl, Dataline):
            dl = self.selected_dataline_data()
        canvas = dl.plots.canvas

        for artist in canvas.ax.lines + canvas.ax.collections:
            if dl.artist == artist:
                artist.remove()
                dl.artist = None
        #canvas.ax.clear()

        for label in (canvas.ax.get_xticklabels() + canvas.ax.get_yticklabels()):
            label.set_fontsize(self.plt_ticksize_sb.value())
        canvas.ax.xaxis.label.set_size(
            self.plt_labelsize_sb.value())
        canvas.ax.yaxis.label.set_size(
            self.plt_labelsize_sb.value())
        canvas.ax.title.set_size(self.plt_titlesize_sb.value())

        x, y =  dl.dataset.get_datapoints(
            dl.xsource, dl.ysource, dl.casenum)

        if (dl.transform == 1):
            y = np.abs(y)
        elif (dl.transform == 2):
            y = np.angle(y, deg=True)
        elif (dl.transform == 3):
            y = np.unwrap(np.angle(y, deg=True), period=360)
        elif (dl.transform == 4):
            y = 20 * np.log10(y)
        elif (dl.transform == 5):
            y = 20 * np.log10(np.abs(y))
        elif (dl.transform == 6):
            y = np.unwrap(y, period=360)
        else:
            y = np.real(y)

        if (dl.transform in [2, 3, 6]):
            canvas.ax.yaxis.set_major_locator(ticker.MaxNLocator(
                nbins='auto', steps=[1.8, 2.25, 4.5, 9]))
        else:
            canvas.ax.yaxis.set_major_locator(
                ticker.AutoLocator())

        try:
            line, = canvas.ax.plot(
                x * dl.xscale + dl.xoffset,
                y * dl.yscale + dl.yoffset,
                linestyle=LINE_STYLES[dl.linestyle],
                linewidth=dl.linewidth,
                marker=MARKER_STYLES[dl.markerstyle],
                markersize=dl.markersize,
                color=dl.color,
                label=dl.name,
            )
            dl.artist = line
            if (dl.name != '' and dl.name[0] != '_'):
                if (self.plt_legendpos.currentText() == 'None'):
                    canvas.ax.get_legend().remove()
                else:
                    canvas.ax.legend(handles=[line], fontsize=self.plt_legendsize_sb.value(
                    ), loc=self.plt_legendpos.currentIndex())
                if (self.plt_grid.isChecked()):
                    canvas.ax.grid(True, which="both", linestyle=':')
                else:
                    canvas.ax.grid(False)
            canvas.draw()


        except ValueError:
            self.statusbar.showMessage('ERROR: Los tipos de datos para graficar NO son adecuados', 10000)

    def updatePlots(self):
        i=0
        for dl in self.datalines:
            self.updatePlot(dl)
            i+=1
        self.autoscalePlots()
