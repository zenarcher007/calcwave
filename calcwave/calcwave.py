#!/usr/bin/env python3
version = "1.4.0"


# Copyright (C) 2021 by: Justin Douty (jdouty03 at gmail dot com)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Calcwave
# Interactively generates and plays audio from mathematical formulas.
  
import sys
import os
from sys import platform
import struct
import math
from random import random
import argparse
import threading
import time
import wave
import gc


# Supress SyntaxWarning from Math module
import warnings
warnings.filterwarnings(
    action='ignore',
    category=SyntaxWarning,
    #module=r'math'
)
global useVirtualCursor
useVirtualCursor = False
# Decide which imports are neccessary based on arguments
if len(sys.argv) == 1 or (not(sys.argv.count('-o') or sys.argv.count('--export'))): 
  # Don't need pyaudio if just exporting audio as a file - only because this is a bit hard to install
  import pyaudio
  import numpy as np
  #import matplotlib.pylab as plt
  #import matplotlib
  #from matplotlib import pyplot as plt
  import matplotlib.pyplot as plt
  
# You will only need curses if using gui mode
if len(sys.argv) == 1 or sys.argv.count('--gui') and not(sys.argv.count('-o') or sys.argv.count('--export')):
  import curses
  from curses.textpad import Textbox, rectangle
  from curses import wrapper
  
  
  # To provide compatibility between different operating systems, use different
  # key settings for the corresponding operating system.
  # backspace: 127 on Mac and Linux, 8 on windows.
  # delete: 126 on Mac, 27 on Linux
  pform = sys.platform
  if "darwin" in pform:
    curses.KEY_BACKSPACE = 127
    curses.KEY_DC = 330
    curses.KEY_ENTER = 10
  elif "linux" in pform:
    #curses.KEY_BACKSPACE = 127
    #curses.KEY_DC = 126
    curses.KEY_ENTER = 10 # Was 343 when tested on Linux Mint (Debian)
  elif "win" in pform:
    curses.KEY_BACKSPACE = 8
    curses.KEY_ENTER = 10
    useVirtualCursor = True
  else:
    sys.stderr.write("Warning: unsupported platform, \"" + str(pform) + "\"\n")
    # Use default curses key definitions; doesn't change them

# This represents a left-corner starting location and an row/col size.
# Unlike curses function calls, this uses the more standard (x,y)
# convention as opposed to (y,x). It accepts an x,y point followed by an x,y size.
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
    newCols = self.col + cols
    extraRows = int(newCols / width)
    wrappedCols = newCols % width
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

# Helpful and necessary functionality for editors
class BasicEditor:
  def __init__(self, box: Box):
    self.win = curses.newwin(box.rowSize, box.colSize, box.rowStart, box.colStart) # Initialize curses window
    self.cursorPos = Point(0,0)
    self.oldCursorPos = self.cursorPos
    self.oldHighlightPos = self.cursorPos
    self.shape = box # Public - holds the shape / dimensions of this window
    
  def highlightChar(self, p : Point):
    self.oldHighlightPos = p
    self.win.chgat(p.row, p.col, 1, curses.A_UNDERLINE)
    self.win.refresh()

  def restoreLastHighlight(self):
    self.win.chgat(self.oldHighlightPos.row, self.oldHighlightPos.col, 1, curses.A_NORMAL)

  # Hides the cursor temporarily, until it is moved.
  def hideCursor(self):
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_NORMAL) # Un-highlight new position
    self.win.refresh()

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
        self.refresh()
        return True
    elif ch == curses.KEY_DOWN:
      newPos = self.cursorPos.relative(row = 1, col = 0)
      if newPos.row < self.shape.rowSize:
        self.setCursorIndex(newPos)
        self.refresh()
        return True
    elif ch == curses.KEY_LEFT:
      newPos = self.cursorPos.relative(row = 0, col = -1)
      if newPos.row >= 0:
        self.setCursorIndex(newPos)
        self.refresh()
        return True
    elif ch == curses.KEY_RIGHT:
      newPos = self.cursorPos.relative(row = 0, col = 1)
      if newPos.row < self.shape.colSize:
        self.setCursorIndex(newPos)
        self.refresh()
        return True
    else:
      return False

    

  # Calls a window refresh
  def refresh(self):
    self.restoreLastHighlight()

    # Redraw cursor
    self.win.chgat(self.oldCursorPos.row, self.oldCursorPos.col, 1, curses.A_NORMAL) # Unhighlight old position
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight new position
    self.oldCursorPos = self.cursorPos

    self.win.refresh()




# A full text editor that supports newlines and scrolling
class TextEditor(BasicEditor):
  def __init__(self, box: Box):
    super(TextEditor, self).__init__(box)
    self.data = [[]]
    self.dataPos = self.cursorPos
    self.oldHighlightPos = Point(0,0)
    self.cursorOffset = 0
    self.scrollOffset = 0
    self.lineOffset = 0 # For reference when the cursor wraps to the next line
    self.win.scrollok(True) # Enable curses scrolling

  def setText(self, text: str):
    self.win.clear()
    self.data = [[]]
    self.cursorOffset = 0
    self.scrollOffset = 0
    self.lineOffset = 0
    self.cursorPos = Point(0,0)
    self.dataPos = Point(0,0)
    for ch in text:
      self.type(ch)
    

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
    return int(len(self.data[line]) / self.shape.colSize)+1

  # Changes the current line of text selected, relatively, updating the cursor offset and snapping to the end of the line
  def mvLine(self, lines, cursorOriented = True):
    ### Update cursor offset
    cursorDepth = int(self.dataPos.col / self.shape.colSize) # How far down is the cursor on the current line relative to its start?
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
    

  def insertChar(self, ch):
    self.data[self.dataPos.row].insert(self.dataPos.col, ch)
    if(self.cursorPos.col == self.shape.colSize-1):
      self.win.insertln()
    self.moveCursor(rows = 0, cols = 1)

  # Refreshes the last line, closest to the end of the text editor
  def refreshLastLine(self):
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
    
    if self.dataPos.col == 0: # Delete this line, move the cursor to the end of the previous line, and bring following text with it
      charList = self.data.pop(self.dataPos.row)
      self.win.deleteln()
      self.mvLine(-1)
      self.goToEol()
      self.data[self.dataPos.row].extend(charList)
      ### Refresh a line of text at the end without changing cursor parameters ###
      self.refreshLastLine()
    else: # Delete a character on the current line, and move the cursor back
      self.slideData(-1)
      self.data[self.dataPos.row].pop(self.dataPos.col)
    return True
    
  def enter(self):
    line = self.data[self.dataPos.row]
    oldTail = line[self.dataPos.col: len(line)]
    self.data.insert(self.dataPos.row+1, oldTail) if self.dataPos.row != len(self.data)-1 else self.data.append(oldTail) # Add the tail of the last line (if any) to a new line
    self.win.insertln()
    for i in range(len(oldTail)): # Delete tail of original line
      self.data[self.dataPos.row].pop(self.dataPos.col)
    self.refresh() # Refresh optimization will not otherwise see it, as it is switching lines
    self.hideCursor()
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
        self.goToEol()
      elif self.dataPos.row < len(self.data)-1: # If it is within the bounds of the screen
        self.mvLine(1)
      else: # I give up
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
    self.refresh()
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
      if move_virtual:
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
    self.win.refresh()
                
  
  # Does the equivalent of a backspace. Includes workarounds for the many bugs it had...
  def backSpace(self):
    if not(self.curCol == 0 and self.curRow == 0): # Can't backspace if at the start
      if self.checkEmpty(self.curRow, self.curCol + 1) or self.curCol == self.colSize-1:
        self.goLeft()
        self.win.delch()
        # A workaround for a bug where it wouldn't bring text on the next line
        # with it when it backspaced when the cursor was two places to the left of the right
        # side of the window
        if self.curCol + 1 == self.shape.colSize-1:
          self.insert(0, None)
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
    self.win.refresh()
