import math

from PySide6 import QtCore, QtGui


class StageGraphZoom:
    """Zoom level of a stage graph view and the math between level and scale.

    The level is a number of steps: `DEFAULT_ZOOM` is 100% scale, every step changes the
    scale by `zoom_in_factor`.

    Attributes:
        zoom (float): current zoom level.
        zoom_in_factor (float): scale factor of one zoom step.
        zoom_step (float): zoom levels moved by one wheel step.
        zoom_range (tuple[float, float]): lowest and highest zoom level.
        zoom_clamp (bool): keep the zoom level within the range.
    """

    DEFAULT_ZOOM = 10  # zoom level at 100% scale
    HIGH_QUALITY_ZOOM = 4  # text is antialiased above this zoom level

    def __init__(self):
        """Initialize StageGraphZoom."""
        self.zoom: float = self.DEFAULT_ZOOM
        self.zoom_in_factor = 1.25
        self.zoom_step = 1
        self.zoom_range = (-5.0, 10.0)
        self.zoom_clamp = True

    @property
    def scale(self) -> float:
        """float: scale of the current zoom level."""
        return self.scale_for(self.zoom)

    @property
    def transform(self) -> QtGui.QTransform:
        """QtGui.QTransform: view transform of the current zoom level."""
        return QtGui.QTransform.fromScale(self.scale, self.scale)

    @property
    def wants_text_antialiasing(self) -> bool:
        """bool: the zoom level is high enough for antialiased text."""
        return self.zoom > self.HIGH_QUALITY_ZOOM

    def scale_for(self, zoom: float) -> float:
        """Get the scale of a zoom level.

        Args:
            zoom (float): zoom level.

        Returns:
            float: scale, 1.0 at `DEFAULT_ZOOM`.
        """
        return self.zoom_in_factor ** (zoom - self.DEFAULT_ZOOM)

    def clamp(self, zoom: float) -> float:
        """Limit a zoom level to the zoom range.

        Args:
            zoom (float): zoom level.

        Returns:
            float: zoom level within the range.
        """
        return max(self.zoom_range[0], min(self.zoom_range[1], zoom))

    def set_zoom(self, zoom: float):
        """Set the zoom level, limited to the zoom range.

        Args:
            zoom (float): zoom level.
        """
        self.zoom = self.clamp(zoom)

    def step(self, zoom_in: bool) -> float | None:
        """Move the zoom level by one step.

        Args:
            zoom_in (bool): zoom in (True) or out (False).

        Returns:
            float | None: scale factor to apply to the view, None if the step left the
                zoom range and clamping is on. The level is still limited to the
                range then.
        """
        self.zoom += self.zoom_step if zoom_in else -self.zoom_step
        clamped = self.clamp(self.zoom) != self.zoom
        if clamped:
            self.zoom = self.clamp(self.zoom)
        if clamped and self.zoom_clamp:
            return None
        return self.zoom_in_factor if zoom_in else 1.0 / self.zoom_in_factor

    def zoom_to_fit(
        self, viewport_size: QtCore.QSize, scene_rect: QtCore.QRectF
    ) -> float:
        """Get the zoom level that fits a scene rect into a viewport.

        Args:
            viewport_size (QtCore.QSize): size of the viewport.
            scene_rect (QtCore.QRectF): scene rect to fit.

        Returns:
            float: zoom level, limited to the zoom range if clamping is on.
        """
        fit_scale = min(
            viewport_size.width() / scene_rect.width(),
            viewport_size.height() / scene_rect.height(),
        )
        zoom = self.DEFAULT_ZOOM + math.log(fit_scale, self.zoom_in_factor)
        return self.clamp(zoom) if self.zoom_clamp else zoom
