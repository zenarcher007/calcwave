#!/usr/bin/env python3
version = "1.0.0b8"


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
from sys import platform
import struct
from math import *
import numpy as np
import pyaudio
import argparse
import threading
import time

# You will only need curses if using gui mode
if len(sys.argv) == 1 or sys.argv.count('--gui'):
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
    pass # Defaults seem to work fine on linux??
    #curses.KEY_BACKSPACE = 127
    #curses.KEY_DC = 126
    #curses.KEY_ENTER = 10
  elif "win" in pform:
    curses.KEY_BACKSPACE = 8
  else:
    sys.stderr.write("Warning: unsupported platform, \"" + str(pform) + "\"\n")
    # Use default curses key definitions; don't change them


# A special window that allows typing through characters provided in the type(ch)
# function. Note that despite its name, this is a curses window, not a pad.
# Also note that this is not a traditional text editor. Even though text may wrap to the next line,
# it doesn't allow new lines. It is more like a string editor.
class InputPad:
  #Constructor
  def __init__(self, ySize, xSize, yStart, xStart): # xStart, yStart, xSize, ySize):
    #Define window boundaries
    self.xSize = xSize
    self.ySize = ySize
    
    #These hold the actual x and y positions
    #of the bounds of the pad
    #Upper left corner
    self.boxX1 = xStart
    self.boxY1 = yStart
    #Lower right corner
    self.boxX2 = xStart + xSize - 1
    self.boxY2 = yStart + ySize - 1
    
    #Make window
    self.win = curses.newwin(ySize, xSize, yStart, xStart)
    
    self.curX = 0
    self.curY = 0
    
    self.oldHighlightX = 0
    self.oldHighlightY = 0
    self.highlighted = False
    
  #Moves the cursor relatively if space permits and updates the screen
  def curMove(self, relX, relY):
    if self.checkBounds(self.curX + relX, self.curY + relY):
      self.win.move(self.curY + relY, self.curX + relX)
      self.curY = self.curY + relY
      self.curX = self.curX + relX
  
  # Sets absolute cursor position
  def curPos(self, x, y):
    self.curX = x
    self.curY = y
    self.win.move(self.curY, self.curX)
  #def checkCharacter(self, x, y):
    
  # Calls a window refresh
  def refresh(self):
    self.win.refresh()
    
  # Moves the cursor right, wrapping to the next line if needed.
  def goRight(self):
    if self.curX + 1 > self.xSize-1:
      if self.checkBounds(0, self.curY + 1):
        self.curPos(0, self.curY + 1)
    else:
      self.curPos(self.curX + 1, self.curY)
    
  # Moves the cursor left, wrapping to the previous line if needed.
  def goLeft(self):
    if self.curX-1 < 0: ###self.boxX1:
      if self.checkBounds(self.curX, self.curY - 1):
        self.curPos(self.xSize-1, self.curY - 1)
    else:
      self.curPos(self.curX - 1, self.curY)
      
      
      #Returns True if the given actual position is valid in the pad
  def checkBounds(self, posX, posY):
    #print(self.curX, self.curY)
    #rows, cols = curses.initscr().getmaxyx()
    #print(self.posX, self.posY, "|", self.boxX1, self.boxY1, "|", self.boxX2, self.boxY2)
    ###if posY <= self.boxY2 and posX <= self.boxX2 and posY >= self.boxY1 and posX >= self.boxX1:
    if posY <= self.ySize-1 and posX <= self.xSize-1 and posY >= 0 and posX >= 0:
      return True
    else:
      return False
  
  # Checks if there is a free space to the right of this position
  def canGoRight(self, x, y):
    if self.checkBounds(self.curX + 1, self.curY):
      return True
    elif self.checkBounds(0, self.curY + 1):
      return True
    else:
      return False
  
  # Inserts a character at a position relative to the cursor, wrapping
  # text to the next line if needed
  def insert(self, pos, ch):
    oldPosX = self.curX
    oldPosY = self.curY
    x = self.curX
    text = ""
    for row in range(self.curY, self.ySize):  ###self.boxY2
      self.curPos(x, row)
      text = text + self.win.instr().decode("utf-8").replace(' ', '')
      x = 0 ### self.boxX1
    self.curPos(oldPosX, oldPosY)
    self.win.clrtobot()
    if pos > 0:
      for _ in range(pos):
        self.goRight()
    elif pos < 0:
      for _ in range(-pos):
        self.goLeft()
    if ch:
      if self.canGoRight(self.curX, self.curY):
        self.win.addstr(chr(ch) + text)
        #print(">" + text + "<")
    else:
      if self.canGoRight(self.curX, self.curY):
        self.win.addstr(text)
    self.curPos(oldPosX, oldPosY)
    
    
  # Gets all text and returns it as a string
  def getText(self):
    oldPosX = self.curX
    oldPosY = self.curY
    self.curPos(0, 0)
    text = ""
    for row in range(0, self.ySize):
      self.curPos(0, row)
      text = text + self.win.instr().decode("utf-8").replace(' ', '')
    self.curPos(oldPosX, oldPosY)
    return text
  
  # Checks if there is an empty slot at the given position
  def checkEmpty(self, x, y):
    if not self.checkBounds(x, y):
      return False
    elif self.win.inch(y, x) == 32:
      return True
    else:
      return False
      
  
  # Un-highlights the last highlighted character.
  def unHighlight(self):
    if self.highlighted == True:
      self.highlighted = False
      self.win.chgat(self.oldHighlightY, self.oldHighlightX, 1, curses.A_NORMAL)
      
  # Highlights a character at a position.
  def highlightChar(self, x, y):
    if curses.has_colors():
      self.highlighted = True
      oldCurX = self.curX
      oldCurY = self.curY
      
      self.unHighlight()
      self.highlighted = True
      self.oldHighlightX = x
      self.oldHighlightY = y
      
      # Add new color at position
      self.win.chgat(y, x, 1, curses.A_UNDERLINE)
      curses.use_default_colors()
      self.curPos(oldCurX, oldCurY)
      
  # Erases everything and sets the pad's text to text, with the cursor at the end
  def setText(self, text):
    maxLen = (self.xSize-1) * (self.ySize)-1
    if len(text) >= maxLen:
      text = text[0:maxLen-1]
    self.win.erase()
    self.win.addstr(0, 0, text) # Display text
    column = len(text)
    xWidth = self.xSize
    #self.curPos(self.boxX1+(column % xWidth), self.boxY1+int(column / xWidth))
    self.curPos(column % xWidth, int(column / xWidth))
    self.win.refresh()
                
  
  # Does the equivalent of a backspace. Includes workarounds for the many bugs it had...
  def backSpace(self):
    if not(self.curX == 0 and self.curY == 0): # Can't backspace if at the start
      if self.checkEmpty(self.curX + 1, self.curY) or self.curX == self.xSize-1:
        self.goLeft()
        self.win.delch()
        # A workaround for a bug where it wouldn't bring text on the next line
        # with it when it backspaced when the cursor was two places to the left of the right
        # side of the window
        if self.curX + 1 == self.xSize-1:
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
      if not(self.checkEmpty(self.curX, self.curY)):
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



