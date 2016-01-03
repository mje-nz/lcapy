"""
This module performs schematic drawing using circuitikz from a netlist.

>>> from lcapy import Schematic
>>> sch = Schematic()
>>> sch.add('P1 1 0.1; down')
>>> sch.add('R1 3 1; right')
>>> sch.add('L1 2 3; right')
>>> sch.add('C1 3 0; down')
>>> sch.add('P2 2 0.2; down')
>>> sch.add('W 0 0.1; right')
>>> sch.add('W 0.2 0.2; right')
>>> sch.draw()

Copyright 2014, 2015 Michael Hayes, UCECE
"""

# Components are positioned using two pairs of graphs; one pair for
# the x direction and the other for the y direction.  Each pair
# consists of a forward and a reverse graph. 
#
# x and y component positioning are performed independently.  Let's
# consider the x or horizontal positioning.  There are three stages:
#   1. Component nodes that share a y position are linked; this can
#      occur, for example, for a vertically oriented component.
#   2. The x positions are then...



from __future__ import print_function
import numpy as np
import re
from lcapy.latex import latex_str
from lcapy.core import Expr
import grammar
from parser import Parser
import schemcpts as cpts
from os import system, path, remove, mkdir, chdir, getcwd
import math

__all__ = ('Schematic', )

parser = Parser(cpts, grammar)

class Opts(dict):

    def _parse(self, string):

        for part in string.split(','):
            part = part.strip()
            if part == '':
                continue

            if part in ('up', 'down', 'left', 'right'):
                self['dir'] = part
                continue

            fields = part.split('=')
            key = fields[0].strip()
            arg = '='.join(fields[1:]).strip() if len(fields) > 1 else ''
            self[key] = arg

    def __init__(self, arg=None):

        if arg is None:
            return

        if isinstance(arg, str):
            self._parse(arg)
            return

        for key, val in arg.iteritems():
            self[key] = val

    @property
    def size(self):

        size = self.get('size', 1)
        return float(size)

    def format(self):

        return ', '.join(['%s=%s' % (key, val)
                          for key, val in self.iteritems()])

    def copy(self):
        
        return self.__class__(super(Opts, self).copy())

    def strip(self, *args):

        stripped = Opts()
        for opt in args:
            if opt in self:
                stripped[opt] = self.pop(opt)        
        return stripped

    def strip_voltage_labels(self):

        return self.strip('v', 'vr', 'v_', 'v^', 'v_>', 'v_<', 'v^>', 'v^<')

    def strip_current_labels(self):

        return self.strip('i', 'ir', 'i_', 'i^', 'i_>', 'i_<', 'i^>', 'i^<',
                          'i>_', 'i<_', 'i>^', 'i<^')

    def strip_labels(self):

        return self.strip('l', 'l^', 'l_')

    def strip_all_labels(self):

        self.strip_voltage_labels()
        self.strip_current_labels()
        self.strip_labels()


class SchematicOpts(Opts):

    def __init__(self):

        super (SchematicOpts, self).__init__(
            {'draw_nodes': 'primary',
             'label_values': True,
             'label_ids': True,
             'label_nodes': 'primary',
             'scale' : 1,
             'stretch' : 1,
             'style' : 'american'})


class EngFormat(object):

    def __init__(self, value, unit=''):

        self.value = value
        self.unit = unit

    def latex(self, trim=True, hundreds=False):

        prefixes = ('f', 'p', 'n', '$\mu$', 'm', '', 'k', 'M', 'G', 'T')

        sfmax = 3

        value = self.value
        m = math.log10(abs(value))

        if m < -1 or m >= 3.0:
            if hundreds:
                # Generate 100 m
                n = int(math.floor(m / 3))
                k = int(math.floor(m)) - n * 3
            else:
                # Generate 0.1
                n = int(round(m / 3))
                k = int(round(m)) - n * 3
        else:
            n = 0
            k = m - 1

        dp = sfmax - k

        idx = n + 5
        if idx < 0:
            idx = 0
            return '%e\,' % value + self.unit
        elif idx >= len(prefixes):
            idx = len(prefixes) - 1
            return '%e\,' % value + self.unit

        fmt = '%%.%df' % dp

        n = idx - 5
        value = value * 10**(-3 * n)

        string = fmt % value

        if trim:
            # Remove trailing zeroes after decimal point
            string = string.rstrip('0').rstrip('.')

        return string + '\,' + r'\mbox{' + prefixes[idx] + self.unit + r'}'


