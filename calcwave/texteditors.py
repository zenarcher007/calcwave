import curses
from curses.textpad import Textbox, rectangle
from curses import wrapper
from calcwave.elementaltypes import * # Box, Point
import sys
import threading
import math


def detect_os_monkeypatch_curses_keybindings(curses_module):
  # To provide better compatibility between different operating systems, use different
  # key settings for the corresponding operating system, found by experimentation as the defaults are sometimes
  # wrong on their corresponding systems. Example:
  # backspace: 127 on Mac and Linux, but 8 on windows.
  # delete: 126 on Mac, but 27 on Linux
  pform = sys.platform
  if "darwin" in pform:
    curses_module.KEY_BACKSPACE = 127
    curses_module.KEY_DC = 330
    curses_module.KEY_ENTER = 10
  elif "linux" in pform:
    #curses.KEY_BACKSPACE = 127
    #curses.KEY_DC = 126
    curses_module.KEY_ENTER = 10 # Was 343 when tested on Linux Mint (Debian)
  elif "win" in pform:
    curses_module.KEY_BACKSPACE = 8
    curses_module.KEY_ENTER = 10
  else:
    sys.stderr.write("Warning: unsupported platform, \"" + str(pform) + "\"\n")
    # Use default curses key definitions; doesn't change them

# Helpful and necessary functionality for editors
class BasicEditor:
  def __init__(self, box: Box):
    self.win = curses.newwin(box.rowSize, box.colSize, box.rowStart, box.colStart) # Initialize curses window
    self.cursorPos = Point(0,0)
    self.oldCursorPos = self.cursorPos
    self.oldHighlightPos = self.cursorPos
    self.shape = box # Public - holds the shape / dimensions of this window
    self.cursorHidden = False
    
  def highlightChar(self, p : Point):
    self.oldHighlightPos = p
    self.win.chgat(p.row, p.col, 1, curses.A_UNDERLINE)
    self.win.refresh()

  def restoreLastHighlight(self):
    self.win.chgat(self.oldHighlightPos.row, self.oldHighlightPos.col, 1, curses.A_NORMAL)

  # Hides the cursor temporarily, until it is moved.
  def hideCursor(self):
    self.cursorHidden = True
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_NORMAL) # Un-highlight new position
    self.win.refresh()

  def showCursor(self):
    self.cursorHidden = False
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight cursor position
    self.win.refresh()

  def onFocus(self):
    self.showCursor()

  def onUnfocus(self):
    self.hideCursor()

  def setCursorPos(self, p: Point):
    self.win.move(p.row, p.col)
    self.cursorPos = p
    # Real cursor is hidden; move "virtual cursor" by changing the highlighting of cells
    #self.win.chgat(self.oldCursorPos.row, self.oldCursorPos.col, 1, curses.A_NORMAL) # Unhighlight old position
    #self.win.chgat(p.row, p.col, 1, curses.A_REVERSE) # Highlight new position
    #self.oldCursorPos = self.cursorPos

  # A convienence function
  def moveCursor(self, rows, cols):
    self.setCursorPos(self.cursorPos.relative(rows = rows, cols = cols))

  # Example functions for type. Returns False if this function did not handle the event
  def type(self, ch):
    #Handle special key presses
    if ch == curses.KEY_UP:
      newPos = self.cursorPos.relative(row = -1, col = 0)
      if newPos.row >= 0:
        self.setCursorIndex(newPos)
        #self.refresh()
        return True
    elif ch == curses.KEY_DOWN:
      newPos = self.cursorPos.relative(row = 1, col = 0)
      if newPos.row < self.shape.rowSize:
        self.setCursorIndex(newPos)
        #self.refresh()
        return True
    elif ch == curses.KEY_LEFT:
      newPos = self.cursorPos.relative(row = 0, col = -1)
      if newPos.row >= 0:
        self.setCursorIndex(newPos)
        #self.refresh()
        return True
    elif ch == curses.KEY_RIGHT:
      newPos = self.cursorPos.relative(row = 0, col = 1)
      if newPos.row < self.shape.colSize:
        self.setCursorIndex(newPos)
        #self.refresh()
        return True
    else:
      return False

    

  # Calls a window refresh
  def refresh(self):
    self.restoreLastHighlight()

    # Redraw cursor
    if self.cursorHidden == False:
      self.win.chgat(self.oldCursorPos.row, self.oldCursorPos.col, 1, curses.A_NORMAL) # Unhighlight old position
      self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight new position
    self.oldCursorPos = self.cursorPos
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight new position
    
    self.win.refresh()


