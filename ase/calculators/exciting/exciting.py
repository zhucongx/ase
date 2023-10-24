"""ASE Calculator for the ground state exciting DFT code.

Exciting calculator class in this file allow for writing exciting input
files using ASE Atoms object that allow for the compiled exciting binary
to run DFT on the geometry/material defined in the Atoms object. Also gives
access to developer to a lightweight parser (lighter weight than NOMAD or
the exciting parser in the exciting repository) to capture ground state
properties.

Note: excitingtools must be installed using `pip install excitingtools` to
use this calculator.
"""

from os import PathLike
from pathlib import Path
from typing import Any, Mapping

import ase.io.exciting
from ase.calculators.calculator import PropertyNotImplementedError
from ase.calculators.exciting.runner import (SimpleBinaryRunner,
                                             SubprocessRunResults)
from ase.calculators.genericfileio import (CalculatorTemplate,
                                           GenericFileIOCalculator)


class ExcitingProfile:
    """Defines all quantities that are configurable for a given machine.

    Follows the generic pattern BUT currently not used by our calculator as:
       * species_path is part of the input file in exciting.
       * OnlyTypo fix part of the profile used in the base class is the run
         method, which is part of the BinaryRunner class.
    """
    def __init__(self, exciting_root, species_path):
        from excitingtools.input.base_class import query_exciting_version
        self.version = query_exciting_version(exciting_root)
        self.species_path = species_path


class ExcitingGroundStateTemplate(CalculatorTemplate):
    """Template for Ground State Exciting Calculator

    Abstract methods inherited from the base class:
        * write_input
        * execute
        * read_results
    """
    program_name = 'exciting'
    parser = {'info.xml': ase.io.exciting.parse_output}
    output_names = list(parser)
    # Use frozenset since the CalculatorTemplate enforces it.
    implemented_properties = frozenset(['energy', 'tforce'])

    def __init__(self):
        """Initialise with constant class attributes.

        :param program_name: The DFT program, should always be exciting.
        :param implemented_properties: What properties should exciting
            calculate/read from output.
        """
        super().__init__(self.program_name, self.implemented_properties)

    @staticmethod
    def _require_forces(
            input_parameters):
        """Expect ASE always wants forces, enforce setting in input_parameters.

        :param input_parameters: exciting ground state input parameters, either
            as a dictionary or ExcitingGroundStateInput.
        :return: Ground state input parameters, with "compute
                forces" set to true.
        """
        from excitingtools import ExcitingGroundStateInput

        input_parameters = ExcitingGroundStateInput(input_parameters)
        input_parameters.tforce = True
        return input_parameters

    def write_input(self,
                    directory: PathLike,
                    atoms: ase.Atoms,
                    parameters: dict,
                    properties=None):
        """Write an exciting input.xml file based on the input args.

        :param directory: Directory in which to run calculator.
        :param atoms: ASE atoms object.
        :param parameters: exciting ground state input parameters, in a
            dictionary. Expect species_path, title and ground_state data,
            either in an object or as dict.
        :param properties: Currently, unused. Base method's API expects the
            physical properties expected from a ground state
            calculation, for example energies and forces.
        """
        del properties  # Unused but kept for API consistency.
        # Create a copy of the parameters dictionary so we don't
        # modify the callers dictionary.
        parameters_dict = parameters
        assert set(parameters_dict.keys()) == {
            'title', 'species_path', 'ground_state_input'}, \
            'Keys should be defined by ExcitingGroundState calculator'
        file_name = Path(directory) / 'input.xml'
        species_path = parameters_dict.pop('species_path')
        title = parameters_dict.pop('title')

        ase.io.exciting.write_input_xml_file(
            file_name, atoms, parameters_dict['ground_state_input'],
            species_path, title)

    def execute(
            self, directory: PathLike,
            profile) -> SubprocessRunResults:
        """Given an exciting calculation profile, execute the calculation.

        :param directory: Directory in which to execute the calculator
            exciting_calculation: Base method `execute` expects a profile,
            however it is simply used to execute the program, therefore we
            just pass a SimpleBinaryRunner.
        :param profile: This name comes from the superclass CalculatorTemplate.
                It contains machine specific information to run the
                calculation.

        :return: Results of the subprocess.run command.
        """
        return profile.run(directory)

    def read_results(self, directory: PathLike) -> Mapping[str, Any]:
        """Parse results from each ground state output file.

        Note we allow for the ability for there to be multiple output files.

        :param directory: Directory path to output file from exciting
            simulation.
        :return: Dictionary containing important output properties.
        """
        results = {}
        for file_name in self.output_names:
            full_file_path = Path(directory) / file_name
            result: dict = self.parser[file_name](full_file_path)
            results.update(result)
        return results


class ExcitingGroundStateResults:
    """Exciting Ground State Results."""
    def __init__(self, results: dict) -> None:
        self.results = results
        self.final_scl_iteration = list(results["scl"].keys())[-1]

    def total_energy(self) -> float:
        """Return total energy of system."""
        # TODO(Alex) We should a common list of keys somewhere
        # such that parser -> results -> getters are consistent
        return float(
            self.results['scl'][self.final_scl_iteration][
                'Total energy'])

    def band_gap(self) -> float:
        """Return the estimated fundamental gap from the exciting sim."""
        return float(
            self.results['scl'][self.final_scl_iteration][
                'Estimated fundamental gap'])

    def forces(self):
        """Return forces present on the system.

        Currently, not all exciting simulations return forces. We leave this
        definition for future revisions.
        """
        raise PropertyNotImplementedError

    def stress(self):
        """Get the stress on the system.

        Right now exciting does not yet calculate the stress on the system so
        this won't work for the time being.
        """
        raise PropertyNotImplementedError


class ExcitingGroundStateCalculator(GenericFileIOCalculator):
    """Class for the ground state calculation.

    :param runner: Binary runner that will execute an exciting calculation and
        return a result.
    :param ground_state_input: dictionary of ground state settings for example
        {'rgkmax': 8.0, 'autormt': True} or an object of type
        ExcitingGroundStateInput.
    :param directory: Directory in which to run the job.
    :param species_path: Path to the location of exciting's species files.
    :param title: job name written to input.xml

    :return: Results returned from running the calculate method.


    Typical usage:

    gs_calculator = ExcitingGroundState(runner, ground_state_input)

    results: ExcitingGroundStateResults = gs_calculator.calculate(
            atoms: Atoms)
    """
    def __init__(self, *,
                 runner: SimpleBinaryRunner,
                 ground_state_input,
                 directory='./',
                 species_path='./',
                 title='ASE-generated input'):

        self.runner = runner
        # Package data to be passed to
        # ExcitingGroundStateTemplate.write_input(..., input_parameters, ...)
        # Structure not included, as it's passed when one calls .calculate
        # method directly
        self.exciting_inputs = {
            'title': title, 'species_path': species_path,
            'ground_state_input': ground_state_input}
        self.directory = Path(directory)

        # GenericFileIOCalculator expects a `profile`
        # containing machine-specific settings, however, in exciting's case,
        # the species file are defined in the input XML (hence passed in the
        # parameters argument) and the only other machine-specific setting is
        # the BinaryRunner. Furthermore, in GenericFileIOCalculator.calculate,
        # profile is only used to provide a run method. We therefore pass the
        # BinaryRunner in the place of a profile.
        super().__init__(
            profile=runner,
            template=ExcitingGroundStateTemplate(),
            parameters=self.exciting_inputs,
            directory=directory)