class Cnodes(dict):
    """Common nodes"""

    def __init__(self, nodes):

        super (Cnodes, self).__init__()
        for node in nodes:
            self[node] = (node, )

    def link(self, n1, n2):
        """Make nodes n1 and n2 share common node"""

        set1 = self[n1]
        set2 = self[n2]
        newset = set1 + set2

        for n in self[n1]:
            self[n] = newset
        for n in self[n2]:
            self[n] = newset


class Graph(dict):

    def __init__(self, name):

        self.name = name


    def add(self, n1, n2, size):

        if size == 0:
            return

        if n1 not in self:
            self[n1] = []
        if n2 not in self:
            self[n2] = []

        if size < 0:
            self[n2].append((n1, -size))
        else:
            self[n1].append((n2, size))


    def longest_path(self):
        """Find longest path through DAG.  all_nodes is an iterable for all
        the nodes in the graph, from_nodes is a directory indexed by node
        that stores a tuple of tuples.  The first tuple element is the
        parent node and the second element is the minimium size of the
        component connecting the nodes.
        """

        if self['start'] == []:
            raise ValueError("Cannot find start node for graph '%s'. "
                             "Probably a component has an incorrect direction."
                             % self.name)

        all_nodes = self.keys()
        from_nodes = self

        memo = {}

        def get_longest(to_node):

            if to_node in memo:
                return memo[to_node]

            best = 0
            for from_node, size in from_nodes[to_node]:
                best = max(best, get_longest(from_node) + size)

            memo[to_node] = best

            return best

        try:
            length, node = max([(get_longest(to_node), to_node)
                                for to_node in all_nodes])
        except RuntimeError:
            raise RuntimeError(
                ("The schematic graph '%s' is dodgy, probably a component"
                 " is connected to the wrong node\n%s") 
                % (self.name, from_nodes))

        return length, node, memo


class Graphs(object):

    def __init__(self, name):

        self.fwd = Graph('forward ' + name)
        self.rev = Graph('reverse ' + name)

    def add(self, n1, n2, size):
        self.fwd.add(n1, n2, size)
        self.rev.add(n2, n1, size)

    @property
    def nodes(self):
        return self.fwd.keys()

    def add_start_nodes(self):

        # Chain all potential start nodes to node 'start'.
        orphans = []
        rorphans = []
        for node in self.fwd.keys():
            if self.fwd[node] == []:
                orphans.append((node, 0))
            if self.rev[node] == []:
                rorphans.append((node, 0))
        self.fwd['start'] = rorphans
        self.rev['start'] = orphans


class Node(object):

    def __init__(self, name):

        self.name = name
        self._port = False
        self._count = 0
        parts = name.split('_')
        self.rootname = parts[0] if name[0] != '_' else name
        self.primary = len(parts) == 1
        self.list = []

    def append(self, elt):
        """Add new element to the node"""

        if elt.type == 'P':
            self._port = True

        self.list.append(elt)
        if elt.type not in ('O', ):
            self._count += 1

    @property
    def count(self):
        """Number of elements (including wires but not open-circuits)
        connected to the node"""

        return self._count

    def visible(self, draw_nodes):
        """Return true if node drawn"""

        if self.port:
            return True

        if draw_nodes in ('none', None, False):
            return False
        
        if draw_nodes == 'all':
            return True

        if draw_nodes == 'connections':
            return self.count > 2

        return self.name.find('_') == -1

    @property
    def port(self):
        """Return true if node is a port"""

        return self._port or self.count == 1