class LineEditor(BasicEditor):
  def __init__(self, box: Box):
    super(LineEditor, self).__init__(box)
    self.text = []
    self.scrollOffset = 0
   
  def getPos(self):
    return Point(col = self.cursorPos.col + self.scrollOffset, row = self.cursorPos.row)

  # Gets the complete text
  def getText(self):
    return ''.join(self.text)

  def setText(self, text):
    self.text = list(text)
    self.goToBeginning()
    #self.refresh()

   # Scrolls left one space
  def scrollLeft(self):
    self.scrollOffset = self.scrollOffset - 1
  
  # Scrolls right one space
  def scrollRight(self):
    self.scrollOffset = self.scrollOffset + 1

  # Moves the cursor left, scrolling as needed. Checks if outside of text bounds
  def goLeft(self):
    if self.cursorPos.col <= 0 and self.scrollOffset <= 0:
      return False
    elif self.cursorPos.col <= 0:
      self.scrollLeft()
    elif self.scrollOffset + self.cursorPos.col > 0: # If not at the very beginning
      self.setCursorPos(self.cursorPos.relative(cols = -1, rows = 0))
    return True
    
  # Moves the cursor right, scrolling as needed. Checks if outside of text bounds.
  def goRight(self):
    if self.cursorPos.col + self.scrollOffset < len(self.text):
      if(self.cursorPos.col >= self.shape.colSize - 1): # If off right edge
        self.scrollRight()
      else:
        self.setCursorPos(self.cursorPos.relative(cols = 1, rows = 0))
    else: 
      return False
    return True
  
  # Goes to the beginning of the text, with the cursor at 0.
  def goToBeginning(self):
    self.setCursorPos(self.cursorPos.withCol(0))
    self.scrollOffset = 0
    #self.refresh()
  
  # Sets the cursor at the end, and puts the scroll window in view.
  def goToEnd(self):
    self.setCursorPos( self.cursorPos.withCol(min(len(self.text), self.shape.colSize-1)))
    self.scrollOffset = max(0, len(self.text) - self.shape.colSize)
    #self.refresh()

  def refresh(self):
    self.win.clear()
    text = self.text[self.scrollOffset : min(self.scrollOffset + self.shape.colSize-1, len(self.text))]
    self.win.addstr(0, 0, ''.join(text))
    super().refresh()

  def insert(self, ch):
    self.text.insert(self.scrollOffset + self.cursorPos.col, chr(ch))
    #self.charsAfter.append(self.charAt(self.shape.colSize - 1)) # Rightmost char gets pushed off the end
    ###self.insCharAt(self.cursorPos.col, ch)
    self.goRight()

  def backspace(self):
    if self.cursorPos.col <= 0 and self.scrollOffset <= 0:
      return # TODO: Why doesn't the goLeft() return value actually get it right?????!!!!!!
    #self.goLeft()
    #if True:
    if self.goLeft():
      ###self.win.delch(0, self.cursorPos.col)
      self.text.pop(self.scrollOffset + self.cursorPos.col)
      #self.refresh()
    else:
      return False
    return True

  def type(self, ch):
    retVal = True
    if ch == curses.KEY_LEFT:
      retVal = self.goLeft()
    elif ch == curses.KEY_RIGHT:
      retVal = self.goRight()
    elif ch == curses.KEY_BACKSPACE:
      retVal = self.backspace()
    else:
      self.insert(ch)
    #self.refresh()
    return retVal



