import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import namedtuple
from pyiron_base import GenericJob
from pyiron_base.generic.filedata import FileDataTemplate

NanoIndentingCycle = namedtuple('NanoIndentingCycle', ('load', 'depth', 'time'))


class DAF:
    def __init__(self, coefficients):
        self._coefs = coefficients

    def __call__(self, h):
        result = 0
        for p, c in enumerate(self._coefs):
            result += c * pow(h, p)
        return result

    @property
    def coefficients(self):
        return self._coefs


class Indenter:

    def __init__(self, E0, T0, C, poisson, daf, *, T=None):
        self._E0 = E0
        self._T0 = T0
        self._C = C
        self._poisson = poisson
        if isinstance(daf, list):
            self._daf = DAF(daf)
        else:
            raise ValueError
        self._T = T if T is not None else T0

    @property
    def E(self):
        """Bulk modulus of the indenter material at the set temperature"""
        return self._E0 - self._C * self._T * np.exp(-self._T0 / self._T)

    @property
    def poisson(self):
        """Poisson's constant of the indenter material."""
        return self._poisson

    @property
    def T(self):
        """Temperature at which indenter has been used in Kelvin."""
        return self._T if self._T else self._T0

    @T.setter
    def T(self, value):
        self._T = value

    def daf(self, h):
        """Defect Area Function of the indenter in nm^2."""
        return self._daf(h)

    def with_daf(self, daf):
        """Return new instance with updated DAF."""
        return self.__class__(self._E0, self._T0, self._C, self._poisson, daf, T=self.T)

    def to_dict(self):
        return {'E0': self._E0, 'T0':  self._T0, 'C': self._C, 'poisson':  self._poisson, 'T': self._T, 'daf': self._daf.coefficients}


class NanoIndentingExperimentData:

    def __init__(self, samples, *, meta_data=None):
        self._samples = samples
        if isinstance(meta_data, dict):
            self._meta_data = meta_data
        elif meta_data is not None:
            self._meta_data = {k: v for k, v in meta_data.items()}
        else:
            meta_data = {}
        if 'poisson' in meta_data:
            self._poisson = meta_data['poisson']
        else:
            self._poisson = None

    @property
    def data(self):
        return self._samples

    @property
    def poisson(self):
        return self._poisson

    @poisson.setter
    def poisson(self, poisson):
        self._poisson = poisson
        self._meta_data['poisson'] = poisson

    @property
    def meta_data(self):
        return self._meta_data

    @classmethod
    def from_txt(cls, file, **meta_data):
        """Read sample and cycle data from given file.  Expects cycles to be delimited by empty lines and samples
        by two empty lines."""

        with open(file) as f:
            text = f.read()

        return cls.from_str(text, **meta_data)

    @classmethod
    def from_str(cls, text, **meta_data):
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        cycles = [[ NanoIndentingCycle(*np.loadtxt(c.strip().split('\n'), unpack = True))
                           for c in s.split('\n' * 2) ]
                                 for s in text.split('\n' * 3) ]
        return cls(cycles, meta_data=meta_data)

    @classmethod
    def from_data(cls, data, **meta_data):
        text = b''.join(data)
        return cls.from_str(text.decode('utf8'), **meta_data)


