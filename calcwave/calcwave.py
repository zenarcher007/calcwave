#!/usr/bin/env python3
version = "1.6.4"


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
import random
import argparse
import threading
import re
import time
import wave
import gc
#import calcwave
from calcwave import mathextensions
#import calcwave.mathextensions
import json
import itertools
import time
import numpy as np
import pyaudio

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
  #import matplotlib.pylab as plt
  #import matplotlib
  #from matplotlib import pyplot as plt
  import matplotlib.pyplot as plt
  
# You will only need curses if using gui mode
if not sys.argv.count('--cli'):
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


#self.start = -100000
#self.end = 100000
#self.channels = 1
#self.rate = 44100
#self.frameSize = 1024
#self.isGUI = False
#self.shutdown = False
#self.step = 1. # How much to increment x
#self.functionTable = self.getFunctionTable()
#self.evaluator = Evaluator("main=0")
#self.lock = threading.Lock()

# Checks every "delay" seconds, and saves to a file if flag has been set
class SaveTimer:
  def __init__(self, delay, filepath, Config):
    self.delay = delay
    self.filepath = filepath
    self.pendingsave = False
    self.global_config = Config
    self.thread = None
    self.timerstate = False
    self.titleWidget = None # To display whether your code is saved

  def __del__(self):
    self.notify()
    self.timerOff()
    if self.thread:
      self.thread.join()

  def setTitleWidget(self, titleWidget):
    self.titleWidget = titleWidget

  def clearSaveMsg(self):
    if self.titleWidget:
        self.titleWidget.setMessage("")
        self.titleWidget.refresh()

  # Notifies the timer that a change has been made
  def notify(self):
    if self.pendingsave == False:
      self.pendingsave = True
      self.clearSaveMsg()

  def timerThread(self):
    while self.global_config.shutdown == False and self.timerstate == True:
      time.sleep(self.delay)
      if self.pendingsave:
        self.pendingsave = False
        self.save()
    self.thread = None

  def timerOn(self):
    if self.timerstate == False:
      self.timerstate = True
      self.thread = threading.Thread(target=self.timerThread, daemon=True)
      self.thread.start()

  def timerOff(self):
    self.timerstate = False

  def getFilepath(self):
    return self.filepath
  
  # Saves to the file
  def save(self):
    dict = {"start": self.global_config.start,
            "end": self.global_config.end,
            "step": self.global_config.step,
            "rate": self.global_config.rate,
            "channels": self.global_config.channels,
            "frameSize": self.global_config.frameSize,
            "expr": self.global_config.evaluator.getText()
            }
    
    id = str(random.randint(1000,9999))
    fil = self.filepath
    with open(fil + id, 'w') as file:
      json.dump(dict, file)
    os.rename(fil + id, fil) # Replace original file with new "temp" file
    if self.titleWidget:
      self.titleWidget.setMessage("(Saved Last Compilation)")
      self.titleWidget.refresh()

                                     
  



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
    with global_display_lock:
      self.win.refresh()

  def restoreLastHighlight(self):
    self.win.chgat(self.oldHighlightPos.row, self.oldHighlightPos.col, 1, curses.A_NORMAL)

  # Hides the cursor temporarily, until it is moved.
  def hideCursor(self):
    self.cursorHidden = True
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_NORMAL) # Un-highlight new position
    with global_display_lock:
      self.win.refresh()

  def showCursor(self):
    self.cursorHidden = False
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight cursor position
    with global_display_lock:
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
    if self.cursorHidden == False:
      self.win.chgat(self.oldCursorPos.row, self.oldCursorPos.col, 1, curses.A_NORMAL) # Unhighlight old position
      self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight new position
    self.oldCursorPos = self.cursorPos
    self.win.chgat(self.cursorPos.row, self.cursorPos.col, 1, curses.A_REVERSE) # Highlight new position
    with global_display_lock:
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
    self.refresh()

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
    self.refresh()
  
  # Sets the cursor at the end, and puts the scroll window in view.
  def goToEnd(self):
    self.setCursorPos( self.cursorPos.withCol(min(len(self.text), self.shape.colSize-1)))
    self.scrollOffset = max(0, len(self.text) - self.shape.colSize)
    self.refresh

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
      self.refresh()
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
    self.refresh()
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
        self.refresh()
    self.refresh()


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
    with global_display_lock:
      self.win.refresh()
      
      



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
    self.refresh() # Refresh optimization will not otherwise see it, as it is switching lines
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
    with global_display_lock:
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
    with global_display_lock:
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
    with global_display_lock:
      self.win.refresh()
##################################################################



#To hold data that is passed to multiple running threads
# Code should be able to check against the values here and gracefully handle unset variables.
# Modification of variables should be generally avoided.
class Config:
  def __init__(self):
    #self.expression = ""
    self.start = -100000
    self.end = 100000
    self.channels = 1
    self.rate = 44100
    self.frameSize = 1024
    self.isGUI = False
    self.shutdown = False
    self.step = 1. # How much to increment x
    #self.functionTable = self.getFunctionTable()
    self.evaluator = None
    self.SaveTimer = None
    self.updateAudio = False # Audio interrupt to read new data
    self.output_fd = None # File descriptor for pipe of info display; check if this is set before using
    self.AUDIO_MAP = {}

    self.lock = threading.Lock()
    global global_display_lock 
    global_display_lock = threading.Lock()

    
  
class MemoryClassCompiler:
  def __init__(self):
    self._instances = {}
    self.functionTable = {}
    self._func_count = {}
    self._reSET = set() # A set used for converting the reset() operation for resetting function call counts into O(1) time


  def run(self, fn_name, class_initializer, *args, **kwargs):
    # Handle pseudo-resetting all func_count values to 0
    if not fn_name in self._reSET:
      self._func_count[fn_name] = 0
      self._reSET.add(fn_name)
    
    # Get list of instances of the memory class (equal to the number of times the function is called in user code)
    ilist = self._instances[fn_name]
    
    # Create new instance of memory class for each greater number of calls of the function in user code
    count = self._func_count[fn_name]
    if count > len(ilist)-1:
      self._instances[fn_name].append(class_initializer())
    clazz = self._instances[fn_name][count]
    self._func_count[fn_name] += 1 # Increment to next instance
    
    # Call memory class's evaluate()
    return clazz.evaluate(*args, **kwargs)
  
  # Pseudo-resets the function call counts in O(1) time. Call this before a new evaluation takes place.
  def reset(self):
    self._reSET = set()

  # Adds mappings from each desired function name to a function that calls from a list of instances of each respective class
  def compile(self):
    for memoryClass in mathextensions.getMemoryClasses():
      fn_name = memoryClass.__callname__()
      # https://stackoverflow.com/a/21054384
      fncreate = lambda fn, mc: lambda *args, **kwargs: self.run(fn, mc, *args, **kwargs)
      self.functionTable[fn_name] = fncreate(fn_name, memoryClass)
      self._func_count[fn_name] = 0
      self._instances[fn_name] = []

  def getFunctionTable(self):
    return self.functionTable


