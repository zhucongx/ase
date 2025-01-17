import numpy as np

from ase.calculators.lammpslib import is_upper_triangular


def test_lammpslib_interface():
    """test some functionality of the interace"""
    m = np.ones((3, 3))
    assert not is_upper_triangular(m)

    m[2, 0:2] = 0
    m[1, 0] = 0
    assert is_upper_triangular(m)