# Handles GUI
def windowThread(tArgs, scr, menu):
  scr.keypad(True)
  scr.nodelay(True)
  curses.noecho()
  
  rows, cols = scr.getmaxyx()
  lock = threading.Lock()
  #Initialize input pad
  # ySize, xSize, yStart, xStart
  pad = InputPad(rows - 4, cols, 1, 0)
  
  # Tell the menu that this is the main window
  menu.setMainWindow(pad.win)
  
  #Initialize info display window
  infoPad = InfoDisplay(2, cols, rows - 2, 0)
  infoPad.setMainWindow(pad.win) # So it will know
  # what window to return the cursor to when it updates
  
  menu.setInfoDisplay(infoPad) # Give the menu an infoPad
  # so it can display its own information on it.
  
  # Set the background and text color of the infoPad
  if curses.has_colors():
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    infoPad.win.bkgd(' ', curses.color_pair(1))
    
  
  oldTime = 0
  menuFocus = False
  settingFocus = False
  startUp=True
  try:
    while tArgs.shutdown is False:
      #updateInfo(infoWin, pad, scr, "")
      ch = scr.getch()
     
      if ch == 27: # Escape key
        with lock:
          infoPad.updateInfo("ESC recieved. Shutting down...")
          tArgs.shutdown = True
        
        
      # Only runs once
      if startUp == True:
        startUp = False
        menu.refreshSides()
        pad.refresh()
        menu.title.refresh()
      
      if ch != -1 and ch != 27:
        
        # Switch between menu and inputPad with the arrow keys
        if ch == curses.KEY_UP:
          menuFocus = False
          settingFocus = True
          with lock:
            infoPad.setMainWindow(pad.win)
            menu.setMainWindow(pad.win)
            menu.getProgressBar().temporaryPause = False
            menu.focusedWindow.unhighlight()
          infoPad.updateInfo("")
          menu.title.refresh() # Good time to refresh the title?
        elif ch == curses.KEY_DOWN:
          menuFocus = True
          settingFocus = True
          menu.getProgressBar().temporaryPause = True
          menu.focusedWindow.highlight()
          menu.title.refresh()
        
        if menuFocus == True:
          menu.type(ch)
        elif settingFocus == False:
          # Type on the inputPad, verifying each time
          oldTime = time.time()
          infoPad.updateInfo("Wait...")
          with lock:
            # Don't update the progress bar while typing
            menu.getProgressBar().temporaryPause = True
          pad.type(ch)
        
          text = pad.getText()
          infoPad.updateInfo("Verifying...")
          try: # Verify expression
            eval('lambda x: ' + text)
            # TODO: better verification and improved "security"...
            with lock:
              tArgs.expression = text # Update the expression for the audioThread
            infoPad.updateInfo("Playing...")
          except (SyntaxError, NameError, TypeError) as e:
            # Highlight problem character
            if len(e.args) == 2 and len(text) > 0:
              error = str(e.args[1])
              parseString = error.split(',', 3)
              if len(parseString) >= 3:
                column = int(parseString[2]) - 11
                x = pad.boxX1+column
                y = pad.boxY1
                if x >= pad.boxX1 and y >= pad.boxY1:
                  xWidth = pad.boxX2 - pad.boxX1+1
                  pad.highlightChar(column % xWidth, int(column / xWidth))
              infoPad.updateInfo(str(e.args[0]))
            else:
              if len(text) > 0:
                error = str(e.args)
                infoPad.updateInfo(error)
              else:
                tArgs.expression = "0"
                infoPad.updateInfo("")
          with lock:
            menu.getProgressBar().temporaryPause = False
        settingFocus = False
      else:
        # Improve typing performance, but save CPU when not typing
        if time.time() - oldTime > 0.5:
          time.sleep(0.1)
        
  except (KeyboardInterrupt, SystemExit):
    pass
  finally:
    sys.stderr.write("Shutting down GUI...\n")
    stopCursesSettings(scr)
    tArgs.shutdown = True
    
