import dataclasses

from PySide6 import QtCore, QtGui


@dataclasses.dataclass(frozen=True)
class BranchLines:
    """Lines connecting a row of the tree to its parent and its siblings.

    A level is a column of the branch area, as wide as the indentation. A line at level
    `k` runs under the arrow of the parent of the rows at depth `k + 1`.

    Attributes:
        depth: depth of the row, 0 for the children of the root index of the view
        passing_levels: levels where a line runs through the whole row, because an
            ancestor of the row has a sibling after it
        has_next_sibling: the line of the row's own level goes on below the row
        has_children: the row has an expand arrow, so its stub stops short of it
    """

    depth: int
    passing_levels: tuple[int, ...]
    has_next_sibling: bool
    has_children: bool

    @property
    def own_level(self) -> int | None:
        """int | None: level of the line that connects the row, None at depth 0."""
        return self.depth - 1 if self.depth > 0 else None


class BranchLinesMixin:
    """Draws the lines that connect the rows of a tree view to their parents.

    The Fusion style only draws the expand arrow. Put the mixin before the tree view
    class: `class MyTree(BranchLinesMixin, QtWidgets.QTreeView)`.

    Attributes:
        BRANCH_LINE_ROLE: palette role of the color of the lines
        BRANCH_LINE_WIDTH: width of the lines in pixels
    """

    BRANCH_LINE_ROLE = QtGui.QPalette.ColorRole.Mid
    BRANCH_LINE_WIDTH = 1

    def get_branch_lines(self, index: QtCore.QModelIndex) -> BranchLines:
        """Work out the lines that connect a row to its parent and siblings.

        Args:
            index (QtCore.QModelIndex): index of the row in the model the view shows.

        Returns:
            BranchLines: lines of the row.
        """
        # The row and its ancestors up to the children of the root, the row first
        chain = [index]
        while chain[-1].parent().isValid() and chain[-1].parent() != self.rootIndex():
            chain.append(chain[-1].parent())
        depth = len(chain) - 1
        # chain[depth - k] is the ancestor at depth k
        passing = tuple(
            level
            for level in range(max(depth - 1, 0))
            if self._has_next_sibling(chain[depth - (level + 1)])
        )
        return BranchLines(
            depth=depth,
            passing_levels=passing,
            has_next_sibling=self._has_next_sibling(index),
            has_children=self.model().hasChildren(index),
        )

    @staticmethod
    def _has_next_sibling(index: QtCore.QModelIndex) -> bool:
        """Check if a row has a sibling after it.

        Args:
            index (QtCore.QModelIndex): index of the row.

        Returns:
            bool: True if there is a row after it under the same parent.
        """
        return index.siblingAtRow(index.row() + 1).isValid()

    def drawBranches(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
        index: QtCore.QModelIndex,
    ) -> None:
        """Draw the lines to the parent and siblings, then the expand arrow.

        The Fusion style only draws the arrow.

        Args:
            painter (QtGui.QPainter): painter.
            rect (QtCore.QRect): branch area of the row.
            index (QtCore.QModelIndex): index of the row.
        """
        lines = self.get_branch_lines(index)
        if lines.depth > 0:
            self._paint_branch_lines(painter, rect, lines)
        super().drawBranches(painter, rect, index)

    def _paint_branch_lines(
        self, painter: QtGui.QPainter, rect: QtCore.QRect, lines: BranchLines
    ) -> None:
        """Paint the lines of a row.

        Args:
            painter (QtGui.QPainter): painter.
            rect (QtCore.QRect): branch area of the row.
            lines (BranchLines): lines to paint.
        """
        indent = self.indentation()
        top, bottom, middle = rect.top(), rect.bottom(), rect.center().y()

        def level_center(level: int) -> int:
            return rect.left() + level * indent + indent // 2

        painter.save()
        pen = QtGui.QPen(self.palette().color(self.BRANCH_LINE_ROLE))
        pen.setWidth(self.BRANCH_LINE_WIDTH)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        for level in lines.passing_levels:
            painter.drawLine(level_center(level), top, level_center(level), bottom)
        trunk_x = level_center(lines.own_level)
        painter.drawLine(
            trunk_x, top, trunk_x, bottom if lines.has_next_sibling else middle
        )
        # The arrow takes the cell of the row, the stub stops where it starts
        own_cell_left = rect.left() + lines.depth * indent
        stub_end = own_cell_left if lines.has_children else own_cell_left + indent
        painter.drawLine(trunk_x, middle, stub_end, middle)
        painter.restore()