# Accepts CalcWave text input
# Parses and evaluates Python syntax (with any extra features)
# Compiles the given code ("text") upon construction, and throws any errors it produces
class Evaluator:
  # Lightweight constructor that then immediately compiles text - a new instance is created for every version of the expression
  def __init__(self, text, symbolTable = vars(math), channels = 1, audio_map = {}):
    self.text = text
    self.symbolTable = symbolTable.copy()

    self.audio_map = audio_map
    #symbolTable['log'] = None
    self.symbolTable['x'] = 0
    self.symbolTable["out"] = np.zeros(channels, dtype=np.float32)
    self.symbolTable["load"] = self.load # For syntactical loading of audio files
    #if audio_map != []:
    #  for arr in audio_map.values():
    #    arr.setflags(write = False)
    #  self.symbolTable.update(audio_map)
    self.audio_aliases = set() # A smaller set to hold aliases already detected via "in" for performance reasons

    self.symbolTable.update(mathextensions.getFunctionTable())

    self.memory_class = MemoryClassCompiler()
    self.memory_class.compile()
    self.symbolTable.update(self.memory_class.getFunctionTable())

    self.prog = compile(text, '<string>', 'exec', optimize=2)

  ### A custom Evaluator function that loads and adds audio to the audio_map. This will be available globally in the syntax
  def load(self, path, alias):
    if not alias in self.audio_aliases:
      self.audio_aliases.add(alias)
      audioarr = None
      if not alias in self.audio_map.keys():      
        if not os.path.exists(path):
          raise FileNotFoundError('load "{alias}": path "{path}" does not exist.')
        audioarr = self.loadAudioFile(path)
        audioarr.setflags(write = False)
        self.audio_map[alias] = audioarr
      else:
        audioarr = self.audio_map[alias]
      self.symbolTable[alias] = audioarr

  
  def loadAudioFile(self, path: str):
    try:
      # TODO: stop auto normalization??? https://github.com/bastibe/python-soundfile/issues/20
      import soundfile as sf
    except ImportError as e:
      print("Error importing pydub module needed for loading audio. You may install this using \"python3 -m pip install soundfile\". Note: the ffmpeg library will be needed for this.")
      raise e
    #filename, file_extension = os.path.splitext(path)
    #a = pydub.AudioSegment.from_file(path)
    #arr = a.get_array_of_samples()

    # Note: samplerate is not used for now... This could cause issues...
    arr, samplerate = sf.read(path, always_2d = True)
    audioarr = arr
    #channels = arr.shape[1]
    #audioarr = arr.reshape(channels, -1).astype(float)
    
    #print(arr.shape)
    #arr = arr.reshape( (arr.shape[1], arr.shape[0]) )
    #nparr = np.array(arr)
    #print(audioarr.dtype, arr.dtype)
    #print(np.mean(audioarr))
    #time.sleep(2)
    if not np.issubdtype(arr.dtype, np.floating):
      audioarr /= np.iinfo(arr.dtype).max # Scale between -1 and 1 as float
      #print("ISNOTFLOATING", arr.dtype, np.iinfo(arr.dtype).max, arr, audioarr)
      #time.sleep(2)

    return audioarr
      

  # Retrieves the current expression contents as a string
  def getText(self):
    return self.text

  # Gets the last logged value, or the last computed value if none was specified
  # Note: 'log' is Deprecated
  def getLog(self):
    return str(self.symbolTable['out'])
    #log = self.symbolTable['log']
    #if log is None:
    #  return str(self.symbolTable['main'])
    #else:
    #  return str(self.symbolTable['log'])

  # Evaluates the expression code with the global value x, and returns the result (stored in var "main"). Throws any error thrown by exec.
  def evaluate(self, x):
    #self.symbolTable["out"] = np.zeros(2, dtype=np.float32)
    self.symbolTable['x'] = x # Add x to the internal symbol table
    exec(self.prog, self.symbolTable, self.symbolTable) # Run compiled program with scope of symbolTable
    self.memory_class.reset() # This resets the count of function calls for memistic functions to 0 (as each's data is mapped to its call number)
    return self.symbolTable["out"] # Return result


# Handles GUI
class WindowManager:
  def __init__(self, global_config, scr, initialExpr, audioClass, exportDtype = int):
    self.global_config = global_config
    self.scr = scr
    self.oldStdout = None

    self.initCursesSettings()
  
    rows, cols = self.scr.getmaxyx()
    #Initialize text editor
    self.editor = TextEditor(Box(rowSize = rows - 8, colSize = cols, rowStart = 1, colStart = 0))
  
    #Initialize info display window
    self.infoDisplay = InfoDisplay(Box(rowSize = 4, colSize = cols, rowStart = rows - 4, colStart = 0))
    self.global_config.output_fd = self.infoDisplay.getWriteFD()

    self.menu = UIManager(Box(rowSize = 2, colSize = cols, rowStart = rows - 7, colStart = 0), global_config, audioClass, self.infoDisplay, exportDtype = exportDtype)
    
    self.thread = threading.Thread(target=self.windowThread, args=(global_config, scr, self.menu, audioClass), daemon=True)
    self.thread.start()
    self.editor.setText(initialExpr)
  
  def initCursesSettings(self):
    self.scr.keypad(True)
    self.scr.nodelay(True)
    curses.noecho()

  def getInfoDisplay(self):
    return self.infoDisplay

  # Controls whether to redirect all stdout to the infoDisplay
  def setRedirectOutput(self, redirect: bool):
    if redirect == True and self.oldStdout == None:
      newWrite = self.infoDisplay.getWriteFD()
      if not newWrite:
        return False
      self.oldStdout = sys.stdout
      sys.stdout = os.fdopen(newWrite, 'w')
    elif self.oldStdout != None:
      oldfd = sys.stdout
      sys.stdout = self.oldStdout
      oldfd.close()
      self.oldStdout = None
    return True

  def windowThread(self, global_config, scr, menu, audioClass):
    self.scr.getch()
    self.scr.nodelay(0) # Turn delay mode on, such that curses will now wait for new keypresses on calls to getch()
    # Draw graphics
    self.menu.refreshAll()
    self.editor.refresh()
    self.menu.title.refresh()

    self.focused = self.editor
    try:
      while self.global_config.shutdown is False:
        ch = self.scr.getch()

        if ch == 27 and self.focused != self.menu: # Escape key
          self.infoDisplay.updateInfo("ESC recieved. Shutting down...")
          with self.global_config.lock:
            self.global_config.shutdown = True
          break
        isArrowKey = (ch == curses.KEY_UP or ch == curses.KEY_DOWN or ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT)
        successful = self.focused.type(ch)
        if successful and self.focused == self.editor:
          p = self.editor.getPos()
          self.infoDisplay.updateInfo(f"Line: {p.row+1}, Col: {p.col}, Scroll: {self.editor.scrollOffset}")
          if isArrowKey:
            continue
          self.global_config.SaveTimer.clearSaveMsg()
          # Display cursor position
          text = self.editor.getText()
          try:
            evaluator = Evaluator(text, audio_map = global_config.AUDIO_MAP, channels = global_config.channels) # Compile on-screen code
            with global_config.lock:
              global_config.evaluator = evaluator # Install newly compiled code
              self.global_config.SaveTimer.notify()
              self.global_config.updateAudio = True
              if audioClass.isPausedOnException():
                audioClass.setPaused(False)
          except Exception as e:
            # Display exceptions to the user
            self.infoDisplay.updateInfo(f"[Compile error] {e.__class__.__name__}: {e.msg}\nAt line {e.lineno} col {e.offset}: {e.text}")
            self.editor.highlightRange(Point(row = e.lineno, col = e.offset), Point(row = e.end_lineno, col = e.end_offset))
          continue
        
        # Switch between menu and inputPad with the arrow keys
        if self.menu.isEditing(): continue # Don't remove focus from the menu while it's editing
        if ch == curses.KEY_UP and not self.menu.isEditing(): 
          self.focused.onUnfocus()
          self.focused = self.editor
          self.focused.onFocus()
        elif ch == curses.KEY_DOWN:
          self.focused.onUnfocus()
          self.focused = self.menu
          self.focused.onFocus()
          
    except (KeyboardInterrupt, SystemExit):
      pass
    finally:
      sys.stderr.write("Shutting down GUI...\n")
      #self.stopCursesSettings(self.scr)
      self.global_config.shutdown = True
      
  # Changes curses settings back in order to restore terminal state
  # Call this when you are done with this object!
  def stopCursesSettings(self, scr):
    curses.echo()
    curses.nocbreak()
    scr.keypad(False)