# Changes curses settings back in order to restore terminal state
def stopCursesSettings(scr):
  curses.echo()
  curses.nocbreak()
  scr.keypad(False)
  curses.endwin()


# A menu item in the format "name=..." that types like an InputPad
# If this were Java, the methods in here would be an interface.
class NamedMenuSetting(InputPad): # Extend the InputPad class
  def __init__(self, ySize, xSize, yStart, xStart, name):
    super().__init__(ySize, xSize, yStart, xStart)
    self.name = name
    self.toolTip = name
    self.hoverMsg = name
    self.actionMsg = name
    self.setText(name + "=")
    self.lastValue = "0"
    self.refresh()
  
  def setToolTip(self, text):
    self.toolTip = text
  def setHoverMsg(self, text):
    self.hoverMsg = text
  def setActionMsg(self, text):
    self.actionMsg = text
  
  def setToolTip(self, text):
    self.toolTip = text
  
  def updateValue(self, value):
    self.setText(self.name + "=" + str(value))
    self.lastValue = value
    
  # All objects that ProgressBar has set to its main window must have a refresh() method
  def refresh(self):
    self.win.refresh()
  
  # Highlights / un-highlights entire window
  def highlight(self):
    for row in range(0, self.ySize):
      self.win.chgat(0, row, self.xSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
  
  def unhighlight(self):
    for row in range(0, self.ySize):
      self.win.chgat(0, row, self.xSize, curses.A_NORMAL)
    curses.use_default_colors()
    self.win.refresh()
  
  def getValue(self):
    index = len(str(self.name + "="))
    text = self.getText()
    result = text[index:]
    #self.lastValue = result # Updated in the classes extending this
    return result
  
  # Override InputPad goLeft() method
  def goLeft(self):
    # Don't allow going to the left of the '='
    if self.curX > len(str(self.name + "=")):
      super().goLeft()
  
  # Override InputPad type method
  def type(self, ch):
    super().type(ch)
    self.refresh()
    
# A special case of a NamedMenuSetting that sets the start range in tArgs
class startRangeMenuItem(NamedMenuSetting):
  def __init__(self, ySize, xSize, yStart, xStart, name, tArgs):
    super().__init__(ySize, xSize, yStart, xStart, name)
    self.lock = threading.Lock()
    self.tArgs = tArgs
  
  def doAction(self):
    value = str(self.getValue())
    if len(value) == 0:
      value = "0"
    try:
      value = int(value)
    except:
      self.actionMsg = "Error converting string \"" + value + "\" to int."
    else:
      self.actionMsg = "Start range changed to " + str(value) + "."
      self.lastValue = str(value)
      with self.lock:
        self.tArgs.start = value
      
  
  # Override NamedMenuSetting type method
  def type(self,ch):
    # Only allow these keys
    if (ch >= 48 and ch <= 57) or ch == curses.KEY_BACKSPACE or ch == 127 or ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT or ch == curses.KEY_DC or chr(ch) == '-':
    # or ch == 260 or ch == 261 or ch == 127 or ch == 45 or ch == 126:
      super().type(ch)
      
# A special case of a NamedMenuSetting that sets the end range in tArgs
class endRangeMenuItem(NamedMenuSetting):
  def __init__(self, ySize, xSize, yStart, xStart, name, tArgs):
    super().__init__(ySize, xSize, yStart, xStart, name)
    self.lock = threading.Lock()
    self.tArgs = tArgs
  
  def doAction(self):
    value = str(self.getValue())
    if len(value) == 0:
      value = "0"
    try:
      value = int(value)
    except:
      self.actionMsg = "Error converting string \"" + value + "\" to int."
    else:
      self.actionMsg = "End range changed to " + str(value) + "."
      self.lastValue = str(value)
      with self.lock:
        self.tArgs.end = value
      
  
  # Override NamedMenuSetting type method
  def type(self,ch):
    # Only allow these keys
    if (ch >= 48 and ch <= 57) or ch == curses.KEY_BACKSPACE or ch == 127 or ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT or ch == curses.KEY_DC or chr(ch) == '-':
      super().type(ch)
    
# A ProgressBar that displays the current position from a start to end value.
class ProgressBar:
  def __init__(self, ySize, xSize, yStart, xStart):
    self.ySize = ySize
    self.xSize = xSize
    self.yStart = yStart
    self.xStart = xStart
    self.win = curses.newwin(ySize, xSize, yStart, xStart)
    self.lock = threading.Lock()
    self.lastValue = 0
    self.progressBarEnabled = True
    self.temporaryPause = False
    self.lastStart = 0
    self.lastEnd = 0
    self.lastValue = 0 # All menu items must have lastValue
    self.toolTip = "Progress Bar"
    self.hoverMsg = "Progress Bar"
    self.actionMsg = "Progress Bar"
    
    
  def setToolTip(self, text):
    self.toolTip = text
  def setHoverMsg(self, text):
    self.hoverMsg = text
  def setActionMsg(self, text):
    self.actionMsg = text
    
  # All objects that ProgressBar has set to its main window must have a refresh() method
  def refresh(self):
    self.win.refresh()
    
  # All menu items must have updateValue method
  def updateValue(self, i):
    self.updateIndex(i, self.lastStart, self.lastEnd)
  
    
  # Highlights / un-highlights entire window
  def highlight(self):
    for row in range(0, self.ySize):
      self.win.chgat(0, row, self.xSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
  
  def unhighlight(self):
    for row in range(0, self.ySize):
      self.win.chgat(0, row, self.xSize, curses.A_NORMAL)
    curses.use_default_colors()
    self.win.refresh()
  
  def type(self, ch):
    pass
  
  def doAction(self):
    if self.progressBarEnabled == True:
      self.progressBarEnabled = False
      self.actionMsg = "Progress bar visibility turned off!"
      # Set progress bar text full of '-'
      text = ''.join([char*(self.xSize-1) for char in '-' ])
    else:
      self.progressBarEnabled = True
      text = ''.join([char*(self.xSize-1) for char in '░' ])
      self.actionMsg = "Progress bar visibility turned on!"
    self.win.erase()
    self.win.addstr(0, 0, text)
    self.win.refresh()
      
  
  # You can tell it what window to return the cursor
  # to after updating
  def setMainWindow(self, window):
    self.otherWindow = window
  
  # Displays the current x-value as a progress bar
  def updateIndex(self, i, start, end):
    if self.progressBarEnabled == False or self.temporaryPause:
      return
    maxLen = self.xSize * self.ySize
    value = int(np.interp(i, [start,end], [0, maxLen - 2]))
    if value == self.lastValue:
      return # Don't update again for performance improvements
    self.lastStart = start
    self.lastEnd = end
    self.lastValue = value
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
    

# Just a title display at the top of the screen
class TitleWindow:
  def __init__(self, ySize, xSize, yStart, xStart):
    self.xSize = xSize
    self.win = curses.newwin(ySize, xSize, yStart, xStart)
    self.refresh()
  
  # Draws the title and highlights it
  def refresh(self):
    self.win.addstr("Calcwave v" + version)
    self.win.chgat(0, 0, self.xSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    
    
# A class that controls and handles interactions with menus and other UI.
# Drive UIManager's type(ch) function with keyboard characters
# to interact with it when needed.
class UIManager:
  def __init__(self, ySize, xSize, yStart, xStart, tArgs):
    #self.ySize = ySize
    #self.xSize = xSize
    #self.yStart = yStart
    #self.xStart = xStart
    
    self.tArgs = tArgs
    self.infoPad = None
        
    self.settingPads = []
    self.boxWidth = int(xSize / 3)
    
    self.title = TitleWindow(1, xSize, 0, 0)
    
    # Create three windows, side-by-side, two of which are inputPads and are stored in
    # the settingPads list
    startWin = startRangeMenuItem(ySize, self.boxWidth, yStart, xStart, "beg", tArgs)
    startWin.setHoverMsg("Press enter to change the start range.")
    startWin.setToolTip("Setting start range... Press enter to apply.")
    startWin.setActionMsg("Start range changed!")
    startWin.updateValue(tArgs.start)
    
    progressWin = ProgressBar(ySize, self.boxWidth, yStart, xStart + self.boxWidth)
    progressWin.setHoverMsg("Press enter to change the progress bar settings")
    progressWin.setToolTip("Press enter to toggle the progress bar on or off.")
    progressWin.setActionMsg("Progress bar visibility toggled!")
    
    endWin = endRangeMenuItem(ySize, self.boxWidth, yStart, xStart + self.boxWidth * 2, "end", tArgs)
    endWin.setHoverMsg("Press enter to change the end range.")
    endWin.setToolTip("Setting end range... Press enter to apply.")
    endWin.setActionMsg("End range changed!")
    endWin.updateValue(tArgs.end)

    if curses.has_colors():
      curses.init_pair(2, curses.COLOR_RED, -1)
      progressWin.win.bkgd(' ', curses.color_pair(2))
    
    self.settingPads.append(startWin)
    self.settingPads.append(progressWin)
    self.settingPads.append(endWin)
    
    self.focusedWindow = startWin
    self.focusedWindowIndex = 0
    self.editing = False
    
    self.refreshSides()
    # End of constructor
    
  # These are "optional" settings that enhance the experience of the menu.
  # If you specify the main window as a window object, UIManager can return
  # the cursor to the main window after updating one of its own windows
  def setMainWindow(self, window):
    self.getProgressBar().setMainWindow(window)
    if self.infoPad:
      self.infoPad.setMainWindow(window)
    
  # Set the infoPad in order for it to display information
  def setInfoDisplay(self, infoPad):
    self.infoPad = infoPad
  
  # Calls refresh() for the InputPads for the start and end values,
  # and updates the title window
  def refreshSides(self):
    self.settingPads[0].updateValue(self.tArgs.start) #.setText("beg=" + str(self.tArgs.start))
    self.settingPads[2].updateValue(self.tArgs.end) #.setText("end=" + str(self.tArgs.end))
    self.settingPads[0].refresh()
    self.settingPads[2].refresh()
    
  # Retrieves the ProgressBar object so that it can be set to certain values
  def getProgressBar(self):
    return self.settingPads[1]
    
  # Handles typing and switching between items
  def type(self, ch):
    # Switch between menu items
    if self.editing == False and (ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT):
      self.focusedWindow.unhighlight()
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
      self.focusedWindow.highlight()
      self.setMainWindow(self.focusedWindow)
      self.infoPad.updateInfo(self.focusedWindow.hoverMsg)
      return
      
    self.setMainWindow(self.focusedWindow)
    
    # Toggle editing on and off and handle highlighting
    if ch == curses.KEY_ENTER:
      if self.editing == False:
        self.editing = True
        self.focusedWindow.unhighlight()
        self.infoPad.updateInfo(self.focusedWindow.toolTip)
        self.focusedWindow.updateValue(self.focusedWindow.lastValue) # Only
        # to make sure it displays right when entering edit mode
        self.focusedWindow.refresh()
      else:
        self.editing = False
        self.focusedWindow.highlight()
        # Run action specified in class
        self.focusedWindow.doAction()
        self.infoPad.updateInfo(self.focusedWindow.actionMsg)
      return
      
    # Drive the type function
    if not (ch == curses.KEY_UP or ch == curses.KEY_DOWN):
      self.focusedWindow.type(ch)
    elif self.editing:
      self.infoPad.updateInfo(self.focusedWindow.toolTip)
    else:
      self.infoPad.updateInfo(self.focusedWindow.hoverMsg)

    

# The display at the bottom of the screen that shows status
# and error messages
class InfoDisplay:
  def __init__(self, ySize, xSize, yStart, xStart):
  # Make info display window (ySize, xSize, yStart, xStart)
    self.win = curses.newwin(ySize, xSize, yStart, xStart)
    self.otherWindow = None
    
    self.xSize = xSize
    self.ySize = ySize
    
  # If you tell it what window to go back to, it will retain
  # the cursor focus.
  def setMainWindow(self, window):
    self.otherWindow = window
  
# Updates text on the info display window
# window is the infoDisplay window
# otherWindow is the one you want to keep the cursor on
  def updateInfo(self, text):
    maxLen = self.xSize * self.ySize
    if len(text) >= maxLen:
      text = text[0:maxLen-1]
    self.win.erase()
    self.win.addstr(0, 0, text) # Display text
    self.win.refresh()
    if self.otherWindow:
      self.otherWindow.refresh()
      




#Thread generating and playing audio
def audioThread(tArgs, menu):
  p = pyaudio.PyAudio()
  stream = p.open(format=pyaudio.paFloat32,
                  channels = tArgs.channels,
                  rate = tArgs.rate,
                  output = True,
                  frames_per_buffer = tArgs.frameSize)
  
  value = 0.0
  oldTime = 0
  
  #Thanks to https://stackoverflow.com/a/12467755 by Ohad
  #for a much more efficient eval() for performance improvements
  
  try: # Don't error-out on an empty text box
    exp_as_func = eval('lambda x: ' + tArgs.expression)
  except SyntaxError:
    sys.stderr.write("Expression has not yet been set, or other SyntaxError\n")
    pass
    
    
  try: #Make breaking out of the infinate loop possible by a keyboard interrupt
    #exp_as_func = eval('lambda x: ' + tArgs.expression)
    while tArgs.shutdown is False: # Main loop
      result = []
      if abs(tArgs.end - tArgs.start < tArgs.frameSize) or tArgs.end <= tArgs.start:
        sys.stdout.write("Error: Invalid range!")
        tArgs.shutdown = True
        break
        
      for i in range(tArgs.start, tArgs.end, 1):
        try:
          if tArgs.expression:
            value = exp_as_func(i) # This is where the waveform values are actually calculated
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
        
        if i % tArgs.frameSize == 0 or i == 0:
          if tArgs.shutdown == True:
            sys.exit()
          try: # Set the new expression for next time
            exp_as_func = eval('lambda x: ' + tArgs.expression)
          except:
            pass
          chunk = np.array(result)
          try: # This try statement may not be needed if better verification is made beforehand...
            stream.write( chunk.astype(np.float32).tobytes() )
          except TypeError:
            time.sleep(0.5)
          result = []
          # Update menu index display
          t = time.time()
          if menu and t - oldTime > 0.5: # Don't update too fast
            oldTime = t
            if tArgs.shutdown == False:
              menu.getProgressBar().updateIndex(i, tArgs.start, tArgs.end)
          
          if i < tArgs.start or i > tArgs.end:
            break
      
  except (KeyboardInterrupt, SystemExit):
    pass
  finally:
    tArgs.shutdown = True
    stream.stop_stream()
    stream.close()
    p.terminate()
    sys.stderr.write("Audio thread shut down.\n")
    






def main(argv = None):
  
  parser = argparse.ArgumentParser(description="A cross-platform script for creating and playing with sound waves through mathematical expressions", prog="calcwave")
  
  parser.add_argument('expression', type = str,
                      help = "The expression, in terms of x. When using the command line, it may help to surround it in single quotes. If --gui is specified, use 0 for this parimeter")
  parser.add_argument("-s", "--start", type = int, default = -100000,
                      help = "The lower range of x to start from.")
  parser.add_argument("-e", "--end", type = int, default = 100000,
                      help = "The upper range of x to end at.")
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
  
  window = None
  scr = None
  menu = None
  #The program may be started either in GUI mode or CLI mode. Test for GUI mode vvv
  if len(sys.argv) == 1 or args.gui == True: #If no arguments are supplied - GUI
    sys.stderr.write("Starting GUI mode\n")
    tArgs.isGUI = True
    
    scr = curses.initscr()
    rows, cols = scr.getmaxyx()
    
    if curses.has_colors():
      curses.start_color()
      curses.use_default_colors()
    
    # ySize, xSize, yStart, xStart
    menu = UIManager(1, cols, rows - 3, 0, tArgs)
    #Start the GUI input thread
    window = threading.Thread(target=windowThread, args=(tArgs, scr, menu), daemon=True)
    window.start()
    
    tArgs.expression = "0" # Default value
  else:
    tArgs.isGUI = False
    
    
    
  #Start the audio player thread
  #audio = threading.Thread(target=audioThread, args=(tArgs,), daemon=False)
  #audio.start()
  
  # Keep in mind that menu will be None when it is not in GUI mode...
  audioThread(tArgs, menu)
  
  # When that exits
  tArgs.shutdown = True
  
  if window:
    window.join()
    

if __name__ == "__main__":
  main()
