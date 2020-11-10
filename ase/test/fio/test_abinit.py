from io import StringIO

import numpy as np
import pytest

from ase.io import read, write
from ase.build import bulk
from ase.calculators.calculator import compare_atoms
from ase.io.abinit import read_abinit_out
from ase.units import Hartree, Bohr


def test_abinit_roundtrip():
    m1 = bulk('Ti')
    m1.set_initial_magnetic_moments(range(len(m1)))
    write('abinit_save.in', images=m1, format='abinit-in')
    m2 = read('abinit_save.in', format='abinit-in')

    # (How many decimals?)
    assert not compare_atoms(m1, m2, tol=1e-7)


# "Hand-written" (reduced) abinit txt file based on v8.0.8 format:
sample_outfile = """\

.Version 8.0.8 of ABINIT

 -outvars: echo values of preprocessed input variables --------
            natom           2
           ntypat           1
            rprim      5.0  0.0  0.1
                       0.0  6.0  0.0
                       0.0  0.0  7.0
            typat      1  1
            znucl        8.0

================================

 ----iterations are completed or convergence reached----

 cartesian coordinates (angstrom) at end:
    1      2.5     2.5     3.7
    2      2.5     2.5     2.5

 cartesian forces (eV/Angstrom) at end:
    1     -0.1    -0.3    0.4
    2     -0.2    -0.4   -0.5

 Components of total free energy (in Hartree) :

    >>>>>>>>> Etotal= -42.5

 Cartesian components of stress tensor (hartree/bohr^3)
  sigma(1 1)=  2.3  sigma(3 2)=  3.1
  sigma(2 2)=  2.4  sigma(3 1)=  3.2
  sigma(3 3)=  2.5  sigma(2 1)=  3.3

"""


def test_read_abinit_output():
    fd = StringIO(sample_outfile)
    results = read_abinit_out(fd)

    assert results.pop('version') == '8.0.8'

    atoms = results.pop('atoms')
    assert all(atoms.symbols == 'OO')
    assert atoms.positions == pytest.approx(
        np.array([[2.5, 2.5, 3.7], [2.5, 2.5, 2.5]]))
    assert all(atoms.pbc)
    assert atoms.cell[:] == pytest.approx(
        np.array([[5.0, 0.0, 0.1], [0.0, 6.0, 0.0], [0.0, 0.0, 7.0]]))

    ref_stress = pytest.approx([2.3, 2.4, 2.5, 3.1, 3.2, 3.3])
    assert results.pop('stress') * (Hartree / Bohr**3) == ref_stress
    assert results.pop('forces') == pytest.approx(
        np.array([[-0.1, -0.3, 0.4], [-0.2, -0.4, -0.5]]))

    for name in 'energy', 'free_energy':
        assert results.pop(name) / Hartree == -42.5

    assert not results
