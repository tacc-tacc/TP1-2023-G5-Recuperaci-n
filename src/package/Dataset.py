from unicodedata import name
import ltspice
import matplotlib.pyplot as plt
import numpy as np
import csv
from src.package.transfer_function import TFunction
from src.package.Filter import AnalogFilter
from src.package.Sampler import Sampler
from collections import defaultdict
from PyQt5.QtCore import QFileInfo
from src.package.Dataline import Dataline

class Dataset:
    def __init__(self, filepath='', title='', origin=''):
        qfi = QFileInfo(filepath)

        self.color = 0
        self.data = []
        self.zeros = []
        self.poles = []
        self.type = ''
        self.origin = filepath if origin == '' else origin
        self.tf = TFunction()
        self.title = qfi.fileName() if title == '' else title
        self.text = self.title
        self.datalines = []
        self.fields = []
        self.miscinfo = ''
        self.casenames = []
        self.suggestedXscale = 1
        self.suggestedYscale = 1
        self.suggestedXsource = ''
        self.suggestedYsource = ''

        extension = qfi.suffix()
        if(extension == 'raw'):
            self.type = 'spice'
            self.parse_from_spice(filepath)
        elif(extension == 'csv'):
            self.type = 'csv'
            self.parse_from_csv(filepath)
        elif(extension == 'txt'):
            self.type = 'txt'
            self.parse_from_txt(filepath)
        elif(filepath == ''):
            if isinstance(origin, AnalogFilter):
                self.tf = self.origin.tf
                self.type = 'filter'
                self.parse_from_tf(origin.tf)
            elif isinstance(origin, Sampler):
                self.type = 'sampler'
                self.parse_from_sampler(origin)
            else:
                self.tf = self.origin
                self.type = 'TF'
                self.parse_from_tf(origin)
        else:
            raise ValueError
        
        for field in self.data[0]:
            self.fields.append(field)
        
    def parse_from_spice(self, filepath):
        l = ltspice.Ltspice(filepath)
        l.parse()
        self.data = []
        self.miscinfo += f'Spice simulation, MODE: {l._mode}'
        for i in range(l.case_count):
            self.data.append(defaultdict(list))
            for varname in l.variables:
                vardata = []
                if(varname == 'time'):
                    vardata = l.get_time(case=i)
                elif(varname == 'frequency'):
                    vardata = l.get_frequency(case=i)
                else:
                    vardata = l.get_data(name=varname, case=i)
                self.data[i][varname] = vardata

    def parse_from_txt(self, filepath):
        with open(filepath, mode='r') as file:
            fields = file.readline().replace('\n', '').split('\t')
            case = -1
            for line in file.readlines():
                if('Step Information:' in line):
                    self.data.append(defaultdict(list))
                    self.casenames.append(line[18:line.index('  (Run: ')])
                    case += 1
                else:
                    linedata = line.replace('\n', '').split('\t')
                    for x in range(len(fields)):
                        if('i' in linedata[x]):
                            self.data[case][fields[x]].append(np.complex128(linedata[x]))
                        else:
                            self.data[case][fields[x]].append(float(linedata[x]))

    def parse_from_csv(self, filepath):
        with open(filepath, mode='r') as csv_file:
            i = 0
            for line in csv_file:
                if line[0] == '#' or len(line) < 3:
                    i += len(line)
                else:
                    break
            csv_file.seek(i) #Salteo los comentario y me paro donde esta lo que importa
            csv_reader = csv.DictReader(csv_file)
            self.data = [{}]
            first_row = next(csv_reader)
            for (field, val) in first_row.items():
                self.data[0][field] = []

            csv_file.seek(i)
            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                for (field, val) in row.items():
                    try:
                        if('i' in val or 'j' in val):
                            self.data[0][field].append(np.complex128(val))
                        else:
                            self.data[0][field].append(float(val))
                    except(ValueError):
                        pass
                    except(TypeError):
                        pass
                    except(KeyError):
                        pass
                    
            if('rigol' in filepath.lower()):
                self.miscinfo += ('- taken from Rigol DSO')
                self.suggestedXscale = float(self.data[0]['Increment'][0])
                if('' in self.data[0]):
                    self.data[0].pop('')
                self.data[0].pop('Increment')
                self.data[0].pop('Start')
                self.suggestedXsource = 'X'
                for chnum in ['CH4', 'CH3', 'CH2', 'CH1']:
                    if(chnum in self.data[0]):
                        self.suggestedYsource = chnum
            elif('agilent' in filepath.lower()):
                self.miscinfo += ('- taken from Agilent DSO')
                self.suggestedXsource = 'x-axis'
                for chnum in ['4', '3', '2', '1']:
                    if(chnum in self.data[0]):
                        self.suggestedYsource = chnum
            csv_file.close()

    def parse_from_tf(self, tf, fin=None):
        f, g, ph, gd = tf.getBode(f=fin)
        z, p = tf.getZP()
        self.data = [{}]
        self.zeros = [{}]
        self.poles = [{}]
        self.data[0]['f'] = f
        self.data[0]['g'] = g
        self.data[0]['ph'] = ph
        self.data[0]['gd'] = gd
        self.zeros[0] = z
        self.poles[0] = p
        self.suggestedXsource = 'f'
        self.suggestedYsource = 'g'

    def parse_from_sampler(self, s):
        self.data = [{}]
        self.zeros = [{}]
        self.poles = [{}]
        self.data[0]['t'] = s.t
        self.data[0]['f'] = s.f
        self.data[0]['xs'] = s.samplingSignal
        self.data[0]['gs'] = s.samplingSignalG
        self.data[0]['phs'] = s.samplingSignalPH
        self.data[0]['gds'] = s.samplingSignalGD
        self.data[0]['x'] = s.sampled
        self.data[0]['g'] = s.sampledG
        self.data[0]['ph'] = s.sampledPH
        self.data[0]['gd'] = s.sampledGD
        self.suggestedXsource = 'f'
        self.suggestedYsource = 'g'
            
    def get_datapoints(self, xvar_name='time', yvar_name='v', case=0):
        xdata = np.real(self.data[case][xvar_name])
        ydata = np.array(self.data[case][yvar_name])
        return (xdata, ydata)

    def create_dataline(self, casenum=0):
        name = f'{self.title} {len(self.datalines) + 1}'
        dl = Dataline(self, name=name, casenum=casenum, color='#303030', xsource=self.suggestedXsource, ysource=self.suggestedYsource)
        dl.xscale = self.suggestedXscale
        dl.yscale = self.suggestedYscale
        if(self.type == 'csv' or self.type == 'spice'):
            dl.linestyle = 'None'
            dl.markerstyle = 'Point'
        self.datalines.append(dl)
        return dl