# The basic neccesities for the UIManager to accept your widget as a menu item
class BasicMenuItem:
  def __init__(self, shape: Box):
    self.shape = shape
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    #self.hovering = False
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
    with global_display_lock:
      self.win.refresh()

  # Standard hooks to hide and show the cursor, if your widget has one.
  def hideCursor(self):
    pass

  def showCursor(self):
    pass

  def displayText(self, text):
    self.win.erase()
    self.win.addstr(0, 0, text)
    with global_display_lock:
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
    with global_display_lock:
      self.win.refresh()
    return "Hover Message"
  
  # Called when UIManager tells the cursor to leave your item
  def onHoverLeave(self):
    self.hovering = False
    for row in range(0, self.shape.rowSize):
      self.win.chgat(0, row, self.shape.colSize, curses.A_NORMAL)
    curses.use_default_colors()
    with global_display_lock:
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
class exportButton(LineEditor, BasicMenuItem):
  def __init__(self, shape: Box, global_config, progressBar, infoDisplay, dtype):
    super().__init__(shape)
    self.global_config = global_config
    self.infoPad = infoDisplay
    self.progressBar = progressBar
    self.setText("Export Audio")
    self.hideCursor()
    self.dtype = dtype


  def getDisplayName(self):
    return "Export Button"
  
  def updateValue(self, text):
    self.setText(text)
    
  def onBeginEdit(self):
      self.setText("") # Clear and allow you to enter the filename
      return "Please enter filename, and press enter to save. Any existing file will be overwritten."
  
  def onHoverEnter(self):
    self.hideCursor()
    super().onHoverEnter()
    return "Press enter to save a recording as a WAV file."

  def onHoverLeave(self):
    self.showCursor()
    self.setText("Export Audio")
    super().onHoverLeave()
    
  # Override type, make it check filenames live
  def type(self, ch):
    super().type(ch)
    name = self.getText()
    name = os.path.expanduser(name)
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
    name = os.path.expanduser(name)
    actionMessage = "File saved in same directory!"
    if name == '':
      self.setText("Export Audio")
      return "Cancelled."
    self.setText("Export Audio")
    path = ''
    if '/' in name:
      fullPath = name + ".wav"
      parDir = '/'.join(fullPath.split('/')[0:-1]) # Remove ending '/'
      if not os.path.isdir(parDir):
        actionMsg = "Cannot export audio: invalid path \"" + fullPath + "\""
        self.setText("Export Audio")
        return
    else:
      path = os.getcwd()
      fullPath = path + "/" + name + ".wav"
    actionMsg = "Saving file as " + fullPath
    
    #with self.lock:
    if(self.infoPad):
      self.infoPad.updateInfo("Writing...")
    
    # Do in a separate thread?
    thread = threading.Thread(target=exportAudio, args=(fullPath, self.global_config, self.progressBar, self.infoPad, self.dtype), daemon = True)
    thread.start()
    #exportAudio(fullPath)
    return actionMsg
    
  # Accepts a generator, and returns chunk arrays of size n until depleted, courtesy as a convienence of ChatGPT
def chunker(generator, n):
  while True:
    chunk = list(itertools.islice(generator, n))
    if not chunk:
      break
    yield chunk

def npchunker(generator, n, arrsize, dtype = None):
  while True:
    # Note that audio length will be clipped to multiples of arrsize
    chunk = None
    try:
      chunk = np.fromiter(generator, count = n, dtype = (dtype, arrsize)) # Requires numpy version >=1.23
    except ValueError:
      break
    yield chunk

def npflatchunker(generator, n, arrsize, dtype = None):
  #chunk = np.zeros((n, arrsize), dtype = dtype)
  chunk = np.zeros(n*arrsize, dtype = dtype)
  while True:
    # Note that audio length will be clipped to multiples of arrsize
    
    i=0
    for arr in itertools.islice(generator, n):
      chunk[i:i+len(arr)] = arr[:]
      i = i + len(arr)
    if i == 0:
      break
    
    #chunk = None
    #try:
    #  chunk = np.fromiter(generator, count = n, dtype = (dtype, arrsize)) # Requires numpy version >=1.23
    #except ValueError:
    #  break

    # This is probably more efficient than you think - a calculation is made anyways every time the generator is called
    #i=0
    #for arr in itertools.islice(generator, n):
    #  chunk[i] = arr
    #  i = i + 1
    #if i is 0:
    #  break
    yield chunk

def exportAudio(fullPath, global_config, progressBar, infoPad, dtype = float):
  def exHandler(e):
    print(f"Exception at x={str(i)}: {type(e).__name__ }: {str(e)}") # Use print system

  start, end, step = (0,0,0)
  with global_config.lock:
    start, end, step, evaluator = (global_config.start, global_config.end, global_config.step, global_config.evaluator)
  
  # If datatype is a float, remove clipping to preserve data depth (clipping is still used in live mode)
  minVal, maxVal = (-1, 1)
  if dtype == float:
    minVal, maxVal = (None, None)

  iter = maybeCalcIterator(start, end, step, evaluator.evaluate, minVal = minVal, maxVal = maxVal, exceptionHandler=exHandler)

  # Logic for progress display
  i = 0
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
  

  with open(fullPath, 'wb') as file:
    totalsize = int((end - start) / step)
    file.write(get_wav_header(totalsize, global_config.rate, dtype, global_config.channels))
    
    j = 0
    # Write wave file
    oldtime = time.time()
    for chunk in npchunker(iter, global_config.frameSize, global_config.channels, dtype=np.float32):
      chunkold = chunk
      chunk = np.ravel(chunk)
      assert np.may_share_memory(chunkold, chunk) # Ensures that the ravel did not make a deep copy of chunk for performance reasons
      if dtype == float:
        file.write(struct.pack('<%df' % len(chunk), *chunk))
      elif dtype == int:
        file.write(struct.pack('<%dh' % len(chunk), *(int(c*32767) for c in chunk) ) )
      timenow = time.time()
      if timenow > oldtime+0.25:
        oldtime = timenow
        progtext = "Writing (" + str(int(abs(i-progressStart)/(abs(end-start))*100)) + "%)..."
        if infoPad:
          infoPad.updateInfo(progtext)
        else:
          print('\r' + progtext, file=sys.stderr, end = '')
      i = i + int(len(chunk)/global_config.channels)
      j = j + 1
  progtext = "Exported as " + fullPath
  if infoPad:
    infoPad.updateInfo("Exported as " + fullPath)
  else:
    print('\n' + progtext, file=sys.stderr)



# Adapted from https://stackoverflow.com/a/15650213
def get_wav_header(totalsize, sample_rate, dtype, channels):
  byte_count = (totalsize) * (4 if dtype == float else 2) * channels # 32-bit floats
  # write the header
  wav_file = struct.pack('<ccccIccccccccIHHIIHHccccI',
    b'R', b'I', b'F', b'F',
    byte_count + 44 - 8,  # header size
    b'W', b'A', b'V', b'E', b'f', b'm', b't', b' ',
    16,  # size of 'fmt ' header
    3 if dtype == float else 1,  # format 3 = floating-point PCM
    channels,  # channels
    sample_rate,  # samples / second
    sample_rate * (4 if dtype == float else 2),  # bytes / second
    4 if dtype == float else 2,  # block alignment
    32 if dtype == float else 16,  # bits / sample
    b'd', b'a', b't', b'a', byte_count)
  return wav_file
  





