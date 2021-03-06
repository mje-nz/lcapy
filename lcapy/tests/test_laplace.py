from lcapy import *
from lcapy.laplace import inverse_laplace_ratfun
import unittest
import sympy as sym


class LcapyTester(unittest.TestCase):

    """Unit tests for lcapy

    """

    def test_laplace(self):

        a = 0 * t + 1
        r1, r2 = inverse_laplace_ratfun(a.expr, s.var, t.var)
        self.assertEqual(r1, delta(t).expr, "inverse_laplace_ratfun")
        self.assertEqual(r2, 0, "inverse_laplace_ratfun")        

        a = 1 / (s + 2)
        r1, r2 = inverse_laplace_ratfun(a.expr, s.var, t.var)
        self.assertEqual(r1, 0, "inverse_laplace_ratfun")        
        self.assertEqual(r2, exp(-2 * t).expr, "inverse_laplace_ratfun")

        self.assertEqual(Heaviside(t).laplace(), 1 / s, "Heaviside(t)")
        self.assertEqual(DiracDelta(t).laplace(), 1, "DiracDelta(t)")
        self.assertEqual(Vt('x(t)').laplace(), Vs('X(s)'), "x(t)")
        self.assertEqual(Vt('5 * x(t)').laplace(), Vs('5 * X(s)'), "5 * x(t)")

        v = expr('R0 * exp(-alpha * t) * i(t)') 
        V = expr('R0 * I(s + alpha)')

        self.assertEqual(v.laplace(), V, "R0 * exp(-alpha * t) * i(t)")
        
        
    def test_inverse_laplace(self):

        self.assertEqual((1 / s).inverse_laplace(causal=True), Heaviside(t),
                         "1 / s")
        self.assertEqual((s * 0 + 1).inverse_laplace(causal=True), DiracDelta(t),
                         "1")
        self.assertEqual((s * 0 + 10).inverse_laplace(causal=True), 10
                         * DiracDelta(t), "0")
        self.assertEqual(Vs('V(s)').inverse_laplace(causal=True),
                         Vt('v(t)'), "V(s)")
        self.assertEqual(Vs('10 * V(s)').inverse_laplace(causal=True),
                         Vt('10 * v(t)'), "V(s)")
        self.assertEqual(Vs('10 * V(s) * exp(-5 * s)').inverse_laplace(causal=True), Vt('10 * v(t - 5)'), "10 * V(s) * exp(-5 * s)")
        self.assertEqual(Vt('v(t)').laplace().inverse_laplace(causal=True),
                         Vt('v(t)'), "v(t)")
        self.assertEqual(expr('1/(s+a)').inverse_laplace(causal=True), expr('exp(-a * t) * u(t)'), "1/(s+a)")
        self.assertEqual(expr('1/(s**2)').inverse_laplace(causal=True), expr('t * u(t)'), "1/(s**2)")        
        self.assertEqual(expr('s/(s+a)').inverse_laplace(causal=True), expr('-a * exp(-a * t) * u(t) + delta(t)'), "s/(s+a)")
        self.assertEqual(expr('s/(s**2+a**2)').inverse_laplace(causal=True), expr('cos(a * t) * u(t)'), "s/(s**2+a**2)")
        self.assertEqual(expr('a/(s**2+a**2)').inverse_laplace(causal=True), expr('sin(a * t) * u(t)'), "a/(s**2+a**2)")                                                                           

    def test_damped_sin(self):

        H1 = 2 / (2 * s ** 2 + 5 * s + 6)
        H2 = H1 * s
        H3 = H1 * s * s

        self.assertEqual(H1(t, damped_sin=True)(s), H1, "damped sin1")
        self.assertEqual(H2(t, damped_sin=True)(s), H2, "damped sin2")
        self.assertEqual(H3(t, damped_sin=True)(s), H3, "damped sin3")
        self.assertEqual((H1 + H2)(t, damped_sin=True)(s), H1 + H2, "damped sin1, 2")
        self.assertEqual((H1 + H3)(t, damped_sin=True)(s), H1 + H3, "damped sin1, 3")
        self.assertEqual((H1 + H2 + H3)(t, damped_sin=True)(s), H1 + H2 + H3, "damped sin1, 2, 3")                


    def test_derivative_undef(self):

        H = s * 'I(s)'
        h = H(t)
        H2 = h(s)

        self.assertEqual(H, H2, "derivative of undef")

        H = s**2 * 'I(s)'
        h = H(t)
        H2 = h(s)

        self.assertEqual(H, H2, "second derivative of undef")                
        
