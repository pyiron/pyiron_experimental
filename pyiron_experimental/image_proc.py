import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.widgets as plt_wid
import numpy as np


class LineSelector(plt_wid._SelectorWidget):
    """
    Select a line region of an axes.

    For the cursor to remain responsive you must keep a reference to it.
    """

    def __init__(self, ax, onselect, useblit=False, button=None, maxdist=10, marker_props=None,
                 state_modifier_keys=None, interactive=False, plot_props=None, x=None, y=None):
        r"""
        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The parent axes for the widget.

        onselect : function
            A callback function that is called after a selection is completed.
            It must have the signature::

                def onselect(eclick: MouseEvent, erelease: MouseEvent)

            where *eclick* and *erelease* are the mouse click and release
            `.MouseEvent`\s that start and complete the selection.

        useblit : bool, default: False
            Whether to use blitting for faster drawing (if supported by the
            backend).

        plot_props : dict, optional
            Properties with which the selection is drawn.
            Default::

                dict(color="black", linestyle="-", linewidth=2, alpha=0.5)

        button : `.MouseButton`, list of `.MouseButton`, default: all buttons
            Button(s) that trigger rectangle selection.

        maxdist : float, default: 10
            Distance in pixels within which the interactive tool handles can be
            activated.

        marker_props : dict
            Properties with which the interactive handles are drawn.

        interactive : bool, default: False
            Whether to draw a set of handles that allow interaction with the
            widget after it is drawn.

        state_modifier_keys : dict, optional
            Keyboard modifiers which affect the widget's behavior.  Values
            amend the defaults.

            - "move": Move the existing shape, default: no modifier.
            - "clear": Clear the current shape, default: "escape".
            - "square": Makes the shape square, default: "shift".
            - "center": Make the initial point the center of the shape,
              default: "ctrl".

            "square" and "center" can be combined.
        """
        super().__init__(ax, onselect, useblit=useblit, button=button,
                         state_modifier_keys=state_modifier_keys)
        self.interactive = interactive

        self._init_to_draw(plot_props)

        self.maxdist = maxdist

        if marker_props is None:
            marker_props = dict(markeredgecolor='r')
        x = [xi for xi in x] if x is not None else [0, 0]
        y = [yi for yi in y] if y is not None else [0, 0]
        self._extents = x + y

        self._corner_order = ['I', 'E']  # initial and end point
        self._corner_handles = plt_wid.ToolHandles(self.ax, x, y, marker_props=marker_props,
                                                   useblit=self.useblit)

        xc, yc = self.center
        self._center_handle = plt_wid.ToolHandles(self.ax, [xc], [yc], marker='s',
                                                  marker_props=marker_props,
                                                  useblit=self.useblit)

        self.active_handle = None

        self._selection_artist = self.to_draw
        self._handles_artists = self._center_handle.artists + self._corner_handles.artists

        self.visible = True


        if not self.interactive:
            self._handles_artists = ()

        self._extents_on_press = None

        if self.extents != [0, 0, 0, 0]:
            self.extents = self.extents

    def remove(self):
        for artist in self.artists:
            artist.remove()

    def set_active(self, active):
        if active:
            for artist in self._handles_artists:
                artist.set_markerfacecolor('red')
        else:
            for artist in self._handles_artists:
                artist.set_markerfacecolor('white')
        super().set_active(active)

    def _init_to_draw(self, plot_props):
        _plot_props = dict(color='black', linestyle='-',
                           linewidth=2, alpha=0.5)

        if plot_props is not None:
            _plot_props.update(plot_props)

        _plot_props['animated'] = self.useblit
        self.plot_props = _plot_props
        self.to_draw = plt.Line2D([0, 0], [0, 0], visible=False,
                                  **self.plot_props)
        self.ax.add_line(self.to_draw)

    def _press(self, event):
        """Button press event handler."""
        # make the drawn box/line visible get the click-coordinates,
        # button, ...
        if self.interactive and self.to_draw.get_visible():
            self._set_active_handle(event)
        else:
            self.active_handle = None

        if self.active_handle is None or not self.interactive:
            # Clear previous rectangle before drawing new rectangle.
            self.update()

        if not self.interactive:
            x = event.xdata
            y = event.ydata
            self.extents = x, x, y, y

        self.set_visible(self.visible)

    def draw_shape(self, extents):
        x0, x1, y0, y1 = extents
        self.to_draw.set_data([x0, x1], [y0, y1])

    def _set_active_handle(self, event):
        """Set active handle based on the location of the mouse event."""
        # Note: event.xdata/ydata in data coordinates, event.x/y in pixels
        c_idx, c_dist = self._corner_handles.closest(event.x, event.y)
        _, m_dist = self._center_handle.closest(event.x, event.y)

        if 'move' in self.state:
            self.active_handle = 'C'
            self._extents_on_press = self.extents

        # Set active handle as closest handle, if mouse click is close enough.
        elif m_dist < self.maxdist * 2:
            self.active_handle = 'C'
        elif c_dist > self.maxdist:
            self.active_handle = None
            return
        else:
            self.active_handle = self._corner_order[c_idx]

        # Save coordinates of rectangle at the start of handle movement.
        x1, x2, y1, y2 = self.extents
        # Switch variables so that only x2 and/or y2 are updated on move.
        if self.active_handle == 'I':
            x1, x2 = x2, event.xdata
            y1, y2 = y2, event.ydata

        self._extents_on_press = x1, x2, y1, y2

    @property
    def extents(self):
        return self._extents

    @extents.setter
    def extents(self, extents):
        # Update displayed shape
        self._extents = extents
        self.draw_shape(extents)
        # Update displayed handles
        self._corner_handles.set_data([extents[0], extents[1]], y=[extents[2], extents[3]])
        self._center_handle.set_data(*self.center)
        self.set_visible(self.visible)
        self.update()

    @property
    def center(self):
        return (self.extents[0] + self.extents[1]) / 2., (self.extents[2] + self.extents[3]) / 2.

    def _release(self, event):
        """Button release event handler."""
        if not self.interactive:
            self.to_draw.set_visible(False)

        # update the eventpress and eventrelease with the resulting extents
        x1, x2, y1, y2 = self.extents
        self.eventpress.xdata = x1
        self.eventpress.ydata = y1
        xy1 = self.ax.transData.transform([x1, y1])
        self.eventpress.x, self.eventpress.y = xy1

        self.eventrelease.xdata = x2
        self.eventrelease.ydata = y2
        xy2 = self.ax.transData.transform([x2, y2])
        self.eventrelease.x, self.eventrelease.y = xy2

        # call desired function
        self.onselect(self.eventpress, self.eventrelease)
        self.update()

        return False

    def _onmove(self, event):
        """Cursor move event handler."""
        # resize an existing shape
        if self.active_handle and self.active_handle != 'C':
            x1, x2, y1, y2 = self._extents_on_press
            x2 = event.xdata
            y2 = event.ydata

        # move existing shape
        elif (('move' in self.state or self.active_handle == 'C')
              and self._extents_on_press is not None):
            x1, x2, y1, y2 = self._extents_on_press
            dx = event.xdata - self.eventpress.xdata
            dy = event.ydata - self.eventpress.ydata
            x1 += dx
            x2 += dx
            y1 += dy
            y2 += dy

        # new shape
        else:
            center = [self.eventpress.xdata, self.eventpress.ydata]
            center_pix = [self.eventpress.x, self.eventpress.y]
            dx = (event.xdata - center[0]) / 2.
            dy = (event.ydata - center[1]) / 2.

            # square shape
            if 'square' in self.state:
                dx_pix = abs(event.x - center_pix[0])
                dy_pix = abs(event.y - center_pix[1])
                if not dx_pix:
                    return
                maxd = max(abs(dx_pix), abs(dy_pix))
                if abs(dx_pix) < maxd:
                    dx *= maxd / (abs(dx_pix) + 1e-6)
                if abs(dy_pix) < maxd:
                    dy *= maxd / (abs(dy_pix) + 1e-6)

            # from center
            if 'center' in self.state:
                dx *= 2
                dy *= 2

            # from corner
            else:
                center[0] += dx
                center[1] += dy

            x1, x2, y1, y2 = (center[0] - dx, center[0] + dx,
                              center[1] - dy, center[1] + dy)

        self.extents = x1, x2, y1, y2

    def _on_scroll(self, event):
        """Mouse scroll event handler."""

    def _on_key_press(self, event):
        """Key press event handler - for widget-specific key press actions."""

    def _on_key_release(self, event):
        """Key release event handler."""