##################################################################



#To hold data that is passed to multiple running threads
class threadArgs:
  def __init__(self):
    self.expression = ""
    self.start = -100000
    self.end = 100000
    self.channels = 1
    self.rate = 44100
    self.frameSize = 1024
    self.isGUI = False
    self.shutdown = False
    self.step = 1. # How much to increment x
    self.functionTable = self.getFunctionTable()
    self.lock = threading.Lock()
    
  # Define functions available to eval here.
  def getFunctionTable(self):
    functionsDict = vars(math)
 
    # Returns a random number between -1 and 1. Can be used to generate fuzz noises.
    def rand():
      return random() * 2 - 1
    functionsDict["rand"] = rand
 
    return functionsDict

# Accepts CalcWave text input
# Parses and evaluates the CalcWave syntax
class Evaluator:
  def __init__(self, text, symbolTable = vars(math)):
    self.symbolTable = symbolTable
    self.text = text
    symbolTable['x'] = 0
    symbolTable["main"] = 0
    self.prog = compile(text, '<string>', 'exec', optimize=2)
  
  def evaluate(self, x):
    self.symbolTable['x'] = x
    try:
      exec(self.prog, self.symbolTable, self.symbolTable)
    except:
      pass
    return self.symbolTable["main"]
    
#  exp_as_func = eval('lambda x: ' + "(" + tArgs.expression + ")*32767", tArgs.functionTable)
  def parse(self):
    byLines = self.text.split('\n')
    for lineNum in range(len(byLines)): # Search for substitution assignments
      line = byLines(lineNum)
      if '=' in line:
        try:
          var, assignment = line.split('=')
          var.strip() # Remove spaces from either side
          assignment.strip()
          self.symbolTable[var] = eval()
        except ValueError as e:
          raise AttributeError(f"[row={lineNum},col=0,len={len(line)}]: Unable to parse assignment")
      


# Handles GUI
class WindowManager:
  def __init__(self, tArgs, scr, menu):
    self.tArgs = tArgs
    self.scr = scr
    self.menu = menu
    
    self.scr.keypad(True)
    self.scr.nodelay(True)
    curses.noecho()
  
    rows, cols = self.scr.getmaxyx()
    #Initialize text editor
    self.pad = TextEditor(Box(rowSize = rows - 6, colSize = cols, rowStart = 1, colStart = 0))
    
    
    # Tell the menu that this is the main window
    self.menu.setMainWindow(self.pad.win)
  
    #Initialize info display window
    self.infoPad = InfoDisplay(Box(rowSize = 2, colSize = cols, rowStart = rows - 2, colStart = 0))
    self.infoPad.setMainWindow(self.pad.win) # So it will know
    # what window to return the cursor to after it updates
    self.menu.setInfoDisplay(self.infoPad) # Give the menu an infoPad
    # so it can display its own information on it.
    

    self.thread = threading.Thread(target=self.windowThread, args=(tArgs, scr, menu), daemon=True)
    self.thread.start()
    self.pad.setText(tArgs.expression)
    
  def windowThread(self, tArgs, scr, menu):
    lock = threading.Lock()
    
    oldTime = 0
    menuFocus = False
    settingFocus = False
    startUp=True
    try:
      while self.tArgs.shutdown is False:
        #updateInfo(infoWin, self.pad, self.scr, "")
        ch = self.scr.getch()
        
        
        if ch == 27 and menuFocus == False: # Escape key
          with lock:
            self.infoPad.updateInfo("ESC recieved. Shutting down...")
            self.tArgs.shutdown = True
            break
          
          
        # Only runs once
        if startUp == True:
          startUp = False
          self.menu.refreshAll()
          self.pad.refresh()
          self.pad.infoPad = self.infoPad ###### TEMP; For debugging ######
          self.menu.title.refresh()
          
        
        if ch != -1:
          oldTime = time.time()

          # Switch between menu and inputPad with the arrow keys
          
          
          if menuFocus == True:
            self.menu.type(ch)
          elif settingFocus == False:
            p = self.pad.getPos()
            self.infoPad.updateInfo(f"Line: {p.row}, Col: {p.col}")
            # Type on the inputPad, verifying each time
###            self.infoPad.updateInfo("Wait...")                # Disabled for testing
            #with lock:
              # Don't update the progress bar while typing. This helps a problem where the terminal cursor may sporadically jump (wrongly) to the progess bar.
            #  self.menu.getProgressBar().temporaryPause = True
            if self.pad.type(ch):
              text = self.pad.getText()
###              self.infoPad.updateInfo("Verifying...")
          
              try: # Verify expression
                eval('lambda x: ' + text, tArgs.functionTable)
                with lock:
                  self.tArgs.expression = text # Update the expression for the audioThread
###                self.infoPad.updateInfo("Playing...")
              except (SyntaxError, NameError, TypeError) as e:
                # Highlight problem character
                if len(e.args) == 2 and len(text) > 0:
                  error = str(e.args[1])
                  parseString = error.split(',', 3)
                  if len(parseString) >= 3:
                    column = int(parseString[2]) - 11
                    #x = self.pad.shape.colStart + column
                    #y = self.pad.shape.rowStart
                    #if x >= self.pad.shape.colStart and y >= self.pad.shape.rowStart:
                    ###xWidth = (self.pad.shape.colStart + self.pad.shape.colSize) - self.pad.shape.colStart+1
                    ###self.pad.highlightChar(Point(col = int(column / xWidth), row = column % xWidth))
                    ###self.pad.highlightChar(column)
###                  self.infoPad.updateInfo(str(e.args[0]))
                else:
                  if len(text) > 0:
                    error = str(e.args)
