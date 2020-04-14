from distutils.version import LooseVersion
import numpy as np
import pytest

from ase import Atoms
from ase.io import read
from ase.build import bulk

pytestmark = pytest.mark.skipif(LooseVersion(np.__version__) <
                                LooseVersion("1.14"),
                                reason="This test requires numpy >= 1.14")


def make_STO_atoms():
    atoms = Atoms(['Sr', 'Ti', 'O', 'O', 'O'],
                  scaled_positions=[[0, 0, 0],
                                    [0.5, 0.5, 0.5],
                                    [0.5, 0.5, 0],
                                    [0.5, 0, 0.5],
                                    [0, 0.5, 0.5]],
                  cell=[3.905, 3.905, 3.905],
                  pbc=True)

    return atoms


def test_write_read_cycle_xyz_prismatic():
    """Check writing and reading a xtl mustem file."""
    # Reproduce the SI100.XYZ file distributed with prismatic
    atoms = bulk('Si', cubic=True)
    atoms.set_array('occupancy', np.ones_like(atoms.numbers))
    atoms.set_array('debye_waller_factors', np.ones_like(atoms.numbers) * 0.076)

    filename = 'SI100.XYZ'
    atoms.write(filename=filename, format='prismatic',
                comments='one unit cell of 100 silicon')

    atoms_loaded = read(filename=filename, format='prismatic')

    np.testing.assert_allclose(atoms.positions, atoms_loaded.positions)
    np.testing.assert_allclose(atoms.cell, atoms_loaded.cell)
    np.testing.assert_allclose(atoms.get_array('occupancy'),
                               atoms_loaded.get_array('occupancy'))
    np.testing.assert_allclose(atoms.get_array('debye_waller_factors'),
                               atoms_loaded.get_array('debye_waller_factors'))


def test_write_error():
    """Check missing parameter when writing xyz prismatic file."""
    atoms_Si100 = bulk('Si', cubic=True)
    atoms_STO = make_STO_atoms()
    filename = 'SI100.XYZ'

    with pytest.raises(ValueError):
        # DW not provided
        atoms_Si100.write(filename, format='prismatic')

    # Write file with DW provided as scalar
    atoms_Si100.write(filename, format='prismatic',
                      debye_waller_factors=0.076)

    # Write file with DW provided as dict
    atoms_Si100.write(filename, format='prismatic',
                      debye_waller_factors={'Si': 0.076})

    STO_DW_dict = {'Sr': 0.78700E-02, 'O': 0.92750E-02, 'Ti': 0.55700E-02}
    STO_DW_dict_Ti_missing = {key:STO_DW_dict[key] for key in ['Sr', 'O']}

    with pytest.raises(ValueError):
        # DW missing keys
        atoms_STO.write(filename, format='prismatic',
                        debye_waller_factors=STO_DW_dict_Ti_missing)

    atoms_STO.write(filename, format='prismatic',
                    debye_waller_factors=STO_DW_dict)

    with pytest.raises(ValueError):
        # Raise an error if the unit cell is not defined.
        atoms4 = Atoms(['Sr', 'Ti', 'O', 'O', 'O'],
                       positions=[[0, 0, 0],
                                  [0.5, 0.5, 0.5],
                                  [0.5, 0.5, 0],
                                  [0.5, 0, 0.5],
                                  [0, 0.5, 0.5]])
        atoms4.write(filename, format='prismatic',
                     debye_waller_factors=STO_DW_dict)