# A menu item in the format "name=..." that types like an InputPad
# this allows setting variables, etc in a typing-based way
class NamedMenuSetting(LineEditor, BasicMenuItem): # Extend the InputPad and BasicMenuItem classes
  def __init__(self, shape: Box, name):
    super().__init__(shape)
    self.name = name
    self.setText(name + "=")
    self.lastValue = "0"
    self.hideCursor()
    #self.refresh()
  
  def updateValue(self, value):
    self.setText(self.name + "=" + str(value))
    self.lastValue = value
  
  # Updates the last value first in order to leave the cursor in the right position
  def onHoverLeave(self):
    super().onHoverLeave()
    self.updateValue(self.lastValue)
    self.showCursor()
    self.goToBeginning()
    #self.refresh()
  
  def onHoverEnter(self):
    self.hideCursor()
    return super().onHoverEnter()
  
  # Override BasicMenuItem's onBeginEdit()
  def onBeginEdit(self):
    ret = super().onBeginEdit()
    self.goToEnd()
    return ret

  def getValue(self):
    index = len(str(self.name + "="))
    text = self.getText()
    result = text[index:]
    return result
  
  # Override InputPad goLeft() method
  def goLeft(self):
    # Don't allow going to the left of the '='
    ##if self.curCol > len(str(self.name + "=")):
    if self.getPos().col > len(str(self.name + "=")):
      return super().goLeft()
    else:
      return False
  
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

# A special case of a NamedMenuSetting that sets the start range in global_config
class startRangeMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, global_config):
    super().__init__(shape, name, "int")
    self.lock = threading.Lock()
    self.global_config = global_config

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
      if self.global_config.AUDIO_MAP is not None and value < 0:
        actionMsg = "Start range cannot be less than starting bound of AUDIO_IN. Value updated to 0"
        self.updateValue(0)
      elif value > self.global_config.end: # Don't allow crossing start / end ranges
        actionMsg = "Start range cannot be greater than end range!"
        self.updateValue(self.global_config.start)
      else:
        actionMsg = "Start range changed to " + str(value) + "."
        self.lastValue = str(value)
        with self.lock:
          self.global_config.start = value
      return actionMsg


# A special case of a NamedMenuSetting that sets the end range in global_config
class endRangeMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, global_config):
    super().__init__(shape, name, "int")
    self.lock = threading.Lock()
    self.global_config = global_config
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
      #if self.global_config.AUDIO_MAP is not None and value >= len(self.global_config.AUDIO_MAP):
      #  actionMsg = "End range cannot be greater than length of AUDIO_IN. Value updated to maximum length, " + str(len(self.global_config.AUDIO_MAP))
      #  self.updateValue(len(self.global_config.AUDIO_MAP))
      if value < self.global_config.start: # Don't allow crossing start / end ranges
        actionMsg = "End range cannot be less than start range!"
        self.updateValue(self.global_config.end)
      else:
        actionMsg = "End range changed to " + str(value) + "."
        self.lastValue = str(value)
        with self.lock:
          self.global_config.end = value

      return actionMsg
      

  # A special case of a NamedMenuSetting that sets the step amount in global_config
class stepMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, global_config):
    super().__init__(shape, name, "float")
    self.global_config = global_config

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
      with self.global_config.lock:
        self.global_config.step = value
    return "Step amount changed to " + str(value) + ". Note: baud rate is " + str(self.global_config.rate) + "hz."
    
    
    
    
    

# A ProgressBar that displays the current position of AudioPlayer's range
class ProgressBar(BasicMenuItem):
  def __init__(self, shape: Box, audioClass, global_config, infoDisplay):
    super().__init__(shape)
    self.infoDisplay = infoDisplay
    self.lock = threading.Lock()
    self.audioClass = audioClass
    self.progressBarEnabled = True
    self.global_config = global_config
    self.isEditing = False
    
    # Start progress bar thread
    self.progressThread = threading.Thread(target=self.progressThread, args=(global_config, audioClass), daemon=True)
    self.progressThread.start()

  def getDisplayName(self):
    return "Progress Bar"

  def onBeginEdit(self):
    self.isEditing = True
    super().onBeginEdit()
    return self.getCtrlsMsg()

  def onHoverEnter(self):
    super().onHoverEnter()
    return "Press enter to pause, seek, and change progress bar settings."
    
  def onHoverLeave(self):
    super().onHoverLeave()
    
  def type(self, ch):
    #with self.lock:
    # Handle left/right stepping
    
    blockWidth = self.global_config.step
    if ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT:
      range = abs(self.global_config.end - self.global_config.start)
      blockWidth = int(range / self.shape.colSize)
      # Use bigger increments if not paused
    if self.audioClass.isPaused() == False:
        blockWidth = blockWidth * 5
      
    if ch == 32: # Space
      with self.audioClass.getLock():
        self.audioClass.setPaused(not(self.audioClass.isPaused())) # This function includes a lock, and must be done separately
      self.infoDisplay.updateInfo(("Paused" if self.audioClass.isPaused() else "Unpaused") + " audio player!\n" + self.getCtrlsMsg())
      return
    elif chr(ch) == 'v' or chr(ch) == 'V':
      self.toggleVisibility()
      return

    with self.audioClass.getLock():
      index = self.audioClass.index
      if ch == curses.KEY_LEFT or ch == curses.KEY_SLEFT:
        index = index - blockWidth
      elif ch == curses.KEY_RIGHT or ch == curses.KEY_SRIGHT:
        index = index + blockWidth
      if index < self.global_config.start: # Limit between acceptable range
        index = self.global_config.start
      elif index > self.global_config.end:
        index = self.global_config.end
      # Write back to audio player
      self.audioClass.index = index
      self.audioClass.nextStart = index
      self.audioClass.paused = True
      self.global_config.updateAudio = True
      if self.audioClass.isPaused():
        self.debugIndex(index) # Show debugging info about current index
      self.updateIndex(index, self.global_config.start, self.global_config.end)
    
  
  # Defines action to do when activated
  def doAction(self):
    self.isEditing = False # TODO: Possibly not used
    return "Done editing progress bar."
  
  # Returns a string explaining how to use the progress bar widget
  def getCtrlsMsg(self):
    pauseStr = "pause" if not self.audioClass.isPaused() else "unpause"
    return f"Space: {pauseStr}, left/right arrows: seek (hold shift for fine seek), v: toggle visibility, enter / esc: exit progress bar"
  
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
    with global_display_lock:
      self.win.refresh()
    
  def progressThread(self, global_config, audioClass):
    index = 0
    while self.global_config.shutdown == False:
    # Update menu index display
      time.sleep(0.25)
      #with self.lock:
      #if self.global_config.shutdown == False and self.progressBarEnabled and pause == False:
      #  with self.lock:
      #    index = audioClass.index
      #  self.updateIndex(index, global_config.start, global_config.end)
      index = audioClass.index # relaxed read # TODO: How to actually use relaxed atomics in Python?
      if self.global_config.shutdown == False and self.progressBarEnabled and not self.audioClass.isPaused():
        self.updateIndex(index, global_config.start, global_config.end)
      
      # Display blank while not playing anything
      if self.global_config.evaluator == None and self.progressBarEnabled == True: # TODO: global_config.evaluator is probably never going to be None. How to check if it's a placeholder evaluator?
        self.toggleVisibility()
        while self.global_config.evaluator == None:
          time.sleep(0.2)
        self.toggleVisibility()

  def debugIndex(self, i):
    evl = self.global_config.evaluator
    controlsMsg = self.getCtrlsMsg()
    try:
      evl.evaluate(i)
      log = evl.getLog()
      self.infoDisplay.updateInfo("x=" + str(i) + ", result = " + log + "\n" + controlsMsg)
    except Exception as e:
      self.infoDisplay.updateInfo("Exception at x=" + str(i) + ": " + type(e).__name__ + ": " + str(e))

  # Displays the current x-value as a progress bar
  def updateIndex(self, i, start, end):  
    if self.progressBarEnabled == False: # TODO: Move this check to its callers, not the actual function?
      return
    maxLen = self.shape.colSize * self.shape.rowSize
    value = int(np.interp(i, [start,end], [0, maxLen - 2]))
    
    text = "{" + ''.join([char*value for char in '░' ])
    
    # Lock thread - for what?
    #self.lock.acquire(blocking=True, timeout=1)
    self.win.erase()
    self.win.addstr(0, 0, text) # Display text
    self.win.addch(0, maxLen - 2, '}')
    with global_display_lock:
      self.win.refresh()
    # Unlock thread
    #self.lock.release()
    