# A full text editor that supports newlines and scrolling
class TextEditor(BasicEditor):
  def __init__(self, box: Box):
    super(TextEditor, self).__init__(box)
    self.data = [[]] # An array of lines constisting of an array of chars
    self.dataPos = self.cursorPos
    self.oldHighlightPos = Point(0,0)
    self.cursorOffset = 0
    self.scrollOffset = 0
    self.lineOffset = 0 # For reference when the cursor wraps to the next line
    self.win.scrollok(True) # Enable curses scrolling
    self.highlightedRanges = [] # Holds tuples with the beginning and end ranges of highlighted portions of the screen to be removed later.

  def setText(self, text: str):
    #self.win.clear()
    self.data = [[]]
    self.cursorOffset = 0
    self.scrollOffset = 0
    self.lineOffset = 0
    self.setCursorPos(Point(0,0))
    self.dataPos = Point(0,0)
    byLine = text.split('\n')
    lineCount = len(byLine)
    for i, line in enumerate(byLine):
      self.data[i] = list(line)
      self.dataPos = Point(row = i, col = 0)
      self.goToEol()
      if i < lineCount-1:
        self.enter()
        #self.refresh()
    #self.refresh()


  def getText(self):
    return '\n'.join(''.join(line) for line in self.data)

  # Increments the data position, going to the next line entry when it reaches the end of the current line
  def slideData(self, cols):
    self.dataPos = self.dataPos.relative(rows = 0, cols = cols)
    if self.dataPos.col < 0:
      undershoot = -self.dataPos.col
      self.dataPos = self.dataPos.withCol((1+len(self.data[self.dataPos.row-1])) - undershoot)
      self.mvLine(-1, cursorOriented = False)
      self.slideData(0) # Re-evaluate undershoot
    elif self.dataPos.col > len(self.data[self.dataPos.row]) and self.dataPos.row < len(self.data)-1:
      overshoot = self.dataPos.col - (1+len(self.data[self.dataPos.row]))
      self.dataPos = self.dataPos.withCol(overshoot)
      self.mvLine(1, cursorOriented = False)
      self.slideData(0) # Re-evaluate overshoot
    self.setCursorPos(self.getLineCurPos().withCol(self.dataPos.col))
    return True

  # Returns the cursor row that the current data line starts at in the display
  def getLineStartRow(self):
    cursorRow = self.cursorPos.row
    #cursorDepth = int(self.dataPos.col / self.shape.colSize) # How many (display) rows down is the cursor?
    return cursorRow - self.lineOffset #- cursorDepth

  # Calculates the display height of the given line
  def getLineHeight(self, line: int):
    return int((len(self.data[line])-1) / self.shape.colSize)+1

  # Changes the current line of text selected, relatively, updating the cursor offset and snapping to the end of the line
  def mvLine(self, lines, cursorOriented = True):
    ### Update cursor offset
    cursorDepth = int((self.dataPos.col) / (self.shape.colSize)) # How far down is the cursor on the current line relative to its start?
    lookback = 1 if lines < 0 else 0
    correctionLines = int(math.copysign(1, lines) * (self.getLineHeight(self.dataPos.row - lookback)-1))
    self.cursorOffset = self.cursorOffset + correctionLines # Increment / decrement cursor offset accordingly
    # Change dataPos line
    self.dataPos = self.dataPos.withRow(self.dataPos.row + lines)
    # Apply cursorOffset
    self.setCursorPos(self.cursorPos.withRow(self.dataPos.row + self.cursorOffset))

    self.goToEol(ifPast = True, cursorOriented = cursorOriented)
    if(abs(lines) > 1):
      self.mvLine(int(math.copysign(1, lines) * (abs(lines)-1))) # Repeat for the number of lines specified to reconsider line lengths

  def scroll(self, lines):
    self.scrollOffset = self.scrollOffset + lines
    self.cursorOffset = self.cursorOffset - lines
    self.win.scroll(lines)
    

  # Override BasicEditor's setCursorPos function to allow handling of cursor position outside the actual length of the window, and scroll if beyond the top / bottom edges
  # This should not be used directly within this class if you are changing the cursor's row. Instead, use relative movements, such as mvLine to change line, and slideData to change column position
  def setCursorPos(self, p: Point):
    self.lastCurPos = p
    self.lineOffset = int(p.col / self.shape.colSize)
    row = p.row + self.lineOffset # + int(p.col / self.shape.colSize)# + self.cursorOffset
    col = p.col % self.shape.colSize

    if(row < 0):
      lines = -row
      self.hideCursor()
      self.scroll(-lines)
      row = 0
    elif(row > self.shape.rowSize-1):
      self.rowHallOfFame = row
      lines = row - (self.shape.rowSize-1)
      self.hideCursor()
      self.scroll(lines)
      #self.setCursorPos(Point(row = row - lines, col = col))
      row = row - lines

    super().setCursorPos(Point(row = row, col = col))

  # Gets the cursor position with the row at the beginning of the current line, and the column as the absolute position within the line (possibly beyond the width of the window)
  # Since columns beyond the width of the window are abstracted to actually add to the cursor's row, this gets the corrected position of the cursor
  # (the exact point you would have called setCursorPos() with)
  def getLineCurPos(self):
    lineOffset = self.lineOffset
    return Point(row = self.cursorPos.row - self.lineOffset, col = self.dataPos.col)
    
  # Moves the cursor by a relative amount, and supports column sizes greater than the window size. If lineWrap is enabled, understands line positioning,
  # as if you pressed the arrow keys n times.
  def moveCursor(self, rows, cols, lineWrap = False):
    if cols != 0: self.slideData(cols) # if: Avoid expensive function calls
    if rows != 0: self.mvLine(rows)


  # Convienence function to go to the end of the current line
  def goToEol(self, ifPast = False, cursorOriented = False):
    lineSize = len(self.data[self.dataPos.row])
    orient = self.cursorPos.col if cursorOriented else self.dataPos.col
    pos = min(lineSize, orient) if ifPast else lineSize
    self.dataPos = self.dataPos.withCol(pos)
    self.setCursorPos(self.cursorPos.withCol(pos))
  
  # "Safer" version of goToEol
  def goToEolV2(self):
    startRow = self.getLineStartRow()
    col = len(self.data[self.dataPos.row])
    self.setCursorPos(Point(row = startRow, col = col))
    self.dataPos = self.dataPos.withCol(col)


  # Clears visuals to the end of the current (simulated) line, moving bottom text upwards
  def clearToEol(self):
    startRow = self.getLineStartRow()
    height = self.getLineHeight(self.dataPos.row)
    curr = self.cursorPos.row
    diff = (startRow+height) - curr
    self.win.clrtoeol()
    oldPos = self.getPos()
    if self.cursorPos.row == self.shape.rowSize-1:
      return
    for i in range(diff):
      self.setCursorPos(Point(col = 0, row = self.cursorPos.row + 1))
      self.win.deleteln()
    self.setCursorPos(oldPos)
    
    
    

  def insertChar(self, ch):
    dataLen = len(self.data[self.dataPos.row])
    if( (dataLen > 0 and dataLen % self.shape.colSize == 0) ): #and not len(self.data[self.dataPos.row]) >= self.shape.colSize ):
      oldCur = self.cursorPos
      oldData = self.dataPos
      #self.goToEolV2()
      #self.mvLine(2)
      #self.refresh()
      #self.mvLine(-2)
      #self.setCursorPos(Point(col = 0, row = self.cursorPos.row + self.cursorOffset))
      #self.moveCursor(rows = 1, cols = 0)
      start = self.getLineStartRow()
      self.win.move(start + self.getLineHeight(self.dataPos.row), 0)
      self.win.insertln()
      self.cursorPos = oldCur
      self.dataPos = oldData
    self.data[self.dataPos.row].insert(self.dataPos.col, ch)
    self.moveCursor(rows = 0, cols = 1)

  # Highlights the range of text from p1 to p2, and adds this range into self.highlightedRanges so that it can be removed later
  def highlightRange(self, p1 : Point, p2: Point):
    p1 = p1.relative(rows = -1, cols = -1) # Convert 1-indexed points to 0-indexed points
    p2 = p2.relative(rows = -1, cols = -1)
    self.chattrRange(p1, p2, curses.A_UNDERLINE)
    self.highlightedRanges.append((p1, p2))
  
  # Override restoreLastHighlight of BasicEditor
  def restoreLastHighlight(self):
    for p1, p2, in self.highlightedRanges:
      self.chattrRange(p1, p2, curses.A_NORMAL)
    self.highlightedRanges = []
    return super().restoreLastHighlight()

  # Not-very-efficiently changes a curses attribute on a range of text, beginning at the absolute text position p1, and ending at p2. Assumes p2.row > p1.row and p2.col > p1.col.
  # TODO: Find just the first screen pos, and then use the lengths of its text to iterate?
  def chattrRange(self, p1 : Point, p2: Point, attribute):
    begin = self.findScreenPos(p1)
    if not begin: # If off screen
      return
    cursorRow = begin.row
    dataPt = begin.withCol(0)
    while cursorRow < self.shape.rowSize and dataPt.row < len(self.data):
      height = self.getLineHeight(dataPt.row)
      rowLen = len(self.data[dataPt.row])
      rowSize = min(rowLen - dataPt.col, self.shape.colSize) # Size of the text visible on the current display row
      isFirst = dataPt.row == begin.row and dataPt.col < self.shape.colSize
      colStart = max(0, p1.col) if isFirst else 0 # On the first line?
      isLast = dataPt.row == p2.row and int(dataPt.col / self.shape.colSize) == height-1 
      colEnd = p2.col % self.shape.colSize if isLast else self.shape.colSize #int(dataPt.col / self.shape.colSize) == height-1 # On the last line of the last line? #dataPt.row == p2.row and dataPt.col < self.shape.colSize else rowLen
      #if cursorRow == 1: self.infoPad.updateInfo(f"isFirst: {isFirst}, isLast: {isLast}, cursorRow: {cursorRow}, colStart: {colStart}, colEnd: {colEnd}")
      #for i in range(30):
      #  print(cursorRow, colStart)
      #time.sleep(1)
      try: # TODO: Fix uncommon illegal chgat that sometimes occurs when backspacing a line of code that contains both brackets and parentheses?
        self.win.chgat(cursorRow, colStart, max(colEnd - colStart, 1), attribute)
      except curses.error as e:
        pass
      dataPt = dataPt.add_wrap_col(rowSize, width = max(1, rowLen)) # Go to next visible line
      cursorRow = cursorRow + 1
      if isLast: break
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Refresh cursor, in case it drew on top of it
    
    #self.win.refresh()
      
      



      #dataPt.add_wrap_col(self.shape.colSize)
      ##if dataRow == begin.row:
      ##  fromCol = dataPt.col
      ##  toCol = dataPt.with_wrap_col(p2.col, width = self.shape.colSize)\
      ##cursorRow = cursorRow + 1
      ##data
      #rowSize = min(rowLen - dataPt.col, self.shape.colSize) # Size of the text visible on the current display row
      #dataPt.add_wrap_col(rowSize, width = row)
    
    
  
