"""This modules provides the seqExpr class to provide common methods for
the discrete-time and discrete-frequency expressions.

Copyright 2020 Michael Hayes, UCECE

"""

from .dexpr import dExpr
from .sequence import Sequence
from numpy import arange


class seqExpr(dExpr):

    """Superclass of discrete-time and discrete-frequency expressions."""

    def first_index(self, nvals=None):

        if nvals is None:
            nvals = (-10, 10)                
        if isinstance(nvals, tuple):
            nvals = range(*nvals)

        # Desire SymPy equivalent to argmax
        n2 = nvals[-1]
        for n in reversed(nvals):
            if self(n) != 0:
                n2 = n
        return n2
        
    def last_index(self, nvals=None):

        if nvals is None:
            nvals = (-10, 10)        
        if isinstance(nvals, tuple):
            nvals = range(*nvals)

        # Desire SymPy equivalent to argmin
        n1 = nvals[0]
        for n in nvals:
            if self(n) != 0:
                n1 = n
        return n1

    def seq(self, nvals=None, evaluate=False):

        n1 = self.first_index(nvals)
        n2 = self.last_index(nvals)        

        # Perhaps if find self(n2 + 1) != 0 or self(n1 - 1) != 0 then
        # likely to have infinite extent sequence.  Maybe this could
        # be shown using ellipsis when the sequence is printed?
        
        nvals = arange(n1, n2 + 1)
        v = self(nvals)
        
        return Sequence(v, nvals, evaluate, self.var)
       