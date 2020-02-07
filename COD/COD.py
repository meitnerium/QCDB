import csv
import cif2cell
#import str
import numpy as np
import re
import os
import urllib
import requests
#from crystals import Crystal
import CifFile
import subprocess
from cif2cell.utils import *
from cif2cell.uctools import *
#from cif2cell.ESPInterfaces import *
from cif2cell.elementdata import *
from six.moves import range

#from __future__ import division
#from __future__ import absolute_import
#from __future__ import print_function
import os
import sys
import string
import copy
from math import *
from datetime import datetime
from optparse import OptionParser, OptionGroup
import warnings
import CifFile
import subprocess
from cif2cell.utils import *
from cif2cell.uctools import *
from cif2cell.ESPInterfaces import *
from cif2cell.elementdata import *
from six.moves import range


relpz_PPREP="/home/fradion12/QE/pslibrary/rel-pw91/PSEUDOPOTENTIALS/"
PP='rel-pz'

################################################################################################
# PWSCF (Quantum Espresso)
class PWSCFFileFD(GeometryOutputFile):
    """
    Class for storing the geometrical data for a PWSCF run and the method
    __str__ that outputs to a .in file as a string.
    """
    def __init__(self, crystalstructure, string, kresolution=0.2):
        GeometryOutputFile.__init__(self,crystalstructure,string)
        #
        self.setupall = False
        # Cartesian units?
        self.cartesian = False
        self.cartesianpositions = False
        self.cartesianlatvects = False
        self.scaledcartesianpositions = False
        # What units?
        self.unit = "angstrom"
        self.cell.newunit("angstrom")
        # Pseudopotential string
        self.pseudostring = "_PSEUDO"
        # set up species list
        tmp = set([])
        for a in self.cell.atomdata:
            for b in a:
                tmp.add(b.spcstring())
        self.species = list(tmp)
        # k-space information
        reclatvect = self.cell.reciprocal_latticevectors()
        for j in range(3):
            for i in range(3):
                reclatvect[j][i] = reclatvect[j][i] / self.cell.lengthscale
        # Lengths of reciprocal lattice vectors
        reclatvectlen = [elem.length() for elem in reclatvect]
        self.kgrid = [max(1,int(round(elem/kresolution))) for elem in reclatvectlen]
        # Make sure the docstring has comment form
        self.docstring = self.docstring.rstrip("\n")
        tmpstrings = self.docstring.split("\n")
        self.docstring = ""
        for string in tmpstrings:
            string = string.lstrip("#")
            string = "#"+string+"\n"
            self.docstring += string
        self.docstring += "\n"
    def __str__(self):
        filestring = self.docstring
        # Set current units and stuff
        if self.cartesian:
            self.cartesianpositions = True
            self.cartesianlatvects = True
        self.cell.newunit(self.unit)
        # Determine max width of spcstring
        width = 0
        for a in self.cell.atomdata:
            for b in a:
                width = max(width, len(b.spcstring()))
        #
        filestring += "&CONTROL\n"
        filestring += "    title = 'QE'\n"
        filestring += "    calculation = 'vc-relax'\n"
        filestring += "    restart_mode = 'from_scratch'\n"
        filestring += "    outdir = './1'\n"
        filestring += "    pseudo_dir = '"+relpz_PPREP+"'\n"
        filestring += "    prefix = 'QE'\n"
        filestring += "    etot_conv_thr = 0.0001\n"
        filestring += "    forc_conv_thr = 0.001\n"
        filestring += "    nstep = 400\n"
        filestring += "    wf_collect=.true.\n"
        filestring += "/\n"
        filestring += "&SYSTEM\n"
        filestring += "  ibrav = %i\n"%(0)
        if self.unit == "bohr":
            filestring += "  celldm(1) = %10.5f\n"%(self.cell.lengthscale)
        elif self.unit == "angstrom":
            filestring += "  A = %10.5f\n"%(self.cell.lengthscale)
        filestring += "  nat = %i\n"%(self.cell.natoms())
        filestring += "  ntyp = %i\n"%(len(self.species))
        filestring += "  ecutwfc = 60\n"
        filestring += "  ecutrho = 480\n"









        filestring += "/\n"
        filestring += "&ELECTRONS  \n"
        filestring += "    electron_maxstep = 6000\n"
        filestring += "    conv_thr = 1.0D-7\n"
        filestring += "    diago_thr_init = 1e-4\n"
        filestring += "    startingpot = 'atomic'\n"
        filestring += "    startingwfc = 'atomic'\n"
        filestring += "    mixing_mode = 'plain'\n"
        filestring += "    mixing_beta = 0.5\n"
        filestring += "    mixing_ndim = 8\n"
        filestring += "    diagonalization = 'david'\n"
        filestring += "/    \n"
        filestring += "&IONS    \n"
        filestring += "    ion_dynamics = 'bfgs'\n"
        filestring += "/    \n"
        filestring += "&CELL    \n"
        filestring += "    cell_dynamics = 'bfgs'\n"
        filestring += "/    \n"
        filestring += "    \n"

        if self.cartesianlatvects:
            if self.unit == "bohr":
                filestring += "CELL_PARAMETERS {bohr}\n"
            elif self.unit == "angstrom":
                filestring += "CELL_PARAMETERS {angstrom}\n"
            t = LatticeMatrix(self.cell.latticevectors)
            for i in range(3):
                for j in range(3):
                    t[i][j] = self.cell.latticevectors[i][j]*self.cell.lengthscale
            filestring += str(t)
        else:
            filestring += "CELL_PARAMETERS {alat}\n"
            filestring += str(self.cell.latticevectors)
        filestring += "ATOMIC_SPECIES\n"
        for sp in self.species:
                filestring += "  %2s"%(sp.rjust(width))
                try:
                    filestring += ("  %8.5f"%(ed.elementweight[sp])).rjust(11)
                except:
                    filestring += "   ???".rjust(11)
                if PP == 'PBE':
                  self.getpseudopbe(sp.rjust(width))
                elif PP == 'rel-pw91':
                   self.getpseudorelpw91(sp.rjust(width))

                filestring += "  %2s%s\n"%(sp.rjust(width),self.pseudostring)
        if self.cartesianpositions:
            if self.scaledcartesianpositions:
                filestring += "ATOMIC_POSITIONS {alat}\n"
            else:
                if self.unit == "bohr":
                    filestring += "ATOMIC_POSITIONS {bohr}\n"
                elif self.unit == "angstrom":
                    filestring += "ATOMIC_POSITIONS {angstrom}\n"
        else:
            if self.scaledcartesianpositions:
                filestring += "ATOMIC_POSITIONS {alat}\n"
            else:
                filestring += "ATOMIC_POSITIONS {crystal}\n"
        for a in self.cell.atomdata:
            for b in a:
                if self.cartesianpositions:
                    t = Vector(mvmult3(self.cell.latticevectors,b.position))
                    if self.scaledcartesianpositions:
                        filestring += b.spcstring().rjust(width)+" "+str(t)+"\n"
                    else:
                        for i in range(3):
                            t[i] = self.cell.lengthscale*t[i]
                        filestring += b.spcstring().rjust(width)+" "+str(t)+"\n"
                else:
                    if self.scaledcartesianpositions:
                        t = Vector(mvmult3(self.cell.latticevectors,b.position))
                        filestring += b.spcstring().rjust(width)+" "+str(t)+"\n"
                    else:
                        filestring += b.spcstring().rjust(width)+" "+str(b.position)+"\n"
        # Add k-space mesh

        if self.setupall:
            filestring += "\n# k-space resolution ~"+str(self.kresolution)+"/A.\n"
            # Opt for gamma-point run if possible
            if self.kgrid[0]*self.kgrid[1]*self.kgrid[2] == 1:                
                filestring += "K_POINTS gamma\n"
            else:
                filestring += "K_POINTS automatic\n"
                filestring += str(self.kgrid[0])+" "+str(self.kgrid[1])+" "+str(self.kgrid[2])+"  0 0 0\n"
        filestring += "\n# k-space resolution ~\n"
        filestring += "K_POINTS automatic\n"
        filestring += "1  1  1   0 0 0\n"
        

        return filestring
    # Return the PWscf internal bravais lattice number
    def getpseudorelpw91(self,atom):
        atom = atom.replace(" ","")

    def getpseudopbe(self,atom):
        atom = atom.replace(" ","")

        #H.rel-pw91-kjpaw_psl.1.0.0.UPF
        #H.rel-pw91-rrkjus_psl.1.0.0.UPF
        BEGIN="rel-pw91-kjpaw_psl.1.0.0.UPF"
        if atom == "H" or atom == "He":
           self.pseudostring = ".rel-pw91-kjpaw_psl.1.0.0.UPF"
        #3
        elif atom == "Li" or atom == "Be":
           self.pseudostring = ".rel-pw91-s-kjpaw_psl.1.0.0.UPF"
        #5
        elif atom == "B" or atom == "C" or atom == "N" or atom == "O" or atom == "F" or atom == "Ne" or atom == "Al" or atom == "Si" or atom == "P" or atom == "S" \
         or atom == "Cl" or atom == "Ar" or atom == "Fe" or atom == "Co" or atom == "Ni" or atom == "Au" or atom == "Cd" or atom == "Ir" or atom == "Pt" or atom == "Au" \
         or atom == "Hg":
           self.pseudostring = ".rel-pw91-n-kjpaw_psl.1.0.0.UPF"


        #11
        elif atom == "Na" or atom == "Mg" or atom == "K" or atom == "Ca" or atom == "Sc" or atom == "Ti" or atom == "V" or atom == "Cr" or atom == "Mn" \
         or  atom == "Rb" or atom == "Sr" or atom == "Y" or atom == "Zr" or atom == "Nb" or atom == "Mo" or atom == "Tc" or atom == "Ru" or atom == "Rh" \
         or  atom == "Cs" or atom == "Ba":
           self.pseudostring = ".rel-pw91-spn-kjpaw_psl.1.0.0.UPF"
        elif atom == "Cu" or atom == "Zn" or atom == "Ga" or atom == "Ge" or atom == "As" or atom == "Se" or atom == "Br" or atom == "Kr" or atom == "Pd" \
         or  atom == "In" or atom == "Sn" or atom == "Sb" or atom == "Te" or atom == "I" or atom == "Xe" or atom == "Tl" or atom == "Pb" or atom == "Bi" \
         or atom == "Po" or atom == "At" or atom == "Rn":
           self.pseudostring = ".rel-pw91-dn-kjpaw_psl.1.0.0.UPF"
        elif  atom == "La" or atom == "Ce" or atom == "Pr" or atom == "Nd" or atom == "Pm" or atom == "Sm" or atom == "Eu" or atom == "Gd" or atom == "Tb" \
        or atom == "Dy" or atom == "Ho" or atom == "Er" or atom == "Tm" or atom == "Yb" or atom == "Lu" or atom == "Hf" or atom == "Ta" or atom == "W" or atom == "Re" \
        or atom == "Os" or atom == "Ac" or atom == "Th" or atom == "Pa" or atom == "U" or atom == "Np" or atom == "Pu" or atom == "Am":
           self.pseudostring = ".rel-pw91-spdfn-kjpaw_psl.1.0.0.UPF"
        elif  atom == "Fr" or atom == "Ra": 
           self.pseudostring = ".rel-pw91-spdn-kjpaw_psl.1.0.0.UPF"

        else:
           f = open('../nopseudo.txt','a')
           f.write(atom+"\n")
           f.close()


