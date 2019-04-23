from lcapy import Circuit, R, C, L, V, I, v, exp, Heaviside, Vs, Vn, Vt, It, sqrt, u
from lcapy import Zs, s, t
import unittest
import sympy as sym


class LcapyTester(unittest.TestCase):

    """Unit tests for lcapy circuits

    """

    def assertEqual2(self, ans1, ans2, comment):

        ans1 = ans1.canonical()
        ans2 = ans2.canonical()

        try:
            self.assertEqual(ans1, ans2, comment)
        except AssertionError as e:
            ans1.pprint()
            ans2.pprint()
            raise AssertionError(e)

    def test_RC1(self):
        """Lcapy: check RC network

        """
        a = Circuit()
        a.add('R1 1 2')
        a.add('C1 2 0')

        self.assertEqual2(a.Z(1, 2), R('R1').Z, "Z incorrect for R1.")
        self.assertEqual2(a.Z(2, 0), C('C1').Z, "Z incorrect for C1.")
        self.assertEqual2(
            a.Z(1, 0), (R('R1') + C('C1')).Z, "Z incorrect for R1 + C1.")

        self.assertEqual2(a.Y(1, 2), R('R1').Y, "Y incorrect for R1.")
        self.assertEqual2(a.Y(2, 0), C('C1').Y, "Y incorrect for C1.")
        self.assertEqual2(
            a.Y(1, 0), (R('R1') + C('C1')).Y, "Y incorrect for R1 + C1.")
        self.assertEqual2(a.Isc(1, 0), I(0).Isc, "Isc incorrect")

    def test_VRC1(self):
        """Lcapy: check VRC circuit

        """
        a = Circuit()
        a.add('V1 1 0 {V1 / s}')
        a.add('R1 1 2')
        a.add('C1 2 0')

        # Note, V1 acts as a short-circuit for the impedance/admittance
        self.assertEqual2(
            a.Z(1, 2), (R('R1') | C('C1')).Z, "Z incorrect across R1")
        self.assertEqual2(
            a.Z(2, 0), (R('R1') | C('C1')).Z, "Z incorrect across C1")
        self.assertEqual2(a.Z(1, 0), R(0).Z, "Z incorrect across V1")

        self.assertEqual2(
            a.Y(1, 2), (R('R1') | C('C1')).Y, "Y incorrect across R1")
        self.assertEqual2(
            a.Y(2, 0), (R('R1') | C('C1')).Y, "Y incorrect across C1")
        # This has a non-invertible A matrix.
        # self.assertEqual2(a.Y(1, 0), R(0).Y, "Y incorrect across V1")

        self.assertEqual2(a.Voc(1, 0).s, V('V1 / s').Voc.s, "Voc incorrect across V1")
        self.assertEqual(a.is_ivp, False, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, False, "AC incorrect")


    def test_VRL1(self):
        """Lcapy: check VRL circuit

        """
        a = Circuit()
        a.add('V1 1 0 {V1 / s}')
        a.add('R1 1 2')
        a.add('L1 2 0 L1 0')

        # This currently fails due to two symbols of the same name
        # having different assumptions.

        # Note, V1 acts as a short-circuit for the impedance/admittance
        self.assertEqual2(
            a.thevenin(1, 2).Voc, a.Voc(1, 2), "incorrect thevenin voltage")
        self.assertEqual2(
            a.thevenin(1, 2).Z, a.Z(1, 2), "incorrect thevenin impedance")
        self.assertEqual2(
            a.norton(1, 2).Isc, a.Isc(1, 2), "incorrect norton current")
        self.assertEqual2(
            a.norton(1, 2).Y, a.Y(1, 2), "incorrect norton admittance")
        self.assertEqual2(
            a.Z(1, 2), (R('R1') | L('L1')).Z, "Z incorrect across R1")
        self.assertEqual2(
            a.Z(2, 0), (R('R1') | L('L1')).Z, "Z incorrect across L1")
        self.assertEqual2(a.Z(1, 0), R(0).Z, "Z incorrect across V1")

        self.assertEqual2(
            a.Y(1, 2), (R('R1') | L('L1')).Y, "Y incorrect across R1")
        self.assertEqual2(
            a.Y(2, 0), (R('R1') | L('L1')).Y, "Y incorrect across L1")
        # This has a non-invertible A matrix.
        # self.assertEqual2(a.Y(1, 0), R(0).Y, "Y incorrect across V1")

        self.assertEqual2(a.Voc(1, 0), V('V1' / s).Voc,
                          "Voc incorrect across V1")
        self.assertEqual(a.is_ivp, True, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, False, "AC incorrect")

    def test_IR1(self):
        """Lcapy: check IR circuit

        """
        a = Circuit()
        a.add('I1 1 0 2')
        a.add('R1 1 0 1')

        self.assertEqual2(a.R1.V, V(2).Voc, "Incorrect voltage")

        self.assertEqual2(a[1].V, V(2).Voc, "Incorrect node voltage")

    def test_VCVS1(self):
        """Lcapy: check VCVS

        """
        a = Circuit()
        a.add('V1 1 0 2')
        a.add('R1 1 0 1')
        a.add('E1 2 0 1 0 3')
        a.add('R2 2 0 1')

        self.assertEqual2(a.R2.V, V(6).Voc, "Incorrect voltage")

    def test_VCCS1(self):
        """Lcapy: check VCCS

        """
        a = Circuit()
        a.add('V1 1 0 2')
        a.add('R1 1 0 1')
        a.add('G1 2 0 1 0 3')
        a.add('R2 2 0 1')

        self.assertEqual2(a.R2.V, V(6).Voc, "Incorrect voltage")

    def test_CCCS1(self):
        """Lcapy: check CCCS

        """
        a = Circuit()
        a.add('V1 1 0 10')
        a.add('R1 1 2 2')
        a.add('V2 2 0 0')
        a.add('F1 3 0 V2 2')
        a.add('R2 3 0 1')

        self.assertEqual2(a.R2.V, V(10).Voc, "Incorrect voltage")


    def test_CCVS1(self):
        """Lcapy: check CCVS

        """
        a = Circuit()
        a.add('V1 1 0 10')
        a.add('R1 1 2 2')
        a.add('V2 2 0 0')
        a.add('H1 3 0 V2 2')
        a.add('R2 3 0 1')

        self.assertEqual2(a.R2.V, V(10).Voc, "Incorrect voltage")


    def test_V1(self):
        """Lcapy: test V1"""

        a = Circuit()
        a.add('V1 1 0 10') 

        self.assertEqual(a.V1.V.dc, 10, "Incorrect voltage")


    def test_VRL1_dc(self):
        """Lcapy: check VRL circuit at dc

        """

        a = Circuit()
        a.add('V1 1 0 dc')
        a.add('R1 1 2')
        a.add('L1 2 0')
        self.assertEqual(a.is_ivp, False, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, True, "DC incorrect")
        self.assertEqual(a.is_ac, False, "AC incorrect")


    def test_VRL1_dc2(self):
        """Lcapy: check VRL circuit at dc but with initial conditions

        """

        # TODO: This currently fails due to two symbols of the same name
        # having different assumptions.

        a = Circuit()
        a.add('V1 1 0 {V1 + 1}')
        a.add('R1 1 2')
        a.add('L1 2 0 L1 {(V1 + 1) / R1}')
        # This tests if symbols are converted to the defined ones.
        self.assertEqual2(a.L1.v, V(0).Voc.s.inverse_laplace(), 
                          "Incorrect time domain voltage")        
        v = Vs('(V1+1)/s', dc=False).inverse_laplace()
        self.assertEqual2(a.R1.v, v, 
                          "Incorrect time domain voltage")        
        self.assertEqual(a.is_ivp, True, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, False, "AC incorrect")

    def test_VRL1_dc3(self):
        """Lcapy: check VRL circuit at dc but with initial conditions

        """

        # TODO: This currently fails due to two symbols of the same name
        # having different assumptions.

        a = Circuit()
        a.add('V1 1 0 V1')
        a.add('R1 1 2')
        a.add('L1 2 0 L1 0')
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, False, "AC incorrect")


    def test_VRL1_ac(self):
        """Lcapy: check VRL circuit at ac

        """

        a = Circuit()
        a.add('V1 1 0 ac')
        a.add('R1 1 2')
        a.add('L1 2 0')
        self.assertEqual(a.is_ivp, False, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, True, "AC incorrect")
        self.assertEqual(a.R1.I, a.L1.I, "currents different")
        self.assertEqual(-a.V1.I, a.L1.I, "currents different")


    def test_transfer(self):
        """Lcapy: check transfer function

        """

        a = Circuit()
        a.add('R1 1 0 1')
        a.add('R2 1 2 2')
        a.add('C1 2 0 1')

        H = a.transfer(1, 0, 2, 0)
        self.assertEqual2(H, 1 / (2 * s + 1), "Incorrect transfer function")
        h = H.inverse_laplace()
        self.assertEqual2(h, exp(-t / 2) * Heaviside(t) / 2,
                          "Incorrect impulse response")        


    def test_VRC2(self):
        """Lcapy: check VRC circuit with arbitrary s-domain source

        """

        a = Circuit()
        a.add('V1 1 0 {V(s)}') 
        a.add('R1 1 2') 
        a.add('C1 2 0 C1 0') 
        H = a[2].V.s / a[1].V.s

        self.assertEqual2(H, 1 / (s * 'R1' * 'C1' + 1),  "Incorrect ratio")
    
    def test_noise1(self):
        """Lcapy: check circuit noise for voltage divider"""

        a = Circuit()
        a.add('V1 1 0 noise 3') 
        a.add('R1 1 2 2')
        a.add('R2 2 0 4')
        V1 = a.R1.V.n
        self.assertEqual2(V1, Vn(1, nid=V1.nid), "Incorrect ratio")

    def test_noise2(self):
        """Lcapy: check circuit noise for pair of sources"""

        a = Circuit()
        a.add('V1 1 0 noise 3')
        a.add('V2 2 1 noise 4')
        a.add('R1 2 0 5')
        V1 = a.R1.V.n
        self.assertEqual2(V1, Vn(5, nid=V1.nid), "Incorrect noise sum")        
        
    def test_filtered_noise1(self):
        """Lcapy: check circuit filtered noise"""

        a = Circuit()
        a.add('V1 1 0 noise 3') 
        a.add('R1 1 2 2')
        a.add('C1 2 0 4')         