class OliverPharr:
    #  W. C. Oliver, G.M. Pharr, J. Mater In: Res. 7, 1992, S. 1564.

    def __init__(self, instruments, experiment):
        if 'Indenter' not in instruments:
            raise ValueError("No Indenter specified!")
        self._indenter = instruments['Indenter']
        self._experiment = experiment

    def validate_ready_to_run(self):
        if self._experiment.poisson is None:
            raise ValueError('Specify poisson of sample.')

    @property
    def experiment(self):
        return self._experiment

    @experiment.setter
    def experiment(self, value):
        self._experiment = value
        if self.experiment is not None and self.indenter is not None:
            self.analyse()

    @property
    def indenter(self):
        return self._indenter

    @indenter.setter
    def indenter(self, value):
        self._indenter = value
        if self.experiment is not None and self.indenter is not None:
            self.analyse()

    def _analyse_cycle(self, cycle):
        i = np.argmax(cycle.load)

        unloading_depth = cycle.depth[i:]
        unloading_load = cycle.load[i:]

        S = np.polyval(np.polyder(np.polyfit(unloading_depth, unloading_load, 5), 1), unloading_depth[0])

        Pmax = cycle.load[i]
        # .72 is a geometry factor for cones, should probably also be configurable
        hs = 0.72 * Pmax / S
        hc = cycle.depth[i] - hs

        A = self.indenter.daf(hc)

        H = Pmax / A * 1e6  # conversion from mN/nm**2 to GPa

        Er = S / np.sqrt(A) * np.sqrt(2) / np.pi
        E = (1 - self.experiment.poisson ** 2) / (
                1 / Er - (1 - self.indenter.poisson ** 2) / self.indenter.E)

        return H, Er, E, 1 / S

    def analyse(self):

        def generate_cycles():
            for i, sample in enumerate(self._experiment._samples):
                for j, cycle in enumerate(sample):
                    t = i + 1, j + 1, *self._analyse_cycle(cycle)
                    yield t

        output = pd.DataFrame(generate_cycles())
        output.columns = "Sample", "Cycle", "Hardness [GPa]", "Reduced E [mN/nm**2]", "Sample E[mN/nm**2]", "Contact Compliance [nm/mN]"
        return output

    def plot_hardness(self, output):
        fig, ax = plt.subplots()
        im = ax.scatter(output['Hardness [GPa]'], output['Contact Compliance [nm/mN]'], c=output.Cycle)
        ax.set_xlabel('Hardness [GPa]')
        ax.set_ylabel('Contact Compliance [nm/mN]')
        c = plt.colorbar(im, ax=ax)
        c.set_label('Cycle')
        return ax
#         return self.output.plot(x = 'Hardness [GPa]', y = 'Contact Compliance [nm/mN]', c = "Cycle", kind = 'scatter',
#                                 colormap = "viridis")


class ExperimentalDataJob(GenericJob):
    def collect_output(self):
        pass

    def write_input(self):
        pass

    _experimental_data_type = {'Nanoindentation': NanoIndentingExperimentData}
    _instrument_type = {'Indenter': Indenter}
    _analysis_type = {"OliverPharr": OliverPharr}

    def __init__(self, project, job_name):
        super().__init__(project, job_name)
        self._meta = {}
        self._experiment = None
        self._data = None
        self._instruments = {}

    @property
    def data(self):
        return self._data

    @property
    def data_types(self):
        return list(self._experimental_data_type.keys())

    @property
    def instruments(self):
        return self._instruments

    @property
    def analysis(self):
        return self._experiment

    #TODO: make experiment_type factory?
    def set_data(self, data, experiment_type, meta_data=None, **kwargs):
        if meta_data is None:
            meta_data = {}
        meta_data.update(kwargs)
        if experiment_type not in self._experimental_data_type:
            raise ValueError(f'Unknown experimental data type{experiment_type}, expected one of {self.data_types}.')
        if isinstance(data, FileDataTemplate):
            _meta_data = {k: v for k, v in data.metadata.items()}
            _meta_data.update(meta_data)
            self._data = self._experimental_data_type[experiment_type].from_data(data.data, **_meta_data,
                                                                                 FileHandle=data.location())
        elif isinstance(data, str) and os.path.exists(data):
            self._data = self._experimental_data_type[experiment_type].from_txt(data, **meta_data)
        elif isinstance(data, str):
            self._data = self._experimental_data_type[experiment_type].from_str(data, **meta_data)
        else:
            self._data = self._experimental_data_type[experiment_type].from_data(data, **meta_data)

    def set_instrument(self, instrument_type, **kwargs):
        if instrument_type not in self._instrument_type:
            raise ValueError(f'Unknown instrument type{instrument_type}, expected one of '
                             f'{list(self._instrument_type.keys())}.')
        self._instruments[instrument_type] = self._instrument_type[instrument_type](**kwargs)

    def set_analysis(self, analysis_type):
        self._experiment = self._analysis_type[analysis_type](self._instruments, self.data)

    def validate_ready_to_run(self):
        if self._experiment is None:
            raise ValueError("No analysis selected!")
        self._experiment.validate_ready_to_run()

    def run_static(self):
        self.input = {
            'Data': {'Class': f"{type(self._data)}",
                     'Metadata': self._data.meta_data,
                     },
            'Instruments': [
                {'Class': _class, 'Instrument': _instrument.to_dict()} for _class, _instrument in self.instruments.items()
            ],
            'AnalysisClass': f"{type(self._experiment)}"
        }
        self.output = self._experiment.analyse()
        self.status.finished = True
