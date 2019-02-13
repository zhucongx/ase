import numpy as np
import ase.units
from ase.atoms import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import read
from ase.data import chemical_symbols


class ACEMoleculeReader:

    def __init__(self, filename):
        self.parse(filename)

    def auto_type(self, data):
        ''' tries to determine type'''
        try:
            return float(data)
        except ValueError:
            pass

        try:
            ds = data.split(",")
            array = []

            for d in ds:
                array.append(float(d))

            return array
        except ValueError:
            pass

        return data

    def parse(self, filename):
        ''' Read atoms geometry '''
        f = open(filename, 'r')
        lines = f.readlines()
        start_line = 0
        end_line = 0
        for i in range(len(lines)):
            if(lines[i] == '====================  Atoms  =====================\n'):
                start_line = i
            if(start_line != '' and len(lines[i].split('=')) == '3'):
                end_line = i
                break
        self.data = []
        atoms = []
        positions = []
        new_dict = {}
        for i in range(start_line + 1, end_line):
            atomic_number = lines[i].split()[0]
            atoms.append(str(chemical_symbols[int(atomic_number)]))
            x = lines[i].split()[1]
            y = lines[i].split()[2]
            z = lines[i].split()[3]
            positions.append((x, y, z))
        new_dict["Atomic_numbers"] = atoms
        new_dict["Positions"] = positions
        self.data = new_dict


def read_acemolecule_out(filename, quantity='atoms'):
    '''interface to ACEMoleculeReader and returns various quantities'''
    data = ACEMoleculeReader(filename).data
    atom_symbol = np.array(data["Atomic_numbers"])
    positions = np.array(data["Positions"])
    atoms = Atoms(atom_symbol, positions=positions)

    f = open(filename, 'r')
    lines = f.readlines()
    geometry = zip(atom_symbol, positions)
#    energy = 0.0

    if(quantity == 'excitation-energy'):
        f.close()
        # ee is excitation-energy
        ee = 1
        return ee

    for i in range(len(lines) - 1, 1, -1):
        line = lines[i].split()
        if(len(line) > 2):
            if(line[0] == 'Total' and line[1] == 'energy'):
                energy = float(line[3])
                break
    f.close()
    energy *= ase.units.Hartree
    # energy must be modified, hartree to eV

    for i in range(len(lines) - 1, 1, -1):
        if (lines[i] == '!================================================\n'):
            endline_num = i
        if (lines[i] == '! Atom           x         y         z\n'):
            forces = []
            startline_num = i
            for j in range(startline_num + 1, endline_num):
                forces += [[float(lines[j].split()[3]),
                            float(lines[j].split()[4]),
                            float(lines[j].split()[5])]]
            convert = ase.units.Hartree / ase.units.Bohr
            forces = np.array(forces) * convert
            break
        if(i == 30):
            forces = None
            break
    calc = SinglePointCalculator(atoms, energy=energy, forces=forces)
    atoms.set_calculator(calc)
    if(quantity == 'energy'):
        return energy
    if(quantity == 'forces'):
        return forces
    if(quantity == 'geometry'):
        #        f.close()
        return geometry
    if(quantity == 'atoms'):
        #        f.close()
        return atoms


def read_acemolecule_input(Label):
    '''Reads a Acemolecule input file'''
    filename = Label
    inputtemplate = open(filename, 'r')
    lines = inputtemplate.readlines()
    for line in lines:
        if(len(line.split('GeometryFilename')) > 1):
            geometryfile = line.split()[2]
            break
    atoms = read(geometryfile, format='xyz')
    inputtemplate.close()
    return atoms

if __name__ == "__main__":
    import sys
    from ase.io import read as ACE_read
    Label = str(sys.argv[1].split('.inp')[0])
    system_changes = None
    a = ACE_read(Label + '.inp', format='acemolecule-input')

    filename = Label + '.log'