###                    self.infoPad.updateInfo(error)
                  else:
                    self.tArgs.expression = "0"
###                    self.infoPad.updateInfo("")
              continue
              

                    
            #with lock:
            #  self.menu.getProgressBar().temporaryPause = False
          
          if ch == curses.KEY_UP and not self.menu.editing: # Don't remove focus from the menu while it's editing
            menuFocus = False
            settingFocus = True
            with lock:
              self.infoPad.setMainWindow(self.pad.win)
              self.menu.setMainWindow(self.pad.win)
              #self.menu.getProgressBar().temporaryPause = False
              self.menu.focusedWindow.onHoverLeave()
            self.infoPad.updateInfo("")
            self.menu.title.refresh() # Good time to refresh the title?
            self.pad.refresh() # Set cursor back to typing pad
          elif ch == curses.KEY_DOWN:
            menuFocus = True
            settingFocus = True
            self.pad.hideCursor()
            self.menu.focusedWindow.onHoverEnter()
            if self.menu.editing:
              self.menu.focusedWindow.onBeginEdit()
            self.menu.refreshTitleMessage()
          
          settingFocus = False
        else:
          # Improve typing performance, but save CPU when not typing
          if time.time() - oldTime > 0.5:
            time.sleep(0.1)
          
    except (KeyboardInterrupt, SystemExit):
      pass
    finally:
      sys.stderr.write("Shutting down GUI...\n")
      self.stopCursesSettings(self.scr)
      self.tArgs.shutdown = True
      
  # Changes curses settings back in order to restore terminal state
  def stopCursesSettings(self, scr):
    curses.echo()
    curses.nocbreak()
    scr.keypad(False)
    curses.endwin()






# The basic neccesities for the UIManager to accept your widget as a menu item
class BasicMenuItem:
  def __init__(self, shape: Box):
    self.shape = shape
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    
    #self.toolTip = "Tool Tip"
    #self.hoverMsg = "Hover Message"
    #self.actionMsg = "Action Message"
    self.refresh()
    
  # What should I (UIManager) call you?
  def getDisplayName(self):
   return "BasicMenuItem"

 # Calls refresh() on the window object
 # this must be lightweight, as it may be called often.
  def refresh(self):
    self.win.refresh()
    
  def displayText(self, text):
    self.win.erase()
    self.win.addstr(0, 0, text)
    self.win.refresh()

  def isOneshot(self):
    return False # By default, this item can enter and exit focus, rather than immediately exiting.

  # Redraws the button graphics (text, background, etc.)
  def updateValue(self, value):
    pass # This is a hook
   
  # Called when UIManager has the cursor over your item
  def onHoverEnter(self):
    for row in range(0, self.shape.rowSize):
      self.win.chgat(0, row, self.shape.colSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    return "Hover Message"
  
  # Called when UIManager tells the cursor to leave your item
  def onHoverLeave(self):
    for row in range(0, self.shape.rowSize):
      self.win.chgat(0, row, self.shape.colSize, curses.A_NORMAL)
    curses.use_default_colors()
    self.win.refresh()
    
  # Sets messages displayed in the infoDisplay when selected or activated
 #def setToolTip(self, text):
 #   self.toolTip = text
 # def setHoverMsg(self, text):
 #   self.hoverMsg = text
 # def setActionMsg(self, text):
 #   self.actionMsg = text
#def setDisplayName(self, text):
#  #  self.displayName = text
    
  # Control what happens when you send keyboard presses to it
  def type(self, ch):
    pass # This is a hook
    
  # Called when entering edit mode on the item
  def onBeginEdit(self):
    return "Begin Edit Message"
    pass # This is a hook
    
  # What happens when this is activated by pressing enter?
  def doAction(self):
    return "Action Completed Message"
    #pass # This is a hook


# A button to export audio as a WAV file, assuming you have the "wave" module installed.
class exportButton(InputPad, BasicMenuItem):
  def __init__(self, shape: Box, tArgs, progressBar):
    super().__init__(shape)
    self.tArgs = tArgs
    self.infoPad = None
    self.progressBar = progressBar
    self.setText("Export Audio")
    self.refresh()

  def getDisplayName(self):
    return "Export Button"
  
  def updateValue(self, text):
    self.setText(text)
    
  def onBeginEdit(self):
      self.setText("") # Clear and allow you to enter the filename
      return "Please enter filename, and press enter to save. Any existing file will be overwritten."
    
  def setInfoDisplay(self, infoPad):
    self.infoPad = infoPad
    
  def onHoverEnter(self):
    super().onHoverEnter()
    return "Press enter to save a recording as a WAV file."

  def onHoverLeave(self):
    self.setText("Export Audio")
    super().onHoverLeave()
    
  # Override type, make it check filenames live
  def type(self, ch):
    super().type(ch)
    name = self.getText()
    if name == '':
      self.infoPad.updateInfo("Please enter filename, and press enter to save. Any existing file will be overwritten.")
      return
    
    # Update the infoDisplay
    fullPath = ''
    if '/' in name:
      # Use absolute specified path
      fullPath = name + ".wav"
      parDir = '/'.join(fullPath.split('/')[0:-1])
      try:
        if parDir != '' and not os.path.isdir(parDir):
          self.infoPad.updateInfo("Invalid directory \"" + parDir + "\"")
          return
      except PermissionError:
        self.infoPad.updateInfo("Permission denied: " + parDir)
    else:
      path = os.getcwd()
      fullPath = path + "/" + name + ".wav"
      
    if os.path.isfile(fullPath):
      self.infoPad.updateInfo("Will overwrite " + fullPath)
    else:
      self.infoPad.updateInfo("Will export as " + fullPath)
  
  # Where it actually saves the file
  def doAction(self):
    name = self.getText()
    actionMessage = "File saved in same directory!"
    if name == '':
      self.setText("Export Audio")
      return "Cancelled."
    self.setText("Export Audio")
    path = ''
    if '/' in name:
      fullPath = name + ".wav"
      parDir = '/'.join(fullPath.split('/')[0:-1])
      if not os.path.isdir(parDir):
        actionMsg = "Cannot export audio: invalid path \"" + fullPath + "\""
        self.setText("Export Audio")
        return
    else:
      path = os.getcwd()
      fullPath = path + "/" + name + ".wav"
    actionMsg = "Saving file as " + fullPath
    
    #with self.lock:
    self.progressBar.temporaryPause = False
    if(self.infoPad):
      self.infoPad.updateInfo("Writing...")
    
    # Do in a separate thread?
    thread = threading.Thread(target=exportAudio, args=(fullPath, self.tArgs, self.progressBar, self.infoPad), daemon = True)
    thread.start()
    #exportAudio(fullPath)
    return actionMsg
    
    
# Exports audio to a wav file, optionally showing progress on the infoPad if specified
def exportAudio(fullPath, tArgs, progressBar, infoPad):
  lock = threading.Lock()
  oldTime = time.time()
  with wave.open(fullPath, 'w') as f:
    f.setnchannels(tArgs.channels)
    f.setsampwidth(2)
    f.setframerate(tArgs.rate)
    x = 0
    exp_as_func = eval('lambda x: ' + "(" + tArgs.expression + ")*32767", tArgs.functionTable)
    # Goes from -32767 to 32767 instead of -1 to 1, and needs to produce ints
    
    # Cache values to prevent changes while writing
    step = tArgs.step
    start = tArgs.start
    end = tArgs.end
    value = 0
    
    i=0
    progressStart = 0 # The point the progress display will start from, so it doesn't go backwards
    # Support negative (backwards) step
    if step < 0:
      i = end
      progressStart = end
    elif step > 0:
      i = start
      progressStart = start
    elif step == 0:
      raise(ValueError("Step value cannot be zero!"))
    while i <= end and i >= start: # Python's range() does not support using floats as step value
      try:
        value = int(exp_as_func(i))
      except:
        pass
        
      if value > 32767:
        value = 32767
      elif value < -32767:
        value = -32767
        
      f.writeframesraw( bytes(struct.pack('<h', value)) )
      
      newTime = time.time()
      
      if newTime - oldTime > 1 and infoPad and progressBar:
        oldTime = newTime
        #with lock:
        progressBar.temporaryPause = True
        infoPad.updateInfo("Writing (" + str(int(abs(i-progressStart)/(abs(end-start))*100)) + "%)...")
        progressBar.temporaryPause = False
      i = i + step
  if infoPad:
    infoPad.updateInfo("Exported as " + fullPath)
    


# A menu item in the format "name=..." that types like an InputPad
# this allows setting variables, etc in a typing-based way
class NamedMenuSetting(InputPad, BasicMenuItem): # Extend the InputPad and BasicMenuItem classes
  def __init__(self, shape: Box, name):
    super().__init__(shape)
    self.name = name
    self.setText(name + "=")
    self.lastValue = "0"
    self.refresh()
  
  def updateValue(self, value):
    self.setText(self.name + "=" + str(value))
    self.lastValue = value
  
  # Updates the last value first in order to leave the cursor in the right position
  def onHoverLeave(self):
    super().onHoverLeave()
    self.updateValue(self.lastValue)
    self.refresh()
  
  def getValue(self):
    index = len(str(self.name + "="))
    text = self.getText()
    result = text[index:]
    return result
  
  # Override InputPad goLeft() method
  def goLeft(self):
    # Don't allow going to the left of the '='
    if self.curCol > len(str(self.name + "=")):
      super().goLeft()
  
  # Override InputPad type method
  def type(self, ch):
    super().type(ch)
    self.refresh()
    

      
# A special case of a NamedMenuSetting that only allows typing numbers. Returns the number as
# an int or float when getValue() is called based on which one you specified in valueType
class NumericalMenuSetting(NamedMenuSetting):
  def __init__(self, shape: Box, name, type):
    super().__init__(shape, name)
    self.valueType = "int" # String containing "int" or "float". Defaults to int.
    self.valueType = type
  
  # Override getValue()
  def getValue(self):
    value = str(super().getValue())
    if len(value) == 0:
      value = "0"
    try:
      if self.valueType == "int":
        value = int(value)
      elif self.valueType == "float":
        value = float(value)
    except ValueError:
      self.actionMsg = "Error converting string \"" + value + "\" to " + self.valueType + "."
      raise ValueError("Error converting string \"" + value + "\" to " + self.valueType + ".")
    else:
      self.lastValue = str(value)
      return value
        
    # Override NamedMenuSetting type method
  def type(self, ch):
    # Only allow these keys
    if (ch >= 48 and ch <= 57) or ch == curses.KEY_BACKSPACE or ch == 127 or ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT or ch == curses.KEY_DC or chr(ch) == '-' or chr(ch) == '.':
      if not(chr(ch) == '.' and self.valueType == "int"):
        super().type(ch)

# A special case of a NamedMenuSetting that sets the start range in tArgs
class startRangeMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, tArgs):
    super().__init__(shape, name, "int")
    self.lock = threading.Lock()
    self.tArgs = tArgs

  def getDisplayName(self):
    return "Start Value"

  # Info message definitions
  def onHoverEnter(self):
    super().onHoverEnter()
    return "Press enter to change the start range."
  def onBeginEdit(self):
    super().onBeginEdit()
    return "Setting start range... Press enter to apply."

  def doAction(self):
    value = 0
    actionMsg = "Start range Changed!"
    try:
      value = self.getValue()
    except ValueError:
      pass
    else:
      if value > self.tArgs.end: # Don't allow crossing start / end ranges
        actionMsg = "Start range cannot be greater than end range!"
        self.updateValue(self.tArgs.start)
      else:
        actionMsg = "Start range changed to " + str(value) + "."
        self.lastValue = str(value)
        with self.lock:
          self.tArgs.start = value
      return actionMsg


