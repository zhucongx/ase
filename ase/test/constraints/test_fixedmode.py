def test_fixedmode():
    """Test that FixedMode can be set, turned into a dict, and
    back to a constraint with the same mode."""
    import numpy as np

    from ase.build import molecule
    from ase.constraints import FixedMode, dict2constraint

    # Create a simple mode.
    atoms = molecule('CH3OH')
    initial_positions = atoms.positions.copy()
    atoms.rattle(stdev=0.5)
    mode = atoms.positions - initial_positions

    # Test the constraint.
    constraint = FixedMode(mode)
    dict_constraint = constraint.todict()
    new_constraint = dict2constraint(dict_constraint)
    assert np.isclose(new_constraint.mode, constraint.mode).all()