#    end = self.findScreenPos(p2)
#    if begin is None:
#      begin = Point(0,0)
#    if end is None:
#      end = Point(row = self.shape.rowSize-1, col = self.shape.colSize - 1)
#    dataPt = self.dataPos
#    for row in range(begin.row, end.row): # Follow the rows of text as would be displayed on screen by moving line by line, or sooner if the tail is shorter than the page width
#      rowLen = len(self.data[dataPt.row])
#      rowSize = min(rowLen - dataPt.col, self.shape.colSize) # Size of the text visible on the current display row
#      colStart = p1.col if row == p1.row else 0
#      colEnd = p2.col if row == p2.row else rowSize
#      self.win.chgat(row, colStart, colEnd - colStart, attribute)
#      dataPt = dataPt.add_wrap_col(rowSize, width = rowLen)
#    self.win.refresh()

  # Attempts to crawl to, and return the point of, the visible portion on the screen that matches up with the absolute dataPos point.
  # Returns None if the given point is off the screen
  def findScreenPos(self, textPos : Point):
    dataRow = self.dataPos.row
    increment = -1 if textPos.row < self.cursorPos.row else 1
    newRow = self.getLineCurPos().row
    while True:
      if dataRow == textPos.row:
        return Point(row = newRow, col = 0).with_wrap_col(textPos.col, width = self.shape.colSize) # Wrap to below lines if the position is greater than the width of the screen
      elif newRow < 0 or newRow > self.shape.rowSize:
        return None
      else:
        dataRow = dataRow + increment
        if dataRow >= len(self.data):
          return None
        else:
          newRow = newRow + self.getLineHeight(dataRow) * increment
  
  # Crawls to, and refreshes the bottommost visible line in the text editor
  def refreshLastLine(self):
      #return
    # Skip to the ending line
      row = self.cursorPos.row
      dataRow = self.dataPos.row
      while dataRow < len(self.data)-1:
        newRow = row + self.getLineHeight(dataRow)
        if newRow < self.shape.rowSize:
          dataRow = dataRow + 1
          row = newRow
        else:
          break

      for line in range(row, self.shape.rowSize):
        self.win.move(line, 0)
        self.win.clrtoeol()
      self.win.move(row, 0)
      textLen = len(self.data[dataRow])
      visibleLen = ((self.shape.rowSize) - row) * self.shape.colSize
      self.win.addstr(''.join(self.data[dataRow][0:min(visibleLen, textLen)]))

  def backspace(self):
    if self.dataPos == Point(0,0):
      return False
    
    dataLen = len(self.data[self.dataPos.row])
    #charList = self.data.pop(self.dataPos.row)
    #self.data[self.dataPos.row].extend(charList)
    #if dataLen > 0 and dataLen % self.shape.colSize == 0:
    #  self.win.deleteln()
    #self.slideData(-1)
    #return True
    #if self.cursorPos.col == 0:
    #  self.win.deleteln()
    if self.dataPos.col == 0: # Delete this line, move the cursor to the end of the previous line, and bring following text with it
      charList = self.data.pop(self.dataPos.row) # Take the current line contents
      self.win.deleteln()
      self.mvLine(-1)
      self.goToEol()
      self.data[self.dataPos.row].extend(charList)
      ### Refresh a line of text at the end without changing cursor parameters ###
      self.refreshLastLine()
    elif dataLen != self.cursorPos.col and dataLen % self.shape.colSize == 1: # Bring text below the current up with it once it shrinks and traverses lines
      # ; a visual-only effect
      self.slideData(-1)
      self.data[self.dataPos.row].pop(self.dataPos.col)
      oldPos = self.cursorPos
      start = self.getLineStartRow()
      self.win.move(start + self.getLineHeight(self.dataPos.row), 0)
      self.win.deleteln()
      self.cursorPos = oldPos
    else: # Delete a character on the current line, and move the cursor back
      self.slideData(-1)
      self.data[self.dataPos.row].pop(self.dataPos.col)
    return True
    
  def enter(self):
    line = self.data[self.dataPos.row]
    oldTail = line[self.dataPos.col: len(line)]
    #self.clearToEol()

    realLineSize = len(self.data[self.dataPos.row])
    #lineStart = self.getLineStartRow()
    #lineHeight = self.getLineHeight()
    #if self.dataPos.col >= realLineSize - (realLineSize % self.shape.colSize): # Only if you are on the very last line
    if self.cursorPos.col < (realLineSize % self.shape.colSize) or self.cursorPos.col == self.dataPos.col:
      self.win.insertln()
    
    self.data.insert(self.dataPos.row+1, oldTail) if self.dataPos.row != len(self.data)-1 else self.data.append(oldTail) # Add the tail of the last line (if any) to a new line
    for i in range(len(oldTail)): # Delete tail of original line
      self.data[self.dataPos.row].pop(self.dataPos.col)
    #self.refresh() # Refresh optimization will not otherwise see it, as it is switching lines
    self.mvLine(1) # Go to next line
    self.setCursorPos(self.getLineCurPos().withCol(0)) # Go to beginning of line
    self.dataPos = self.dataPos.withCol(0) # Go to beginning of line in data pointer
    return True

  # Refresh current line
  def refresh(self):
    row = self.getLineStartRow()
    visibleOffset = -min(0, row) # How much is invisible?
    lineSize = self.getLineHeight(self.dataPos.row)
    oldCur = self.cursorPos
    for line in range(max(0, row), min(row + lineSize, self.shape.rowSize)): # Clear entire line
      self.win.move(line, 0)
      self.win.clrtoeol()
    self.win.move(max(0, row), 0)
    rowLen = len(self.data[self.dataPos.row])
    line = self.data[self.dataPos.row]
    self.win.addstr(''.join(line[visibleOffset*self.shape.colSize:rowLen]))
    super().refresh()
  
  # Returns the absolute position of the cursor; may be displayed outside of this class
  def getPos(self):
    return self.dataPos
  
  # Moves the cursor by the number of spaces within the text window, wrapping around when necessary
  def moveCursorLinearWindow(self, spaces):
    if spaces == 0:
      return
    p = self.cursorPos.relative(rows = int(self.shape.colSize / spaces), cols = self.shape.colSize % abs(spaces))
    self.setCursorPos(p)

  # These alternative key codes were tested on Mac, obtained by pressing fn + arrow keys
  def decodeFnModifier(self, key):
    match key:
       case 262: return curses.KEY_LEFT
       case 339: return curses.KEY_UP
       case 360: return curses.KEY_RIGHT
       case 338: return curses.KEY_DOWN
       case _: return None
    
  # Drives this editor from keystrokes. Returns True if the event could do any useful action to the editor, or False if not
  def type(self, key):
    retVal = True
    fnModified = self.decodeFnModifier(key)
    if fnModified: # Repeat this keypress a number of times if the fn key is held to speed up travel
      key = fnModified
      for i in range(0, 9): self.type(key) # Tenth key press will be the continuation after this statement
      
    if key == curses.KEY_UP:
      oldRowLen = len(self.data[self.dataPos.row])
      oldDataCol = self.dataPos.col
      if self.dataPos.col >= self.shape.colSize: # If it has room for a full (negative) rotation by colSize (up 1 line)
        self.slideData(-self.shape.colSize)
      elif self.dataPos.row > 0: # If it is within the bounds of the screen
        self.mvLine(-1)
      else:
        retVal = False
      
      newRowLen = len(self.data[self.dataPos.row])
      if newRowLen > oldRowLen and newRowLen > self.shape.colSize:
        oldCurCol = self.cursorPos.col
        self.goToEol()
        self.slideData(-((newRowLen - oldCurCol) % self.shape.colSize))
    elif key == curses.KEY_DOWN:
      rowLen = len(self.data[self.dataPos.row])
      if(self.dataPos.col + self.shape.colSize <= rowLen): # If there is room for a full rotation by colSize (down 1 line)
        self.slideData(self.shape.colSize)
      # vvv If the latter is not true, but there is still room to go to the end of the line, and it is not already near the end of the line (or the line is a single line)
      elif rowLen - self.dataPos.col < self.shape.colSize and rowLen - self.dataPos.col > rowLen % self.shape.colSize:
        self.goToEolV2()        
      elif self.dataPos.row < len(self.data)-1: # If it is within the bounds of the screen
        self.mvLine(1)
      else: # "I give up"
        retVal = False
    elif key == curses.KEY_LEFT:
      if self.dataPos != Point(0,0):
        self.slideData(-1)
      else:
        retVal = False
    elif key == curses.KEY_RIGHT:
      if not ( self.dataPos.row == len(self.data)-1 and self.dataPos.col > len(self.data[self.dataPos.row])-1 ):
         self.slideData(1)
      else:
        retVal = False
    elif key == curses.KEY_ENTER:
      retVal = self.enter()
    elif key == curses.KEY_BACKSPACE:
      retVal = self.backspace()
    else:
      self.insertChar(chr(key))
    #self.refresh()
    return retVal
  

  