# A special case of a NamedMenuSetting that sets the end range in tArgs
class endRangeMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, tArgs):
    super().__init__(shape, name, "int")
    self.lock = threading.Lock()
    self.tArgs = tArgs
    self.stepWin = None
    
  def onHoverEnter(self):
    super().onHoverEnter()
    return "Press enter to change the end range."
  def onBeginEdit(self):
    super().onBeginEdit()
    return "Setting end range... Press enter to apply."

  # You may give it the stepMenuItem object in order for it to refresh
  # and update the step if needed.
  def setStepWin(self, win):
    self.stepWin = win
    
  def doAction(self):
    value = 0
    actionMsg = "End range changed!"
    try:
      value = self.getValue()
    except ValueError:
      pass
    else:
      if value < self.tArgs.start: # Don't allow crossing start / end ranges
        actionMsg = "End range cannot be less than start range!"
        self.updateValue(self.tArgs.end)
      else:
        actionMsg = "End range changed to " + str(value) + "."
        self.lastValue = str(value)
        with self.lock:
          self.tArgs.end = value

      return actionMsg
      

  # A special case of a NamedMenuSetting that sets the step amount in tArgs
class stepMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, tArgs):
    super().__init__(shape, name, "float")
    self.lock = threading.Lock()
    self.tArgs = tArgs

  # Tooltip Message Definitions
  def onBeginEdit(self):
    super().onBeginEdit()
    return "Setting step amount... Press enter to apply."
  def onHoverEnter(self):
    super().onHoverEnter()
    return "Press enter to change the step amount."
  
  def doAction(self):
    value = 0.
    try:
      value = self.getValue()
    except ValueError:
      pass
    else:
      self.updateValue(value)
      self.lastValue = str(value)
      with self.lock:
        self.tArgs.step = value
    return "Step amount changed to " + str(value) + ". Note: baud rate is " + str(self.tArgs.rate) + "hz."
    
    
    
    
    