class RectangleSelector(LineSelector):
    """
    Select a rectangle region of an axes.

    The selection is based on a single line which is interpret as the diagonal of the rectangle.
    For the cursor to remain responsive you must keep a reference to it.
    """

    def _init_to_draw(self, plot_props):
        rectprops = dict(facecolor='red', edgecolor='black',
                         alpha=0.2, fill=True)
        if plot_props is not None:
            rectprops.update(plot_props)
        rectprops['animated'] = self.useblit
        self.plot_props = rectprops
        self.to_draw = plt.Rectangle((0, 0), 0, 1, visible=False,
                                     **self.plot_props)
        self.ax.add_patch(self.to_draw)

    def draw_shape(self, extents):
        x0, x1, y0, y1 = extents
        xmin, xmax = sorted([x0, x1])
        ymin, ymax = sorted([y0, y1])
        xlim = sorted(self.ax.get_xlim())
        ylim = sorted(self.ax.get_ylim())

        xmin = max(xlim[0], xmin)
        ymin = max(ylim[0], ymin)
        xmax = min(xmax, xlim[1])
        ymax = min(ymax, ylim[1])

        self.to_draw.set_x(xmin)
        self.to_draw.set_y(ymin)
        self.to_draw.set_width(xmax - xmin)
        self.to_draw.set_height(ymax - ymin)


