
import numpy as np
from scipy import signal
from scipy.fft import fftfreq, fftshift, fft
from scipy.interpolate import interp1d
from matplotlib import pyplot as plt

SH, NATURAL, NO_SAMPLE = range(3)

class Sampler():
    def __init__(self, fs, dc, type):
        assert (fs > 0 and 0 <= dc and dc <= 1 and 0 <= type and type <= NO_SAMPLE)
        self.fs = fs
        self.dc = dc
        self.type = type
        self.enabled = True

        self.t = []
        self.f = []
        self.samplingSignal = []
        self.samplingSignalG = []
        self.samplingSignalPH = []
        self.samplingSignalGD = []
        self.sampled = []
        self.sampledG = []
        self.sampledPH = []
        self.sampledGD = []

        

    def Sample(self, x, t):
        self.x = x
        self.t = t
        self.f  = fftshift(fftfreq((self.x.size), d=(self.t[1]-self.t[0])))
        self.samplingSignal = 0.5*signal.square(2*np.pi*self.fs*self.t, duty=self.dc) + 0.5
        self.samplingSignalFreq = fftshift(fft(self.samplingSignal))/self.samplingSignal.size
        self.samplingSignalG = np.abs(self.samplingSignalFreq)
        self.samplingSignalPH = np.unwrap(np.angle(self.samplingSignalFreq, deg=True))
        self.samplingSignalGD = (-1) * [(self.samplingSignalPH[i+1]-self.samplingSignalPH[i])/(self.f[i+1] - self.f[i]) for i in range(len(self.f)-1)]
        self.samplingSignalGD.append(self.samplingSignalPH[-1])

        self.sampled = np.zeros(len(t))

        self.interpol = interp1d(t, x)

        if not self.enabled:
            self.sampled = self.x
            
        else:
            if self.type == NATURAL:
                self.sampled = self.x * self.samplingSignal

                
            elif self.type == SH:
                last = self.x[0]
                for i in range(len(self.t)):
                    sampling = self.samplingSignal[i] > 0.5
                    if sampling:
                        last = self.x[i]
                    self.sampled[i] = last

            else:
                self.sampled = self.x

        self.sampledFreq = fftshift(fft(self.sampled))/self.x.size
        self.sampledG = np.abs(self.sampledFreq)
        self.sampledPH = np.unwrap(np.angle(self.sampledFreq, deg=True))
        self.sampledGD = (-1) * [(self.sampledPH[i+1]-self.sampledPH[i])/(self.f[i+1] - self.f[i]) for i in range(len(self.f)-1)]
        self.sampledGD.append(self.sampledPH[-1])

        return self.sampled

    def setEnabled(self, enable):
        self.enabled = enable
    """
    def sampleAndHold(self, x, t, ts):
        xSampled = np.zeros(len(t))
        j = 0
        for i in range(len(t)):
            xSampled[i] = x[j]
            if  j < len(ts) - 1:
                if t[i] >= ts[j+1]:               
                    j+=1
        return xSampled
    """
    def sampleAndHold(self, t_d, x_d, t):
        x = np.zeros(len(t))
        j = 0
        for i in range(len(t)):
            x[i] = x_d[j]
            if  j < len(t_d) - 1:
                if t[i] >= t_d[j+1]:               
                    j+=1
        return x