# A ProgressBar that displays the current position of AudioPlayer's range
class ProgressBar(BasicMenuItem):
  def __init__(self, shape: Box, audioClass, tArgs):
    super().__init__(shape)
    self.lock = threading.Lock()
    self.audioClass = audioClass
    self.progressBarEnabled = True
    self.temporaryPause = False
    self.tArgs = tArgs
    
    # Start progress bar thread
    self.progressThread = threading.Thread(target=self.progressThread, args=(tArgs, audioClass), daemon=True)
    self.progressThread.start()

  def getDisplayName(self):
    return "Progress Bar"

  def onBeginEdit(self):
    super().onBeginEdit()
    return "V- toggle visibility, Left/Right Arrows- move back and forth, Space- pause/play"

  def onHoverEnter(self):
    self.temporaryPause = True # To prevent unhighlighting
    super().onHoverEnter()
    return "Press enter to pause, seek, and change progress bar settings."
    
  def onHoverLeave(self):
    self.temporaryPause = False
    super().onHoverLeave()
    
  def type(self, ch):
    with self.lock:
      self.temporaryPause = False
    # Handle left/right stepping
    if ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT:
      range = abs(self.tArgs.end - self.tArgs.start)
      blockWidth = int(range / self.colSize)
      # Use bigger increments if not paused
      if self.audioClass.paused == False:
        blockWidth = blockWidth * 5
      
      with self.lock:
        index = self.audioClass.index
        
      if ch == curses.KEY_LEFT:
        index = index - blockWidth
      elif ch == curses.KEY_RIGHT:
        index = index + blockWidth
      # Limit between acceptable range
      if index < self.tArgs.start:
        index = self.tArgs.start
      elif index > self.tArgs.end:
        index = self.tArgs.end
      # Write back to AudioPlayer
      with self.lock:
        self.audioClass.index = index
      self.updateIndex(index, self.tArgs.start, self.tArgs.end)
      
    if ch == 32: # Space
      with self.lock:
        self.audioClass.setPaused(not(self.audioClass.paused))
        
    if chr(ch) == 'v' or chr(ch) == 'V':
      self.toggleVisibility()
  
  # Defines action to do when activated
  def doAction(self):
    return "Done editing progress bar."
  
  
  # Toggles progress bar visibility
  def toggleVisibility(self):
    if self.progressBarEnabled == True:
      with self.lock:
        self.progressBarEnabled = False
      #self.actionMsg = "Progress bar visibility turned off!"
      # Set progress bar text full of '-'
      text = ''.join([char*(self.shape.colSize-1) for char in '-' ])
    else:
      with self.lock:
        self.progressBarEnabled = True
      text = ''.join([char*(self.shape.colSize-1) for char in '░' ])
      #self.actionMsg = "Progress bar visibility turned on!"
    self.win.erase()
    self.win.addstr(0, 0, text)
    self.win.refresh()
    if self.otherWindow: # Preserve cursor position
      self.otherWindow.refresh()
      
  
  # You can tell it what window to return the cursor
  # to after updating
  def setMainWindow(self, window):
    self.otherWindow = window
    
  def progressThread(self, tArgs, audioClass):
    index = 0
    while self.tArgs.shutdown == False:
    # Update menu index display
      time.sleep(0.5)
      with self.lock:
        pause = self.temporaryPause
      if self.tArgs.shutdown == False and self.progressBarEnabled and pause == False:
        with self.lock:
          index = audioClass.index
        self.updateIndex(index, tArgs.start, tArgs.end)
      
      # Display blank while not playing anything
      if self.tArgs.expression == "0" and self.progressBarEnabled == True:
        self.toggleVisibility()
        while self.tArgs.expression == "0":
          time.sleep(0.2)
        self.toggleVisibility()
  
  # Displays the current x-value as a progress bar
  def updateIndex(self, i, start, end):
    if self.progressBarEnabled == False:
      return
    maxLen = self.shape.colSize * self.shape.rowSize
    value = int(np.interp(i, [start,end], [0, maxLen - 2]))
    
    text = "{" + ''.join([char*value for char in '░' ])
    
    # Lock thread
    self.lock.acquire(blocking=True, timeout=1)
    self.win.erase()
    self.win.addstr(0, 0, text) # Display text
    self.win.addch(0, maxLen - 2, '}')
    self.win.refresh()
    if self.otherWindow:
      self.otherWindow.refresh()
    # Unlock thread
    self.lock.release()
    
class graphButtonMenuItem(BasicMenuItem):
  isGraphThreadRunning = False
  def __init__(self, shape: Box, tArgs, audioClass):
    super().__init__(shape)
    self.tArgs = tArgs
    self.audioClass = audioClass
    self.isGraphThreadRunning = False
    self.graphThread = None

  def __del__(self):
    with threading.Lock():
      self.isGraphThreadRunning = False

  def refresh(self):
    super().refresh()
    if self.isGraphThreadRunning:
      self.displayText("Graph On")
    else:
      self.displayText("Graph Off")

  def isOneshot(self):
    return True

  def getDisplayName(self):
    return "Graph"

  # TODO: Why doesn't this highlight it???
  def onHoverEnter(self):
    super().onHoverEnter()
    return "Press enter to toggle a graph of the output"

  def onBeginEdit(self):
    super().onBeginEdit()
    return "Toggling graph..."

  # Currently disabled ; doesn't work in a thread...
  def graphThreadRunner(self, tArgs, audioClass):
    plt.ion()
    plt.show()
    while(self.isGraphThreadRunning):
      exp_as_func = audioClass.getAudioFunc() # Update expression
      if exp_as_func is not None:
        curr = audioClass.index # Get current position
        plt.plot([x for x in self.calcIterator(curr, curr+10000, tArgs.step, exp_as_func)])
        plt.draw()
      time.sleep(1)
    plt.close()

  def graphOn(self):
    self.audioClass.enableGraph()
    #with threading.Lock(): # This should at least flush the changes... Right?
    #  self.isGraphThreadRunning = True    
    #self.graphThread = threading.Thread(target=self.graphThreadRunner, args=(self.tArgs, self.audioClass), daemon=True)
    #self.graphThread.start()
    # matplotlib.use("macOSX")
    
   

  def graphOff(self):
    self.audioClass.disableGraph()
    #with threading.Lock():
    #  self.isGraphThreadRunning = False

  def doAction(self):
    actionMsg = "Toggled Graph!"
    with threading.Lock(): # This should at least flush the changes... Right?
      self.isGraphThreadRunning = not self.isGraphThreadRunning
    if not self.isGraphThreadRunning: # Just a negation of the above, so that the variable is seen by the thread beforehand
      self.graphOff()
      actionMsg = "Turned Graph off."
    else:
      self.graphOn()
      actionMsg = "Turned Graph on."


    #curr = self.audioClass.index # Get current position
    #exp_as_func = self.audioClass.getAudioFunc() # Update expression
    #actionMsg = str([x for x in self.calcIterator(curr, curr+10000, self.tArgs.step, exp_as_func)])
    #plt.plot([x for x in self.calcIterator(curr, curr+10000, self.tArgs.step, exp_as_func)])
    #plt.show()
    #plt.draw()
    return actionMsg



