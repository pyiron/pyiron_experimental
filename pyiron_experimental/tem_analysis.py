import hyperspy.api as hs
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from pyiron_experimental.image_proc import ROISelector
from pyiron_base import GenericMaster, GenericJob, DataContainer, InteractiveBase


class LineProfiles(GenericJob):
    def __init__(self, project, job_name):
        super().__init__(project=project, job_name=job_name)
        self._signal = None
        # self.fig = self.ax = None
        is_interactive = plt.isinteractive()
        plt.ioff()
        self.fig, self.ax = plt.subplots()
        plt.close(self.fig)
        if is_interactive:
            plt.ion()
        self._line_profiles = []
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

    def validate_ready_to_run(self):
        if self._signal is None:
            raise ValueError("signal is not defined! Define a signal for which the LineProfiles are computed.")

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
        super(LineProfiles, self).to_hdf()
        self._storage.to_hdf(hdf=self._hdf5)

    def from_hdf(self, hdf=None, group_name=None):
        super(LineProfiles, self).from_hdf()
        self._storage.from_hdf(hdf=self._hdf5)
        if self.input.signal.hs_class_name is not None:
            _signal_class = getattr(hs.signals, self.input.signal.hs_class_name)
            _data = self.input.signal.data
            _axes = self.input.signal.axes
            _metadata = self.input.signal.metadata
            _original_metadata = self.input.signal.original_metadata
            self._signal = _signal_class(_data, axes=_axes, metadata=_metadata, original_metadata=_original_metadata)
            for line, x, y, lw in zip(self.input.lines, self.input.x, self.input.y, self.input.lw):
                self._add_line_interactive(lw, line['lin_prop'], x, y)

    def plot_signal(self, ax=None):
        #if ax is None:
        #    self.fig, self.ax = plt.subplots()
        #else:
        #    self.ax = ax
        self.ax.imshow(self._signal.data)
        return self.fig

    def plot_roi(self):
        active_line = self.active_line
        for line in self._line_profiles:
            line.plot_roi(active=False)
        self.active_line = active_line
        return self.fig

    @property
    def active_line(self):
        return self._active_selector

    @active_line.setter
    def active_line(self, value):
        if self.status.finished:
            raise ValueError("Finished jobs cannot be changed.")
        self._active_selector = value
        for selector in self._line_profiles:
            selector.set_active(False)
        if value is not None:
            self._line_profiles[value].set_active(True)

    def _add_line_interactive(self, lw, line_properties, x, y):
        line_profile = LineProfile(self._signal, ax=self.ax)
        self._line_profiles.append(line_profile)
        line_profile.select_roi(lw=lw, line_properties=line_properties, x=x, y=y)

    def add_line(self, lw=5, line_properties=None, x=None, y=None):
        if self.ax is None:
            self.plot_signal()
        if line_properties is None:
            line_properties = dict(color=f"C{len(self._line_profiles)}")
        self._add_line_interactive(lw, line_properties, x, y)
        self.active_line = len(self._line_profiles) - 1
        self.input.lines.append(
            {'line': self.active_line,
             'lw': lw,
             'lin_prop': line_properties}
        )
        self.input.x.append(x)
        self.input.y.append(y)
        self.input.lw.append(lw)

    def _add_line_static(self, x, y, lw):
        print(f"lw={lw}, x={x}, y={y}")
        lw = lw or 5
        line_profile = LineProfile(self._signal, ax=self.ax)
        self._line_profiles.append(line_profile)
        line_profile.calc_roi(lw_px=lw, x_px=x, y_px=y)

    def plot_line_profiles(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        else:
            fig = ax.figure
        lengths = [line_prof.line_length_px * line_prof.scale for line_prof in self._line_profiles]
        for i, profile in enumerate(self._line_profiles):
            profile.plot_line_profile(ax=ax, line_properties={"label": f"Line profile {i}"})
        ax.set_xlim(0, np.max(lengths))
        return fig, ax

    def run_static(self):
        self.status.running = True
        if self.job_id is not None:
            self.project.db.item_update({"timestart": datetime.now()}, self.job_id)
        if len(self.input.x) != len(self.input.y):
            raise ValueError("Inconsistent number of x and y values!")
        if len(self.input.lw) > 0:
            if len(self.input.lw) != len(self.input.x):
                raise ValueError("Inconsistent number of x/y and lw values!")
            else:
                lw = self.input.lw
        else:
            lw = [None for _ in self.input.x]
        self.input.lw = lw

        for x, y, _lw in zip(self.input.x, self.input.y, self.input.lw):
            self._add_line_static(x, y, _lw)
        self._calc()
        self.to_hdf()
        self.active_line = None
        self.status.finished = True

    def _calc(self):
        for i, profile in enumerate(self._line_profiles):
            self.input.x[i] = profile.x_in_px
            self.input.y[i] = profile.y_in_px
            self.input.lw[i] = profile.lw_in_px
            line_prof = profile.hs_line_profile
            self.output.append({
                'line': i,
                'x': self.input.x[i],
                'y': self.input.x[i],
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
    def __init__(self, emd_signal, ax=None):
        self._signal = emd_signal
        if ax is None:
            self.fig = self.ax = None
        else:
            self.fig = ax.figure
            self.ax = ax
        self._selector = None
        self._lw = None
        self._line_properties = None
        self._hs_line_profile = None
        self._hs_roi = None
        self._x = None
        self._y = None
        self._scale = self._signal.axes_manager[0].scale
        self._unit = self._signal.axes_manager[0].units

    def set_active(self, active):
        self._selector.set_active(active)

    def plot_signal(self):
        self.fig, self.ax = plt.subplots()
        self.ax.imshow(self._signal.data)
        return self.fig, self.ax

    @property
    def unit(self):
        return self._unit

    @property
    def lw_in_px(self):
        return self._lw

    @property
    def lw_in_unit(self):
        return self.scale * self._lw

    @property
    def x_in_px(self):
        if self._x is None:
            self._x = self._selector.x
        return self._x

    @property
    def y_in_px(self):
        if self._y is None:
            self._y = self._selector.y
        return self._y

    def plot_roi(self, x=None, y=None, active=True):
        if self.ax is None:
            self.plot_signal()
        if self._selector is None:
            self._selector = ROISelector(self.ax)
        if not active:
            x = x or self.x_in_px
            y = y or self.y_in_px
        self._selector.select_line(line_properties=self._line_properties, x=x, y=y)
        self.set_active(active)

    def select_roi(self, lw=5, line_properties=None, x=None, y=None):
        if line_properties is None:
            line_properties = dict(linewidth=lw)
        else:
            line_properties['linewidth'] = lw
        self._lw = lw
        self._line_properties = line_properties
        self.plot_roi(x=x, y=y)

    def calc_roi(self, x_px=None, y_px=None, lw_px=None):
        if (x_px is None or y_px is None or lw_px is None) and self._selector is None:
            raise RuntimeError('One parameter not provided and no active roi selector.')
        self._hs_line_profile = None

        scale = self.scale
        self._x = np.array(x_px or self._selector.x)
        self._y = np.array(y_px or self._selector.y)
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
        if line_properties is not None:
            _line_properties.update(line_properties)

        profile = self.hs_line_profile
        if ax is None:
            fig, ax = plt.subplots()
        ax.plot(np.arange(profile.data.shape[0]) * self.scale, profile.data, **_line_properties)

        ax.legend()
        ax.set_yticks([])

        ax.set_xlim(0, self.line_length_px * self.scale)

        ax.set_xlabel(f"Distance ({self.unit})")
        ax.set_ylabel("Intensity (a.u)")