class graphButtonMenuItem(BasicMenuItem):
  isGraphThreadRunning = False
  def __init__(self, shape: Box, global_config, audioClass):
    super().__init__(shape)
    self.global_config = global_config
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

  # Currently disabled ; plt.plot doesn't work in a thread...
  def graphThreadRunner(self, global_config, audioClass):
    plt.ion()
    plt.show()
    while(self.isGraphThreadRunning):
      exp_as_func = audioClass.getAudioFunc() # Update expression
      if exp_as_func is not None:
        curr = audioClass.index # Get current position
        plt.plot([x for x in self.calcIterator(curr, curr+10000, global_config.step, exp_as_func)])
        plt.draw()
      time.sleep(1)
    plt.close()

  def graphOn(self):
    self.audioClass.enableGraph()
    #with threading.Lock(): # This should at least flush the changes... Right?
    #  self.isGraphThreadRunning = True    
    #self.graphThread = threading.Thread(target=self.graphThreadRunner, args=(self.global_config, self.audioClass), daemon=True)
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
    #actionMsg = str([x for x in self.calcIterator(curr, curr+10000, self.global_config.step, exp_as_func)])
    #plt.plot([x for x in self.calcIterator(curr, curr+10000, self.global_config.step, exp_as_func)])
    #plt.show()
    #plt.draw()
    return actionMsg



# Just a title display at the top of the screen
class TitleWindow:
  def __init__(self, shape: Box):
    self.shape = shape
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    self.message = ""
    self.refresh()
    
  # Draws the title and onHoverEnters it
  def refresh(self):
    self.win.clear()
    self.win.addstr("Calcwave v" + version + self.message)
    self.win.chgat(0, 0, self.shape.colSize, curses.A_REVERSE)
    with global_display_lock:
      curses.use_default_colors()
      self.win.refresh()
    
  # Use custom text
  def customTitle(self, text):
    self.win.clear()
    self.win.addstr(text + self.message)
    self.win.chgat(0, 0, self.shape.colSize, curses.A_REVERSE)
    with global_display_lock:
      curses.use_default_colors()
      self.win.refresh()

  # Appends a mandantory message to the end of the title
  def setMessage(self, text):
    if text == "":
      self.message = ""
    else:
      self.message = " " + text
    
    
# A class that controls and handles interactions with menus and other UI.
# Drive UIManager's type(ch) function with keyboard characters
# to interact with it when needed.
class UIManager:
  def __init__(self, shape: Box, global_config, audioClass, infoDisplay, exportDtype = int):
    self.infoDisplay = infoDisplay
    self.global_config = global_config
    
    self.settingPads = []
    self.boxWidth = int(shape.colSize / 3)
    
    self.title = TitleWindow(Box(rowSize = 1, colSize = shape.colSize, rowStart = 0, colStart = 0))
    self.lock = threading.Lock()
    
    # Create windows and store them in the self.settingPads list.
    
    # Graph Button
    graphBtn = graphButtonMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart, colStart = shape.colStart), global_config, audioClass)

    # Start range
    startWin = startRangeMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart+1, colStart = shape.colStart), "beg", global_config)
    startWin.updateValue(global_config.start)
    
    # Progress bar
    progressWin = ProgressBar(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart+1, colStart = shape.colStart + self.boxWidth), audioClass, global_config, self.infoDisplay)
    
    # End range
    endWin = endRangeMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart+1, colStart = shape.colStart + self.boxWidth * 2), "end", global_config)
    endWin.updateValue(global_config.end)
    
    # Step value
    stepWin = stepMenuItem(Box(rowSize = int(shape.rowSize/2), colSize = self.boxWidth, rowStart = shape.rowStart + 2, colStart = shape.colStart + self.boxWidth * 2), "step", global_config)
    stepWin.updateValue(global_config.step)
    
    # This currently takes up the width of the screen. Change the value from colSize to resize it
    saveWin = exportButton(Box(rowSize = int(shape.rowSize/2), colSize = int(shape.colSize*(2/3)-1), rowStart = shape.rowStart+2, colStart = shape.colStart), global_config, progressWin, self.infoDisplay, exportDtype)

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
  
  # Returns true if this is busy editing a widget
  def isEditing(self):
    return self.editing

  def onFocus(self):
    self.refreshTitleMessage()
    self.infoDisplay.updateInfo(self.focusedWindow.onHoverEnter())

  def onUnfocus(self):
    self.focusedWindow.onHoverLeave()
    self.focusedWindow.hideCursor()
    self.infoDisplay.updateInfo("")
    self.title.refresh()
  
  # Calls refresh() for the InputPads for the start and end values,
  # and updates the title window
  # TODO: This is a crime...
  def refreshAll(self): # TODO: Wait... Don't I give each object a global_config anyways??? This is... despicable...
    self.settingPads[0].updateValue(0)
    self.settingPads[1].updateValue(self.global_config.start)
    self.settingPads[3].updateValue(self.global_config.end)
    self.settingPads[4].updateValue("Export Audio")
    self.settingPads[5].updateValue(self.global_config.step)
    for win in self.settingPads:
      win.refresh()
      win.hideCursor()
  
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
        self.infoDisplay.updateInfo("Cancelled editing!")
        self.focusedWindow.onHoverEnter()
        self.refreshTitleMessage()
        return
      else: # Not editing? Interpret as shut down
        with self.lock:
          self.infoDisplay.updateInfo("ESC recieved. Shutting down...")
          self.global_config.shutdown = True

    # Switch between menu items
    if self.editing == False and (ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT):
      self.focusedWindow.onHoverLeave()
      self.focusedWindow.hideCursor()
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
      #self.setMainWindow(self.focusedWindow)
      self.infoDisplay.updateInfo(msg)
      return
      
    #self.setMainWindow(self.focusedWindow)
    
    # Function macro to end editing ; TODO: Make this not horribly inline inside this function?
    def endEdit():
      self.editing = False
      # Run action specified in class
      actionMsg = self.focusedWindow.doAction()
      self.focusedWindow.onHoverEnter()
      self.infoDisplay.updateInfo(actionMsg)
      self.refreshTitleMessage()
      self.global_config.SaveTimer.notify()
      self.global_config.updateAudio = True
    
    # Function macro to begin edting
    def beginEdit():
      self.editing = True
      self.focusedWindow.onHoverLeave() # Item exits hover mode while editing
      self.refreshTitleMessage()
      tooltipMsg = self.focusedWindow.onBeginEdit()
      self.infoDisplay.updateInfo(tooltipMsg)
      if self.focusedWindow.isOneshot(): # If onBeginEdit() returns True, end edit immediately after.
        endEdit()
      self.focusedWindow.refresh()
    
    # Toggle editing on and off and handle highlighting (with onHoverEnter)
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
    self._r, self._w = os.pipe()
    self.shutdown = False
    self._has_new_message = False
    self.message_cv = threading.Condition()
    self.lock = threading.Lock()

    # Set the background and text color of the display
    if curses.has_colors():
      curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
      self.win.bkgd(' ', curses.color_pair(1))

    # For now, lines written will be deleted off the screen when scrolling,
    # until perhaps a selection / scrolling mechanism is implemented.
    self.win.scrollok(True)
    self.thread = threading.Thread(target=self.writeThread, args = (self._r, self.win, self.message_cv), daemon=True)
    self.thread.start()
    self.thread2 = threading.Thread(target=self.refreshThread, args = (self.win, self.message_cv), daemon=True)
    self.thread2.start()
  


  def __del__(self):
    self.shutdown = True
    os.write(self._w, b"Shutting Down...")
    #with open(self._w) as stream:
    #  print("Shutting Down...", file = stream) # This is really to wake up the reader
    self.thread.join()
    os.close(self._w)
    self._has_new_message = True
    with self.message_cv:
      self.message_cv.notify()
    self.thread2.join()
    
    
  # If you tell it what window to go back to, it will retain
  # the cursor focus.
  def setMainWindow(self, window):
    self.otherWindow = window

  def getWriteFD(self):
    return self._w # Must be opened with os.fdopen(... , 'w')
  
  def refreshThread(self, win, message_cv):
    while self.shutdown == False:
      time.sleep(0.1) # Rate limiting to prevent UI lock up and improve performance
      with message_cv:
        message_cv.wait()
      if self._has_new_message:
        with self.lock:
          self._has_new_message = False
          with global_display_lock:
            win.refresh()

  def writeThread(self, reader, win, message_cv):
    #win = curses.newwin(self.shape.rowSize, self.shape.colSize, self.shape.rowStart, self.shape.colStart)
    win.scrollok(True)
    try:
      with os.fdopen(reader, 'r') as r:
        while self.shutdown == False:
          for line in r:
            if self.shutdown: break
            with self.lock:
              self.win.scrollok(True)
              for i in range(0, len(line), self.shape.colSize):
                win.scroll(1)
                self.win.addstr(self.shape.rowSize - 1, 0, line[max(0, i - self.shape.colSize) : -1])
              self._has_new_message = True
            with message_cv:
              message_cv.notify()
            #win.refresh()
            
    except Exception as e:
      print("EXCEPTION IN INFODISPLAY WRITER: " + str(e), file = sys.stderr)

    
  
