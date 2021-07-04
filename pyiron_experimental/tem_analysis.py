import hyperspy.roi as hs_roi
import matplotlib.pyplot as plt
import numpy as np

from pyiron_experimental.image_proc import ROISelector


class LineProfiles:
    def __init__(self, emd_signal):
        self._signal = emd_signal
        self.fig = self.ax = None
        self._line_profiles = []
        self._active_selector = None

    def plot_signal(self, ax=None):
        #if ax is None:
        #    self.fig, self.ax = plt.subplots()
        #else:
        #    self.ax = ax
        self.fig, self.ax = plt.subplots()
        self.ax.imshow(self._signal.data)
        return self.fig, self.ax

    @property
    def active_line(self):
        return self._active_selector

    @active_line.setter
    def active_line(self, value):
        self._active_selector = value
        for selector in self._line_profiles:
            selector.set_active(False)
        self._line_profiles[value].set_active(True)

    def add_line(self, lw=5, line_properties=None):
        if self.ax is None:
            self.plot_signal()
        line_profile = LineProfile(self._signal, ax=self.ax)
        self._line_profiles.append(line_profile)
        if line_properties is None:
            line_properties = dict(color=f"C{len(self._line_profiles)}")
        line_profile.select_roi(lw=lw, line_properties=line_properties)
        self.active_line = len(self._line_profiles) - 1

    def plot_line_profiles(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        for i, profile in enumerate(self._line_profiles):
            profile.plot_line_profile(ax=ax, line_properties={"label": f"Line profile {i}"})


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

    def set_active(self, active):
        self._selector.set_active(active)

    def plot_signal(self, ax=None):
        #if ax is None:
        #    self.fig, self.ax = plt.subplots()
        #else:
        #    self.ax = ax
        self.fig, self.ax = plt.subplots()
        self.ax.imshow(self._signal.data)

    def select_roi(self, lw=5, line_properties=None):
        if line_properties is None:
            line_properties = dict(linewidth=lw)
        else:
            line_properties['linewidth'] = lw
        self._lw = lw
        self._line_properties = line_properties
        if self.ax is None:
            self.plot_signal()
        if self._selector is None:
            self._selector = ROISelector(self.ax)
        self._selector.select_line(line_properties=line_properties)

    @property
    def hs_line_profile(self):
        return self.hs_roi(self._signal)

    def plot_line_profile(self, ax=None, line_properties=None):
        _line_properties = dict(linestyle="-", color="C1", label="Line profile")
        _line_properties.update(self._line_properties)
        if line_properties is not None:
            _line_properties.update(line_properties)

        profile = self.hs_line_profile
        scale = self._signal.axes_manager[0].scale
        if ax is None:
            fig, ax = plt.subplots()
        ax.plot(np.arange(profile.data.shape[0]) * scale, profile.data, **_line_properties)

        ax.legend()
        ax.set_yticks([])
        x1, x2 = self._selector.x
        y1, y2 = self._selector.y

        line_length = np.linalg.norm(np.array([x2, y2]) - np.array([x1, y1]))
        ax.set_xlim(0, line_length * scale)

        ax.set_xlabel(f"Distance ({profile.axes_manager[0].units})")
        ax.set_ylabel("Intensity (a.u)")

    @property
    def hs_roi(self):
        if self._selector is None:
            raise RuntimeError("You need to select a ROI (select_roi) before this can be converted to hyperspy!")
        scale = self._signal.axes_manager[0].scale
        x = self._selector.x * scale
        y = self._selector.y * scale
        x += self._signal.axes_manager[0].offset
        y += self._signal.axes_manager[1].offset
        return hs_roi.Line2DROI(x[0], y[0], x[1], y[1], linewidth=self._lw * scale)