class Pos(object):

    def __init__(self, x, y):

        self.x = x
        self.y = y

    def __mul__(self, scale):

        return Pos(self.x * scale, self.y * scale)

    def __str__(self):

        xstr = ('%.2f' % self.x).rstrip('0').rstrip('.')
        ystr = ('%.2f' % self.y).rstrip('0').rstrip('.')

        return "%s,%s" % (xstr, ystr)

    def __repr__(self):

        return 'Pos(%s)' % self

    @property
    def xy(self):

        return np.array((self.x, self.y))


class Schematic(object):

    def __init__(self, filename=None, **kwargs):

        self.elements = {}
        self.nodes = {}
        # Shared nodes (with same voltage)
        self.snodes = {}
        self.hints = False

        if filename is not None:
            self.netfile_add(filename)

    def __getitem__(self, name):
        """Return component by name"""
        try:
            return self.elements[name]
        except KeyError:
            raise AttributeError('Unknown component %s' % name)

    def netfile_add(self, filename):
        """Add the nets from file with specified filename"""

        file = open(filename, 'r')

        lines = file.readlines()

        for line in lines:
            self.add(line)

    def netlist(self):
        """Return the current netlist"""

        return '\n'.join([elt.__str__() for elt in self.elements.values()])

    def _invalidate(self):

        for attr in ('_xcnodes', '_ycnodes', '_coords'):
            if hasattr(self, attr):
                delattr(self, attr)

    def _node_add(self, node, elt):

        if node not in self.nodes:
            self.nodes[node] = Node(node)
        self.nodes[node].append(elt)

        vnode = self.nodes[node].rootname

        if vnode not in self.snodes:
            self.snodes[vnode] = []

        if node not in self.snodes[vnode]:
            self.snodes[vnode].append(node)


    def parse(self, string):
        """The general form is: 'Name Np Nm symbol'
        where Np is the positive nose and Nm is the negative node.

        A positive current is defined to flow from the positive node
        to the negative node.
        """

        def tex_name(name, subscript=None):

            if subscript is None:
                subscript = ''

            if len(name) > 1:
                name = r'\mathrm{%s}' % name
            if len(subscript) > 1:
                subscript = r'\mathrm{%s}' % subscript
            if len(subscript) == 0:
                return name
        
            return '%s_{%s}' % (name, subscript)


        if '\n' in string:
            lines = string.split('\n')
            for line in lines:
                self.add(line)
            return

        cpt = parser.parse(string)
        if cpt is None:
            return

        # There are two possible labels for a component:
        # 1. Component identifier, e.g., R1
        # 2. Component value, expression, or symbol
        id_label = tex_name(cpt.type, cpt.id)
        value_label = None

        if cpt.type in ('O', 'P', 'W') or id_label.find('#') != -1:
            id_label = None

        if hasattr(cpt, 'Value'):

            # TODO, extend for mechanical and acoustical components.
            units_map = {'V': 'V', 'I': 'A', 'R': '$\Omega$',
                         'C': 'F', 'L': 'H'}

            expr = cpt.Value
            if cpt.classname in ('Vimpulse', 'Iimpulse'):
                expr = '(%s) * DiracDelta(t)' % expr
                value_label = Expr(expr, cache=False).latex()
            elif cpt.classname in ('Vstep', 'Istep'):
                expr = '(%s) * Heaviside(t)' % expr
                value_label = Expr(expr, cache=False).latex()
            elif cpt.classname in ('Vs', 'Is'):
                value_label = Expr(expr, cache=False).latex()
            elif cpt.classname == 'TF':
                value_label = '1:%s' % expr
            elif cpt.classname not in ('TP',):
                try:
                    value = float(expr)
                    if cpt.type in units_map:
                        value_label = EngFormat(
                            value, units_map[cpt.type]).latex()
                    else:
                        value_label = Expr(expr, cache=False).latex()

                except ValueError:
                    value_label = Expr(expr, cache=False).latex()

        # Currently, we only annnotated the component with the value,
        # expression, or symbol.  If this is not specified, it
        # defaults to the component identifier.  Note, some objects
        # we do not want to label, such as wires and ports.

        cpt.id_label = '' if id_label is None else latex_str(id_label)
        cpt.value_label = '' if value_label is None else latex_str(value_label)
        cpt.default_label = cpt.id_label if cpt.value_label == '' else cpt.value_label

        # Drawing hints
        opts = Opts(cpt.opts_string)

        if 'dir' not in opts:
            opts['dir'] = None
        if 'size' not in opts:
            opts['size'] = 1

        if opts['dir'] is None:
            opts['dir'] = 'down' if cpt.type in ('O', 'P') else 'right'
        cpt.opts = opts

        return cpt

    def add(self, string):
        """The general form is: 'Name Np Nm symbol'
        where Np is the positive nose and Nm is the negative node.

        A positive current is defined to flow from the positive node
        to the negative node.
        """

        cpt = self.parse(string)
        if cpt is None:
            return

        if cpt.opts_string != '':
            self.hints = True

        self._invalidate()

        if cpt.name in self.elements:
            print('Overriding component %s' % cpt.name)
            # Need to search lists and update component.

        self.elements[cpt.name] = cpt

        # Ignore nodes for mutual inductance.
        if cpt.type == 'K':
            return

        nodes = cpt.nodes
        # The controlling nodes are not drawn.
        if cpt.type in ('E', 'G'):
            nodes = nodes[0:2]

        for node in nodes:
            self._node_add(node, cpt)


    def _make_graphs(self, dir='horizontal'):

        # Use components in orthogonal directions as constraints.  The
        # nodes of orthogonal components get combined into a
        # common node.

        cnodes = Cnodes(self.nodes)

        if dir == 'horizontal':
            for m, elt in enumerate(self.elements.values()):
                elt.xlink(cnodes)                
        else:
            for m, elt in enumerate(self.elements.values()):
                elt.ylink(cnodes)                

        # Now form forward and reverse directed graphs using components
        # in the desired directions.
        graphs = Graphs(dir)

        if dir == 'horizontal':
            for m, elt in enumerate(self.elements.values()):
                elt.xplace(graphs, cnodes)                
        else:
            for m, elt in enumerate(self.elements.values()):
                elt.yplace(graphs, cnodes)                

        graphs.add_start_nodes()

        if False:
            print(graphs.fwd)
            print(graphs.rev)
            print(cnodes._node_map)
            import pdb
            pdb.set_trace()

        # Find longest path through the graphs.
        length, node, memo = graphs.fwd.longest_path()
        length, node, memor = graphs.rev.longest_path()

        pos = {}
        posr = {}
        posa = {}

        for node, gnode in cnodes.iteritems():
            pos[node] = length - memo[gnode]
            posr[node] = memor[gnode]
            posa[node] = 0.5 * (pos[node] + posr[node])

        if False:
            print(pos)
            print(posr)
        return posa, cnodes, length

    def _positions_calculate(self):

        # The x and y positions of a component node are determined
        # independently.  The principle is that each component has a
        # minimum size (usually 1 but changeable with the size option)
        # but its wires can be stretched.

        # When solving the x position, first nodes that must be
        # vertically aligned (with the up or down option) are combined
        # into a set.  Then the left and right options are used to
        # form a graph.  This graph is traversed to find the longest
        # path and in the process each node gets assigned the longest
        # distance from the root of the graph.  To centre components,
        # a reverse graph is created and the distances are averaged.

        xpos, self._xcnodes, self.width = self._make_graphs('horizontal')
        ypos, self._ycnodes, self.height = self._make_graphs('vertical')

        coords = {}
        for node in xpos.keys():
            coords[node] = Pos(xpos[node], ypos[node])

        self._coords = coords

    @property
    def xcnodes(self):
        """Names of common x nodes; for debugging"""

        if not hasattr(self, '_xcnodes'):
            self._positions_calculate()
        return self._xcnodes

    @property
    def ycnodes(self):
        """Names of common y nodes; for debugging"""

        if not hasattr(self, '_ycnodes'):
            self._positions_calculate()
        return self._ycnodes

    @property
    def coords(self):
        """Directory of position tuples indexed by node name"""

        if not hasattr(self, '_coords'):
            self._positions_calculate()
        return self._coords

    def _make_wires1(self, snode_list):

        num_wires = len(snode_list) - 1
        if num_wires == 0:
            return []

        wires = []

        # TODO: remove overdrawn wires...
        for n in range(num_wires):
            n1 = snode_list[n]
            n2 = snode_list[n + 1]
            
            wires.append(self.parse('W_ %s %s' % (n1, n2)))

        return wires

    def _make_wires(self):
        """Create implict wires between common nodes."""

        wires = []

        snode_dir = self.snodes

        for m, snode_list in enumerate(snode_dir.values()):
            wires.extend(self._make_wires1(snode_list))

        return wires

    def _tikz_draw(self, style_args='', label_values=True, 
                   draw_nodes=True, label_ids=True,
                   label_nodes='primary'):

        opts = r'scale=%.2f,/tikz/circuitikz/bipoles/length=%.1fcm,%s' % (
            self.node_spacing, self.cpt_size, style_args)
        s = r'\begin{tikzpicture}[%s]''\n' % opts

        # Write coordinates
        for coord in self.coords.keys():
            s += r'  \coordinate (%s) at (%s);''\n' % (
                coord, self.coords[coord])

        # Draw components
        for m, elt in enumerate(self.elements.values()):
            s += elt.draw(nodes=self.nodes, label_values=label_values, 
                          draw_nodes=draw_nodes)

        wires = self._make_wires()

        # Label primary nodes
        if label_nodes:
            for m, node in enumerate(self.nodes.values()):
                if label_nodes == 'primary' and not node.primary:
                    continue
                s += r'  \draw {[anchor=south east] (%s) node {%s}};''\n' % (
                    node.name, node.name.replace('_', r'\_'))

        s += r'\end{tikzpicture}''\n'

        return s

    def _tmpfilename(self, suffix=''):

        from tempfile import gettempdir, NamedTemporaryFile

        # Searches using TMPDIR, TEMP, TMP environment variables
        tempdir = gettempdir()
        
        filename = NamedTemporaryFile(suffix=suffix, dir=tempdir, 
                                      delete=False).name
        return filename

    def _convert_pdf_svg(self, pdf_filename, svg_filename):

        system('pdf2svg %s %s' % (pdf_filename, svg_filename))
        if not path.exists(svg_filename):
            raise RuntimeError('Could not generate %s with pdf2svg' % 
                               svg_filename)

    def _convert_pdf_png(self, pdf_filename, png_filename, oversample=1):

        system('convert -density %d %s %s' %
               (oversample * 100, pdf_filename, png_filename))
        if path.exists(png_filename):
            return

        # Windows has a program called convert, try im-convert
        # for image magick convert.
        system('im-convert -density %d %s %s' %
               (oversample * 100, pdf_filename, png_filename))
        if path.exists(png_filename):
            return

        raise RuntimeError('Could not generate %s with convert' % 
                           png_filename)

    def tikz_draw(self, filename, **kwargs):

        root, ext = path.splitext(filename)

        debug = kwargs.pop('debug', False)
        oversample = float(kwargs.pop('oversample', 2))
        style = kwargs.pop('style', 'american')
        stretch = float(kwargs.pop('stretch', 1.0))
        scale = float(kwargs.pop('scale', 1.0))

        self.node_spacing = 2 * stretch * scale
        self.cpt_size = 1.5 * scale
        self.scale = scale

        if style == 'american':
            style_args = 'american currents,american voltages'
        elif style == 'british':
            style_args = 'american currents, european voltages'
        elif style == 'european':
            style_args = 'european currents, european voltages'
        else:
            raise ValueError('Unknown style %s' % style)

        content = self._tikz_draw(style_args=style_args, **kwargs)

        if debug:
            print('width = %d, height = %d, oversample = %d, stretch = %.2f, scale = %.2f'
                  % (self.width, self.height, oversample, stretch, scale))

        if ext == '.pytex':
            open(filename, 'w').write(content)
            return

        template = ('\\documentclass[a4paper]{standalone}\n'
                    '\\usepackage{circuitikz}\n'
                    '\\begin{document}\n%s\\end{document}')
        content = template % content

        texfilename = filename.replace(ext, '.tex')
        open(texfilename, 'w').write(content)

        if ext == '.tex':
            return

        dirname = path.dirname(texfilename)
        baseroot = path.basename(root)
        cwd = getcwd()
        if dirname != '':
            chdir(path.abspath(dirname))

        system('pdflatex -interaction batchmode %s.tex' % baseroot)

        if dirname != '':
            chdir(cwd)            

        if not debug:
            try:
                remove(root + '.aux')
                remove(root + '.log')
                remove(root + '.tex')
            except:
                pass

        pdf_filename = root + '.pdf'
        if not path.exists(pdf_filename):
            raise RuntimeError('Could not generate %s with pdflatex' % 
                               pdf_filename)

        if ext == '.pdf':
            return

        if ext == '.svg':
            self._convert_pdf_svg(pdf_filename, root + '.svg')
            if not debug:
                remove(pdf_filename)
            return

        if ext == '.png':
            self._convert_pdf_png(pdf_filename, root + '.png', oversample)
            if not debug:
                remove(pdf_filename)
            return

        raise ValueError('Cannot create file of type %s' % ext)

    def draw(self, filename=None, opts={}, **kwargs):

        for key, val in opts.iteritems():
            if key not in kwargs or kwargs[key] is None:
                kwargs[key] = val

        def in_ipynb():
            try:
                ip = get_ipython()
                cfg = ip.config

                kernapp = cfg['IPKernelApp']

                # Check if processing ipynb file.
                if 'connection_file' in kernapp:
                    return True
                elif kernapp and kernapp['parent_appname'] == 'ipython-notebook':
                    return True
                else:
                    return False
            except (NameError, KeyError):
                return False

        if not self.hints:
            raise RuntimeWarning('No schematic drawing hints provided!')

        png = 'png' in kwargs and kwargs.pop('png')
        svg = 'svg' in kwargs and kwargs.pop('svg')

        if not png and not svg:
            png = True

        if in_ipynb() and filename is None:

            if png:
                from IPython.display import Image, display_png

                pngfilename = self._tmpfilename('.png')
                self.tikz_draw(pngfilename, **kwargs)

                # Create and display PNG image object.
                # There are two problems:
                # 1. The image metadata (width, height) is ignored
                #    when the ipynb file is loaded.
                # 2. The image metadata (width, height) is not stored
                #    when the ipynb file is written non-interactively.
                display_png(Image(filename=pngfilename,
                                  width=self.width * 100, 
                                  height=self.height * 100))
                return

            if svg:
                from IPython.display import SVG, display_svg

                svgfilename = self._tmpfilename('.svg')
                self.tikz_draw(svgfilename, **kwargs)

                # Create and display SVG image object.
                # Note, there is a problem displaying multiple SVG
                # files since the later ones inherit the namespace of
                # the first ones.
                display_svg(SVG(filename=pngfilename, 
                                width=self.width * 100, height=self.height * 100))
                return

        display = False
        if filename is None:
            filename = self._tmpfilename('.png')
            display = True

        self.tikz_draw(filename=filename, **kwargs)
        
        if display:
            # TODO display as SVG so have scaled fonts...

            from matplotlib.pyplot import figure
            from matplotlib.image import imread

            img = imread(filename)

            fig = figure()
            ax = fig.add_subplot(111)
            ax.imshow(img)
            ax.axis('equal')
            ax.axis('off')

def test():

    sch = Schematic()

    sch.add('P1 1 0.1')
    sch.add('R1 1 3; right')
    sch.add('L1 3 2; right')
    sch.add('C1 3 0; down')
    sch.add('P2 2 0.2')
    sch.add('W 0.1 0; right')
    sch.add('W 0 0.2; right')

    sch.draw()
    return sch