# Just a title display at the top of the screen
class TitleWindow:
  def __init__(self, shape: Box):
    self.shape = shape
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    self.refresh()
  
  # Draws the title and onHoverEnters it
  def refresh(self):
    self.win.clear()
    self.win.addstr("Calcwave v" + version)
    self.win.chgat(0, 0, self.shape.colSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    
  # Use curstom text
  def customTitle(self, text):
    self.win.clear()
    self.win.addstr(text)
    self.win.chgat(0, 0, self.shape.colSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    
    
# A class that controls and handles interactions with menus and other UI.
# Drive UIManager's type(ch) function with keyboard characters
# to interact with it when needed.
class UIManager:
  def __init__(self, shape: Box, tArgs, audioClass):
    #self.rowSize = rowSize
    #self.colSize = colSize
    #self.rowStart = rowStart
    #self.colStart = colStart

    self.tArgs = tArgs
    self.infoPad = None
        
    self.settingPads = []
    self.boxWidth = int(shape.colSize / 3)
    
    self.title = TitleWindow(Box(rowSize = 1, colSize = shape.colSize, rowStart = 0, colStart = 0))
    self.lock = threading.Lock()
    
    # Create windows and store them in the self.settingPads list.
    
    # Graph Button
    graphBtn = graphButtonMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart, colStart = shape.colStart), tArgs, audioClass)

    # Start range
    startWin = startRangeMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart+1, colStart = shape.colStart), "beg", tArgs)
    startWin.updateValue(tArgs.start)
    
    # Progress bar
    progressWin = ProgressBar(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart+1, colStart = shape.colStart + self.boxWidth), audioClass, tArgs)
    
    # End range
    endWin = endRangeMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart+1, colStart = shape.colStart + self.boxWidth * 2), "end", tArgs)
    endWin.updateValue(tArgs.end)
    
    # Step value
    stepWin = stepMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart + 2, colStart = shape.colStart + self.boxWidth * 2), "step", tArgs)
    stepWin.updateValue(tArgs.step)
    
    # This currently takes up the width of the screen. Change the value from colSize to resize it
    saveWin = exportButton(Box(rowSize = int(shape.rowSize/2), colSize = int(shape.colSize*(2/3)-1), rowStart = shape.rowStart+2, colStart = shape.colStart), tArgs, progressWin)

    if curses.has_colors():
      curses.init_pair(2, curses.COLOR_RED, -1)
      progressWin.win.bkgd(' ', curses.color_pair(2))
    
    # Be sure to add your object to the settingPads list!
    # They will be selected by the arrow keys in the order of this list.
    self.settingPads.append(graphBtn)
    self.settingPads.append(startWin)
    self.settingPads.append(progressWin)
    self.settingPads.append(endWin)
    self.settingPads.append(saveWin)
    self.settingPads.append(stepWin)
    
    self.focusedWindow = startWin
    self.focusedWindowIndex = 0
    self.editing = False
      
    self.refreshAll()
    # End of constructor
    
  # These are "optional" settings that enhance the experience of the menu.
  # If you specify the main window as a window object, UIManager can return
  # the cursor to the main window after updating one of its own windows
  def setMainWindow(self, window):
    self.getProgressBar().setMainWindow(window)
    if self.infoPad:
      self.infoPad.setMainWindow(window)
    
  # Set the infoPad in the most godawful way in order for it to display information
  def setInfoDisplay(self, infoPad):
    self.infoPad = infoPad
    self.settingPads[4].setInfoDisplay(infoPad) # Give to exportButton
  
  # Calls refresh() for the InputPads for the start and end values,
  # and updates the title window
  def refreshAll(self): # TODO: Wait... Don't I give each object a tArgs anyways??? This is... despicable...
    self.settingPads[0].updateValue(0)
    self.settingPads[1].updateValue(self.tArgs.start)
    self.settingPads[3].updateValue(self.tArgs.end)
    self.settingPads[4].updateValue("Export Audio")
    self.settingPads[5].updateValue(self.tArgs.step)
    for win in self.settingPads:
      win.refresh()
  
  # Retrieves the ProgressBar object in the most godawful way...
  def getProgressBar(self):
    return self.settingPads[2]
    
  # Refreshes title message based on editing status
  def refreshTitleMessage(self):
    if self.editing:
      displayName = self.focusedWindow.getDisplayName()
      if displayName != "":
          self.title.customTitle("Editing " + displayName)
    else:
      self.title.refresh()
      
    
  # Handles typing and switching between items
  def type(self, ch):
    # Make it possible to cancel editing using the escape key
    if ch == 27: # Escape key
      if self.editing == True:
        self.editing = False
        #self.focusedWindow.onHoverEnter()
        self.infoPad.updateInfo("Cancelled editing!")
        self.focusedWindow.onHoverEnter()
        self.refreshTitleMessage()
        return
      else: # Not editing? Interpret as shut down
        with self.lock:
          self.infoPad.updateInfo("ESC recieved. Shutting down...")
          self.tArgs.shutdown = True

    # Switch between menu items
    if self.editing == False and (ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT):
      self.focusedWindow.onHoverLeave()
      if ch == curses.KEY_LEFT:
        if self.focusedWindowIndex > 0:
          self.focusedWindowIndex = self.focusedWindowIndex - 1
        else:
          self.focusedWindowIndex = len(self.settingPads) - 1
      elif ch == curses.KEY_RIGHT:
        if self.focusedWindowIndex < len(self.settingPads) - 1:
          self.focusedWindowIndex = self.focusedWindowIndex + 1
        else:
          self.focusedWindowIndex = 0
      self.focusedWindow = self.settingPads[self.focusedWindowIndex]
      msg = self.focusedWindow.onHoverEnter()
      self.setMainWindow(self.focusedWindow)
      self.infoPad.updateInfo(msg)
      return
      
    self.setMainWindow(self.focusedWindow)
    
    # Function macro to end editing ; TODO: Make this not horribly inline with code?
    def endEdit():
      self.editing = False
      # Run action specified in class
      actionMsg = self.focusedWindow.doAction()
      self.focusedWindow.onHoverEnter()
      self.infoPad.updateInfo(actionMsg)
      self.refreshTitleMessage()
    
    # Function macro to begin edting
    def beginEdit():
      self.editing = True
      self.focusedWindow.onHoverLeave() # Item exits hover mode while editing
      self.refreshTitleMessage()
      tooltipMsg = self.focusedWindow.onBeginEdit()
      self.infoPad.updateInfo(tooltipMsg)
      if self.focusedWindow.isOneshot(): # If onBeginEdit() returns True, end edit immediately after.
        endEdit()
      self.focusedWindow.refresh()
    
    # Toggle editing on and off and handle onHoverEntering (highlighting)
    if ch == curses.KEY_ENTER:
      if self.editing == False:
        beginEdit()
      else:
        endEdit()
      return
      
      
    # Drive the type function
    if not (ch == curses.KEY_UP or ch == curses.KEY_DOWN):
      if self.editing == False:
        beginEdit() # Begin editing automatically
      self.focusedWindow.type(ch)
    
    