class EllipsoidSelector(LineSelector):
    """
    Select an ellipsoidal region of an axes.

    The selection is based on a single line which is interpret as the diagonal of a rectangle. The ellipsoid is
    constructed by taking the same height and the width of that rectangle, i.e. no rotated ellipsoid.
    For the cursor to remain responsive you must keep a reference to it.
    """
    def _init_to_draw(self, plot_props):
        ellipsoid_props = dict(facecolor='red', edgecolor='black',
                               alpha=0.2, fill=True)

        if plot_props is not None:
            ellipsoid_props.update(plot_props)
        ellipsoid_props['animated'] = self.useblit
        self.plot_props = ellipsoid_props
        self.to_draw = mpl.patches.Ellipse((0, 0), 0, 0, visible=False,
                                           **self.plot_props)
        # self.to_draw = plt.Circle((0, 0), 0, visible=False,
        #                          **self.rectprops)
        self.ax.add_patch(self.to_draw)

    def draw_shape(self, extents):
        x0, x1, y0, y1 = extents
        # radius = np.linalg.norm(np.array([x0, y0]) - np.array([x1, y1]))
        # xlim = sorted(self.ax.get_xlim())
        # ylim = sorted(self.ax.get_ylim())

        self.to_draw.set_center([x0, y0])
        self.to_draw.set_width(2*(x1-x0))
        self.to_draw.set_height(2*(y1-y0))

    def _onmove(self, event):
        if self.active_handle == 'I':
            self.active_handle = 'C'
            x1, x2, y1, y2 = self._extents_on_press
            self._extents_on_press = x2, x1, y2, y1
        super()._onmove(event)


