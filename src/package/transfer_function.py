import sympy as sym
import scipy.signal as signal
from scipy.optimize import basinhopping
from scipy.fft import fftfreq, fftshift, fft
import numpy as np
from numpy.polynomial import Polynomial
from .Parser import ExprParser
import traceback

LPN, HPN, LP2, HP2, LP1, HP1, BP, BR = range(8)

# Evaluate a polynomial in reverse order using Horner's Rule,
# for example: a3*x^3+a2*x^2+a1*x+a0 = ((a3*x+a2)x+a1)x+a0
def poly_at(p, x):
    total = 0
    for a in p:
        total = total * x + a
    return total

class TFunction():
    def __init__(self, *args, normalize=False):
        self.tf_object = {}
        self.eparser = ExprParser()

        self.p = []
        self.z = []
        self.k = 1 #ganancia de fórmula
        self.gain = 1 #ganancia verdadera
        self.N = []
        self.D = []
        self.dN = []
        self.dD = []

        if(len(args) == 1):
            self.setExpression(args[0], normalize=normalize)
        if(len(args) == 2):
            self.setND(args[0], args[1], normalize=normalize)
        if(len(args) == 3):
            self.setZPK(args[0], args[1], args[2], normalize=normalize)
        if(len(args) == 5):
            self.setZPKND(args[0], args[1], args[2], args[3], args[4])

    def setExpression(self, txt, normalize=False):
        try:
            self.eparser.setTxt(txt)
            N, D = self.eparser.getND()
            self.setND(N, D, normalize=normalize)
            return True
        except:
            return False

    def setND(self, N, D, normalize=False):
        if not hasattr(N, '__iter__'):
            N = [N]
        if not hasattr(D, '__iter__'):
            D = [D]
        self.N, self.D = np.array(N, dtype=np.float64), np.array(D, dtype=np.float64)
        self.z, self.p, self.k = signal.tf2zpk(self.N, self.D)        
        if normalize:
            self.normalize()
        self.tf_object = signal.TransferFunction(self.N, self.D)
        self.computedDerivatives = False
    
    def getND(self):
        return self.N, self.D

    #Nota: signal NO normaliza la transferencia, por lo que k multiplica pero no es la ganancia en s=0
    def setZPK(self, z, p, k, normalize=False):
        self.z, self.p, self.k = np.array(z, dtype=np.complex128), np.array(p, dtype=np.complex128), k
        N, D = signal.zpk2tf(self.z, self.p, self.k)
        if not hasattr(N, '__iter__'):
            N = [N]
        if not hasattr(D, '__iter__'):
            D = [D]
        self.N, self.D = np.array(N, dtype=np.float64), np.array(D, dtype=np.float64)
        if normalize:
            self.normalize()
        self.computedDerivatives = False
        self.tf_object = signal.ZerosPolesGain(self.z, self.p, self.k)

    
    def setZPKND(self, z, p, k, N, D):
        if not hasattr(N, '__iter__'):
            N = [N]
        if not hasattr(D, '__iter__'):
            D = [D]
        self.N, self.D = np.array(N, dtype=np.float64), np.array(D, dtype=np.float64)
        self.z, self.p, self.k = z, p, k      
        self.tf_object = signal.ZerosPolesGain(self.z, self.p, self.k)
        self.computedDerivatives = False

    def getZPK(self, in_hz=False):
        if(in_hz):
            return self.z/(2*np.pi), self.p/(2*np.pi), self.k
        else:
            return self.z, self.p, self.k

    def getDerivatives(self):
        N = Polynomial(np.flip(self.N))
        D = Polynomial(np.flip(self.D))
        self.dN = np.flip(N.deriv().coef)
        self.dD = np.flip(D.deriv().coef)
        self.computedDerivatives = True

    def normalize(self):
        self.gain = self.k
        a = 1+0j #lo voy a usar para normalizar, los zpk que da numpy no vienen normalizados
        for zero in self.z:
            if abs(np.real(zero)) + abs(np.imag(zero)) < 1e-32:
                continue
            a = -a*zero
        for pole in self.p:
            if abs(np.real(pole)) + abs(np.imag(pole)) < 1e-32:
                continue
            a = -a/pole
        self.k = self.k/a
        self.N = self.N/a
        self.computedDerivatives = False
    
    def denormalize(self):
        a = 1+0j
        for zero in self.z:
            a *= -zero
        for pole in self.p:
            a /= -pole
        self.k = self.k*a
        self.N = self.N*a
        self.computedDerivatives = False

    def at(self, s):
        return poly_at(self.N, s) / poly_at(self.D, s)
    
    def minFunctionMod(self, w):
        return abs(self.at(1j*w))
    
    def maxFunctionMod(self, w):
        return -abs(self.at(1j*w))
    
    #como ln(H) = ln(G) + j phi --> H'/H = G'/G + j phi'
    def gd_at(self, w0):
        if not self.computedDerivatives:
            self.getDerivatives()
        return -np.imag(1j*(poly_at(self.dN, 1j*w0)/poly_at(self.N, 1j*w0) - poly_at(self.dD, 1j*w0)/poly_at(self.D, 1j*w0))) #'1j*..' --> regla de la cadena
        
    def getZP(self, in_hz=False):
        if(in_hz):
            return self.z/(2*np.pi), self.p/(2*np.pi)
        else:
            return self.z, self.p

    def getBode(self, f=None, linear=False, start=-2, stop=6, num=10000, db=False):
        if isinstance(f, np.ndarray):
            ws = 2*np.pi*f
        elif linear:
            ws = np.linspace(start, stop, num) * 2 * np.pi
        else:
            ws = np.logspace(start, stop, num) * 2 * np.pi
        #h = self.at(1j*ws)
        w, g, ph = signal.bode(self.tf_object, w=ws)
        gd = self.gd_at(ws) #/ (2 * np.pi) #--> no hay que hacer regla de cadena porque se achica tmb la escala de w
        f = ws / (2 * np.pi)
        return f, g if db else 10**(g/20), ph, gd

    #No funciona (y no lo necesitamos) actualmente
    def optimize(self, start, stop, maximize = False):
        # rewrite the bounds in the way required by L-BFGS-B
        bounds = [(start, stop)]
        w0 = 0.5*(start + stop)

        if not maximize:
            f = lambda w : self.minFunctionMod(w)
        else:
            f = lambda w : self.maxFunctionMod(w)

        # use method L-BFGS-B because the problem is smooth and bounded
        minimizer_kwargs = dict(method="L-BFGS-B", bounds=bounds)
        res = basinhopping(f, w0, minimizer_kwargs=minimizer_kwargs)
        return res.x, (res.fun if not maximize else -res.fun)

    def appendStage(self, tf):
        self.setZPK(np.append(self.z, tf.z), np.append(self.p, tf.p), self.k*tf.k)

    def removeStage(self, tf):
        self.setZPK([i for i in self.z if i not in tf.z], [i for i in self.p if i not in tf.p], self.k/tf.k)
        
    def getLatex(self, txt):
        return self.eparser.getLatex(txt=txt)
    
    def buildSymbolicText(self, asterisk=False):
        txt = "("
        nmax = len(self.N)
        dmax = len(self.D)
        for i, coeff in enumerate(self.N[:1]):
            txt += str(coeff) + '*s' + ('**' if asterisk else '^') + str(nmax - i - 1)
            if(i != len(self.N) - 2): txt += '+'
        txt += '{:+}'.format(self.N[nmax - 1])
        txt += ')/('
        for i, coeff in enumerate(self.D[:1]):
            txt += str(coeff) + '*s' + ('**' if asterisk else '^') + str(dmax - i - 1)
            if(i != len(self.D) - 2): txt += '+'
        txt += '{:+}'.format(self.D[dmax - 1])
        txt += ')'
        return txt

    def getSOFilterType(self):
        zp_ord = [len(self.z), len(self.p)]
        if(zp_ord == [2, 2]):
            w0 = np.abs(self.p[0])
            Q = w0 / self.D[1]
            print(np.abs(self.z[0]), np.abs(self.p[0]))
            if(np.isclose(np.abs(self.z[0]), 0)):
                return HP2, "Second order high pass wc={:.2f}".format(np.abs(self.p[0]))
            elif(np.isclose(np.abs(self.z[0]), np.abs(self.p[0]))):
                return BR, "Second order band reject w0={:.2f} Q={:.2f}".format(w0, Q)
            elif(np.abs(self.z[0]) > np.abs(self.p[0])):
                return LPN, "Second order low pass notch w0={:.2f} Q={:.2f}".format(w0, Q)
            else:
                return HPN, "Second order high pass notch w0={:.2f} Q={:.2f}".format(w0, Q)
        elif(zp_ord == [1, 2]):
            w0 = np.sqrt(self.D[2]/self.D[0])
            Q = w0 / self.D[1]
            return BP, "Second order band pass w0={:.2f} Q={:.2f}".format(w0, Q)
        elif(zp_ord == [0, 2]):
            return LP2, "Second order low pass wc={:.2f}".format(np.abs(self.p[0]))
        elif(zp_ord == [1, 1]):
            if(np.isclose(np.abs(self.z[0]), 0)):
                return HP1, "1st order high pass, wc={:.2f}".format(self.p[0].real)
            else:
                if(np.abs(self.z[0]) > np.abs(self.p[0])):
                    return -1, "Single pole single zero high pass"
                else:
                    return -1, "Single pole single zero low pass"
        elif(zp_ord == [0, 1]):
            return LP1, "1st order low pass"
        elif(zp_ord == [0, 0]):
            return "Cable"
        return "Invalid"

    def getEdgeGainsInRange(self, isReject, bpw, db=True):
        if isReject:
            f1, g1, ph1, gd1 = self.getBode(linear=True, start=bpw[0][0], stop=bpw[0][1], num=1000, db=db)
            f2, g2, ph2, gd2 = self.getBode(linear=True, start=bpw[1][0], stop=bpw[1][1], num=1000, db=db)
            minGain, maxGain = min(g1 + g2), max(g1 + g2)
        else:
            f, g, ph, gd = self.getBode(linear=True, start=bpw[0], stop=bpw[1], num=1000, db=db)
            minGain, maxGain = min(g), max(g)
        return minGain, maxGain

    def getPoleQ(self):
        if(len(self.p) == 2):
            return np.abs(self.p[0])/(- 2 * self.p[0].real)
        return 0
    
    def simulateInputSignal(self, xi, time):
        return signal.lsim(self.tf_object, U=xi, T=time)[1]
    
    def getFFT(self, xi):
        xf = fftshift(fft(xi))/xi.size
        return xf