# The display at the bottom of the screen that shows status
# and error messages
class InfoDisplay:
  def __init__(self, shape: Box):
    self.shape = shape
  # Make info display window (rowSize, colSize, rowStart, colStart)
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    self.otherWindow = None
    
    # Set the background and text color of the display
    if curses.has_colors():
      curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
      self.win.bkgd(' ', curses.color_pair(1))
    
    
  # If you tell it what window to go back to, it will retain
  # the cursor focus.
  def setMainWindow(self, window):
    self.otherWindow = window
  
# Updates text on the info display window
# window is the infoDisplay window
# otherWindow is the one you want to keep the cursor on
  def updateInfo(self, text):
    #maxLen = self.colSize * self.rowSize
    #if len(text) >= maxLen:
    #  text = text[0:maxLen-1]
    self.win.erase()
    try:
      self.win.addstr(0, 0, text) # Display text
    except curses.error:
      pass # Python Curses does not provide the functions necessary to ensure the cursor is not updated beyond the width of the window (https://stackoverflow.com/a/54412404/16386050) 
    self.win.refresh()
    if self.otherWindow:
      self.otherWindow.refresh()
      




#Thread generating and playing audio
class AudioPlayer:
  def __init__(self, tArgs):
    self.tArgs = tArgs
    self.index = 0
    self.paused = False
    self.graph = None
    self.isGraphEnabled = None
    #self.enableGraph()

  # A simple iterator that calls func from start to end over step.
  # Sort of like Python range(), but can work with any number, including floats
  # Returns 0 if there was an exception evaluating the function (hence "maybe")
  class maybeCalcIterator(object):
    def __init__(self, start, end, step, func):
      self.start, self.end, self.step, self.func, self.curr = start, end, step, func, start
    def __iter__(self):
      return self
    def __next__(self):
      if(self.curr > self.end):
        raise StopIteration()
      x, self.curr = self.curr, self.curr + self.step
      try:
        return self.func(x)
      except Exception as e:
        return 0

  def enableGraph(self):
    with threading.Lock():
      self.isGraphEnabled = True
  
  def disableGraph(self):
    with threading.Lock():
      self.isGraphEnabled = False

  # It periodically will check if the graph should be enabled to make it so the graph won't be enabled from another thread. This is terrible code.
  def updateGraphState(self):
    if self.isGraphEnabled == None:
      pass
    elif self.isGraphEnabled == True:
      self.graphOn()
    elif self.isGraphEnabled == False:
      self.graphOff()
    self.isGraphEnabled = None

  def graphOn(self):
    plt.ion()
    plt.ylim([-1,1])
    #X = [x for x in self.calcIterator(self.tArgs.start, self.tArgs.end, self.tArgs.step), lambda x: x]
    audioFunc = self.getAudioFunc()
    if not audioFunc:
      audioFunc = lambda x: 0 # If compiling an audio function failed, make a function that always returns 0
    X = [x for x in self.maybeCalcIterator(self.tArgs.start, self.tArgs.start+self.tArgs.step * (self.tArgs.frameSize-1), self.tArgs.step, lambda x: x)]
    Y = [0.0] * self.tArgs.frameSize #[x for x in self.maybeCalcIterator(self.tArgs.start, self.tArgs.start+self.tArgs.step * self.tArgs.frameSize, self.tArgs.step, audioFunc)]
    self.graph = plt.plot(X, Y)[0] #plt.plot([x for x in self.calcIterator(self.tArgs.start, self.tArgs.start+self.tArgs.step * 10000, self.tArgs.step, self.exp_as_func)])[0]

  # TODO: Why doesn't it actually close?
  def graphOff(self):
    plt.close('all')
    self.graph = None
    #gc.collect(2)
    

  # NOTE: Not used for now...
  #def drawGraph(self, curr, start, end, step, exp_as_func):
  #  data = [x for x in self.maybeCountingIterator(10000, exp_as_func, curr, step, start, end)]
  #  self.graph.set_ydata([x for x in self.maybeCalcIterator(start, start+step * 10000, step, exp_as_func)])
  #  plt.draw()
  #  plt.pause(0.01) 

  

  def play(self):
    self.audioThread(self.tArgs,)
  
  # Set this to True to pause
  def setPaused(self, paused):
    self.paused = paused

  def getAudioFunc(self):
    try: # Don't error-out on an empty text box
      if(self.tArgs.expression):
        exp_as_func = eval('lambda x: ' + self.tArgs.expression, self.tArgs.functionTable)
        return exp_as_func
      #exp_as_func = eval('lambda x: ' + tArgs.expression, tArgs.functionTable)
    except SyntaxError:
      #sys.stderr.write("Error creating generator function: Expression has not yet been set, or other SyntaxError\n")
      pass

  # Calculates n results from func, starting at curr, and optionally looping to start it reaches more than end, and returns 0 for any errors that occur.
  class maybeCountingIterator(object):
    def __init__(self, n, func, curr, step, start = None, end = None):
      #self.start, self.end, self.step, self.func, self.curr = start, end, step, func, start
      self.n, self.func, self.curr, self.step, self.start, self.end = n, func, curr, step, start, end
      self.count = 0
      if start == None: # Loop to curr if end is provided, but start is none for some reason
        self.start = curr
    def __iter__(self):
      return self
    def __next__(self):
      if(self.count > self.n):
        raise StopIteration()
      self.count = self.count + 1
      x, self.curr = self.curr, self.curr + self.step
      if self.end is not None and self.curr > self.end: # Loop around to start if end is provided
        self.curr = self.start
      try:
        return self.func(x)
      except Exception as e:
        return 0

  def audioThread(self, tArgs):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels = tArgs.channels,
                    rate = tArgs.rate,
                    output = True,
                    frames_per_buffer = tArgs.frameSize)
    
    value = 0.0
    oldTime = 0
    frameCount = 0
    
    #Thanks to https://stackoverflow.com/a/12467755 by Ohad
    #for a much more efficient eval() for performance improvements
    #exp_as_func = eval('lambda x: ' + tArgs.expression)
    exp_as_func = self.getAudioFunc()
    
    try: #Make breaking out of the infinate loop possible by a keyboard interrupt
      #exp_as_func = eval('lambda x: ' + tArgs.expression)
      while tArgs.shutdown is False: # Main loop
        result = []
        #if abs(tArgs.end - tArgs.start < tArgs.frameSize) or tArgs.end <= tArgs.start:
        #  sys.stdout.write("Error: Invalid range!")
        #  tArgs.shutdown = True
        #  break
        if tArgs.shutdown:
          break
          
        #for self.index in range(tArgs.start, tArgs.end, 1):
        while self.index >= tArgs.start and self.index <= tArgs.end: # Loop over range
          try:
            if tArgs.expression:
              value = exp_as_func(self.index) # This is where the waveform values are actually calculated
              # for an input value, substituted for x
            else:
              value = 0
          except:
            pass
            
          
          if not(isinstance(value, float)):
            value = 0
          
          # Limit to prevent going over the system-set volume level
          if value > 1:
            value = 1
          elif value < -1:
            value = -1
            
          result.append(value)
         # frameCount = frameCount + 1
          if frameCount >= tArgs.frameSize:
            frameCount = 0
            if tArgs.shutdown == True:
              sys.exit()

            #if self.graph is not None: # Graph?
              #self.drawGraph(self.index,tArgs.end+self.tArgs.step*10000, self.tArgs.step, (exp_as_func if exp_as_func is not None else lambda x: 0))
              #self.drawGraph(self.index, tArgs.start, tArgs.end, tArgs.step, (exp_as_func if exp_as_func is not None else lambda x: 0))
            try: # Set the new expression for next time
              exp_as_func = eval('lambda x: ' + tArgs.expression, tArgs.functionTable)
            except:
              pass
            chunk = np.array(result)

            try: # This try statement may not be needed if better verification is made beforehand...
              stream.write( chunk.astype(np.float32).tobytes() )
            except TypeError:
              time.sleep(0.5)
            self.updateGraphState() # Have this thread manage the graph
            if self.graph is not None and len(result) == self.tArgs.frameSize: # Draw the graph if enabled # TODO: len(result) should ALWAYS be equal to frameSize...
              self.graph.set_ydata(result)
              plt.draw()
              plt.pause(0.01) 
            result = []
          
          if tArgs.shutdown:
            break
          
          while self.paused == True or (tArgs.expression == "0" and tArgs.shutdown == False):
            # Wait to become unpaused
            time.sleep(0.2)
            if tArgs.shutdown == True:
              self.paused = False
          
          self.index = self.index + tArgs.step
          frameCount = frameCount + 1
        if tArgs.step < 0: # Allow going backwards
          self.index = self.tArgs.end
        else:
          self.index = self.tArgs.start
          
    except (KeyboardInterrupt, SystemExit):
      pass
    finally:
      tArgs.shutdown = True
      stream.stop_stream()
      stream.close()
      p.terminate()
      sys.stderr.write("Audio player shut down.\n")
        
      
    