#
#
#
#
#
#
#
#
#
#        if atom == "Nd":
#           self.pseudostring = ".GGA-PBE-paw-v1.0.UPF"
#        elif atom == "Al":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "Mo":
#           self.pseudostring = ".pbe-spn-kjpaw_psl.1.0.0.UPF"
#        elif atom == "O" or atom == " O" or atom == "  O" or atom == "   O":
#           self.pseudostring = ".pbe-n-kjpaw_psl.0.1.UPF"
#        elif atom == "P" or atom == " P" or atom == "  P" or atom == "   P":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "S" or atom == " S" or atom == "  S" or atom == "   S":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "B" or atom == " B" or atom == "  B" or atom == "   B":
#           self.pseudostring = "_pbe_v1.01.uspp.F.UPF"
#        elif atom == "K" or atom == " K" or atom == "  K" or atom == "   K":
#           self.pseudostring = ".pbe-spn-kjpaw_psl.1.0.0.UPF"
#        elif atom == "Ni":
#           self.pseudostring = ".pbe-sp-mt_gipaw.UPF"
#        elif atom == "Li":
#           self.pseudostring = ".pbe-s-kjpaw_psl.1.0.0.UPF"
#        elif atom == "Cu":
#           self.pseudostring = "_ONCV_PBE-1.0.upf"
#        elif atom == "C" or atom == " C" or atom == "  C" or atom == "   C" or atom == "    C":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "N" or atom == " N" or atom == "  N" or atom == "   N" or atom == "    N":
#           self.pseudostring = ".oncvpsp.upf"
#        elif atom == "F" or atom == " F" or atom == "  F" or atom == "   F" or atom == "    F":
#           self.pseudostring = ".oncvpsp.upf"
#        elif atom == "Zn":
#           self.pseudostring = "_pbe_v1.uspp.F.UPF"
#        elif atom == "Te":
#           self.pseudostring = "_pbe_v1.uspp.F.UPF"
#        elif atom == "Cl":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "Si":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "Sb":
#           self.pseudostring = ".pbe-n-kjpaw_psl.1.0.0.UPF"
#        elif atom == "Br":
#           self.pseudostring = ".pbe-dn-kjpaw_psl.1.0.0.UPF"


    def ibrav(self):
        system = self.cell.crystal_system()
        setting = self.cell.spacegroupsetting
        if self.supercell:
            return 14
        if system == 'cubic':
            if self.primcell:
                if setting == 'P':
                    return 1
                elif setting == 'F':
                    return 2
                elif setting == 'I':
                    return 3
            else:
                return 1
        if system == 'hexagonal':
            if self.primcell:
                if setting == 'P':
                    return 4
                elif setting == 'R':
                    return 5
        