# Updates text on the info display window
# window is the infoDisplay window
# otherWindow is the one you want to keep the cursor on
  def updateInfo(self, text):
    #maxLen = self.colSize * self.rowSize
    #if len(text) >= maxLen:
    #  text = text[0:maxLen-1]
    self.win.erase()
    #text = text + "\n"
    #os.write(self._w, bytes(text.encode('UTF-8')))
    #return
    try:
      with self.lock:
        self.win.scrollok(False)
        self.win.addstr(0, 0, text) # Display text
        self.win.scrollok(True)
    except curses.error:
      pass # Python Curses does not provide the functions necessary to ensure the cursor is not updated beyond the width of the window (https://stackoverflow.com/a/54412404/16386050) 
    with global_display_lock:
      self.win.refresh()
    if self.otherWindow:
      self.otherWindow.refresh()
      

  # A simple iterator that calls func from start to end over step.
  # Sort of like Python range(), but can work with any number, including floats
  # Returns 0 if there was an exception evaluating the function (hence "maybe")
  # Modified to work with numpy arrays
class maybeCalcIterator(object):
  def __init__(self, start, end, step, func, minVal = None, maxVal = None, exceptionHandler = None, repeatOnException = False):
    self.start, self.end, self.step, self.func = start, end, step, func
    self.curr = end if step < 0 else start
    self.minVal, self.maxVal = minVal, maxVal
    self.exceptionHandler = lambda e: 0 if not exceptionHandler else exceptionHandler(e)
    self.repeatOnException = repeatOnException
    self.max_clip = False
    self.min_clip = False
  def __iter__(self):
    return self
  def get_clipping(self): # Returns whether clipping has occured since the last call of this function (min, max)
    minc, maxc = self.min_clip, self.max_clip
    self.min_clip, self.max_clip = (False, False)
    return minc, maxc
  def __next__(self):
    if(self.curr > self.end or self.curr < self.start):
      raise StopIteration()
    x, self.curr = self.curr, self.curr + self.step
    try:
      v = self.func(x)
      #v = np.array([max(-1,min(1,e)) for e in v])

      #clip_low = np.where(np.any(v < self.minVal, axis = 0))
      #self.min_clip = len(clip_low) > 0
      #v[clip_low] = self.minVal

      #clip_high = np.where(np.any(v > self.maxVal, axis = 0))
      #self.max_clip = len(clip_high) >0
      #v[clip_high] = self.maxVal
      
      # Clip
      # After trying multiple options, not involving numpy seemed to be the fastest?
      for i in range(len(v)):
        if self.minVal and v[i] < self.minVal:
          self.min_clip = True
          v[i] = self.minVal
        elif self.maxVal and v[i] > self.maxVal:
          self.max_clip = True
          v[i] = self.maxVal

      #if self.minVal and v < self.minVal:
      #  self.min_clip = True
      #  v = self.minVal
      #elif self.maxVal and v > self.maxVal:
      #  self.max_clip = True
      #  v = self.maxVal
      return v
    
    except Exception as e:
      #print(self.exceptionHandler)
      self.exceptionHandler(e)
      if self.repeatOnException: # Undo last step
        self.curr = self.curr - self.step
      return 0