def main(argv = None):
  
  parser = argparse.ArgumentParser(description="A cross-platform script for creating and playing sound waves through mathematical expressions", prog="calcwave")
  
  parser.add_argument('expression', type = str,
                      help = "The expression, in terms of x. When using the command line, it may help to surround it in single quotes. If --gui is specified, use 0 for this parimeter")
  parser.add_argument("-s", "--start", type = int, default = -100000,
                      help = "The lower range of x to start from.")
  parser.add_argument("-e", "--end", type = int, default = 100000,
                      help = "The upper range of x to end at.")
  parser.add_argument("-o", "--export", type = str, default = "", nargs = '?',
                      help = "Export to specified file as wav. File extension is automatically added.")
  parser.add_argument("--channels", type = int, default = 1,
                      help = "The number of audio channels to use")
  parser.add_argument("--rate", type = int, default = 44100,
                      help = "The audio rate to use")
  parser.add_argument("--buffer", type = int, default = 1024,
                      help = "The audio buffer frame size to use. This is the length of the list of floats, not the memory it will take.")
  parser.add_argument("--gui", default = False, action = "store_true",
                      help = "Start with the GUI")
  
  if argv is None:
    argv = sys.argv
  
  # The class that is passed to other threads and holds
  # information about how to play sound and act
  tArgs = threadArgs()
  
  isGuiArgument = False
  isExportArgument = False
  isExpressionProvided = False
  args = None
  if len(sys.argv) > 1:
    args = parser.parse_args() #Parse arguments
    #Set variables
    tArgs.expression = args.expression
    tArgs.start = args.start
    tArgs.end = args.end
    tArgs.channels = args.channels
    tArgs.rate = args.rate
    tArgs.frameSize = args.buffer
    
    isExportArgument = args.export != ""
    isGuiArgument = args.gui
    isExpressionProvided = args.expression != ""
    
  # Initialize AudioPlayer
  audioClass = AudioPlayer(tArgs)
  
  window = None
  scr = None
  menu = None
  
  #The program may be started either in GUI mode or CLI mode. Test for GUI mode vvv
  if len(sys.argv) == 1 or isGuiArgument or not(isExportArgument or isExpressionProvided):
    #If no arguments are supplied - GUI
    if isExpressionProvided:
      tArgs.expression = args.expression
    sys.stderr.write("Starting GUI mode\n")
    tArgs.isGUI = True
    
    scr = curses.initscr()
    curses.curs_set(0) # Disable the actual cursor
    rows, cols = scr.getmaxyx()
    
    if curses.has_colors():
      curses.start_color()
      curses.use_default_colors()

  try:
    # rowSize, colSize, rowStart, colStart
    menu = UIManager(Box(rowSize = 2, colSize = cols, rowStart = rows - 5, colStart = 0), tArgs, audioClass)
    #Start the GUI input thread
    window = WindowManager(tArgs, scr, menu)
  except Exception as e: # Catch any exception so that the state of the terminal can be restored correctly
    curses.curs_set(1) # Re-enable the actual cursor
    curses.echo()
    curses.nocbreak()
    scr.keypad(False)
    curses.endwin()
    print("Exception caught in UI. Restored terminal state.", file=sys.stderr)
    raise e
   
    
    tArgs.expression = "0" # Default value
  else:
    tArgs.isGUI = False
    
    
  
  if len(sys.argv) >= 1 and isExportArgument:
    exportAudio(args.export, tArgs, None, None) # CLI operation
  else:
    # Keep in mind that menu will be None when it is not in GUI mode...
    audioClass.play() # Hangs on this until closed in GUI operation.
    curses.curs_set(1) # Re-enable the actual cursor
  
  
  # When that exits
  tArgs.shutdown = True
  
  if window:
    window.thread.join()
    

if __name__ == "__main__":
  main()
  