#        self.assertEqual2(a.R1.V.n, Vn(1), "Incorrect ratio")


    def test_filtered_noise2(self):
        """Lcapy: check circuit filtered noise"""

        a = Circuit()
        a.add('V1 1 0 noise {sqrt(4 * k * T * R)}') 
        a.add('R1 1 2 R')
        a.add('C1 2 0 C')         
        self.assertEqual2(a.C1.V.n.rms(), Vt('sqrt(k * T / C)'),
                          "Incorrect capacitor voltage")

    def test_filtered_noise3(self):
        """Lcapy: check circuit filtered noise"""

        a = Circuit()
        a.add('V1 1 0 noise 20') 
        a.add('R1 1 2 1')
        a.add('C1 2 0 2')         
        self.assertEqual(a.C1.V.n.rms(), 5 * sqrt(2),
                         "Incorrect capacitor voltage")

    def test_noisy1(self):

        a = Circuit()
        a.add('R1 1 0')
        a.add('R2 1 0')
        an = a.noisy()
        b = Circuit()
        b.add('R1 1 0 {R1 * R2 / (R1 + R2)}')
        bn = b.noisy()
        self.assertEqual(an[1].V.n.expr, bn[1].V.n.expr, "Incorrect noise")

    def test_causal1(self):

        a = Circuit()
        a.add('V1 1 0 {4 + 2 * u(t)}; down')
        a.add('R1 1 2 2; right=2')
        a.add('L1 2 3 2; down')
        a.add('W 0 3; right')

        self.assertEqual(a.sub['s'].is_causal, True, "Causal incorrect")
        self.assertEqual2(a.L1.v, 2 * exp(-t) * u(t), "L current incorrect")

    def test_VR1_ac2(self):
        """Lcapy: check VR circuit at ac for angular frequency 1

        """

        # This can be solved in the time-domain
        a = Circuit()
        a.add('V1 1 0 ac 5 0 1')
        a.add('R1 1 0 1')
        self.assertEqual(a.is_ivp, False, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, True, "AC incorrect")
        self.assertEqual(a.is_causal, False, "Causal incorrect")
        self.assertEqual(a.is_time_domain, True, "Time domain incorrect")
        self.assertEqual(a.V1.v, Vt('5*cos(t)'), "V1 voltage incorrect")
        self.assertEqual(a.R1.v, Vt('5*cos(t)'), "R1 voltage incorrect")
        self.assertEqual(a.V1.i, It('-5*cos(t)'), "V1 current incorrect")
        self.assertEqual(a.R1.i, It('5*cos(t)'), "R1 current incorrect")

        
    def test_VRL1_ac2(self):
        """Lcapy: check VRL circuit at ac for angular frequency 1

        """

        a = Circuit()
        a.add('V1 1 0 ac 5 0 1')
        a.add('R1 1 2 3')
        a.add('L1 2 0 4')
        self.assertEqual(a.is_ivp, False, "Initial value problem incorrect")
        self.assertEqual(a.is_dc, False, "DC incorrect")
        self.assertEqual(a.is_ac, True, "AC incorrect")
        self.assertEqual(a.is_causal, False, "Causal incorrect")
        self.assertEqual(a.is_time_domain, False, "Time domain incorrect")
        self.assertEqual(a.V1.v, Vt('5*cos(t)'), "V1 voltage incorrect")
        self.assertEqual(a.R1.i, It('(4*sin(t)+3*cos(t))/5'), "R1 current incorrect")
        