#Thread generating and playing audio
class AudioPlayer:
  def __init__(self, global_config, info_update_fn = None):
    self.global_config = global_config
    self.info_update_fn = info_update_fn
    self.index = 0
    self.paused = False
    self.graph = None
    self.isGraphEnabled = None
    self.is_paused_on_error = False
    #self.enableGraph()
    #self.lock = threading.Lock()
    self.nextStart = None

  def getLock(self):
    return self.global_config.lock
    #return self.lock
  

  def enableGraph(self):
    self.isGraphEnabled = True

  def set_info_update_fn(self, info_update):
    self.info_update_fn = info_update

  def pauseOnException(self, e):
    msg = f"[paused] Runtime Exception at x={str(self.index)}:\n{type(e).__name__}: {e}"
    if self.info_update_fn:
      self.info_update_fn(msg)
    else:
      print(msg)
    self.setPaused(True)
    self.is_paused_on_error = True
    # TODO: Make it display the error message in the display. This function will be disabled until this is implemented.
  
  def disableGraph(self):
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
    plt.close('all')
    plt.ylim([-1, 1])
    X = list(range(self.global_config.frameSize))
    Y = [0.0] * self.global_config.frameSize
    fig, ax = plt.subplots()

    # Create one line per channel, stored in a list
    lines = [ax.plot(X, Y)[0] for _ in range(self.global_config.channels)]
    for i in range(len(lines)):
      lines[i].set_label("Channel " + str(i))
    fig.legend()
    plt.close(1) # Note that this does not fix the problem! I am not sure why two figures are created.
    self.graph = (fig, ax, lines)


  # TODO: Why doesn't it actually close on Mac? - this may be a bug with MPL
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
    self.audioThread(self.global_config,)
  
  def isPausedOnException(self):
    return self.is_paused_on_error

  # Note that this doesn't use a lock by default for performance. However, you can manually retrive one using autoPlayer.getLock()
  def isPaused(self):
    return self.paused

  # Set this to True to pause. Note: A lock is not used autmatically. Please manually aquire the lock for this class if needed.
  def setPaused(self, paused):
    self.paused = paused
    self.is_paused_on_error = False

  #def getAudioFunc(self):
  #  try: # Don't error-out on an empty text box
  #    if(self.global_config.expression):
  #      exp_as_func = eval('lambda x: ' + self.global_config.expression, self.global_config.functionTable)
  #      return exp_as_func
  #    #exp_as_func = eval('lambda x: ' + global_config.expression, global_config.functionTable)
  #  except SyntaxError:
  #    #sys.stderr.write("Error creating generator function: Expression has not yet been set, or other SyntaxError\n")
  #    pass

  # Calculates n results from func, starting at curr, and optionally looping to start it reaches more than end, and returns 0 for any errors that occur.
  #class maybeCountingIterator(object):
  #  def __init__(self, n, func, curr, step, start = None, end = None):
  #    #self.start, self.end, self.step, self.func, self.curr = start, end, step, func, start
  #    self.n, self.func, self.curr, self.step, self.start, self.end = n, func, curr, step, start, end
  #    self.count = 0
  #    if start == None: # Loop to curr if end is provided, but start is none for some reason
  #      self.start = curr
  #  def __iter__(self):
  #    return self
  #  def __next__(self):
  #    if(self.count > self.n):
  #      raise StopIteration()
  #    self.count = self.count + 1
  #    x, self.curr = self.curr, self.curr + self.step
  #    if self.end is not None and self.curr > self.end: # Loop around to start if end is provided
  #      self.curr = self.start
  #    try:
  #      return self.func(x)
  #    except Exception as e:
  #      return 0


  def audioThread(self, global_config): # The config is needed to dynamically change start/end
    try:
      p = pyaudio.PyAudio()

      stream = p.open(format=pyaudio.paFloat32,
                      channels = global_config.channels,
                      rate = global_config.rate,
                      output = True,
                      frames_per_buffer = global_config.frameSize)
      
      
      frameSize = global_config.frameSize
      start, end, step, evaluator = (0,0,0, None)
      with global_config.lock:
        start, end, step, evaluator = (global_config.start, global_config.end, global_config.step, global_config.evaluator)
      graphtimer = time.time()
      while global_config.shutdown == False:

        while self.paused == True:
          paused = self.paused # Basically relaxed read
          # Wait to become unpaused
          time.sleep(0.2)
          if global_config.shutdown == True:
            self.setPaused(False)

        # Refresh data
        with global_config.lock:
          start, end, step, evaluator = (global_config.start, global_config.end, global_config.step, global_config.evaluator)
          if self.nextStart != None:
            if step < 0:
              end = self.nextStart
            else:
              start = self.nextStart
            self.nextStart = None

        iter = maybeCalcIterator(start, end, step, evaluator.evaluate, minVal = -1, maxVal = 1, exceptionHandler = self.pauseOnException, repeatOnException = True)
        for chunk in npchunker(iter, global_config.frameSize, global_config.channels, dtype=np.float32):
          chunkold = chunk
          chunk = np.ravel(chunk)
          assert np.may_share_memory(chunkold, chunk) # Ensures that the ravel did not make a deep copy of chunk for performance reasons

          r = struct.pack('<%df' % len(chunk), *chunk)
          stream.write( r )
          self.updateGraphState() # Have this thread manage the graph
          cont = False
          self.index = iter.curr
          with self.getLock():
            if global_config.updateAudio or global_config.shutdown or self.paused: # Time to read new data
              global_config.updateAudio = False
              cont = True
              self.nextStart = iter.curr # Pick up where you left off this time
              break
          
          
          ### Update the graph
          if self.graph is not None:
            timenow = time.time()
            if int(len(chunk) / global_config.channels) == frameSize and timenow > graphtimer + 0.1:
              fig, ax, lines = self.graph
              ax.set_ylim(bottom=-1, top=1)
              graphtimer = timenow
              
              xd = list(range( int(self.index), int(self.index + global_config.frameSize) ))
              ax.set_xlim(int(self.index), int(self.index + global_config.frameSize) )

              # Update each line with the corresponding channel data
              for i in range(global_config.channels):
                lines[i].set_ydata(chunkold[:, i])
                lines[i].set_xdata(xd)
                #lines[i].set_xdata(list(range(int(self.index), int(self.index + global_config.frameSize))))
              
              min_clip, max_clip = iter.get_clipping()

              # Ensure to remove any extra lines (other than channel plots and clipping lines)
              while len(ax.lines) > global_config.channels:
                ax.lines[global_config.channels].remove()
              
              if min_clip:
                ax.plot([xd[0], xd[-1]], [-1, -1], linewidth=3, color='red')
              
              if max_clip:
                ax.plot([xd[0], xd[-1]], [1, 1], linewidth=3, color='red')
              
              plt.draw()
              plt.pause(0.001)
    
    

        if cont: continue

        

    except (KeyboardInterrupt, SystemExit):
      pass
    finally:
      global_config.shutdown = True
      if stream is not None:
        stream.stop_stream()
        stream.close()
      p.terminate()
      sys.stderr.write("Audio player shut down.\n")
        


    



