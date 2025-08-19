from calcwave.basicui import *
import watchdog
import threading
import time
import numpy as np
import traceback
import os
import curses


# A button to export audio as a WAV file, assuming you have the "wave" module installed.
class ExportButton(LineEditor, BasicMenuItem):
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
  
  def updateValue(self, text, refresh = True):
    self.setText(text, refresh = refresh)

  def refresh(self):
    self.updateValue("Export Audio", refresh = False)
    super().refresh()
    
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
  



  # A special case of a NamedMenuSetting that sets the start range in global_config
class StartRangeMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, global_config):
    self.lock = threading.Lock()
    self.global_config = global_config
    super().__init__(shape, name, "int")

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
      if value > self.global_config.end: # Don't allow crossing start / end ranges
        actionMsg = "Start range cannot be greater than end range!"
        self.updateValue(self.global_config.start)
      else:
        actionMsg = "Start range changed to " + str(value) + "."
        self.lastValue = str(value)
        with self.lock:
          self.global_config.start = value
      return actionMsg


# A special case of a NamedMenuSetting that sets the end range in global_config
class EndRangeMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, global_config):
    self.lock = threading.Lock()
    self.global_config = global_config
    self.stepWin = None
    super().__init__(shape, name, "int")

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
class StepMenuItem(NumericalMenuSetting):
  def __init__(self, shape: Box, name, global_config):
    self.global_config = global_config
    super().__init__(shape, name, "float")

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
      if self.progressBarEnabled == True:
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
    #with global_display_lock:
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
      if self.global_config.shutdown == False and self.progressBarEnabled == True and not self.audioClass.isPaused():
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
    i = max(i, min(i, end))
    maxLen = self.shape.colSize * self.shape.rowSize
    value = int(np.interp(i, [start,end], [0, maxLen - 2]))
    
    text = "{" + ''.join([char*value for char in '░' ]) + ''.join([' '*(maxLen-value-3)]) + '}'
    
    # Lock thread - for what?
    #self.lock.acquire(blocking=True, timeout=1)
    self.win.erase()
    self.win.addstr(0, 0, text) # Display text
    #self.win.addch(0, maxLen - 2, '}')
    #with global_display_lock:
    self.win.refresh()
    # Unlock thread
    #self.lock.release()
    



# To toggle the graph on or off
class GraphButtonMenuItem(BasicMenuItem):
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


# Title display at the top of the screen
class TitleWindow:
  def __init__(self, shape: Box, titlestr):
    self.shape = shape
    self.win = curses.newwin(shape.rowSize, shape.colSize, shape.rowStart, shape.colStart)
    self.message = ""
    self.titlestr = titlestr
    self.refresh()
    
  # Draws the title
  def refresh(self):
    self.win.clear()
    self.win.addstr(self.titlestr + self.message)
    self.win.chgat(0, 0, self.shape.colSize, curses.A_REVERSE)
    #with global_display_lock:
    curses.use_default_colors()
    self.win.refresh()
    
  # Use custom text
  def customTitle(self, text):
    self.win.clear()
    self.win.addstr(text + self.message)
    self.win.chgat(0, 0, self.shape.colSize, curses.A_REVERSE)
    #with global_display_lock:
    curses.use_default_colors()
    self.win.refresh()

  # Appends a mandantory message to the end of the title
  def setMessage(self, text):
    if text == "":
      self.message = ""
    else:
      self.message = " " + text