def cif2cellfunc(cif_file, outputprogram = 'quantum-espresso'):

    outputprogram = 'pwscf'

    # Name and version
    programname = "cif2cell"
    version = "2.0.0"

    # Turn of warnings about deprecated stuff
    warnings.simplefilter("ignore",DeprecationWarning)

    # All supported output formats
    outputprograms = set(['abinit','atat','castep','cfg','coo','cpmd','cp2k','crystal09','elk','emto','exciting','fhi-aims',
                          ## 'fleur','ncol','mcsqs','rspt','siesta','sprkkr','vasp', # mcsqs not ready
                          'fleur','hutsepot','lammps','mopac','ncol', 'pwscf', 'quantum-espresso', 'rspt','siesta','sprkkr','vasp',
                          'ase','bmdl','cellgen','cif','kgrn','kfcd','kstr','shape','spacegroup',
                          'spc','xband','xyz'])

    # Programs that can deal with alloys
    alloyprograms = set(["atat","cfg","emto","kstr","bmdl","shape","kgrn","kfcd","cif","spc","sprkkr","xband"])
    vcaprograms = set(["castep","vasp"])
    #
    setupallprogs = set(["vasp","pwscf","quantum-espresso","rspt","mopac"])
    setupallstring = ""
    for p in setupallprogs:
        setupallstring += p+", "
    setupallstring = setupallstring.rstrip(", ")
    #
    programlist = sorted(list(outputprograms))
    outputprogramstring = ""
    for p in programlist:
        outputprogramstring += p+", "
    outputprogramstring = outputprogramstring.rstrip(", ")

    ############################
    #      INPUT OPTIONS       #
    ############################
    description = "A program for generating input lattice structures to various electronic structure programs from a CIF (Crystallographic Information Framework) file. This code was published in Comput. Phys. Commun. 182, 1183 (2011). Please cite generously."
    usage = "usage: %prog FILE [-p PROGRAM] [other options]"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--version",dest="version",help="Print version number.",action="store_true")
    parser.add_option("-v","--verbose",dest="verbose",help="Be as verbose as possible.",action="store_true")
    parser.add_option("-q","--quiet",dest="quiet",help="Suppress all but explicitly requested screen output. Overrides --verbose flag.",action="store_true")
    # GENERAL OPTIONS
    generalopts = OptionGroup(parser, "General options")
    generalopts.add_option("-f","--file",dest="file",help="Input CIF file, unless given as first argument to the program.",metavar="FILE")
    generalopts.add_option("-p","--program",dest="program",help="The electronic structure code you want to create input file(s) for. Currently supports: "+outputprogramstring+". This keyword is case insensitive.")
    generalopts.add_option("-o","--outputfile",dest="outputfile",help="Name of output file (if other than default for you electronic structure code).",metavar="FILE")
    generalopts.add_option("-a","--append",dest="append",help="Append the output to given output file rather than overwriting.",action="store_true")
    generalopts.add_option("--grammar",dest="grammar",help="Set the CIF grammar to be used when parsing the input file (default is 1.1).")
    generalopts.add_option("--which-filename",dest="filenamequery",help="If given together with the --program option, the name of the output file will be printed to screen.",action="store_true")
    generalopts.add_option("-b","--block",dest="block",help="Block of data in input file (if there are more than one block in the CIF file).")
    # CELL GENERATION OPTIONS
    cellgenopts = OptionGroup(parser, "Cell generation options")
    cellgenopts.add_option("--no-reduce",dest="noreduce",help="Do not reduce to the primitive cell.",action="store_true")
    cellgenopts.add_option("--force",dest="force",help="Attempt to force generation of output file despite problems and/or ambiguities in the input file. There are no guarantees that what you get makes sense, but the program makes an honest attempt. Implies --force-alloy.",action="store_true")
    cellgenopts.add_option("--force-alloy",dest="forcealloy",help="Force generation of output file for an alloy compound for an electronic structure code that does not implement any alloy theory (such as CPA).",action="store_true")
    cellgenopts.add_option("--vca",dest="vca",help="Set up an alloy using the virtual crystal approximation (VCA). Currently only supported by the CASTEP interface.",action="store_true")
    cellgenopts.add_option("--cartesian",dest="cartesian",help="Make the program generate any output in cartesian coordinates.",action="store_true")
    cellgenopts.add_option("--coordinate-tolerance",dest="coordtol",help="Parameter for determining when two coordinates are the same (default=0.0002).")
    cellgenopts.add_option("--setup-all",dest="setupall",help="Make a more complete setup, not just the geometrical part. This is currently only available for "+setupallstring+".",action="store_true")
    cellgenopts.add_option("--k-resolution",dest="kresolution",help="The desired resolution in k-space (default=0.2). Used for generating k-space grid options if --setup-all is specified.")
    cellgenopts.add_option("--transform-cell",dest="celltransformation",help="Transformation matrix applied to the lattice vectors and the symmetry operations if you, for example, want to realign the cell.",metavar="[[],[],[]]")
    cellgenopts.add_option("--body-centred-setting",dest="specialIsetting",help="If set to 1, use the more symmetrical set of primitive translation vectors used for the bcc structure also for other body-centred crystals.",metavar="0,1")
    cellgenopts.add_option("--cubic-diagonal-z",dest="cubediagz",help="Set up cubic cell with [111] direction along the z-axis.",action="store_true")
    cellgenopts.add_option("--rhombohedral-diagonal",dest="rhombdiag",help="Set up rhombohedral cell with threefold axis along pseudocubic [111] direction.",action="store_true")
    cellgenopts.add_option("--random-displacements",dest="randomdisp",help="Randomly displace all atoms. Depending on the distribution, the displacement size is either the maximal displacement (for uniform distribution) or the standard deviation (for gaussian distribution) in Angstrom.",metavar="displacementsize")
    cellgenopts.add_option("--random-displacements-distribution",dest="randomdistr",help="The distribution used for displacing the atoms.",metavar="uniform/gaussian")
    cellgenopts.add_option("--export-cif-labels",dest="exportlabels",help="Export atom labels from the CIF file (currently only supported for castep and RSPt).",action="store_true")
    # SUPERCELL OPTIONS
    supercellopts = OptionGroup(parser, "Supercell generation options")
    supercellopts.add_option("--supercell",dest="supercellmap",help="Three integers separated with commas and enclosed in square brackets that specify the dimensions of a supercell OR three vectors of integers that gives the map to the supercell to be constructed from the primitive cell. If combined with the --no-reduce option the supercell will instead be generated based on the conventional cell.",metavar="[k,l,m]/[[],[],[]]")
    supercellopts.add_option("--supercell-dimensions",dest="supercelldims",help="Three numbers separated with commas and enclosed in square brackets that specify the desired ABSOLUTE dimensions of a supercell (in angstrom) OR three vectors of numbers that gives the desired lattice vectors. The program will automatically generate a supercell, attempting to get as close as possible to the desired dimensions.",metavar="[x,y,z]/[[],[],[]]")
    supercellopts.add_option("--supercell-vacuum",dest="supercellvacuum",help="Three numbers >=0 separated with commas and enclosed in square brackets that specify a number of unit cell units of vacuum to be added along the first, second or third of the generated lattice vectors.",metavar="[k,l,m]")
    supercellopts.add_option("--supercell-translation-vector","--supercell-prevacuum-translation",dest="supercellprevactransvec",help="Three numbers separated with commas and enclosed in square brackets that specify a shift of all atomic positions in the cell prior to vacuum generation (in units of the lattice vectors of the supercell).",metavar="[k,l,m]")
    supercellopts.add_option("--supercell-postvacuum-translation",dest="supercellpostvactransvec",help="Three numbers separated with commas and enclosed in square brackets that specify a final shift of all atomic positions in the final cell (in units of the lattice vectors of the new cell).",metavar="[k,l,m]")
    supercellopts.add_option("--supercell-realign",dest="supercellrealign",help="Realign the supercell lattice vectors with respect to the cartesian reference frame. For orthorhombic cells, it puts the first, second and third lattice vectors along x, y and z, respectively.",metavar="0,1")
    supercellopts.add_option("--supercell-sort",dest="supercellsort",help="Sort the atom positions by some scheme. Currently available are: \n1) By cartesian coordinate - example: xzy will sort first on x then on z then on y. \n2) by lattice vector - example: 132 will sort first by lattice vector 1 then by lattice vector 3 and last by lattice vector 2.")
    # SURFACE OPTIONS
    surfaceopts = OptionGroup(parser, "Surface generation options")
    surfaceopts.add_option("--surface-wizard",dest="surfacewizardhkl",help="Three integers separated with commas and enclosed in square brackets that specify a (hkl) plane. The wizard will suggest a supercell map that gives the first two lattice vectors in the (hkl) plane. The third lattice vector is selected as the [hkl] direction, or reasonably orthogonal to the (hkl) plane (if the [hkl] direction is far from orthogonal to this plane).",metavar="[h,k,l]")
    # PRINTING OPTIONS
    printopts = OptionGroup(parser, "Printing options")
    printopts.add_option("--print-digits",dest="printdigits",help="Number of digits used when printing coordinates etc. to screen (default=8). Useful if you need to tweak the screen output for cutting and pasting into some unsupported program. There is no point in going over 16 because of the floating point accuracy.")
    printopts.add_option("--print-atomic-units",dest="printau",help="Output lattice parameters in bohrradii rather than angstrom.",action="store_true")
    printopts.add_option("--print-cartesian",dest="printcart",help="Atomic sites printed to screen in cartesian rather than lattice coordinates.",action="store_true")
    printopts.add_option("--print-symmetry-operations",dest="printsymops",help="Print symmetry operations of the generated cell.",action="store_true")
    printopts.add_option("--print-seitz-matrices",dest="printseitz",help="Print symmetry operations of the generated cell in Seitz matrix form.",action="store_true")
    printopts.add_option("--print-charge-state","--print-oxidation-numbers",dest="printcharges",help="Print information about the oxidation state from the CIF file.",action="store_true")
    printopts.add_option("--print-reference-bibtex",dest="bibtexref",help="Print citation in BibTeX format and exit.",action="store_true")
    # PROGRAM SPECIFIC OPTIONS
    progspec = OptionGroup(parser, "Program specific options")
    # abinit
    progspec.add_option("--abinit-braces",dest="abinitbraces",help="Put curly braces around input values for ABINIT.",action="store_true")
    # cellgen
    progspec.add_option("--cellgen-map",dest="cellgenmap",help="Nine integers separated with commas and enclosed three and three in square brackets (this is a matrix in Python) that specify the map to a supercell to be output for the RSPt supercell generator 'cellgen'. Overrides --cellgen-supercell-dims.",metavar="[[k,l,m],[n,o,p],[q,r,s]]")
    progspec.add_option("--cellgen-supercell-dimensions",dest="cellgensupercelldims",help="Three integers separated with commas and enclosed in square brackets that specify the dimensions of a supercell to be output to the RSPt supercell generator 'cellgen' (the diagonal elements of the 'map').",metavar="[k,l,m]")
    progspec.add_option("--cellgen-reference-vector",dest="cellgenrefvec",help="Three reals separated with commas and enclosed in square brackets that specify an optional shift of the origin used by the RSPt supercell generator 'cellgen'.",metavar="[x,y,z]")
    # CASTEP
    progspec.add_option("--castep-cartesian",dest="castepcartesian",help="Output atom positions in cartesian rather than lattice coordinates.",action="store_true")
    progspec.add_option("--castep-atomic-units",dest="castepatomicunits",help="Output to CASTEP in atomic units (bohr radii) rather than angstrom.",action="store_true")
    # CPMD
    progspec.add_option("--cpmd-cutoff",dest="cpmdcutoff",help="Set the cutoff written to the &SYSTEM block (default=100.0 Ry).")
    # Crystal09
    progspec.add_option("--crystal09-rhombohedral-setting",dest="crystal09rhombohedral",help="For trigonal spacegroups where this is possible, specify the rhombohedral cell in the Crystal09 input.", action="store_true")
    # emto
    progspec.add_option("--emto-hard-sphere-radii",dest="hardsphereradii",help="Set hard spheres in KSTR to something other than the default (=0.67).")
    # FHI-AIMS
    progspec.add_option("--fhi-aims-cartesian", dest="aimscartesian", help="Store the coordinates for FHI-AIMS in cartesian format.", action="store_true")
    # MOPAC
    progspec.add_option("--mopac-first-line", dest="mopacfirstline", help="String to be used for the first line (the run commands) of the MOPAC input.",metavar='"string"')
    progspec.add_option("--mopac-second-line", dest="mopacsecondline", help="String to be used for the second line (documentation) of the MOPAC input.",metavar='"string"')
    progspec.add_option("--mopac-third-line", dest="mopacthirdline", help="String to be used for the third line (documentation) of the MOPAC input.",metavar='"string"')
    progspec.add_option("--mopac-freeze-structure", dest="mopacfreeze", help="If set to 'T' then add a 0 after each coordinate (freezing the structure), if set to 'F' then add a 1 (allowing everything to relax).",metavar='T/F')
    # PWSCF
    progspec.add_option("--pwscf-pseudostring",dest="pwscfpseudostring",help='String to attach to the element name to identify the pseudopotential file (e.g. something like "_HSCV_PBE-1.0.UPF").',metavar="_PSEUDO")
    progspec.add_option("--pwscf-atomic-units",dest="pwscfatomicunits",help="Write PWSCF .in file in atomic units (bohr) rather than angstrom.",action="store_true")
    progspec.add_option("--pwscf-alat-units",dest="pwscfalatunits",help="Use 'alat' units for the positions in the PWSCF .in file.",action="store_true")
    progspec.add_option("--pwscf-cartesian",dest="pwscfcart",help="Write lattice vectors and positions to PWSCF .in file in cartesian coordinates and set the lengths scale to 1.",action="store_true")
    progspec.add_option("--pwscf-cartesian-latticevectors",dest="pwscfcartvects",help="Write lattice vectors to PWSCF .in file in cartesian coordinates and set the lengths scale to 1.",action="store_true")
    progspec.add_option("--pwscf-cartesian-positions",dest="pwscfcartpos",help="Write lattice positions to PWSCF .in file in cartesian coordinates.",action="store_true")
    # RSPt
    progspec.add_option("--rspt-new", dest="newsymt", help="Generate a symt.inp file in the new format.", action="store_true")
    progspec.add_option("--rspt-spinpol", dest="rsptspinpol", help="Generate new format symt.inp file with spin polarization.", action="store_true")
    progspec.add_option("--rspt-relativistic", dest="rsptrelativistic", help="Generate new format symt.inp file with relativistic effects.", action="store_true")
    progspec.add_option("--rspt-spinaxis", dest="rsptspinaxis", help="Spin axis for symt.inp (default is [0.0,0.0,0.0].", metavar="[x,y,z]")
    progspec.add_option("--rspt-no-spin", dest="rsptnospin", help="Force a nonmagnetic setup in conjunction with --setup-all.", action="store_true")
    progspec.add_option("--rspt-mtradii", dest="rsptmtradii", help="Integer that gives the method for setting muffin tin radii.", metavar="N")
    progspec.add_option("--rspt-cartesian-latticevectors", dest="rsptcartlatvects", help="Put lattice vectors in atomic units and the lenght scale parameter to 1.", action="store_true")
    progspec.add_option("--rspt-pass-wyckoff", dest="rsptpasswyckoff", help="Pass wyckoff labels from CIF file to the symt/rspt.inp file.", action="store_true")
    # SPRKKR/xband
    progspec.add_option("--sprkkr-minangmom",dest="sprkkrminangmom",help="Enforce minimum onsite angular momentum (=l+1, so that 3 will be d-states).")
    # spacegroup
    progspec.add_option("--spacegroup-supercell",dest="spacegroupsupercell",help="Three integers separated with commas and enclosed in square brackets that specify the dimensions of a supercell to be output to the elk input generator 'spacegroup'.",metavar="[k,l,m]")
    # VASP
    progspec.add_option("--vasp-format",dest="vaspformat",help="Format of the generated POSCAR file, either 4 or 5. Default is 4.")
    progspec.add_option("--vasp-print-species",dest="vaspprintspcs",help="Print the atomic species to screen in the order they are put in the POSCAR file (useful for scripting).",action="store_true")
    progspec.add_option("--vasp-cartesian",dest="vaspcart",help="Write lattice vectors and positions to POSCAR file in cartesian coordinates and set length to 1.",action="store_true")
    progspec.add_option("--vasp-cartesian-lattice-vectors",dest="vaspcartvecs",help="Write lattice vectors to POSCAR file in cartesian coordinates and set the length scale to 1.",action="store_true")
    progspec.add_option("--vasp-cartesian-positions",dest="vaspcartpos",help="Write atomic positions to POSCAR file in Cartesian rather than Direct coordinates.",action="store_true")
    progspec.add_option("--vasp-selective-dynamics",dest="vaspselectivedyn",help="Output POSCAR in selective dynamics format (without any constrained atoms).",action="store_true")
    progspec.add_option("--vasp-pseudo-libdr",dest="vasppseudolib",help="Path to the VASP pseudopotential library. Also settable by the VASP_PAWLIB environment variable.")
    progspec.add_option("--vasp-pseudo-priority",dest="vasppppriority",help="Set the priority of different pseudopotentials by a list of suffixes. Also available via the VASP_PP_PRIORITY environment variable.", metavar='"_d,_pv,_sv,_h,_s"')
    progspec.add_option("--vasp-encutfac",dest="vaspencutfac",help="Factor that multiplies the maximal ENCUT found in the POTCAR file.", metavar="1.5")
    # xyz
    progspec.add_option("--xyz-atomic-units",dest="xyzatomicunits",help="Output xyz file in atomic units (bohr radii) rather than angstrom.",action="store_true")
    #
    parser.add_option_group(generalopts)
    parser.add_option_group(cellgenopts)
    parser.add_option_group(supercellopts)
    parser.add_option_group(surfaceopts)
    parser.add_option_group(printopts)
    parser.add_option_group(progspec)
    (options,args) = parser.parse_args()
    options.pwscfcartpos = True

    # Print version number and exit
    if options.version:
        sys.stdout.write(programname+" version "+version+"\n")
        sys.exit(0)

    #############################################################
    # Check that options given are possible
    if options.append and not options.outputfile:
        sys.stderr.write("***Error: option --append requires an output file to be specified.\n")
        sys.exit(1)
    if options.append and (options.program == 'emto' or options.program == 'ncol'):
        sys.stderr.write("***Error: option --append can not be used with "+options.program+".\n")
        sys.exit(1)
    if options.setupall and options.program not in setupallprogs:
        sys.stderr.write("***Error: option --setup-all not supported for "+options.program+".\n")
        sys.exit(1)
    if options.filenamequery and not options.program:
        sys.stderr.write("***Error: option --which-filename requires that --program is given.\n")
        sys.exit(1)
    if options.supercellmap and options.supercelldims:
        sys.stderr.write("***Error: cannot use both --supercell and --supercell-dimensions.\n")
        sys.exit(1)


    print("OUTPUTPROG = "+outputprogram)
    #############################################################
    # INITIAL PARSING OF VARIOUS INPUT DATA
    # Electronic structure program
    if options.program:
        outputprogram = options.program.lower()
        if not outputprogram in outputprograms:
            sys.stderr.write("Error: Unknown output format: "+outputprogram+"\n")
            sys.exit(1)
        # Quantum Espresso is just an alias...
        if outputprogram == 'quantum-espresso':
            outputprogram = 'pwscf'
    #else:
    #    outputprogram = None

    print("OUTPUTPROG = "+outputprogram)
    # recast some input parameters
    if options.noreduce:
        reducetoprim = False
    else:
        reducetoprim = True

    try:
        printdigits = int(options.printdigits)
    except:
        printdigits = 8

    # Set verbosity level
    if options.verbose and not options.quiet:
        verbose = True
    else:
        verbose = False

    # Various parameters
    # Cartesian?
    if options.cartesian:
        options.castepcartesian = True
        options.printcart = True
        options.vaspcart = True
        options.aimscartesian = True
    # Output reference in specific format?
    if options.bibtexref:
        bibtexref = True
    else:
        bibtexref = False
    # Force generation despite problems?
    options.force = True
    if options.force:
        force = True
    else:
        force = False
    # force output for alloys
    if options.forcealloy or force:
        forcealloy = True
    else:
        forcealloy = False

    # Make supercell?
    if options.supercellmap or options.supercelldims or options.supercellvacuum or \
            options.supercellprevactransvec or options.supercellpostvactransvec:
        makesupercell = True
    else:
        makesupercell = False

    # Initialize element data
    ed = ElementData()
    # Number of positions for printing decimal numbers to screen
    if type(options.printdigits) == type(None):
        decpos = 8 + 3
    else:
        decpos = int(options.printdigits) + 3
    # format string for outputting decimal numbers to screen
    decform = "%"+str(decpos)+"."+str(decpos-4)+"f"
    threedecs = " "+decform+" "+decform+" "+decform
    fourdecs = " "+decform+" "+decform+" "+decform+" "+decform
    # For printing time
    today = datetime.today()
    datestring = str(today.year)+"-"+str(today.month).rjust(2,'0')+"-"+str(today.day).rjust(2,'0')+' '+str(today.hour)+":"+str(today.minute).rjust(2,'0')

    # Printing of symmetry operations
    if options.printsymops:
        printsymops = True
    else:
        printsymops = False
    if options.printseitz:
        printseitz = True
    else:
        printseitz = False

    if options.printcharges:
        printcharges = True
    else:
        printcharges = False

    # complete setup options
    if options.setupall:
        setupall = True
    else:
        setupall = False
    # k-space resolution
    if options.kresolution:
        kresolution=float(options.kresolution)
    else:
        kresolution=0.2

    # Cell transformations
    if options.celltransformation or options.cubediagz or options.rhombdiag:
        transformcell = True
    else:
        transformcell = False

    #################################################################
    # Open and read CIF file
    #cif_file = None
    #if len(args) > 0:
        # input CIF file as argument
        #cif_file = args[0]
    if options.file:
        # input CIF file as option (overrides argument)
        cif_file = options.file
    if cif_file:
        if not os.path.exists(cif_file):
            sys.stderr.write("***Error: The file "+cif_file+" could not be found.\n")
            sys.exit(2)
        cif_file_name = cif_file.split("/")[-1]
        # Set CIF grammar
        if options.grammar:
            cif_grammar = options.grammar
        else:
            cif_grammar = '1.1'
        # Skip validation... it causes too much trouble.
        ## cdic = CifFile.CifDic("cif_core.dic",grammar='1.1')
        ## val_results = CifFile.validate(cif_file,dic=cdic)
        ## print(validate_report(val_results))
        ## val_report = CifFile.ValidationResult(val_results)
        try:
            cf = CifFile.ReadCif(cif_file,grammar=cif_grammar)
        #        cf = CifFile.ReadCif(cif_file)
        except Exception as e1:
            print (e1)
            # test if data_ statement in the beginning is missing
            try:
                f = open(cif_file,'r')
                lines = f.readlines()
                f.close()
                datamissing = False
                counter = 0
                for line in lines:
                    if line.strip()[0] == '#':
                        continue
                    else:
                        if not line.strip()[0:5] == 'data_' and counter == 0:
                            datamissing = True
                        counter += 1
                if datamissing:
                    tmpname = cif_file.replace('.cif','_tmp.cif')
                    f = open(tmpname,'w')
                    f.write("data_default\n")
                    for line in lines:
                        f.write(line)
                    f.close()
                    cf = CifFile.ReadCif(tmpname,grammar=cif_grammar)
                    wrongfile = cif_file.replace('.cif','_wrong.cif')
                    sys.stderr.write("***Warning: The cif file is missing a data statement.")
                    sys.stderr.write(" The file has been renamed '"+wrongfile+"' and replaced by a")
                    sys.stderr.write(" corrected file.\n")
                    os.rename(cif_file,wrongfile)
                    os.rename(tmpname,cif_file)
                else:
                    sys.stderr.write("***Error: could not read "+cif_file+".\n")
                    sys.stderr.write("Something may be wrong with the CIF file, you can check it with ")
                    sys.stderr.write("the free IUCr CIF valitation tool at http://checkcif.iucr.org/\n")
                    sys.stderr.write(e1.value+"\n")
                    sys.exit(2)
            except Exception as er2:
                try:
                    os.remove(tmpname)
                except:
                    pass
                sys.stderr.write("***Error: could not read "+cif_file+".\n")
                sys.stderr.write("Something may be wrong with the CIF file, you can check it with ")
                sys.stderr.write("the free IUCr CIF valitation tool at http://checkcif.iucr.org/\n")
                sys.stderr.write(er2.value+"\n")
    #            sys.exit(2)
    else:
        sys.stderr.write("***Error: No input CIF file given\n")
        sys.exit(2)

    # Make supercell?
    if makesupercell:
        if options.supercellmap:
            supercellmap = safe_matheval(options.supercellmap)
        else:
            supercellmap = [1,1,1]
        if options.supercelldims:
            t = safe_matheval(options.supercelldims)
            try:
                supercelldims = [[float(t[0]), 0.0, 0.0],
                                 [0.0, float(t[1]), 0.0],
                                 [0.0, 0.0, float(t[2])]]
            except:
                supercelldims = t
        else:
            supercelldims = None
        if options.supercellvacuum:
            supercellvacuum = safe_matheval(options.supercellvacuum)
        else:
            supercellvacuum = [0,0,0]
        if options.supercellprevactransvec:
            supercellprevactransvec = safe_matheval(options.supercellprevactransvec)
        else:
            supercellprevactransvec = [0,0,0]
        if options.supercellpostvactransvec:
            supercellpostvactransvec = safe_matheval(options.supercellpostvactransvec)
        else:
            supercellpostvactransvec = [0,0,0]
        #
        if options.supercellsort:
            supercellsort = options.supercellsort.lower()
        else:
            supercellsort = ""
        if options.supercellrealign:
            supercellrealign = int(options.supercellrealign)
        else:
            supercellrealign = 0

    ##############################################
    # Get blocks
    cfkeys = list(cf.keys())
    if options.block:
        cb = cf.get(options.block)
        if type(cb) == type(None):
            sys.stderr.write("***Error: No block "+options.block+" in "+cif_file+".\n")
            sys.exit(2)
    else:
        cb = cf.get(cfkeys[0])
    # Get reference data
    ref = ReferenceData()
    ref.getFromCIF(cb)
    if bibtexref:
        sys.stdout.write(ref.bibtexref())
        sys.exit(0)
    if options.coordtol:
        # Get cell data
        cd = CellData(compeps=float(options.coordtol))
    #    cd.coordepsilon = float(options.coordtol)
    else:
        cd = CellData()
    # Suppress warnings if requested.
    cd.quiet = options.quiet
    # Force generation despite problems?
    cd.force = force
    try:
        cd.getFromCIF(cb)
    except PositionError as e:
        sys.stderr.write("***Error: cell setup: "+e.value+"\n")
        sys.exit(2)
    except CellError as e:
        sys.stderr.write("***Error: cell setup: "+e.value+"\n")
        sys.exit(2)
    except SymmetryError as e:
        sys.stderr.write("***Error: cell setup: "+e.value+"\n")
        sys.exit(2)


    ##############################################
    # Set flags for cell generation
    if options.specialIsetting=='1':
        cd.specialIsetting = True

    ##############################################
    # Generate cell
    try:
        if reducetoprim:
            cd.primitive()
        else:
            cd.conventional()
    except SymmetryError as e:
        sys.stderr.write("***Error: cell setup: "+e.value+"\n")
        sys.exit(2)
    except CellError as e:
        sys.stderr.write("***Error: cell setup: "+e.value+"\n")
        sys.exit(2)

    ##############################################
    # Surface wizard
    # If present, print suggestion and exit.
    if options.surfacewizardhkl:
        hkl = safe_matheval(options.surfacewizardhkl)
        mapsuggestion = SurfaceWizard(cd,hkl)
        wizardstr = "--supercell=["
        for i in mapsuggestion:
            wizardstr += "["
            for j in i:
                wizardstr += str(j)+','
            wizardstr = wizardstr.rstrip(',')+"],"
        wizardstr = wizardstr.rstrip(',')+"]\n"
        sys.stdout.write(wizardstr)
        sys.exit()

    ##############################################
    # Test if generated cell agrees with given chemical formula.
    # Too difficult for alloys (no universally agreed-upon way to write the formula into cifs).
    if len(ref.ChemicalComposition) > 0 and not cd.alloy:
        if ref.ChemicalComposition != cd.ChemicalComposition:
            if force:
                sys.stderr.write("***Warning: Chemical composition of the generated cell differs from that given\n"+ \
                                 "            by _chemical_formula_sum.\n")
            else:
                sys.stderr.write("***Error: Chemical composition of the generated cell differs from that given\n"+ \
                                 "          by _chemical_formula_sum. Use --force to generate a cell anyway.\n")
                sys.exit(2)

    ##############################################
    # Randomly displace atoms if requested. This erases all symmetry operations.
    inputcell = copy.copy(cd)
    if options.randomdisp and not makesupercell:
        if options.randomdistr:
            distr = options.randomdistr
        else:
            distr = "uniform"
        try:
            cd.randomDisplacements(float(options.randomdisp),distribution=distr)
        except SetupError as e:
            sys.stderr.write("***Error: random displacements: "+e.value+"\n")
            sys.exit(3)
        # Reset space group operations
        cd.HallSymbol = "P 1"
        cd.spacegroupnr = 1
        cd.HMSymbol = "P1"
        cd.symops = set([SymmetryOperation(['x','y','z'])])

    ##############################################
    # Print cell
    if verbose or not options.program and not options.quiet:
        sys.stdout.write(programname.upper()+" "+version+"\n")
        sys.stdout.write(datestring+"\n")
        # Print compound
        compoundstring = "Output for "
        if ref.cpd == "" and ref.compound == "":
            compoundstring += "unknown compound"
        if ref.cpd != "":
            compoundstring += ref.cpd
        if ref.compound != "":
            compoundstring += " ("+ref.compound+")"
        sys.stdout.write(compoundstring+"\n")
        # Print database
        sys.stdout.write(ref.databasestring)
        if cd.alloy and forcealloy and options.program:
            sys.stdout.write("\nEnforcing generation of file(s) for "+outputprogram+" for an alloy.")
        sys.stdout.write("\n BIBLIOGRAPHIC INFORMATION\n")
        refstrings = ref.referencestring().split()
        tmpstring = ""
        i = 0
        while i < len(refstrings):
            if len(tmpstring+refstrings[i]+" ") < 70:
                tmpstring += refstrings[i]+" "
                i += 1
            else:
                sys.stdout.write(tmpstring)
                tmpstring = ""
        if tmpstring != "":
            sys.stdout.write(tmpstring)
        sys.stdout.write("\n INPUT CELL INFORMATION\n")
        sys.stdout.write("Symmetry information:\n")
        if inputcell.HallSymbol != "":
            sys.stdout.write(inputcell.crystal_system()[0].upper()+inputcell.crystal_system()[1:]+" crystal system.\n")
            sys.stdout.write("Space group number     : ".rjust(2)+str(inputcell.spacegroupnr)+"\n")
            sys.stdout.write("Hall symbol            : "+inputcell.HallSymbol+"\n")
            sys.stdout.write("Hermann-Mauguin symbol : "+inputcell.HMSymbol+"\n")
        else:
            sys.stdout.write("No space group information found.\n")
        # only print these if verbose
        if verbose:
            sys.stdout.write("Symmetry equivalent sites:\n")
            symops = list(inputcell.symops)
            symops.sort()
            for i in range(len(symops)):
                sys.stdout.write("%4i  %8s, %8s, %8s" % (i+1, symops[i].eqsite[0], symops[i].eqsite[1], symops[i].eqsite[2])+"\n")
        sys.stdout.write("\nLattice parameters:\n")
        tmpstring = ""
        for i in ["a", "b", "c"]:
            tmpstring += i.rjust(decpos)+" "
        sys.stdout.write(tmpstring+"\n")
        formatstring = ""
        if options.printau:
            aprint = inputcell.a*angtobohr
            bprint = inputcell.b*angtobohr
            cprint = inputcell.c*angtobohr
        else:
            aprint = inputcell.a
            bprint = inputcell.b
            cprint = inputcell.c
        for i in range(3):
            formatstring = formatstring+decform+" "
        sys.stdout.write(formatstring % (aprint, bprint, cprint)+"\n")
        tmpstring = ""
        for i in ["alpha", "beta", "gamma"]:
            tmpstring += i.rjust(decpos)+" "
        sys.stdout.write(tmpstring+"\n")
        sys.stdout.write(formatstring % (inputcell.alpha, inputcell.beta, inputcell.gamma)+"\n")
        ## sys.stdout.write(formatstring % (inputcell.alphainit, inputcell.betainit, inputcell.gammainit))
        # Pretty printing in columns that need to have variable width
        # w1 = width of the atomic species column
        # w2 = width of a decimal column
        # w3 = width of the occupancy column
        # w4 = width of the charge state column
        if inputcell.alloy:
            w1 = 0
            w3 = 0
            w4 = 0
            # Find atom and occupation column widths
            for a in inputcell.atomdata:
                for b in a:
                    tmpstring1 = ""
                    tmpstring2 = ""
                    tmpstring3 = ""
                    for k,v in b.species.items():
                        tmpstring1 += k+"/"
                        tmpstring2 += str(v).rstrip("0.")+"/"
                        # charge output
                        for k2,v2 in inputcell.chargedict.items():
                            if k2.strip(string.punctuation+string.digits) == k:
                                tmpstring3 += str(v2)+"/"
                    tmpstring1 = tmpstring1.rstrip("/")
                    tmpstring2 = tmpstring2.rstrip("/")
                    tmpstring3 = tmpstring3.rstrip("/")
                    w1 = max(w1,len(tmpstring1))
                    w3 = max(w3,len(tmpstring2))
                    w4 = max(w4,len(tmpstring3))
            # small aesthetic adjustment
            w1 = w1 + 1
            w3 = w3 + 2
            w4 = max(w4 + 2, 8)
        else:
            w1 = 5
            w2 = decpos
            w3 = 0
            # width of charge column
            if printcharges:
                w4 = 7
            else:
                w4 = 0
        # Now for the output...
        tmpstring = "Representative sites :"
        sys.stdout.write(tmpstring+"\n")
        siteheader = "Atom".ljust(w1)+" "
        if options.printcart:
            transmtx = []
            for i in range(3):
                transmtx.append([])
                for j in range(3):
                    transmtx[i].append(inputcell.latticevectors[i][j]*inputcell.lengthscale)
                i += 1
            for i in ["x","y","z"]:
                siteheader += i.rjust(decpos)+" "
        else:
            transmtx = [[1, 0, 0],
                        [0, 1, 0],
                        [0, 0, 1]]
            for i in ["a1","a2","a3"]:
                siteheader += i.rjust(decpos)+" "
        if inputcell.alloy:
            if w3 > 13:
                siteheader += "occupancies".rjust(w3)
            else:
                siteheader += "occ.".rjust(w3)
        if printcharges:
            siteheader += " "+"charge".rjust(w4)
        sys.stdout.write(siteheader+"\n")
        # Representative sites
        for i in range(len(inputcell.ineqsites)):
            tmpstring = ""
            occstring = ""
            chargestring = ""
            for k,v in inputcell.occupations[i].items():
                tmpstring += k+"/"
                occstring += str(v)+"/"
                # charge output
                for k2,v2 in inputcell.chargedict.items():
                    if k2.strip(string.punctuation+string.digits) == k:
                        chargestring += str(v2)+"/"
            tmpstring = tmpstring.rstrip("/")
            occstring = occstring.rstrip("/")
            chargestring = chargestring.rstrip("/")
            v = [t for t in inputcell.ineqsites[i]]
            tmpstring = tmpstring.ljust(w1) + threedecs % (v[0],v[1],v[2])
            if inputcell.alloy:
                tmpstring += " "+occstring.rjust(w3)
            if printcharges:
                tmpstring += " "+chargestring.rjust(w4)
            sys.stdout.write(tmpstring+"\n")

        # Output cell
        sys.stdout.write("\n OUTPUT CELL INFORMATION\n")
        sys.stdout.write("Symmetry information:\n")
        if cd.HallSymbol != "":
            sys.stdout.write(cd.crystal_system()[0].upper()+cd.crystal_system()[1:]+" crystal system.\n")
            sys.stdout.write("Space group number     : ".rjust(2)+str(cd.spacegroupnr)+"\n")
            sys.stdout.write("Hall symbol            : "+cd.HallSymbol+"\n")
            sys.stdout.write("Hermann-Mauguin symbol : "+cd.HMSymbol+"\n")
        else:
            sys.stdout.write("No space group information found.\n")
        # only print these if verbose
        if verbose:
            sys.stdout.write("Symmetry equivalent sites:\n")
            symops = list(cd.symops)
            symops.sort()
            for i in range(len(symops)):
                sys.stdout.write("%4i  %8s, %8s, %8s\n" % (i+1, symops[i].eqsite[0], symops[i].eqsite[1], symops[i].eqsite[2]))

        sys.stdout.write("\n")
        cd.printCell(printcart=options.printcart, printdigits=printdigits, printcharges=options.printcharges)
        # Print volume and density
        if options.printau:
            volume = cd.volume()*(cd.lengthscale*angtobohr)**3
            volstring = "(a.u.)"
        else:
            volume = cd.volume()*cd.lengthscale**3
            volstring = "A"
        sys.stdout.write("\nUnit cell volume  : "+decform%volume+" "+volstring+"^3\n")
        try:
            weight = 0.0
            for a in cd.atomdata:
                for b in a:
                    for k,v in b.species.items():
                        weight += ed.elementweight[k]*v
            density = weight/volume
            sys.stdout.write("Unit cell density : "+decform%density+" u/"+volstring+"^3 = "+decform%(density*uperautogpercm)+" g/cm^3\n")
        except:
            if not options.quiet:
                sys.stderr.write("***Warning: Error printing unit cell density.\n")

    ##############################################
    # Rotate cell
    if transformcell:
        # pre-defined transformations
        if options.cubediagz:
            # Put [111] direction along z axis.
            celltransformation = LatticeMatrix([[0.577350269189626,-1.000000000000000,0.816496580927725],
                                                [0.577350269189626, 1.000000000000000,0.816496580927725],
                                                [-1.154700538379250,0.000000000000000,0.816496580927725]])
            if cd.crystal_system() != 'cubic':
                sys.stderr.write("***Error: Only cubic structures are properly aligned to the z axis by --cubic-diagonal-z.\n")
                if not force:
                    sys.stderr.write("          Use --force to go ahead anyway.\n")
                    sys.exit(1)

        if options.rhombdiag:
            # Put z direction along pseudocubic [111]. Kind of the opposite of the cubediagz.
            t = 1/cd.latticevectors[0].length()   # Normalization to 1
            celltransformation = LatticeMatrix([[0.816496580927726*t,-0.408248290463863*t,-0.408248290463863*t],
                                                [0.000000000000000, 0.707106781186547*t,-0.707106781186547*t],
                                                [0.577350269189626*t, 0.577350269189626*t, 0.577350269189626*t]])
            if not cd.rhombohedral:
                sys.stderr.write("***Error: Only rhombohedral cells are properly aligned to the\n")
                sys.stderr.write("          pseudocubic (111) axis by --rhombohedral-diagonal.\n")
                if not force:
                    sys.stderr.write("          Use --force to go ahead anyway.\n")
                    sys.exit(1)
        # explicitly giving the transformation overrides any other transformation
        if options.celltransformation:
            celltransformation = safe_matheval(options.celltransformation)
        try:
            cd.transformCell(celltransformation)
        except CellError as e:
            sys.stderr.write("***Error: Cell transformation: "+e.value+"\n")
            sys.exit(2)
        if verbose or not options.program and not options.quiet:
            sys.stdout.write("\n TRANSFORMED CELL")
            cd.printCell(printcart=options.printcart, printdigits=printdigits, printcharges=options.printcharges)

    ##############################################
    # Generate supercell
    if makesupercell:
        if supercelldims != None:
            # Determine a suitable map to get the desired supercell dimensions.
            t1 = []
            for i in range(3):
                t1.append([])
                for j in range(3):
                    t1[i].append(cd.latticevectors[i][j]*cd.lengthscale)
            t2 = minv3(t1)
            t2 = mmmult3(supercelldims,t2)
            supercellmap = []
            for i in range(3):
                supercellmap.append([])
                for j in range(3):
                    supercellmap[i].append(int(round(t2[i][j])))
        try:
            cd.getSuperCell(supercellmap,supercellvacuum,supercellprevactransvec,postvactransvec=supercellpostvactransvec,sort=supercellsort,realign=supercellrealign)
        except CellError as e:
            sys.stderr.write("***Error: Supercell setup: "+e.value+"\n")
            sys.exit(2)
        # Randomly displace atoms if requested. This erases all symmetry operations.
        if options.randomdisp:
            if options.randomdistr:
                distr = options.randomdistr
            else:
                distr = "uniform"
            try:
                cd.randomDisplacements(float(options.randomdisp),distribution=distr)
            except SetupError as e:
                sys.stderr.write("***Error: random displacements: "+e.value+"\n")
                sys.exit(3)
            cd.symops = set([SymmetryOperation(['x','y','z'])])

        # Print supercell
        if verbose or not options.program and not options.quiet:
            sys.stdout.write("\n SUPERCELL INFORMATION\n")
            cd.printCell(printcart=options.printcart, printdigits=printdigits, printcharges=options.printcharges)

    if printsymops or printseitz or verbose:
        # Print symmetry operations. Need to make list of it to control order.
        symoplist = sorted(list(cd.symops))
        sys.stdout.write("\nSymmetry operations :\n")
        if printsymops or verbose:
            sys.stdout.write("  3x3 rotation matrix +\n")
            sys.stdout.write("  3x1 translation vector\n")
            i = 1
            for op in symoplist:
                sys.stdout.write("Operation "+str(i)+"\n")
                for v in op.rotation:
                    sys.stdout.write(threedecs%(v[0],v[1],v[2]))
                sys.stdout.write(threedecs%(op.translation[0],op.translation[1],op.translation[2])+"\n")
                i += 1
        if printseitz:
            sys.stdout.write("  In Seitz matrix form\n")
            i = 1
            for op in symoplist:
                sys.stdout.write("Operation "+str(i)+"\n")
                tmpstring = ""
                for j in range(3):
                    tmpstring += fourdecs%(op.rotation[j][0],op.rotation[j][1],op.rotation[j][2],op.translation[j])+"\n"
                tmpstring += fourdecs%(0,0,0,1)
                sys.stdout.write(tmpstring)
                i += 1

            # Remind that the result may be junk when using --force
    if force:
        sys.stderr.write("\n***Warning: You invoked the --force flag, presumably to bypass some error message.\n")
        sys.stderr.write("            Carefully check the results, which may be rubbish, nonsense or both!\n")

    ##############################################
    # Sort sites so that the ones occupied by the heaviest elements come first,
    # if the Python version supports this form of the max function and there is
    # nothing wrong with the site data.
    if not (makesupercell and supercellsort):
        try:
            cd.atomdata.sort(key = lambda a: ed.elementnr[max(a[0].species, key = a[0].species.get)], reverse=True)
        except:
            pass

    print("OUTPUTPROG = "+outputprogram)
    ############################################################################################
    # Output file mode (overwrite or append?)
    if options.append:
        outmode = "a"
    else:
        outmode = "w"
    # Output file. ot parsed until this point, since the default file names for some of
    # the codes contain the names of space group and compound.
    if options.outputfile:
        outputfile = options.outputfile
    else:
        # Default output filenames for different programs
        if outputprogram == "vasp":
            outputfile = "POSCAR"
        elif outputprogram == "rspt":
            if setupall:
                outputfile = "rspt.inp"
            else:
                outputfile = "symt.inp"
        elif outputprogram == "cellgen":
            outputfile = "cellgen.inp"
        elif outputprogram == "elk":
            outputfile = "GEOMETRY.OUT"
        elif outputprogram == "exciting":
            outputfile = "input.xml"
        elif outputprogram == "spacegroup":
            outputfile = "spacegroup.in"
        elif outputprogram == "cif":
            outputfile = cif_file_name.replace(".cif","")+"_allatoms.cif"
        elif outputprogram == "ase":
            outputfile = "positions.py"
        else:
            # A bunch of programs get default output constructed as:
            # 1. chemical abbreviation (i.e. something like H2SO4 or CeRhIn5)
            # 2. if this is too long, use the original cif filename
            outputfile = ref.cpd.replace(" ", "").replace("(","").replace(")","")
            # If the filename seems too long or strange, replace by the name of the cif file
            if len(outputfile.strip(string.punctuation)) == 0:
                outputfile = cif_file_name.replace(".cif","")
            if len(outputfile) > 24:
                if len(cif_file_name) < len(outputfile):
                    outputfile = cif_file_name.replace(".cif","")
                else:
                    outputfile = outputfile[0:9]
            # Append file endings etc.
            if outputprogram == "abinit":
                outputfile = outputfile+".in"
            elif outputprogram == "atat":
                outputfile = outputfile+".in"
            elif outputprogram == "castep":
                outputfile = outputfile+".cell"
            elif outputprogram == "cfg":
                outputfile = outputfile+".cfg"
            elif outputprogram == "coo":
                outputfile = outputfile+".coo"
            elif outputprogram == "cp2k":
                outputfile = outputfile+".inp"
            elif outputprogram == "cpmd":
                outputfile = outputfile+".inp"
            elif outputprogram == "crystal09":
                # This is the naming convention from a large bunch of test cases, no idea why
                outputfile = outputfile+".d12"
            elif outputprogram == "fhi-aims":
                outputfile = "geometry.in"
            elif outputprogram == "fleur":
                outputfile = "inp_"+outputfile
            elif outputprogram == "hutsepot":
                outputfile = outputfile+".str"
            elif outputprogram == "mopac":
                outputfile = outputfile+".mop"
            elif outputprogram == "pwscf":
                outputfile = outputfile+".in"
            elif outputprogram == "siesta":
                outputfile = outputfile+".fdf"
            elif outputprogram == "sprkkr" or outputprogram == "xband":
                outputfile = outputfile+".sys"
            elif outputprogram == "spc":
                outputfile = outputfile+".dat"
            elif outputprogram == "xyz":
                outputfile = outputfile+".xyz"
            elif outputprogram == "lammps":
                outputfile = outputfile+".data"
            else:
                pass

    # Print output filename to screen
    if outputprogram !="":
        if (verbose or options.filenamequery) and outputfile != "":
            sys.stdout.write("Data will be written to the file "+outputfile)

    ################################################################################################
    # stuff that should be printed irrespective of the verbose flag
    if cd.alloy and forcealloy and options.program and not verbose:
        tmpstring = "Enforcing file generation for alloy. "
        if outputprogram == 'bstr' or outputprogram == 'vasp' or outputprogram == 'cpmd':
            sys.stdout.write(tmpstring+"\n")
        else:
            tmpstring += "Warning! The file(s) will be incomplete!"
            sys.stdout.write(tmpstring+"\n")

    ################################################################################################
    # Stop here if no specific output was requested
    print("OUTPUTPROG = "+outputprogram)
    options.program = outputprogram
    if not options.program:
        sys.exit(0)

    # Don't generate output for alloys (for most programs)
    if cd.alloy and not forcealloy and not (outputprogram in alloyprograms or outputprogram in vcaprograms):
        sys.stderr.write("Error: This system is an alloy, but "+codename[outputprogram]+" has no way of dealing with alloys.\n       Run again with --force-alloy (or --force) if you want to generate an (incomplete) output file anyway.\n")
        sys.exit(17)
    # Deal with VCA
    if cd.alloy and outputprogram in vcaprograms:
        if not options.vca and not forcealloy:
            sys.stderr.write("Error: This system is an alloy. "+codename[outputprogram]+" can deal with some alloys using the virtual crystal approximation (VCA).\n       Run again with the flag --vca if you want to produce a VCA setup.\n")
            sys.exit(17)
    vcawarning1 = False
    vcawarning2 = False
    if options.vca:
        # Issue warning for precarious VCA setups
        groups = []
        for a in cd.atomdata:
            if len(a[0].species) > 1:
                t = [ed.elementgroup[sp] for sp,conc in a[0].species.items()]
                groups.append((min(t),max(t)))
                if len(a[0].species) > 2:
                    vcawarning1 = True
        for g in groups:
            if g[1] - g[0] > 1:
                vcawarning2 = True
        if vcawarning1 and vcawarning2:
            sys.stderr.write("Warning: You are setting up a VCA calculation for an alloy with more than two components\n         and not all alloy sites are occupied by species from neighbouring groups in the periodic\n         table. Make doubly sure that you know what you are doing!\n")
        elif vcawarning1:
            sys.stderr.write("Warning: You are setting up a VCA calculation for an alloy with more than two components.\n         Make sure that you know what you are doing!\n")
        elif vcawarning2:
            sys.stderr.write("Warning: You are setting up a VCA calculation but not all alloy sites are occupied by species\n         from neighbouring groups in the periodic table. Make sure that you know what you are doing!\n")


    ################################################################################################
    # Output cell to new CIF file
    if outputprogram == 'cif':
        f = open(outputfile, 'w')
        cf = CifFile.CifFile()
        cb = CifFile.CifBlock()
        if makesupercell or (reducetoprim and cd.spacegroupsetting != 'P') or options.randomdisp:
            a = Vector(cd.latticevectors[0].scalmult(cd.lengthscale))
            b = Vector(cd.latticevectors[1].scalmult(cd.lengthscale))
            c = Vector(cd.latticevectors[2].scalmult(cd.lengthscale))
            cb['_cell_length_a'] = a.length()
            cb['_cell_length_b'] = b.length()
            cb['_cell_length_c'] = c.length()
            cb['_cell_angle_alpha'] = acos(b.dot(c) / (b.length() * c.length())) * 180 / pi
            cb['_cell_angle_beta'] = acos(a.dot(c) / (a.length() * c.length())) * 180 / pi
            cb['_cell_angle_gamma'] = acos(b.dot(a) / (a.length() * b.length())) * 180 / pi
            # Supercell may have broken symmetry, so just put P1
            cb['_space_group_IT_number'] = 1
            cb['_space_group_name_H-M_alt'] = "P1"
            cb['_space_group_name_Hall'] = "P 1"
        else:
            # Else pass on original cell parameters and symmetry information
            cb['_cell_length_a'] = cd.a
            cb['_cell_length_b'] = cd.b
            cb['_cell_length_c'] = cd.c
            cb['_cell_angle_alpha'] = cd.alpha
            cb['_cell_angle_beta'] = cd.beta
            cb['_cell_angle_gamma'] = cd.gamma
            cb['_space_group_IT_number'] = cd.spacegroupnr
            cb['_space_group_name_H-M_alt'] = cd.HMSymbol
            cb['_space_group_name_Hall'] = cd.HallSymbol
        # Positions
        labels = []
        symbols = []
        symmult = []
        fractx = []
        fracty = []
        fractz = []
        occup = []
        i = 0
        for a in cd.atomdata:
            if not makesupercell:
                i += 1
            for b in a:
                if makesupercell:
                    i += 1
                for k in b.species:
                    labels.append(k + str(i))
                    symbols.append(k)
                    if makesupercell:
                        symmult.append("1")
                    else:
                        symmult.append(str(len(a)))
                    fractx.append(("%19.16f" % b.position[0]).strip(" "))
                    fracty.append(("%19.16f" % b.position[1]).strip(" "))
                    fractz.append(("%19.16f" % b.position[2]).strip(" "))
                    occup.append(str(b.species[k]))
        #
        cb.AddCifItem(([['_atom_site_label',
                         '_atom_site_type_symbol',
                         '_atom_site_symmetry_multiplicity',
                         '_atom_site_fract_x',
                         '_atom_site_fract_y',
                         '_atom_site_fract_z',
                         '_atom_site_occupancy']],
                       [[labels, symbols, symmult, fractx, fracty, fractz, occup]]))
        #
        cf['1-cif2cell'] = cb
        f.write(str(cf))
        f.close()

    ################################################################################################
    # Output for ABINIT
    if outputprogram == 'abinit':
        docstring = StandardDocstring(ref)
        abinitinput = ABINITFile(cd, docstring)
        if options.abinitbraces:
            abinitinput.printbraces = True
        f = open(outputfile, outmode)
        f.write(str(abinitinput))
        f.close()

    ################################################################################################
    # Output for ATAT
    if outputprogram == 'atat':
        docstring = StandardDocstring(ref)
        abinitinput = ATATFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(abinitinput))
        f.close()

    ################################################################################################
    # Output for ASE file (python script)
    if outputprogram == 'ase':
        # The second comment line with info from the CIF file
        docstring = StandardDocstring(ref)
        # Initialize the ASEFile structure
        sysfile = ASEFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for CASTEP
    if outputprogram == 'castep':
        docstring = StandardDocstring(ref)
        castepinput = CASTEPFile(cd, docstring)
        if options.castepatomicunits:
            castepinput.unit = "bohr"
        if options.castepcartesian:
            castepinput.cartesian = True
        if options.vca:
            castepinput.vca = True
        if options.exportlabels:
            castepinput.printlabels = True
        f = open(outputfile, outmode)
        f.write(str(castepinput))
        f.close()

    ################################################################################################
    # Output to cfg file
    if outputprogram == 'cfg':
        docstring = StandardDocstring(ref)
        # Initialize the CFGFile structure
        sysfile = CFGFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output to coo file
    if outputprogram == 'coo':
        # !!!TODO: Think of something better for docstring !!!
        docstring = "Generated by cif2cell " + version
        # Initialize the COOFile structure
        sysfile = COOFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for CP2k
    if outputprogram == 'cp2k':
        docstring = StandardDocstring(ref)
        cp2kinput = CP2KFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(cp2kinput))
        f.close()

    ################################################################################################
    # Output for CPMD
    if outputprogram == 'cpmd':
        docstring = StandardDocstring(ref)
        cpmdinput = CPMDFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(cpmdinput))
        f.close()

    ################################################################################################
    # Output for Crystal09
    if outputprogram == 'crystal09':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Crystal09 wants conventional cell input, unless specifically asked to for possible
        # rhombohedral settings.
        if cd.is_spacegroup("rhombohedral") and options.crystal09rhombohedral:
            cd.primitive()
        else:
            cd.conventional()
        # Get output file object
        crystal09file = Crystal09File(cd, docstring, rhombohedral=options.crystal09rhombohedral)
        crystal09file.spacegroupnr = cd.spacegroupnr
        # Print to file
        f = open(outputfile, outmode)
        f.write(str(crystal09file))
        f.close()
        sys.exit(0)

    ################################################################################################
    # EMTO PROGRAMS
    if outputprogram == "emto" or outputprogram == "kgrn" or outputprogram == "kfcd" or outputprogram == "kstr" or outputprogram == "bmdl" or outputprogram == "shape":
        # Get job names
        if cd.HMSymbol == "":
            kstrjobnam = ref.cpd.replace(" ", "").replace("(", "").replace(")", "")
        else:
            kstrjobnam = cd.HMSymbol.replace("/", "")
        kgrnjobnam = ref.cpd.replace(" ", "").replace("(", "").replace(")", "")
        # If the jobnames are long or blank, replace by the name of the cif file
        if len(kstrjobnam) > 30 and len(cif_file_name) < len(kstrjobnam) + 4 or kstrjobnam == "":
            kstrjobnam = cif_file_name.replace(".cif", "")
        if len(kgrnjobnam) > 30 and len(cif_file_name) < len(kgrnjobnam) + 4 or kgrnjobnam == "":
            kgrnjobnam = cif_file_name.replace(".cif", "")
        # Build docstring
        docstring = ref.compound + ", " + ref.referencestring()
        # Document details of creation
        programdoc = "Generated by " + programname + " " + version + " " + datestring
        # Set the lattice number
        if cd.crystal_system() == "cubic":
            if cd.HMSymbol[0] == "F":
                latticenr = 2
            elif cd.HMSymbol[0] == "I":
                latticenr = 3
            else:
                latticenr = 1
        elif cd.crystal_system() == "hexagonal":
            latticenr = 4
        elif cd.crystal_system() == "tetragonal":
            if cd.HMSymbol == "I":
                latticenr = 6
            else:
                latticenr = 5
        elif cd.crystal_system() == "trigonal":
            latticenr = 7
        elif cd.crystal_system() == "orthorhombic":
            if cd.HMSymbol[0] == "A":
                latticenr = 9
            elif cd.HMSymbol[0] == "B":
                latticenr = 9
            elif cd.HMSymbol[0] == "C":
                latticenr = 9
            elif cd.HMSymbol[0] == "I":
                latticenr = 10
            elif cd.HMSymbol[0] == "F":
                latticenr = 11
            else:
                latticenr = 8
        elif cd.crystal_system() == "monoclinic":
            if cd.HMSymbol[0] == "A":
                latticenr = 13
            elif cd.HMSymbol[0] == "B":
                latticenr = 13
            elif cd.HMSymbol[0] == "C":
                latticenr = 13
            else:
                latticenr = 12
        else:
            # Triclinic and default
            latticenr = 14

    # Output for EMTO slope matrix program kstr
    if outputprogram == 'kstr' or outputprogram == 'emto':
        # Create directories
        try:
            os.mkdir('kstr')
        except OSError:
            pass
        try:
            os.mkdir('kstr/smx')
        except OSError:
            pass
        # Initialize BSTRFile
        kstrfile = KSTRFile(cd, docstring)
        kstrfile.jobnam = kstrjobnam
        if options.hardsphereradii:
            kstrfile.hardsphere = float(options.hardsphereradii)
        kstrfile.latticenr = latticenr
        kstrfile.a = cd.a
        kstrfile.b = cd.b
        kstrfile.c = cd.c
        kstrfile.alpha = cd.alpha
        kstrfile.beta = cd.beta
        kstrfile.gamma = cd.gamma
        # Document program
        kstrfile.programdoc = programdoc
        f = open("kstr/" + kstrjobnam + ".dat", "w")
        f.write(str(kstrfile))
        f.close()
        if outputprogram == "kstr":
            sys.exit(0)
    # Output for EMTO Madelung constant program bmdl
    if outputprogram == 'bmdl' or outputprogram == 'emto':
        # Create directories
        try:
            os.mkdir('bmdl')
        except OSError:
            pass
        try:
            os.mkdir('bmdl/mdl')
        except OSError:
            pass
        # Initialize BMDLFile
        bmdlfile = BMDLFile(cd, docstring)
        bmdlfile.jobnam = kstrjobnam
        bmdlfile.latticenr = latticenr
        bmdlfile.a = cd.a
        bmdlfile.b = cd.b
        bmdlfile.c = cd.c
        bmdlfile.alpha = cd.alpha
        bmdlfile.beta = cd.beta
        bmdlfile.gamma = cd.gamma
        # Document program
        bmdlfile.programdoc = programdoc
        f = open("bmdl/" + kstrjobnam + ".dat", "w")
        f.write(str(bmdlfile))
        f.close()
        if outputprogram == "bmdl":
            sys.exit(0)
    # Output for EMTO shape function program 'shape'
    if outputprogram == 'shape' or outputprogram == 'emto':
        # Create directories
        try:
            os.mkdir('shape')
        except OSError:
            pass
        try:
            os.mkdir('shape/shp')
        except OSError:
            pass
        # Initialize ShapeFile
        shapefile = ShapeFile(cd, docstring)
        shapefile.jobnam = kstrjobnam
        # Document program
        shapefile.programdoc = programdoc
        f = open("shape/" + kstrjobnam + ".dat", "w")
        f.write(str(shapefile))
        f.close()
        if outputprogram == "shape":
            sys.exit(0)
    # Output for EMTO main Greens function program 'kgrn'
    if outputprogram == 'kgrn' or outputprogram == 'emto':
        # Create directories
        try:
            os.mkdir('kgrn')
        except OSError:
            pass
        try:
            os.mkdir('kgrn/pot')
        except OSError:
            pass
        try:
            os.mkdir('kgrn/chd')
        except OSError:
            pass
        # Initialize KGRNFile
        kgrnfile = KGRNFile(cd, docstring)
        kgrnfile.jobnam = kgrnjobnam
        kgrnfile.kstrjobnam = kstrjobnam
        kgrnfile.latticenr = latticenr
        # Document program
        kgrnfile.programdoc = programdoc
        f = open("kgrn/" + kgrnjobnam + ".dat", "w")
        f.write(str(kgrnfile))
        f.close()
        if outputprogram == "kgrn":
            sys.exit(0)
    # Output for EMTO charge density program 'kfcd'
    if outputprogram == 'kfcd' or outputprogram == 'emto':
        # Create directories
        try:
            os.mkdir('kfcd')
        except OSError:
            pass
        # Initialize KFCDFile
        kfcdfile = KFCDFile(cd, docstring)
        kfcdfile.jobnam = kgrnjobnam
        kfcdfile.kstrjobnam = kstrjobnam
        # Document program
        kfcdfile.programdoc = programdoc
        f = open("kfcd/" + kgrnjobnam + ".dat", "w")
        f.write(str(kfcdfile))
        f.close()
        if outputprogram == "kfcd":
            sys.exit(0)
    if outputprogram == "emto":
        sys.exit(0)

    ################################################################################################
    # Output for elk
    if outputprogram == 'elk':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Get output file object
        geometryfile = ElkFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(geometryfile))
        f.close()
        sys.exit(0)

    # Output for exciting
    if outputprogram == 'exciting':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Get output file object
        excitingfile = ExcitingFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(excitingfile))
        f.close()
        sys.exit(0)

    # Output for spacegroup.in for Elk/Exciting cell utility spacegroup
    if outputprogram == 'spacegroup':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Get output file object
        spacegroupfile = SpacegroupFile(cd, docstring)
        angtobohr = 1e-10 * 4 * pi * 10973731.568527 / 7.2973525376e-3
        spacegroupfile.HermannMauguin = cd.HMSymbol.replace("/", "")
        spacegroupfile.a = cd.a * angtobohr
        spacegroupfile.b = cd.b * angtobohr
        spacegroupfile.c = cd.c * angtobohr
        spacegroupfile.alpha = cd.alpha
        spacegroupfile.beta = cd.beta
        spacegroupfile.gamma = cd.gamma
        if options.spacegroupsupercell:
            spacegroupfile.supercelldims = safe_matheval(options.spacegroupsupercell)
        # Print to file
        f = open(outputfile, outmode)
        f.write(str(spacegroupfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for Hutsepot
    if outputprogram == 'hutsepot':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Get output file object
        hutsepotinput = HUTSEPOTFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(hutsepotinput))
        f.close()

    ################################################################################################
    # Output for FHI-AIMS
    if outputprogram == 'fhi-aims':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Get output file object
        aimsinput = AIMSFile(cd, docstring)
        if options.aimscartesian:
            aimsinput.cartesian = True
        f = open(outputfile, outmode)
        f.write(str(aimsinput))
        f.close()

    ################################################################################################
    # Output for Fleur
    if outputprogram == 'fleur':
        # The first line with info from the CIF file and species order
        docstring = "Generated by " + programname + " " + version + " : " + ref.cpd + " (" + ref.compound + ")" + " :  " + ref.referencestring()
        fleurinput = FleurFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(fleurinput))
        f.close()

    ################################################################################################
    # Output for mcsqs
    if outputprogram == 'mcsqs':
        # Get documentation string
        docstring = StandardDocstring(ref)
        # Get output file object
        mcsqsinput = MCSQSFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(mcsqsinput))
        f.close()

    ################################################################################################
    # Output for MOPAC
    if outputprogram == 'mopac':
        docstring = StandardDocstring(ref)
        mopacfirstline = ""
        mopacsecondline = ""
        mopacthirdline = ""
        mopacfreeze = -1
        mopacsetup = setupall
        if options.mopacfirstline:
            mopacsetup = True
            mopacfirstline = options.mopacfirstline
        if options.mopacsecondline:
            mopacsetup = True
            mopacsecondline = options.mopacsecondline
        if options.mopacthirdline:
            mopacsetup = True
            mopacthirdline = options.mopacthirdline
        if options.mopacfreeze:
            if options.mopacfreeze.upper() == 'F':
                mopacfreeze = 1
            elif options.mopacfreeze.upper() == 'T':
                mopacfreeze = 0
            else:
                sys.stderr.write(
                    "***Warning: I do not understand. --mopac-freeze-structure takes T (t) or F (f) as inputs.\n")
        mopacinput = MOPACFile(cd, docstring, setupall=mopacsetup, firstline=mopacfirstline, \
                               secondline=mopacsecondline, thirdline=mopacthirdline, freeze=mopacfreeze)
        f = open(outputfile, outmode)
        f.write(str(mopacinput))
        f.close()

    ################################################################################################
    # Output for TB-LMTO program ncol
    if outputprogram == 'ncol' or outputprogram == 'bstr':
        # Set up names for files.
        if cd.HMSymbol == "":
            bstrjobnam = ref.cpd.replace(" ", "").replace("(", "").replace(")", "")
        else:
            bstrjobnam = cd.HMSymbol.replace("/", "")
        jobnam = ref.cpd.replace(" ", "").replace("(", "").replace(")", "")
        # If the jobnames are long, replace by the name of the cif file
        if len(bstrjobnam) > 30 and len(cif_file_name) < len(bstrjobnam) + 4:
            bstrjobnam = cif_file_name.replace(".cif", "")
        if len(jobnam) > 10:
            if len(cif_file_name) < len(jobnam):
                jobnam = cif_file_name.replace(".cif", "")
            else:
                jobnam = jobnam[0:9]
        # Build docstring
        docstring = ref.compound + ", " + ref.referencestring()
        # Document details of creation
        programdoc = "Generated by " + programname + " " + version + " " + datestring

    # Output for TB-LMTO structure constant program bstr
    if outputprogram == 'bstr' or outputprogram == 'ncol':
        # Initialize BSTRFile
        bstrfile = BSTRFile(cd, docstring)
        bstrfile.jobnam = bstrjobnam
        bstrfile.a = cd.a
        bstrfile.b = cd.b
        bstrfile.c = cd.c
        # Document program
        bstrfile.programdoc = programdoc
        f = open(bstrjobnam + ".dat", "w")
        f.write(str(bstrfile))
        f.close()
        if outputprogram == 'bstr':
            sys.exit(0)

    if outputprogram == 'ncol':
        # Initialize ncolfile
        ncolfile = OldNCOLFile(cd, docstring)
        ncolfile.jobnam = jobnam
        ncolfile.bstrjobnam = bstrjobnam
        # Document program
        ncolfile.programdoc = programdoc
        f = open(jobnam + ".dat", "w")
        f.write(str(ncolfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for PWSCF (Quantum Espresso)
    if outputprogram == 'pwscf':
        docstring = StandardDocstring(ref)
        pwscfinput = PWSCFFileFD(cd, docstring, kresolution=kresolution)
        if options.setupall:
            pwscfinput.setupall = True
            pwscfinput.kresolution = kresolution
        if options.pwscfpseudostring:
            pwscfinput.pseudostring = options.pwscfpseudostring
        if options.pwscfcart:
            pwscfinput.cartesian = True
        if options.pwscfcartvects:
            pwscfinput.cartesianlatvects = True
        if options.pwscfcartpos:
            pwscfinput.cartesianpositions = True
        if options.pwscfalatunits:
            pwscfinput.scaledcartesianpositions = True
        if options.pwscfatomicunits:
            pwscfinput.unit = "bohr"
        f = open('scf.in', outmode)
        f.write(str(pwscfinput))
        f.close()

    ################################################################################################
    # Output for VASP
    if outputprogram == 'vasp':
        # The first line with info from the CIF file and species order
        docstring = "Generated by " + programname + " " + version
        if ref.database != "" and ref.databasecode != "":
            docstring += " from " + ref.databaseabbr[ref.database] + " reference: " + ref.databasecode
        docstring += ". "
        if len(ref.cpd) > len(ref.compound):
            docstring += ref.compound
        else:
            docstring += ref.cpd
        docstring += " :  " + ref.referencestring() + "."
        # Initialize the POSCARFile structure
        poscar = POSCARFile(cd, docstring, vca=options.vca)
        # Convert to cartesian coordinates if requested
        if options.vaspcartpos:
            poscar.printcartpos = True
        if options.vaspcartvecs:
            poscar.printcartvecs = True
        if options.vaspcart:
            poscar.printcartpos = True
            poscar.printcartvecs = True
        if options.vaspformat == "5":
            poscar.vasp5format = True
        if options.vaspselectivedyn:
            poscar.selectivedyn = True
        f = open(outputfile, outmode)
        f.write(str(poscar))
        f.close()
        # Print species order to screen if requested
        if options.vaspprintspcs:
            sys.stdout.write(poscar.SpeciesOrder())
        # Set up all files?
        if setupall:
            # POTCAR
            if options.vasppseudolib:
                lib = options.vasppseudolib
            else:
                lib = ""
            # Make selection of potcars
            if options.vasppppriority:
                prioritylist = options.vasppppriority.split(",")
                prioritylist.append("")
                sys.stdout.write(prioritylist)
            else:
                try:
                    pl = os.environ['VASP_PP_PRIORITY']
                    prioritylist = pl.split(",")
                    prioritylist.append("")
                except:
                    prioritylist = ["_d", "_pv", "_sv", "", "_h", "_s"]
            if options.vaspencutfac:
                encutfac = float(options.vaspencutfac)
            else:
                encutfac = 1.5
            potcarfile = POTCARFile(cd, directory=lib, vca=options.vca, prioritylist=prioritylist)
            f = open("POTCAR", "w")
            f.write(str(potcarfile))
            f.close()
            # KPOINTS
            docstring = "Generated by cif2cell " + version + "."
            kpointsfile = KPOINTSFile(cd, docstring=docstring, kresolution=kresolution)
            f = open("KPOINTS", "w")
            f.write(str(kpointsfile))
            f.close()
            # INCAR
            incarfile = INCARFile(cd, docstring=docstring, vca=options.vca, prioritylist=prioritylist, encutfac=encutfac)
            f = open("INCAR", "w")
            f.write(str(incarfile))
            f.close()
        sys.exit(0)

    ################################################################################################
    # Output for RSPt
    if outputprogram == 'rspt':
        # Construct documentation string
        docstring = StandardDocstring(ref)
        # Get file string and print to symt.inp/rspt.inp
        if options.newsymt or setupall:
            symtfile = SymtFile2(cd, docstring, kresolution=kresolution / angtobohr)
            # k-mesh generation etc
            if setupall:
                symtfile.setupall = True
            # spin polarization and relativity
            if options.rsptspinpol:
                symtfile.spinpol = True
            if options.rsptrelativistic:
                symtfile.relativistic = True
            if options.rsptmtradii:
                symtfile.mtradii = int(options.rsptmtradii)
            if options.rsptnospin:
                symtfile.forcenospin = True
        else:
            symtfile = SymtFile(cd, docstring)
        # spin axis
        if options.rsptspinaxis:
            symtfile.spinaxis = Vector(safe_matheval(options.rsptspinaxis))
        if options.rsptpasswyckoff:
            symtfile.passwyckoff = True
        if options.rsptcartlatvects:
            symtfile.rsptcartlatvects = True
        #
        if options.exportlabels:
            symtfile.printlabels = True
        f = open(outputfile, outmode)
        f.write(str(symtfile))
        f.close()
        sys.exit(0)

    # Output for RSPt supercell generator cellgen
    if outputprogram == 'cellgen':
        # Construct documentation string
        docstring = StandardDocstring(ref)
        # Initialize file object
        cellgenfile = CellgenFile(cd, docstring)
        if options.cellgenrefvec:
            cellgenfile.referencevector = safe_matheval(options.cellgenrefvec)
        if options.cellgensupercelldims:
            tmplist = safe_matheval(options.cellgensupercelldims)
            tmpmat = []
            for i in range(3):
                tmpmat.append([])
                for j in range(3):
                    tmpmat[i].append(0)
                tmpmat[i][i] = tmplist[i]
            cellgenfile.supercellmap = tmpmat
        if options.cellgenmap:
            tmpmat = safe_matheval(options.cellgenmap)
            cellgenfile.supercellmap = tmpmat
        # Print to file
        f = open(outputfile, outmode)
        f.write(str(cellgenfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for Siesta
    if outputprogram == 'siesta':
        docstring = StandardDocstring(ref)
        siestainput = SiestaFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(siestainput))
        f.close()

    ################################################################################################
    # Output for SPC file
    if outputprogram == 'spc':
        # The second comment line with info from the CIF file
        docstring = StandardDocstring(ref)
        # Initialize the SPCFile structure
        sysfile = SPCFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for xband
    if outputprogram == 'xband' or outputprogram == 'sprkkr':
        # The first line with info from the CIF file and species order
        docstring = "Generated by " + programname + " " + version
        if ref.database != "" and ref.databasecode != "":
            docstring += " from " + ref.databaseabbr[ref.database] + " reference: " + ref.databasecode
        docstring += ". "
        if len(ref.cpd) > len(ref.compound):
            docstring += ref.compound
        else:
            docstring += ref.cpd
        docstring += " :  " + ref.referencestring() + "."
        # Initialize the file
        sysfile = XBandSysFile(cd, docstring)
        sysfile.filename = outputfile
        if options.sprkkrminangmom:
            sysfile.minangmom = int(options.sprkkrminangmom)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for xyz file
    if outputprogram == 'xyz':
        # The second comment line with info from the CIF file
        docstring = "Generated by " + programname + " " + version
        if ref.database != "" and ref.databasecode != "":
            docstring += " from " + ref.databaseabbr[ref.database] + " reference: " + ref.databasecode
        docstring += ". "
        if len(ref.cpd) > len(ref.compound):
            docstring += ref.compound
        else:
            docstring += ref.cpd
        docstring += " :  " + ref.referencestring() + "."
        # Initialize the XYZFile structure
        if options.xyzatomicunits:
            cd.newunit("bohr")
        sysfile = XYZFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)

    ################################################################################################
    # Output for LAMMPS file
    if outputprogram == 'lammps':
        # The second comment line with info from the CIF file
        docstring = "Generated by " + programname + " " + version
        if ref.database != "" and ref.databasecode != "":
            docstring += " from " + ref.databaseabbr[ref.database] + " reference: " + ref.databasecode
        docstring += ". "
        if len(ref.cpd) > len(ref.compound):
            docstring += ref.compound
        else:
            docstring += ref.cpd
        docstring += " :  " + ref.referencestring() + "."
        # Initialize the LAMMPSFile structure
        sysfile = LAMMPSFile(cd, docstring)
        f = open(outputfile, outmode)
        f.write(str(sysfile))
        f.close()
        sys.exit(0)


# Function for printing a standard docstring
def StandardDocstring(ref):
    cif2cellstring = ' T. Bjorkman, Comp. Phys. Commun. 182, 1183-1186 (2011). Please cite generously.'
    stringlen = max(len(ref.referencestring()),len(ref.cpd+"   ("+ref.compound+")"),len(cif2cellstring))
    docstring = ""
    tmpstring = ""
    tmpstring = tmpstring.ljust(stringlen+4,'*')+'\n'
    docstring += tmpstring
    tmpstring2 = ''
    tmpstring2 = '* '+tmpstring2.center(stringlen)+' *\n'
    tmpstring3 = '* '+cif2cellstring.center(stringlen)+' *\n'
    tmpstring4 = ''
    tmpstring4 = '* '+tmpstring4.center(stringlen)+' *\n'
    docstring += tmpstring2+tmpstring3+tmpstring4
    if ref.database != "":
        tmpstring2 = 'Data obtained from '+ref.databaseabbr[ref.database]
        if ref.databasecode != "":
            tmpstring2 += ". Reference number : "+ref.databasecode
        tmpstring2 = '* '+tmpstring2.center(stringlen)+' *\n'
        docstring += tmpstring2
    tmpstring2 = ref.cpd+"   ("+ref.compound+")"
    tmpstring2 = '* '+tmpstring2.center(stringlen)+' *\n'
    docstring += tmpstring2
    docstring += '* '+ref.referencestring().center(stringlen)+' *\n'
    docstring += tmpstring
    return docstring



