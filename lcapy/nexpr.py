"""This file provides the nExpr class to represent discrete-time expressions.

Copyright 2020 Michael Hayes, UCECE

"""

from __future__ import division
from .expr import Expr
from .functions import exp
from .sym import fsym, ssym, tsym, j, oo
from .acdc import ACChecker, is_dc, is_ac, is_causal
#from .ztransform import ztransform_transform
#from .fourier import fourier_transform

__all__ = ('Hn', 'In', 'Vn', 'Yn', 'Zn')


class nExpr(Expr):

    """t-domain expression or symbol."""

    var = tsym
    domain_name = 'Time'
    domain_units = 's'

    def __init__(self, val, **assumptions):

        assumptions['real'] = True
        super(nExpr, self).__init__(val, **assumptions)

        #self._fourier_conjugate_class = fExpr
        self._ztransform_conjugate_class = zExpr

        if self.expr.find(ssym) != set():
            raise ValueError(
                't-domain expression %s cannot depend on s' % self.expr)

    def infer_assumptions(self):

        self.assumptions['dc'] = False
        self.assumptions['ac'] = False
        self.assumptions['causal'] = False

        var = self.var
        if is_dc(self, var):
            self.assumptions['dc'] = True
            return

        if is_ac(self, var):
            self.assumptions['ac'] = True
            return

        if is_causal(self, var):
            self.assumptions['causal'] = True

    def merge_assumptions(self, **assumptions):
        
        new_assumptions = self.assumptions.copy()
        new_assumptions.update(assumptions)
        return new_assumptions

    def ztransform(self, **assumptions):
        """Determine one-side Ztransform transform with 0- as the lower limit."""

        # The assumptions are required to help with the inverse Ztransform
        # transform is required.
        self.infer_assumptions()

        assumptions = self.merge_assumptions(**assumptions)

        # TODO
        result = None
        #result = ztransform_transform(self.expr, self.var, ssym)

        if hasattr(self, '_ztransform_conjugate_class'):
            result = self._ztransform_conjugate_class(result, **assumptions)
        else:
            result = zExpr(result, **assumptions)
        return result

    # def fourier(self, **assumptions):
    #     """Attempt Fourier transform."""

    #     assumptions = self.merge_assumptions(**assumptions)
        
    #     result = fourier_transform(self.expr, self.var, fsym)

    #     if hasattr(self, '_fourier_conjugate_class'):
    #         result = self._fourier_conjugate_class(result, **assumptions)
    #     else:
    #         result = fExpr(result **self.assumptions)
    #     return result

    def phasor(self, **assumptions):

        check = ACChecker(self, t)
        if not check.is_ac:
            raise ValueError('Do not know how to convert %s to phasor' % self)
        phasor = Phasor(check.amp * exp(j * check.phase), omega=check.omega)
        return phasor

    def plot(self, t=None, **kwargs):
        """Plot the time waveform.  If t is not specified, it defaults to the
        range (-0.2, 2).  t can be a vector of specified instants, a
        tuple specifing the range, or a constant specifying the
        maximum value with the minimum value set to 0.

        kwargs include:
        axes - the plot axes to use otherwise a new figure is created
        xlabel - the x-axis label
        ylabel - the y-axis label
        xscale - the x-axis scaling, say for plotting as ms
        yscale - the y-axis scaling, say for plotting mV
        in addition to those supported by the matplotlib plot command.
        
        The plot axes are returned."""

        from .plot import plot_time
        return plot_time(self, t, **kwargs)

    def sample(self, t):

        """Return a discrete-time signal evaluated at time values specified by
        vector t. """

        return self.evaluate(t)

    def initial_value(self):
        """Determine value at t = 0."""

        return self.subs(0)

    def final_value(self):
        """Determine value at t = oo."""

        return self.__class__(sym.limit(self.expr, self.var, oo))
    

class Yn(nExpr):

    """t-domain 'admittance' value."""

    units = 'siemens/s'

    def __init__(self, val, **assumptions):

        super(Yn, self).__init__(val, **assumptions)
        self._ztransform_conjugate_class = Yz
        #self._fourier_conjugate_class = Yf


class Zn(nExpr):

    """t-domain 'impedance' value."""

    units = 'ohms/s'

    def __init__(self, val, **assumptions):

        super(Zn, self).__init__(val, **assumptions)
        self._ztransform_conjugate_class = Zz
        #self._fourier_conjugate_class = Zf


class Vn(nExpr):

    """t-domain voltage (units V)."""

    quantity = 'Voltage'
    units = 'V'

    def __init__(self, val, **assumptions):

        super(Vn, self).__init__(val, **assumptions)
        self._ztransform_conjugate_class = Vz
        #self._fourier_conjugate_class = Vf

class In(nExpr):

    """t-domain current (units A)."""

    quantity = 'Current'
    units = 'A'

    def __init__(self, val, **assumptions):

        super(In, self).__init__(val, **assumptions)
        self._ztransform_conjugate_class = Iz
        #self._fourier_conjugate_class = If


class Hn(nExpr):

    """impulse response"""

    quantity = 'Impulse response'
    units = ''

    def __init__(self, val, **assumptions):

        super(Hn, self).__init__(val, **assumptions)
        self._ztransform_conjugate_class = Hz
        #self._fourier_conjugate_class = Hf

def nexpr(arg):
    """Create nExpr object.  If `arg` is nsym return n"""

    if arg is nsym:
        return n
    return nExpr(arg)

from .zexpr import Hz, Iz, Vz, Yz, Zz, zExpr
# kexpr?
#from .fexpr import Hf, If, Vf, Yf, Zf, fExpr
from .phasor import Phasor
n = nExpr('n')