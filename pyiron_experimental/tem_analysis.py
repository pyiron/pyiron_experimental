import hyperspy.api as hs
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from pyiron_experimental.image_proc import ROISelector
from pyiron_base import GenericJob, DataContainer


def new_figures_without_auto_plot():
    is_interactive = plt.isinteractive()
    plt.ioff()
    fig, ax = plt.subplots()
    plt.close(fig)
    if is_interactive:
        plt.ion()
    return fig, ax


class HSLineProfiles(GenericJob):
    """
    HSLineProfiles is based on hyperspy and operates on a hyperspy 2DSignal.

    For convenience the hyperspy.api is accessible via the `hs` attribute.
    Attributes:
        signal (hs.Signal2D): 2D signal to analyze.
        hs: Access to the `hyperspy.api`
        fig (matplotlib.Figure): figure in which the signal and the region(s) of interest are plotted.
        input (DataContainer): Input parameters
        output (DataContainer)
    """

    def __init__(self, project, job_name):
        """Create a new HSLineProfiles job."""
        super().__init__(project=project, job_name=job_name)
        self._signal = None
        self.fig, self.ax = new_figures_without_auto_plot()
        self._useblit = True
        self._n_lines = -1
        self._line_profiles = {}
        self._active_selector = None
        self._storage = DataContainer(table_name='storage')
        _input = self._storage.create_group('input')
        _input.create_group('lines')
        _input['x'] = []
        _input['y'] = []
        _input['lw'] = []
        _input.create_group('signal')
        _input.signal.hs_class_name = None
        self._storage.create_group('output')
        self._storage.create_group('_control')

    @property
    def hs(self):
        return hs

    def validate_ready_to_run(self):
        if self._signal is None:
            raise ValueError("signal is not defined! Define a signal for which the HSLineProfiles are computed.")
        self._validate_and_prepare_input_run_static()

    @property
    def input(self):
        return self._storage.input

    @property
    def output(self):
        return self._storage.output

    @property
    def signal(self):
        return self._signal

    @signal.setter
    def signal(self, new_signal):
        if not isinstance(new_signal, hs.hyperspy.signal.BaseSignal):
            raise ValueError('The signal has to have be hyperspy signal!')
        if not self.status.initialized:
            raise RuntimeError("Signal cannot be changed for a started job.")
        self._signal = new_signal
        self.input.signal.hs_class_name = new_signal.__class__.__name__
        self.input.signal.data = new_signal.data
        self.input.signal.axes = list(new_signal.axes_manager.as_dictionary().values())
        self.input.signal.metadata = new_signal.metadata.as_dictionary()
        self.input.signal.original_metadata = new_signal.original_metadata.as_dictionary()

    def to_hdf(self, hdf=None, group_name=None):
        super(HSLineProfiles, self).to_hdf()
        self._storage._control['useblit'] = self._useblit
        self._storage.to_hdf(hdf=self._hdf5)

    def from_hdf(self, hdf=None, group_name=None):
        super(HSLineProfiles, self).from_hdf()
        self._storage.from_hdf(hdf=self._hdf5)
        self._useblit = self._storage._control['useblit']
        if self.input.signal.hs_class_name is not None:
            _signal_class = getattr(hs.signals, self.input.signal.hs_class_name)
            _data = self.input.signal.data
            _axes = self.input.signal.axes
            _metadata = self.input.signal.metadata
            _original_metadata = self.input.signal.original_metadata
            self._signal = _signal_class(_data, axes=_axes, metadata=_metadata, original_metadata=_original_metadata)
            for line, x, y, lw in zip(self.input.lines, self.input.x, self.input.y, self.input.lw):
                line_dict = self.input.lines[line]
                if line_dict['lw'] is not None and line_dict['lw'] != lw:
                    raise ValueError(f"Implementation error: line width from input.lines[lw]={line_dict['lw']}"
                                     f" and input.lw={lw} differ.")
                self._add_line(x=x, y=y, lw=lw, line_properties=line_dict['lin_prop'],
                               line_number=line_dict['line'], append_input=False)
            self._n_lines = max(self._line_profiles.keys())

    def plot_signal(self, ax=None):
        # if ax is None:
        #    self.fig, self.ax = plt.subplots()
        # else:
        #    self.ax = ax
        self.ax.imshow(self._signal.data)
        return self.fig

    def plot_roi(self):
        active_line = self.active_line
        for line in self._line_profiles.values():
            line.plot_roi(active=False)
        self.active_line = active_line
        return self.fig

    @property
    def active_line(self):
        return self._active_selector

    @active_line.setter
    def active_line(self, value):
        if self.status.finished and value is not None:
            raise ValueError("Finished jobs cannot be changed.")
        self._active_selector = value
        for selector in self._line_profiles.values():
            selector.set_active(False)
        if isinstance(value, int):
            self._line_profiles[value].set_active(True)
        elif isinstance(value, list):
            for line in value:
                self._line_profiles[line].set_active(True)
        elif value is not None:
            raise ValueError(f"{value} is not an integer.")

    def remove_line(self, line=None):
        """Remove one or several lines.

        Args:
            line(int/list/None): if None, remove active line, otherwise remove line(s) if the index specified.
        """
        if line is None and self.active_line is None:
            raise ValueError("No line selected!")
        elif line is None and isinstance(self.active_line, list):
            lines = self.active_line
        elif line is None:
            lines = [self.active_line]
        elif isinstance(line, list):
            lines = line
        elif isinstance(line, int):
            lines = [line]
        else:
            raise ValueError(f"'{line}' is not a valid description to select (a) line(s) to be removed.")

        for line in lines:
            self._line_profiles[line].remove_roi_selection()
            del self._line_profiles[line]

    def add_line(self, lw=5, line_properties=None, x=None, y=None):
        if self.ax is None:
            self.plot_signal()
        if line_properties is None:
            line_properties = dict(color=f"C{self._n_lines + 1}")
        valid = self._validate_and_prepare_input_run_static(fail=False)
        if valid is not True:
            raise ValueError(f"Prior defined input is not valid: \n {valid[0].args}") from valid[0]
        self._add_line(x, y, lw, line_properties)
        self.active_line = self._n_lines

    def _add_line(self, x, y, lw, line_properties=None, line_number=None, append_input=True):
        line_profile = LineProfile(self._signal, ax=self.ax)
        line_profile.useblit = self._useblit
        lw = lw or 5
        self._n_lines += 1
        line_number = line_number or self._n_lines
        self._line_profiles[line_number] = line_profile
        if line_properties is not None:
            line_profile.select_roi(lw=lw, line_properties=line_properties, x=x, y=y)
        else:
            line_profile.calc_roi(lw_px=lw, x_px=x, y_px=y)

        if append_input:
            self.input.lines.append(
                {'line': line_number,
                 'lw': lw,
                 'lin_prop': line_properties}
            )
            self.input.x.append(x)
            self.input.y.append(y)
            self.input.lw.append(lw)

    def plot_line_profiles(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        else:
            fig = ax.figure
        if not self.status.finished:
            self.run(run_mode='interactive')
        lengths = [line_prof.line_length_px * line_prof.scale for line_prof in self._line_profiles.values()]
        for i, profile in self._line_profiles.items():
            if profile.line_properties is None:
                profile.line_properties = {'color': f"C{i}"}
            profile.plot_line_profile(ax=ax, line_properties={"label": f"Line profile {i}"})
        ax.set_xlim(0, np.max(lengths))
        return fig, ax

    def _validate_and_prepare_input_run_static(self, fail=True):
        error = []
        # Check for x-y consistency
        if len(self.input.x) != len(self.input.y):
            error.append(ValueError("Inconsistent number of x and y values!"))

        # Check for x/y - lw consistency; fill with None
        if len(self.input.lw) > 0 and len(self.input.lw) != len(self.input.x):
            error.append(ValueError("Inconsistent number of x/y and lw values!"))
        elif len(self.input.lw) > 0:
            lw = self.input.lw
        else:
            lw = [None for _ in self.input.x]

        # Check for x/y - lines consistency; fill with appropriate dict
        if len(self.input.lines) > 0 and len(self.input.lines) != len(self.input.x):
            error.append(ValueError("Inconsistent number of x/y and lw values!"))
        elif len(self.input.lines) > 0:
            lines = self.input.lines
        else:
            lines = [
                {'line': i,
                 'lw': lw,
                 'lin_prop': None}
                for i, lw in enumerate(self.input.lw)
            ]

        if len(error) == 0:
            # Update input variables
            self.input.lw = lw
            self.input.lines = DataContainer(lines)
            return True
        elif fail:
            raise error[0]
        else:
            return error

    def run_static(self):
        self.status.running = True
        if self.job_id is not None:
            self.project.db.item_update({"timestart": datetime.now()}, self.job_id)
        self._validate_and_prepare_input_run_static()
        for x, y, _lw in zip(self.input.x, self.input.y, self.input.lw):
            self._add_line(x=x, y=y, lw=_lw, append_input=False)
        self._calc()
        self.to_hdf()
        self.active_line = None
        self.status.finished = True

    def _calc(self):
        for i, key in enumerate(self._line_profiles.keys()):
            profile = self._line_profiles[key]
            if self.server.run_mode.interactive:
                profile.calc_roi()
            self.input.x[i] = profile.x_in_px
            self.input.y[i] = profile.y_in_px
            self.input.lw[i] = profile.lw_in_px
            line_prof = profile.hs_line_profile
            self.output.append({
                'line': key,
                'x': self.input.x[i],
                'y': self.input.y[i],
                'lw': self.input.lw[i],
                'data': line_prof.data,
                'scale': profile.scale,
                'unit': line_prof.axes_manager[0].units
            })

    def collect_output(self):
        pass

    def run_if_interactive(self):
        self.status.running = True
        self._calc()
        self.to_hdf()

    def interactive_close(self):
        self.to_hdf()
        self.active_line = None
        self.status.finished = True

    def interactive_fetch(self):
        pass

    def interactive_flush(self, path="generic", include_last_step=True):
        pass

    def run_if_refresh(self):
        pass

    def _run_if_busy(self):
        pass

    def write_input(self):
        pass


class LineProfile:
    def __init__(self, signal, ax=None):
        """Calculate a single line profile for a hyperspy.Signal2D

        Args:
            signal(hyperspy.Signal2D): The signal to analyze.
            ax(None/matplotlib.Axis): The axis to plot the signal/roi on.
        """
        self._signal = signal
        self.useblit = True
        if ax is None:
            self.fig, self.ax = new_figures_without_auto_plot()
        else:
            self.fig = ax.figure
            self.ax = ax
        self._init_state_variables()
        self._scale = self._signal.axes_manager[0].scale
        self._unit = self._signal.axes_manager[0].units

    def _init_state_variables(self):
        self._selector = None
        self._lw = None
        self._line_properties = None
        self._hs_line_profile = None
        self._hs_roi = None
        self._x = None
        self._y = None

    def set_active(self, active):
        if self._selector is not None:
            self._selector.set_active(active)

    def remove_roi_selection(self):
        self._selector.clear_select()
        self._init_state_variables()

    def plot_signal(self):
        self.ax.imshow(self._signal.data)
        return self.fig, self.ax

    @property
    def unit(self):
        return self._unit

    @property
    def line_properties(self):
        return self._line_properties

    @line_properties.setter
    def line_properties(self, value):
        if not isinstance(value, dict):
            raise TypeError(f"{value} is not a dictionary")
        if 'lw' in value or 'linewidth' in value:
            print("linewidth only affects plotting!")
        self._line_properties = value

    @property
    def lw_in_px(self):
        return self._lw

    @property
    def lw_in_unit(self):
        return self.scale * self._lw

    @property
    def x_in_px(self):
        if self._x is None and self._selector is not None:
            self._x = self._selector.x
        return self._x

    @property
    def y_in_px(self):
        if self._y is None and self._selector is not None:
            self._y = self._selector.y
        return self._y

    def plot_roi(self, x=None, y=None, active=True):
        if self._selector is None:
            self._selector = ROISelector(self.ax)
            self._selector.useblit = self.useblit
        if not active:
            x = [xi for xi in x] if x is not None else self.x_in_px
            y = [yi for yi in y] if y is not None else self.y_in_px
        line_properties = self.line_properties
        roi_linewidth = line_properties.pop('roi_linewidth', None)
        if 'lw' not in line_properties and 'linewidth' not in line_properties:
            line_properties['linewidth'] = roi_linewidth or self._lw or 5
        self._selector.select_line(line_properties=line_properties, x=x, y=y)
        self.set_active(active)

    def select_roi(self, lw=5, line_properties=None, x=None, y=None):
        if line_properties is None:
            line_properties = dict(roi_linewidth=lw)
        else:
            line_properties['roi_linewidth'] = lw
        self._lw = lw
        self._line_properties = line_properties
        self.plot_roi(x=x, y=y)

    def calc_roi(self, x_px=None, y_px=None, lw_px=None):
        if (x_px is None or y_px is None or lw_px is None) and self._selector is None:
            raise RuntimeError('One parameter not provided and no active roi selector.')
        self._hs_line_profile = None

        scale = self.scale
        self._x = np.array(x_px) if x_px is not None else self._selector.x
        self._y = np.array(y_px) if y_px is not None else self._selector.y
        self._lw = lw_px or self._lw
        x = self._x * scale
        y = self._y * scale
        lw = self._lw * scale
        x += self._signal.axes_manager[0].offset
        y += self._signal.axes_manager[1].offset
        self._hs_roi = hs.roi.Line2DROI(x[0], y[0], x[1], y[1], linewidth=lw)

    @property
    def hs_roi(self):
        if self._hs_roi is None:
            self.calc_roi()
        return self._hs_roi

    @property
    def hs_line_profile(self):
        if self._hs_line_profile is None:
            self._hs_line_profile = self.hs_roi(self._signal)
        return self._hs_line_profile

    @property
    def line_length_px(self):
        x1, x2 = self.x_in_px
        y1, y2 = self.y_in_px
        return np.linalg.norm(np.array([x2, y2]) - np.array([x1, y1]))

    @property
    def scale(self):
        return self._scale

    def plot_line_profile(self, ax=None, line_properties=None):
        _line_properties = dict(linestyle="-", color="C1", label="Line profile")
        if self._line_properties is not None:
            _line_properties.update(self._line_properties)
            _line_properties.pop('lw', None)
            _line_properties.pop('linewidth', None)
            _line_properties.pop('roi_linewidth', None)
        if line_properties is not None:
            _line_properties.update(line_properties)

        profile = self.hs_line_profile
        if ax is None:
            fig, ax = plt.subplots()
        else:
            fig = ax.figure
        ax.plot(np.arange(profile.data.shape[0]) * self.scale, profile.data, **_line_properties)

        ax.legend()
        ax.set_yticks([])

        ax.set_xlim(0, self.line_length_px * self.scale)

        ax.set_xlabel(f"Distance ({self.unit})")
        ax.set_ylabel("Intensity (a.u)")

        return fig