# The runner class for CalcWave
class CalcWave:
  # Constructor - basic setup based on given arguments
  def __init__(self, argv):
    global_config = Config()
    self.global_config = global_config

    # Parses command line arguments to the program
    args = self.parse_args(argv)

    # Fills the global_config object based on all the applicable information as passed as arguments
    self.global_config.start = args.beg
    self.global_config.end = args.end
    self.global_config.rate = args.rate
    self.global_config.frameSize = args.buffer
    self.args = args

    # Check basic argument requirements, syntax, and path validity
    #print("Running checks...  ", end = '', file = sys.stderr)
    self.priorProjectExists = os.path.exists(args.file)
    if args.file and not self.priorProjectExists:
      print(f'\nCreating new project file "{args.file}"', file = sys.stderr)
    
    # If the file.wav already exists, ask the user if they want to overwrite it, exit the program if not
    if args.export:
      if os.path.exists(args.export):
        if not self._confirm_input('\nFile "{args.export}" already exists. Would you like to overwrite it?'):
          sys.exit(0)
    #print("Done")

    self.channels_is_default = False
    self.buffer_is_default = False
    self.global_config.channels = self.args.channels
    self.global_config.frameSize = self.args.buffer
    if self.priorProjectExists:
      self.loadProject(self.args.file) # Populates or updates config with additional project data

    # Runs further program setup, makes modifications to self.global_config based on arguments and self.args.
    # This function may exit the program here.
    self._setup(argv)
  
  def _setup(self, argv):
    if self.global_config.evaluator is None:
      self.global_config.evaluator = Evaluator(self.get_default_prog(), channels = self.global_config.channels, audio_map = self.global_config.AUDIO_MAP)
    ### There is guaranteed to be a self.global_config.evaluator past this point ###

  
  # Thanks to https://stackoverflow.com/a/3042378/16386050
  def _confirm_input(self, prompt):
    if self.args.yes == True:
      return True
    
    sys.stderr.write(prompt + "\n> ")

    yes = {'yes','y', 'ye', ''}
    no = {'no','n'}
    
    choice = raw_input().lower()
    while True:
      if choice in yes:
        return True
      elif choice in no:
        return False
      else:
        sys.stderr.write("Please respond with 'yes' or 'no'")


  def parse_args(self, argv = None):
    if argv[0] == sys.argv[0]:
      argv.pop(0)
    parser = argparse.ArgumentParser(description="A cross-platform script for creating and playing sound waves through mathematical expressions", prog="calcwave")
    
    parser.add_argument('file', type = str, help = "Project file path (*.cw) to load, created if it does not already exist. This will be autosaved - copy the project file as desired for backups")
    # --expr is Deprecated
    #parser.add_argument('-x', '--expr', type = str, default = "0",
    #                    help = "A function in terms of x to preload into the editor (it may help to surround this in single quotes). Default is 0 in gui mode.")
    parser.add_argument("-b", "--beg", type = int, default = -100000,
                        help = "The lower range of x to start from. No effect if loading an existing project.")
    parser.add_argument("-e", "--end", type = int, default = 100000,
                        help = "The upper range of x to end at. No effect if loading an existing project.")
    parser.add_argument("-c", "--channels", type = int, default = 0,
                        help = "The number of audio channels to use (default 1). Values for each can be set using out[channelno] = value. If specified, the value will be updated when loading an existing project.")
    parser.add_argument("-o", "--export", type = str, default = None, nargs = '?',
                        help = "Generate, and export to the specified file in WAVE format.")
    parser.add_argument("-y", "--yes", type = bool, default = False, nargs = '?',
                        help = "Automatically confirms Y/n prompts")
    #parser.add_argument("--channels", type = int, default = 1,
    #                    help = "The number of audio channels to use")
    parser.add_argument("--int", action="store_true", default=False, help = "By default, audio will be exported as float32 wav. Specify this to export audio as integer wav.")
    parser.add_argument("--rate", type = int, default = 44100,
                        help = "The audio rate to use")
    parser.add_argument("--buffer", type = int, default = 0,
                        help = "The audio buffer frame size to use. This is the length of chunks of floats, not the memory it will use. If specified, the value will be updated when loading an existing project.")
    #parser.add_argument("--cli", default = False, action = "store_true",
    #                    help = "Use cli mode - will export generated audio to the provided file path as wav audio, without launching the curses UI")

    if argv is None:
      argv = sys.argv
    
    args = parser.parse_args(argv) #Parse arguments
    if args.channels == 0:
      self.channels_is_default = True
      args.channels = pyaudio.PyAudio().get_default_output_device_info()['maxOutputChannels']
    if args.buffer == 0:
      self.buffer_is_default = True
      args.buffer = 1024
    
    splext = os.path.splitext(args.file)
    if len(splext) == 2 and splext[1] != ".cw":
      print('Warning: Project file does not have extension ".cw". This is a convention. Continuing anyways...', file = sys.stderr)

    return args


  # Loads the CalcWave project from the file, updating self.global_config.
  def loadProject(self, file):
    #t = Config()
    dict = None
    with open(self.args.file, 'r') as f:
      dict = json.load(f)
    self.global_config.start = dict['start']
    self.global_config.end = dict['end']
    self.global_config.step = dict['step']
    self.global_config.rate = dict['rate']

    # If you have changed the number of channels from the default, override what was configured in the project
    if self.channels_is_default == True:
      self.global_config.channels = dict['channels']
    if self.buffer_is_default == True:
      self.global_config.frameSize = dict['frameSize']
    self.global_config.SaveTimer = self
    
    self.global_config.evaluator = Evaluator(dict['expr'], audio_map = self.global_config.AUDIO_MAP, channels = self.global_config.channels)
    return self.global_config
  

    #return audioarr

  # Reading the class's current configuration, returns whether an expression other than the default has been set in the config.
  # Returns True if no Evaluator has been configured in the global_config
  def is_expr_default(self):
    return self.global_config.evaluator is None or not self.global_config.evaluator.getText() == self.get_default_prog()
    # or (os.path.isfile(self.args.file)
  


  # Based on the class's current configuration,
  # Returns the default program, optionally configuring it for audio input defaults
  # based on whether there are audio input variables to be passed in. Note: "expr" is synonymous to "prog"
  # TODO: Update the default example based on the audio files provided!!
  def get_default_prog(self) -> str:
    return "out[:] = 0"

  # Initializes an AudioPlayer (evaluator and stream player) object based on the global_config object currently configured in this class
  def create_audio_player(self):
    return AudioPlayer(self.global_config)
    
  # Creates a SaveTimer object using the class's current configuration, turns it on, and returns it.
  # SaveTimer also manages the loading of files, as well as saving.
  # This will also:
  # * Populate global_config.AUDIO_MAP if audio files are to be loaded.
  # * 
  def create_save_timer(self, filepath):
    saveTimer = SaveTimer(2, filepath, self.global_config) # Save every 2 seconds if changes are present
    self.global_config.SaveTimer = saveTimer # this exists in the config so it can be notified of changes
    saveTimer.timerOn() # Start autosave timer
    return saveTimer
    

  #def cli_export_audio(self):
  
  # Configures curses. Returns the curses screen object
  def init_curses(self):
    scr = curses.initscr()
    curses.curs_set(0) # Disable the actual cursor
    rows, cols = scr.getmaxyx()
      
    if curses.has_colors():
      curses.start_color()
      curses.use_default_colors()
    return scr
  
  def teardown_curses(self, scr):
    curses.curs_set(1) # Re-enable the actual cursor
    curses.echo()
    curses.nocbreak()
    scr.keypad(False)
    curses.endwin()


  # Runs the program with the current configuration
  def main(self):
    # Set the CWD to the project file directory
    # I will hope this works correctly on Windows
    apath = os.path.abspath(self.args.file)
    pardirlist = apath.split('/')[:-1]
    os.chdir('/'.join(pardirlist))

    # If in cli mode, simply try to import the available program, write out an audio file, and exit.
    if self.args.export:
      if not self.global_config.evaluator:
        print("Error: Incorrect _setup: global_config.evaluator is not set")
        exit(1)
      exportAudio(self.args.export, self.global_config, None, None, dtype = int if self.args.int else float)
      sys.exit(0)
    
    saveTimer = self.create_save_timer(apath)
    audioPlayer = self.create_audio_player()

    window = None
    scr = self.init_curses()
    exc = None
    try:
      #Start the GUI input thread
      window = WindowManager(self.global_config, scr, self.global_config.evaluator.getText(), audioPlayer, exportDtype = int if self.args.int else float)
      window.setRedirectOutput(True) # Redirect all output to the InfoDisplay
      saveTimer.setTitleWidget(window.menu.title)
      audioPlayer.set_info_update_fn(window.getInfoDisplay().updateInfo)
      audioPlayer.play() # The program hangs on this call until it is ended.
    except Exception as e: # Catch any exception so that the state of the terminal can be restored correctly
      print("Exception caught in UI. Restored terminal state.", file=sys.stderr)
      exc = e # Hold that thought...
    finally:
      saveTimer.setTitleWidget(None)
      saveTimer.timerOff()
      saveTimer.save() # Save your current program

      if window != None:
        window.setRedirectOutput(False)
        #window.stopCursesSettings(scr)
      self.teardown_curses(scr)

      self.global_config.shutdown = True
      if window:
        window.thread.join()
  
      if exc:
        raise exc


def main(argv = None):
  CalcWave(argv).main()

if __name__ == "__main__":
  main()