class CircleSelector(LineSelector):
    """
    Select a circular region of an axes.

    The selection is based on a single line which is interpret as the radius of the circle.
    For the cursor to remain responsive you must keep a reference to it.
    """
    def _init_to_draw(self, plot_props):
        circle_props = dict(facecolor='red', edgecolor='black',
                         alpha=0.2, fill=True)
        if plot_props is not None:
            circle_props.update(plot_props)

        circle_props['animated'] = self.useblit
        self.plot_props = circle_props
        self.to_draw = plt.Circle((0, 0), 0, visible=False,
                                  transform=self.ax.figure.dpi_scale_trans,  # positions transformed to inch
                                  **self.plot_props)
        self.ax.add_patch(self.to_draw)

    def draw_shape(self, extents):
        x0, x1, y0, y1 = extents
        pt1_in_px = self.ax.transData.transform([x0, y0])
        pt2_in_px = self.ax.transData.transform([x1, y1])

        pt1_in_in = self.ax.figure.dpi_scale_trans.inverted().transform(pt1_in_px)
        pt2_in_in = self.ax.figure.dpi_scale_trans.inverted().transform(pt2_in_px)
        radius_in_in = np.linalg.norm(pt2_in_in - pt1_in_in)

        self.to_draw.set_center(pt1_in_in)
        self.to_draw.radius = radius_in_in

    def _onmove(self, event):
        if self.active_handle == 'I':
            self.active_handle = 'C'
            x1, x2, y1, y2 = self._extents_on_press
            self._extents_on_press = x2, x1, y2, y1
        super()._onmove(event)


class ROISelector:
    """Select a region of interest (ROI) on an axis based on a line selection.

    Attributes:
        ax: the matplotlib.Axis to select the ROI from.
        x: the x values of start and end point of the line to select the ROI.
        y: the y values of start and end point of the line to select the ROI.

    Methods:
        set_active: (de)activate the selector
        clear_select: remove the selector entirely
        select_circle: select a circular ROI on the axis.
        select_ellipse: select an ellipsoidal ROI on the axis.
        select_line: select a line ROI on the axis.
        select_rectangle: select a rectangular ROI on the axis.
    """
    def __init__(self, ax):
        self.ax = ax
        self._selector = None
        self._pt1 = self._pt2 = None
        self.useblit = True

    def _on_select(self, pt1, pt2):
        self._pt1 = pt1
        self._pt2 = pt2

    @property
    def x(self):
        if self._selector is None:
            return None
        else:
            return np.array(self._selector.extents[:2])

    @property
    def y(self):
        if self._selector is None:
            return None
        else:
            return np.array(self._selector.extents[2:])

    def set_active(self, active):
        self._selector.set_active(active)

    def clear_select(self):
        if self._selector is not None:
            self._selector.disconnect_events()
            self._selector.remove()
            self._selector = None

    def select_circle(self, circle_properties=None, x=None, y=None):
        self.clear_select()
        self._selector = CircleSelector(self.ax, self._on_select, useblit=self.useblit,
                                        button=[1, 3], interactive=True, plot_props=circle_properties,
                                        x=x, y=y)

    def select_ellipse(self, ellipsoid_properties=None, x=None, y=None):
        self.clear_select()
        self._selector = EllipsoidSelector(self.ax, self._on_select, useblit=self.useblit,
                                           button=[1, 3], interactive=True, plot_props=ellipsoid_properties,
                                           x=x, y=y)

    def select_rectangle(self, rectangle_properties=None, x=None, y=None):
        self.clear_select()
        self._selector = RectangleSelector(self.ax, self._on_select, useblit=self.useblit,
                                           button=[1, 3], interactive=True, plot_props=rectangle_properties,
                                           x=x, y=y)

    def select_line(self, line_properties=None, x=None, y=None):
        self.clear_select()
        self._selector = LineSelector(self.ax, self._on_select, useblit=self.useblit,
                                      button=[1, 3], interactive=True, plot_props=line_properties,
                                      x=x, y=y)
