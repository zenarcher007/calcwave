# This represents a left-corner starting location and an row/col size.
# This is to aid in handling curses coordinates and simplify design
class Box:
  def __init__(self, rowSize, colSize, rowStart, colStart):
    self.colStart = colStart
    self.rowStart = rowStart
    self.colSize = colSize
    self.rowSize = rowSize
  def __str__(self):
    return f"<Box: X: {self.colStart}, Y: {self.rowStart}, X size: {self.colSize}, Y size: {self.rowSize}>"

# A simple point, that uses the standard x,y convention, rather than curses row,col
class Point:
  def __init__(self, col, row):
    self.col = col
    self.row = row
  def relative(self, cols, rows): # Returns a new Point relative to the position of this one
    return Point(col = self.col + cols, row = self.row + rows)
  def withRow(self, row): # Returns a new Point with the row set to the given absolute position
    return Point(col = self.col, row = row)
  def withCol(self, col): # Returns a new Point with the col set to the given absolute position
    return Point(col = col, row = self.row)
  def with_wrap_col(self, cols, width): # Increments the column by cols, wrapping to width and increasing row if it exceeds this.
    extraRows = int(cols / width)
    wrappedCols = cols % width
    return Point(row = self.row + extraRows, col = wrappedCols)
  def add_wrap_col(self, cols, width): # Same as with_wrap_col, but adds to the current self.col
    return self.with_wrap_col(self.col + cols, width)
  def __eq__(self, other):
    return self.col == other.col and self.row == other.row
  def __str__(self):
    #return f"({self.col}, {self.row})"
    return f"<Point(col={self.col}, row={self.row})>"
    
# Increments the column of a point, wrapping to the next or previous row if this exceeds width.
#  def incrPoint(point: Point, cols, width):
#    newCols = point.col + cols
#    extraRows = int(newCols / width)
#    wrappedCols = newCols % width
#    return Point(row = point.row + extraRows, col = wrappedCols)