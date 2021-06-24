import hyperspy.roi as hs_roi
import matplotlib.pyplot as plt

from pyiron_experimental.image_proc import ROISelector


class LineProfile:
    def __init__(self, emd_signal):
        self._signal = emd_signal
        self.fig = self.ax = None
        self._selector = None
        self._lw = None

    def plot_signal(self):
        self.fig, self.ax = plt.subplots()
        self.ax.imshow(self._signal.data)

    def select_roi(self, lw=5):
        self._lw = lw
        if self.ax is None:
            self.plot_signal()
        self._selector = ROISelector(self.ax)
        self._selector.select_line(lw=lw)

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