# A special window that allows typing through characters provided in the type(ch)
# function. Note that despite its name, this is a curses window, not a pad.
# Also note that this is not a traditional text editor. Even though text may wrap to the next line,
# it doesn't allow new lines. It is more like a string editor.
class InputPad:
  #Constructor
  def __init__(self, shape: Box, virtual_cursor = None): # colStart, rowStart, colSize, rowSize):
    #Define window boundaries
    self.shape = shape
    if virtual_cursor:
      self.isVirtualCursorEnabled = virtual_cursor
    elif 'useVirtualCursor' in globals(): # Default to global setting
      self.isVirtualCursorEnabled = useVirtualCursor
    else: # Default to False
      self.isVirtualCursorEnabled = False
    if virtual_cursor: # Make the real cursor invisible
      curses.curs_set(0)
    #These hold the actual x and y positions
    #of the bounds of the pad
    #Upper left corner
    self.boxCol1 = shape.colStart
    self.boxRow1 = shape.rowStart
    #Lower right corner
    self.boxCol2 = shape.colStart + shape.colSize - 1
    self.boxRow2 = shape.rowStart + shape.rowSize - 1
    
    #Make window
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    
    self.curCol = 0
    self.curRow = 0
    
    self.oldHighlightCol = 0
    self.oldHighlightRow = 0
    self.oldVCursor = (self.boxRow1, self.boxCol1)
    self.onHoverEntered = False
    
  # Moves the cursor relatively if space permits and updates the screen
  def curMove(self, relRow, relCol):
    if self.checkBounds(self.curRow + relRow, self.curCol + relCol, move_virtual = True):
      self.win.move(self.curRow + relRow, self.curCol + relCol)
      self.curRow = self.curRow + relRow
      self.curCol = self.curCol + relCol
      #if move_virtual:
      self.virtCurMove(row=self.curRow, col=self.curCol)
  
  # Sets absolute cursor position
  def curPos(self, row, col, move_virtual=True):
    self.curCol = col
    self.curRow = row
    self.win.move(row, col)
    if move_virtual:
      self.virtCurMove(row = row, col = col)
      
  
  # Calls a window refresh
  def refresh(self):
    
    self.win.refresh()
    
  # Moves the cursor right, wrapping to the next line if needed.
  def goRight(self):
    if self.curCol + 1 > self.shape.colSize-1:
      if self.checkBounds(self.curRow + 1, 0):
        self.curPos(self.curRow + 1, 0)
    else:
      self.curPos(self.curRow, self.curCol + 1)
    
  # Moves the cursor left, wrapping to the previous line if needed.
  def goLeft(self):
    if self.curCol-1 < 0: ###self.boxX1:
      if self.checkBounds(self.curRow - 1, self.curCol):
        self.curPos(self.curRow - 1, self.colSize-1)
    else:
      self.curPos(self.curRow, self.curCol - 1)
      
      
  #Returns True if the given actual position is valid in the pad
  def checkBounds(self, posRow, posCol):
    #print(self.curX, self.curY)
    #rows, cols = curses.initscr().getmaxyx()
    #print(self.posX, self.posY, "|", self.boxX1, self.boxY1, "|", self.boxX2, self.boxY2)
    ###if posY <= self.boxY2 and posX <= self.boxX2 and posY >= self.boxY1 and posX >= self.boxX1:
    if posRow <= self.shape.rowSize-1 and posCol <= self.shape.colSize-1 and posRow >= 0 and posCol >= 0:
      return True
    else:
      return False
  
  # Checks if there is a free space to the right of this position
  def canGoRight(self, row, col):
    if self.checkBounds(self.curRow, self.curCol + 1):
      return True
    elif self.checkBounds(self.curRow + 1, 0):
      return True
    else:
      return False
  
  # Inserts a character at a position relative to the cursor, wrapping
  # text to the next line if needed
  def insert(self, pos, ch):
    oldPosCol = self.curCol
    oldPosRow = self.curRow
    x = self.curCol
    text = ""
    for row in range(self.curRow, self.shape.rowSize):  ###self.boxY2
      self.curPos(row, x)
      text = text + self.win.instr().decode("utf-8").replace(' ', '')
      x = 0 ### self.boxX1
    self.curPos(oldPosRow, oldPosCol)
    self.win.clrtobot()
    if pos > 0:
      for _ in range(pos):
        self.goRight()
    elif pos < 0:
      for _ in range(-pos):
        self.goLeft()
    if ch:
      if self.canGoRight(self.curRow, self.curCol):
        self.win.addstr(chr(ch) + text)
        #print(">" + text + "<")
    else:
      if self.canGoRight(self.curRow, self.curCol):
        self.win.addstr(text)
    self.curPos(oldPosRow, oldPosCol)
    
    
  # Gets all text and returns it as a string
  def getText(self):
    oldPosCol = self.curCol
    oldPosRow = self.curRow
    self.curPos(0, 0)
    text = ""
    for row in range(0, self.shape.rowSize):
      self.curPos(row, 0)
      # Remove spaces (which make up the blank space of the curses window)
      text = text + self.win.instr().decode("utf-8").replace(chr(32), '')
    self.curPos(oldPosRow, oldPosCol)
    # Replace the space placeholder character back with spaces
    text = text.replace(chr(2063), chr(32))
    return text
  
  # Checks if there is an empty slot at the given position
  def checkEmpty(self, row, col):
    if not self.checkBounds(row, col):
      return False
    elif self.win.inch(row, col) == 32:
      return True
    else:
      return False
      
  
  # Un-onHoverEnters the last onHoverEntered character.
  def unHighlight(self):
    if self.onHoverEntered == True:
      self.onHoverEntered = False
      self.win.chgat(self.oldHighlightRow, self.oldHighlightCol, 1, curses.A_NORMAL)
      
  # Highlights a character at a position.
  def onHoverEnterChar(self, row=-1, col=-1):
    if col == -1 or row == -1:
      return
    #print("HIGHLIGHT " + str(x) + ", " + str(y))
    #time.sleep(0.5)
    if curses.has_colors():
      self.onHoverEntered = True
      oldCurCol = self.curCol
      oldCurRow = self.curRow
      
      self.unHighlight()
      self.onHoverEntered = True
      self.oldHighlightCol = col
      self.oldHighlightRow = row

      # Add new color at position
      self.win.chgat(row, col, 1, curses.A_UNDERLINE)
      curses.use_default_colors()
      self.curPos(oldCurRow, oldCurCol, move_virtual = False)
  
  
  
  # Moves the virtual cursor to the specified x, y position, if it is enabled.
  def virtCurMove(self, row=-1, col=-1):
    if col == -1 or row == -1:
      return
    if not(self.isVirtualCursorEnabled) or (row, col) is self.oldVCursor:
      return
    oldRow, oldCol = self.oldVCursor
    
    # Check if character is reversed (https://stackoverflow.com/a/26797300/16386050):
    attrs = self.win.inch(oldRow, oldCol) #[y, x])
    isHighlighted = bool(attrs & curses.A_REVERSE)
    
    if isHighlighted and self.checkBounds(oldRow, oldCol):
      self.win.chgat(oldRow, oldCol, 1, curses.A_NORMAL)
    self.oldVCursor=(col,row)
    if not(isHighlighted or self.checkEmpty(row, col)):
      self.win.chgat(row, col, 1, curses.A_REVERSE)
    
    self.win.move(row, col) # Move the cursor back
    #self.refresh()
    
    
    
  #def virtCurMoveOld(self, x=-1, y=-1):
    #print("HIGHLIGHTING")
    #time.sleep(0.5)
    #self.onHoverEnterChar(x, y)
    #pass
    #print("DONE HIGHLIGHTING")
    #time.sleep(0.5)
    
    
      
  # Erases everything and sets the pad's text to text, with the cursor at the end
  def setText(self, text):
    maxLen = (self.shape.colSize-1) * (self.shape.rowSize)-1
    if len(text) >= maxLen:
      text = text[0:maxLen-1]
    self.win.erase()
    self.win.addstr(0, 0, text) # Display text
    column = len(text)
    xWidth = self.shape.colSize
    #self.curPos(self.boxY1+int(column / xWidth, self.boxX1+(column % xWidth)))
    self.curPos(int(column / xWidth), column % xWidth)
    
    #self.win.refresh()
                
  
  # Does the equivalent of a backspace. Includes workarounds for the many bugs it had...
  def backSpace(self):
    if not(self.curCol == 0 and self.curRow == 0): # Can't backspace if at the start
      if self.checkEmpty(self.curRow, self.curCol + 1) or self.curCol == self.colSize-1:
        self.goLeft()
        self.win.delch()
        # A workaround for a bug where it wouldn't bring text on the next line
        # with it when it backspaced when the cursor was two places to the left of the right
        # side of the window
        #if self.curCol + 1 == self.shape.colSize-1:
        #  self.insert(0, None)
      else:
        self.insert(-1, None)
        self.goLeft()
  
  def type(self, ch):
    #Handle special key presses
    if ch == curses.KEY_DOWN:
      pass
    elif ch == curses.KEY_RIGHT:
      # Don't go off the end of a line
      if not(self.checkEmpty(self.curRow, self.curCol)):
        self.goRight()
    elif ch == curses.KEY_UP:
      pass
      self.win.erase()
    elif ch == curses.KEY_LEFT:
      self.goLeft()
    elif ch == curses.KEY_BACKSPACE:
      self.backSpace()
    elif ch == curses.KEY_DC:
      self.win.delch()
      self.insert(0, None) # Refresh rest of text
    elif ch == curses.KEY_ENTER: # Enter
      pass
      
    else: #If it is not a special key press, handle typing
      #Exclude special characters if they go off the screen
      if ch == 32: # Change spaces to a different character
        # because blank space in a curses window is made of spaces.
        ch = 2063 # Invisible Separator
        
      self.unHighlight()
      self.insert(0, ch)
      self.goRight()
    
    #self.win.refresh()