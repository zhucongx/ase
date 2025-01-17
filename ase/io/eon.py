# Copyright (C) 2012, Jesper Friis, SINTEF
# (see accompanying license files for ASE).
"""Module to read and write atoms EON reactant.con files.

See http://theory.cm.utexas.edu/eon/index.html for a description of EON.
"""
import os
from glob import glob
from warnings import warn

import numpy as np

from ase.atoms import Atoms
from ase.constraints import FixAtoms
from ase.geometry import cell_to_cellpar, cellpar_to_cell
from ase.utils import writer


def read_eon(fileobj, index=-1):
    """Reads an EON reactant.con file.  If *fileobj* is the name of a
    "states" directory created by EON, all the structures will be read."""
    if isinstance(fileobj, str):
        if (os.path.isdir(fileobj)):
            return read_states(fileobj)
        else:
            fd = open(fileobj)
    else:
        fd = fileobj

    more_images_to_read = True
    images = []

    first_line = fd.readline()
    while more_images_to_read:

        comment = first_line.strip()
        fd.readline()  # 0.0000 TIME  (??)
        cell_lengths = fd.readline().split()
        cell_angles = fd.readline().split()
        # Different order of angles in EON.
        cell_angles = [cell_angles[2], cell_angles[1], cell_angles[0]]
        cellpar = [float(x) for x in cell_lengths + cell_angles]
        fd.readline()  # 0 0     (??)
        fd.readline()  # 0 0 0   (??)
        ntypes = int(fd.readline())  # number of atom types
        natoms = [int(n) for n in fd.readline().split()]
        atommasses = [float(m) for m in fd.readline().split()]

        symbols = []
        coords = []
        masses = []
        fixed = []
        for n in range(ntypes):
            symbol = fd.readline().strip()
            symbols.extend([symbol] * natoms[n])
            masses.extend([atommasses[n]] * natoms[n])
            fd.readline()  # Coordinates of Component n
            for i in range(natoms[n]):
                row = fd.readline().split()
                coords.append([float(x) for x in row[:3]])
                fixed.append(bool(int(row[3])))

        atoms = Atoms(symbols=symbols,
                      positions=coords,
                      masses=masses,
                      cell=cellpar_to_cell(cellpar),
                      constraint=FixAtoms(mask=fixed),
                      info=dict(comment=comment))

        images.append(atoms)

        first_line = fd.readline()
        if first_line == '':
            more_images_to_read = False

    if isinstance(fileobj, str):
        fd.close()

    if not index:
        return images
    else:
        return images[index]


def read_states(states_dir):
    """Read structures stored by EON in the states directory *states_dir*."""
    subdirs = glob(os.path.join(states_dir, '[0123456789]*'))
    subdirs.sort(key=lambda d: int(os.path.basename(d)))
    images = [read_eon(os.path.join(subdir, 'reactant.con'))
              for subdir in subdirs]
    return images


@writer
def write_eon(fileobj, images):
    """Writes structure to EON reactant.con file
    Multiple snapshots are allowed."""
    if isinstance(images, Atoms):
        atoms = images
    elif len(images) == 1:
        atoms = images[0]
    else:
        raise ValueError('Can only write one configuration to EON '
                         'reactant.con file')

    out = []
    out.append(atoms.info.get('comment', 'Generated by ASE'))
    out.append('0.0000 TIME')  # ??

    a, b, c, alpha, beta, gamma = cell_to_cellpar(atoms.cell)
    out.append('%-10.6f  %-10.6f  %-10.6f' % (a, b, c))
    out.append('%-10.6f  %-10.6f  %-10.6f' % (gamma, beta, alpha))

    out.append('0 0')    # ??
    out.append('0 0 0')  # ??

    symbols = atoms.get_chemical_symbols()
    massdict = dict(list(zip(symbols, atoms.get_masses())))
    atomtypes = sorted(massdict.keys())
    atommasses = [massdict[at] for at in atomtypes]
    natoms = [symbols.count(at) for at in atomtypes]
    ntypes = len(atomtypes)

    out.append(str(ntypes))
    out.append(' '.join([str(n) for n in natoms]))
    out.append(' '.join([str(n) for n in atommasses]))

    atom_id = 0
    for n in range(ntypes):
        fixed = np.array([False] * len(atoms))
        out.append(atomtypes[n])
        out.append('Coordinates of Component %d' % (n + 1))
        indices = [i for i, at in enumerate(symbols) if at == atomtypes[n]]
        a = atoms[indices]
        coords = a.positions
        for c in a.constraints:
            if not isinstance(c, FixAtoms):
                warn('Only FixAtoms constraints are supported by con files. '
                     'Dropping %r', c)
                continue
            if c.index.dtype.kind == 'b':
                fixed = np.array(c.index, dtype=int)
            else:
                fixed = np.zeros((natoms[n], ), dtype=int)
                for i in c.index:
                    fixed[i] = 1
        for xyz, fix in zip(coords, fixed):
            out.append('%22.17f %22.17f %22.17f %d %4d' %
                       (tuple(xyz) + (fix, atom_id)))
            atom_id += 1
    fileobj.write('\n'.join(out))
    fileobj.write('\n')
