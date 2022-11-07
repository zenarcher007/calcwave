#!/usr/bin/env python3
version = "1.2.9"


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




# A special window that allows typing through characters provided in the type(ch)
# function. Note that despite its name, this is a curses window, not a pad.
# Also note that this is not a traditional text editor. Even though text may wrap to the next line,
# it doesn't allow new lines. It is more like a string editor.
class InputPad:
  #Constructor
  def __init__(self, ySize, xSize, yStart, xStart, virtual_cursor = None): # xStart, yStart, xSize, ySize):
    #Define window boundaries
    self.xSize = xSize
    self.ySize = ySize
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
    self.oldVCursor = (self.boxX1, self.boxY1)
    self.onHoverEntered = False
    
  # Moves the cursor relatively if space permits and updates the screen
  def curMove(self, relX, relY):
    if self.checkBounds(self.curX + relX, self.curY + relY, move_virtual = True):
      self.win.move(self.curY + relY, self.curX + relX)
      self.curY = self.curY + relY
      self.curX = self.curX + relX
      if move_virtual:
        self.virtCurMove(x=self.curX, y=self.curY)
  
  # Sets absolute cursor position
  def curPos(self, x, y, move_virtual = True):
    self.curX = x
    self.curY = y
    self.win.move(y, x)
    if move_virtual:
      self.virtCurMove(x = x, y = y)
      
    
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
      # Remove spaces (which make up the blank space of the curses window)
      text = text + self.win.instr().decode("utf-8").replace(chr(32), '')
    self.curPos(oldPosX, oldPosY)
    # Replace the space placeholder character back with spaces
    text = text.replace(chr(2063), chr(32))
    return text
  
  # Checks if there is an empty slot at the given position
  def checkEmpty(self, x, y):
    if not self.checkBounds(x, y):
      return False
    elif self.win.inch(y, x) == 32:
      return True
    else:
      return False
      
  
  # Un-onHoverEnters the last onHoverEntered character.
  def unHighlight(self):
    if self.onHoverEntered == True:
      self.onHoverEntered = False
      self.win.chgat(self.oldHighlightY, self.oldHighlightX, 1, curses.A_NORMAL)
      
  # Highlights a character at a position.
  def onHoverEnterChar(self, x=-1, y=-1):
    if x == -1 or y == -1:
      return
    #print("HIGHLIGHT " + str(x) + ", " + str(y))
    #time.sleep(0.5)
    if curses.has_colors():
      self.onHoverEntered = True
      oldCurX = self.curX
      oldCurY = self.curY
      
      self.unHighlight()
      self.onHoverEntered = True
      self.oldHighlightX = x
      self.oldHighlightY = y
      
      # Add new color at position
      self.win.chgat(y, x, 1, curses.A_UNDERLINE)
      curses.use_default_colors()
      self.curPos(oldCurX, oldCurY, move_virtual = False)
  
  
  
  # Moves the virtual cursor to the specified x, y position, if it is enabled.
  def virtCurMove(self, x=-1, y=-1):
    if x == -1 or y == -1:
      return
    if not(self.isVirtualCursorEnabled) or (x,y) is self.oldVCursor:
      return
    oldX, oldY = self.oldVCursor
    
    # Check if character is reversed (https://stackoverflow.com/a/26797300/16386050):
    attrs = self.win.inch(oldY, oldX) #[y, x])
    isHighlighted = bool(attrs & curses.A_REVERSE)
    
    if isHighlighted and self.checkBounds(oldX, oldY):
      self.win.chgat(oldY, oldX, 1, curses.A_NORMAL)
    self.oldVCursor=(x,y)
    if not(isHighlighted or self.checkEmpty(x, y)):
      self.win.chgat(y, x, 1, curses.A_REVERSE)
    
    self.win.move(y, x) # Move the cursor back
    #self.refresh()
    
    
    
  def virtCurMoveOld(self, x=-1, y=-1):
    #print("HIGHLIGHTING")
    #time.sleep(0.5)
    #self.onHoverEnterChar(x, y)
    pass
    #print("DONE HIGHLIGHTING")
    #time.sleep(0.5)
    
    
      
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
    self.step = 1. # How much to increment x
    self.functionTable = self.getFunctionTable()
    
  # Define functions available to eval here.
  def getFunctionTable(self):
    functionsDict = vars(math)
 
    # Returns a random number between -1 and 1. Can be used to generate fuzz noises.
    def rand():
      return random() * 2 - 1
    functionsDict["rand"] = rand
 
    return functionsDict



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
    #Initialize input pad
    # ySize, xSize, yStart, xStart
    self.pad = InputPad(rows - 5, cols, 1, 0)
    
    
    # Tell the menu that this is the main window
    self.menu.setMainWindow(self.pad.win)
  
    #Initialize info display window
    self.infoPad = InfoDisplay(2, cols, rows - 2, 0)
    self.infoPad.setMainWindow(self.pad.win) # So it will know
    # what window to return the cursor to after it updates
  
    self.menu.setInfoDisplay(self.infoPad) # Give the menu an infoPad
    # so it can display its own information on it.
    
  
    # Set the background and text color of the infoPad
    if curses.has_colors():
      curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
      self.infoPad.win.bkgd(' ', curses.color_pair(1))

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
          self.menu.title.refresh()
          
        
        if ch != -1:
          oldTime = time.time()

          # Switch between menu and inputPad with the arrow keys
          if ch == curses.KEY_UP and not self.menu.editing: # Don't remove focus from the menu while it's editing
            menuFocus = False
            settingFocus = True
            with lock:
              self.infoPad.setMainWindow(self.pad.win)
              self.menu.setMainWindow(self.pad.win)
              self.menu.getProgressBar().temporaryPause = False
              self.menu.focusedWindow.onHoverLeave()
            self.infoPad.updateInfo("")
            self.menu.title.refresh() # Good time to refresh the title?
            self.pad.refresh() # Set cursor back to typing pad
          elif ch == curses.KEY_DOWN:
            menuFocus = True
            settingFocus = True
            self.menu.focusedWindow.onHoverEnter()
            if self.menu.editing:
              self.menu.focusedWindow.onBeginEdit()
            self.menu.refreshTitleMessage()
          
          if menuFocus == True:
            self.menu.type(ch)
          elif settingFocus == False:
            # Type on the inputPad, verifying each time
            self.infoPad.updateInfo("Wait...")
            with lock:
              # Don't update the progress bar while typing. This helps a problem where the terminal cursor may sporadically jump (wrongly) to the progess bar.
              self.menu.getProgressBar().temporaryPause = True
            self.pad.type(ch)
          
            text = self.pad.getText()
            self.infoPad.updateInfo("Verifying...")
          
            try: # Verify expression
              eval('lambda x: ' + text, tArgs.functionTable)
              with lock:
                self.tArgs.expression = text # Update the expression for the audioThread
              self.infoPad.updateInfo("Playing...")
            except (SyntaxError, NameError, TypeError) as e:
              # Highlight problem character
              if len(e.args) == 2 and len(text) > 0:
                error = str(e.args[1])
                parseString = error.split(',', 3)
                if len(parseString) >= 3:
                  column = int(parseString[2]) - 11
                  x = self.pad.boxX1+column
                  y = self.pad.boxY1
                  if x >= self.pad.boxX1 and y >= self.pad.boxY1:
                    xWidth = self.pad.boxX2 - self.pad.boxX1+1
                    self.pad.onHoverEnterChar(column % xWidth, int(column / xWidth))
                self.infoPad.updateInfo(str(e.args[0]))
              else:
                if len(text) > 0:
                  error = str(e.args)
                  self.infoPad.updateInfo(error)
                else:
                  self.tArgs.expression = "0"
                  self.infoPad.updateInfo("")
                    
            with lock:
              self.menu.getProgressBar().temporaryPause = False
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
  def __init__(self, ySize, xSize, yStart, xStart):
    self.ySize = ySize
    self.xSize = xSize
    self.yStart = yStart
    self.xStart = xStart
    self.win = curses.newwin(ySize, xSize, yStart, xStart)
    
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
    for row in range(0, self.ySize):
      self.win.chgat(0, row, self.xSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    return "Hover Message"
  
  # Called when UIManager tells the cursor to leave your item
  def onHoverLeave(self):
    for row in range(0, self.ySize):
      self.win.chgat(0, row, self.xSize, curses.A_NORMAL)
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
  def __init__(self, ySize, xSize, yStart, xStart, tArgs, progressBar):
    super().__init__(ySize, xSize, yStart, xStart)
    self.tArgs = tArgs
    self.infoPad = None
    self.progressBar = progressBar
    self.lock = threading.Lock()
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
    
    with self.lock:
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
        with lock:
          progressBar.temporaryPause = True
          infoPad.updateInfo("Writing (" + str(int(abs(i-progressStart)/(abs(end-start))*100)) + "%)...")
          progressBar.temporaryPause = False
      i = i + step
  if infoPad:
    infoPad.updateInfo("Exported as " + fullPath)
    


# A menu item in the format "name=..." that types like an InputPad
# this allows setting variables, etc in a typing-based way
class NamedMenuSetting(InputPad, BasicMenuItem): # Extend the InputPad and BasicMenuItem classes
  def __init__(self, ySize, xSize, yStart, xStart, name):
    super().__init__(ySize, xSize, yStart, xStart)
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
    if self.curX > len(str(self.name + "=")):
      super().goLeft()
  
  # Override InputPad type method
  def type(self, ch):
    super().type(ch)
    self.refresh()
    

      
# A special case of a NamedMenuSetting that only allows typing numbers. Returns the number as
# an int or float when getValue() is called based on which one you specified in valueType
class NumericalMenuSetting(NamedMenuSetting):
  def __init__(self, ySize, xSize, yStart, xStart, name, type):
    super().__init__(ySize, xSize, yStart, xStart, name)
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
  def __init__(self, ySize, xSize, yStart, xStart, name, tArgs):
    super().__init__(ySize, xSize, yStart, xStart, name, "int")
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
  def __init__(self, ySize, xSize, yStart, xStart, name, tArgs):
    super().__init__(ySize, xSize, yStart, xStart, name, "int")
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
  def __init__(self, ySize, xSize, yStart, xStart, name, tArgs):
    super().__init__(ySize, xSize, yStart, xStart, name, "float")
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
  def __init__(self, ySize, xSize, yStart, xStart, audioClass, tArgs):
    super().__init__(ySize, xSize, yStart, xStart)
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
      blockWidth = int(range / self.xSize)
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
      text = ''.join([char*(self.xSize-1) for char in '-' ])
    else:
      with self.lock:
        self.progressBarEnabled = True
      text = ''.join([char*(self.xSize-1) for char in '░' ])
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
    maxLen = self.xSize * self.ySize
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
  isGraphOn = False
  def __init__(self, ySize, xSize, yStart, xStart, tArgs, audioClass):
    super().__init__(ySize, xSize, yStart, xStart)
    self.tArgs = tArgs
    self.audioClass = audioClass
    self.isGraphThreadRunning = False
    self.graphThread = None

  def __del__(self):
    with threading.Lock():
      self.isGraphThreadRunning = False

  def refresh(self):
    super().refresh()
    self.displayText("Graph")

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
    if self.isGraphOn:
      self.graphOff()
      actionMsg = "Turned Graph off."
    else:
      self.graphOn()
      actionMsg = "Turned Graph on."
    self.isGraphOn = not self.isGraphOn


    #curr = self.audioClass.index # Get current position
    #exp_as_func = self.audioClass.getAudioFunc() # Update expression
    #actionMsg = str([x for x in self.calcIterator(curr, curr+10000, self.tArgs.step, exp_as_func)])
    #plt.plot([x for x in self.calcIterator(curr, curr+10000, self.tArgs.step, exp_as_func)])
    #plt.show()
    #plt.draw()
    return actionMsg



# Just a title display at the top of the screen
class TitleWindow:
  def __init__(self, ySize, xSize, yStart, xStart):
    self.xSize = xSize
    self.win = curses.newwin(ySize, xSize, yStart, xStart)
    self.refresh()
  
  # Draws the title and onHoverEnters it
  def refresh(self):
    self.win.clear()
    self.win.addstr("Calcwave v" + version)
    self.win.chgat(0, 0, self.xSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    
  # Use curstom text
  def customTitle(self, text):
    self.win.clear()
    self.win.addstr(text)
    self.win.chgat(0, 0, self.xSize, curses.A_REVERSE)
    curses.use_default_colors()
    self.win.refresh()
    
    
# A class that controls and handles interactions with menus and other UI.
# Drive UIManager's type(ch) function with keyboard characters
# to interact with it when needed.
class UIManager:
  def __init__(self, ySize, xSize, yStart, xStart, tArgs, audioClass):
    #self.ySize = ySize
    #self.xSize = xSize
    #self.yStart = yStart
    #self.xStart = xStart

    self.tArgs = tArgs
    self.infoPad = None
        
    self.settingPads = []
    self.boxWidth = int(xSize / 3)
    
    self.title = TitleWindow(1, xSize, 0, 0)
    self.lock = threading.Lock()
    
    # Create windows and store them in the self.settingPads list.
    
    # Graph Button
    graphBtn = graphButtonMenuItem(int(ySize/2), self.boxWidth, yStart, xStart, tArgs, audioClass)

    # Start range
    startWin = startRangeMenuItem(int(ySize/2), self.boxWidth, yStart+1, xStart, "beg", tArgs)
    startWin.updateValue(tArgs.start)
    
    # Progress bar
    progressWin = ProgressBar(int(ySize/2), self.boxWidth, yStart+1, xStart + self.boxWidth, audioClass, tArgs)
    
    # End range
    endWin = endRangeMenuItem(int(ySize/2), self.boxWidth, yStart+1, xStart + self.boxWidth * 2, "end", tArgs)
    endWin.updateValue(tArgs.end)
    
    # Step value
    stepWin = stepMenuItem(int(ySize/2), self.boxWidth, yStart + 2, xStart + self.boxWidth * 2, "step", tArgs)
    stepWin.updateValue(tArgs.step)
    
    # This currently takes up the width of the screen. Change the value from xSize to resize it
    saveWin = exportButton(int(ySize/2), int(xSize*(2/3)-1), yStart+2, xStart, tArgs, progressWin)

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
    rows, cols = scr.getmaxyx()
    
    if curses.has_colors():
      curses.start_color()
      curses.use_default_colors()

  try:
    # ySize, xSize, yStart, xStart
    menu = UIManager(2, cols, rows - 5, 0, tArgs, audioClass)
    #Start the GUI input thread
    window = WindowManager(tArgs, scr, menu)
  except Exception as e: # Catch any exception so that the state of the terminal can be restored correctly
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
    exportAudio(args.export, tArgs, None, None)
  else:
    # Keep in mind that menu will be None when it is not in GUI mode...
    audioClass.play()
  
  
  # When that exits
  tArgs.shutdown = True
  
  if window:
    window.thread.join()
    

if __name__ == "__main__":
  main()