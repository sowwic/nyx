import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core.node_component import NodeComponent
from nyx.editor.graphics.level_of_detail import LevelOfDetail
from nyx.editor.graphics.link_path import build_link_path, get_link_style
from nyx.static.enums import LinkStyle

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_plug import GraphicsPlug
    from nyx.editor.graphics.animation.link_animation import LinkAnimation


class GraphicsLink(QtWidgets.QGraphicsPathItem):
    """Path between the output socket of one plug and the input socket of another.

    The path is drawn in the `LinkStyle` from the config when the link is created, for
    example as a bezier curve or with right angles.

    A link with a missing end is a preview that is being dragged: the missing
    end follows `floating_pos`. Previews are never attached to plugs, only
    complete links are (see `attach`).

    The link is drawn like the component it comes from: its color, and a width that
    the component scales. A link between plugs of different colors fades from the
    color of the source to the one of the target.

    A link can carry animations (see `LinkAnimation`), such as a pulse that travels from
    the source to the target. The link only draws them, `LinkAnimator` decides when and
    how far they are.
    """

    WIDTH = 2.0
    PREVIEW_OPACITY = 0.8

    def __init__(
        self,
        source_plug: GraphicsPlug | None = None,
        target_plug: GraphicsPlug | None = None,
        link_uuid: UUID | None = None,
        style: LinkStyle | None = None,
    ):
        """Initialize GraphicsLink.

        Args:
            source_plug (GraphicsPlug | None): plug the link starts at.
            target_plug (GraphicsPlug | None): plug the link ends at.
            link_uuid (UUID | None): uuid of the link in the stage, None for previews.
            style (LinkStyle | None): style to draw the path in, the configured one if
                omitted.
        """
        super().__init__()
        self._style = style if style is not None else get_link_style()
        self._source_plug = source_plug
        self._target_plug = target_plug
        self._uuid = link_uuid
        self._floating_pos = QtCore.QPointF()
        self._attached = False
        self._animations: dict[type, LinkAnimation] = {}
        self._path_length = 0.0

        # Links are drawn behind nodes, previews above everything.
        self.setZValue(1 if self.is_preview else -1)
        if self.is_preview:
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.update_style()
        self.update_path()

    @property
    def uuid(self) -> UUID | None:
        """UUID | None: uuid of the link in the stage, None for previews."""
        return self._uuid

    @property
    def source_plug(self) -> GraphicsPlug | None:
        """GraphicsPlug | None: plug the link starts at."""
        return self._source_plug

    @property
    def target_plug(self) -> GraphicsPlug | None:
        """GraphicsPlug | None: plug the link ends at."""
        return self._target_plug

    @property
    def is_preview(self) -> bool:
        """bool: link is missing an end."""
        return self._source_plug is None or self._target_plug is None

    @property
    def style_plug(self) -> GraphicsPlug | None:
        """GraphicsPlug | None: plug the look of the link comes from.

        The source of the link, or for a preview dragged from an input socket the plug
        it is dragged from.
        """
        return self._source_plug if self._source_plug is not None else self._target_plug

    @property
    def style(self) -> LinkStyle:
        """LinkStyle: style the path is drawn in."""
        return self._style

    def set_style(self, style: LinkStyle):
        """Draw the path in another style.

        Args:
            style (LinkStyle): new style.
        """
        if style == self._style:
            return
        self._style = style
        self.update_path()

    @property
    def path_length(self) -> float:
        """float: length of the curve in scene units."""
        return self._path_length

    @property
    def animations(self) -> list[LinkAnimation]:
        """list[LinkAnimation]: animations of the link, in the order they were added."""
        return list(self._animations.values())

    def get_animation(self, kind: type[LinkAnimation]) -> LinkAnimation | None:
        """Get the animation of a kind.

        Args:
            kind (type[LinkAnimation]): class of the animation.

        Returns:
            LinkAnimation | None: animation, None if the link has none of the kind.
        """
        return self._animations.get(kind)

    def has_animation(self, kind: type[LinkAnimation]) -> bool:
        """Check whether the link has an animation of a kind.

        Args:
            kind (type[LinkAnimation]): class of the animation.

        Returns:
            bool: the link has the animation.
        """
        return kind in self._animations

    def add_animation(self, animation: LinkAnimation):
        """Let the link draw an animation. One of the same kind is replaced.

        Args:
            animation (LinkAnimation): animation to draw.
        """
        # Animations can be bigger than the stroke, so the bounds change with them.
        self.prepareGeometryChange()
        self._animations[type(animation)] = animation
        self.update()

    def remove_animation(self, kind: type[LinkAnimation]):
        """Stop drawing an animation.

        Args:
            kind (type[LinkAnimation]): class of the animation to remove.
        """
        if kind not in self._animations:
            return
        self.prepareGeometryChange()
        del self._animations[kind]
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the stroke, with room for the animations."""
        rect = super().boundingRect()
        margin = max((a.MARGIN for a in self._animations.values()), default=0.0)
        return rect.adjusted(-margin, -margin, margin, margin)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Paint the link with its animations behind and over the stroke.

        An animation too small on screen to see is left out. The stroke stays
        antialiased, so one thinner than a pixel fades out instead of breaking up.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style option.
            widget (QtWidgets.QWidget | None): widget being painted on.
        """
        scale = LevelOfDetail.scale_from_painter(painter)
        visible = (
            []
            if self.is_preview
            else [a for a in self._animations.values() if a.is_visible_at(scale)]
        )
        for animation in visible:
            animation.paint_below(painter, self)
        super().paint(painter, option, widget)
        for animation in visible:
            animation.paint_above(painter, self)

    def update_style(self):
        """Take color and width from the plug the link comes from.

        A complete link whose plugs differ in color is stroked with a gradient.
        """
        plug = self.style_plug
        color = (
            plug.color
            if plug is not None
            else QtGui.QColor(NodeComponent.DEFAULT_PLUG_COLOR)
        )
        width = self.WIDTH * (plug.link_width_multiplier if plug is not None else 1.0)
        if self.is_preview:
            color.setAlphaF(color.alphaF() * self.PREVIEW_OPACITY)
        pen = QtGui.QPen(self._build_stroke_brush(color), width)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    def _build_stroke_brush(self, color: QtGui.QColor) -> QtGui.QBrush:
        """Build the brush the link is stroked with.

        Args:
            color (QtGui.QColor): color of the plug the link comes from.

        Returns:
            QtGui.QBrush: solid brush, or a gradient from the source to the target
                color for a complete link between plugs of different colors.
        """
        if self.is_preview or self._target_plug.color == color:
            return QtGui.QBrush(color)

        gradient = QtGui.QLinearGradient(
            self._source_plug.output_anchor(), self._target_plug.input_anchor()
        )
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(1.0, self._target_plug.color)
        return QtGui.QBrush(gradient)

    def set_floating_pos(self, scene_pos: QtCore.QPointF):
        """Move the open end of a preview.

        Args:
            scene_pos (QtCore.QPointF): scene position of the open end.
        """
        self._floating_pos = QtCore.QPointF(scene_pos)
        self.update_path()

    def attach(self):
        """Register the link on both of its plugs so it follows them."""
        if self._attached or self.is_preview:
            return
        self._source_plug.add_link(self)
        self._target_plug.add_link(self)
        self._attached = True

    def detach(self):
        """Unregister the link from its plugs."""
        if not self._attached:
            return
        self._source_plug.discard_link(self)
        self._target_plug.discard_link(self)
        self._attached = False

    def update_path(self):
        """Rebuild the path from the current anchors."""
        start = (
            self._source_plug.output_anchor()
            if self._source_plug
            else self._floating_pos
        )
        end = (
            self._target_plug.input_anchor() if self._target_plug else self._floating_pos
        )
        path = build_link_path(self._style, start, end)
        self.setPath(path)
        self._path_length = path.length()
        # The gradient runs between the anchors, so it follows them.
        self.update_style()
