# This file contains a collection of basic building blocks for interactive user interface buttons and displays.
# See texteditors.py for a collection of text editors, which are unrelated to the following classes and not compatible
# in the same way, but still follow similar conventions. Note that some of these classes depend on the text editors.

from calcwave.elementaltypes import Box
from calcwave.texteditors import LineEditor
import curses



# The basic neccesities for a convention-following class (such as UIManager) to accept your widget as a menu item
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
    #with global_display_lock:
    self.win.refresh()

  # Standard hooks to hide and show the cursor, if your widget has one.
  def hideCursor(self):
    pass

  def showCursor(self):
    pass

  def displayText(self, text):
    self.win.erase()
    self.win.addstr(0, 0, text)
    #with global_display_lock:
    self.win.refresh()

  def isOneshot(self):
    return False # By default, this item can enter and exit focus, rather than immediately exiting.

  # Redraws the button graphics (text, background, etc.)
  def updateValue(self, value, refresh = refresh):
    pass # This is a hook
   
  # Called when UIManager has the cursor over your item
  def onHoverEnter(self):
    for row in range(0, self.shape.rowSize):
      self.win.chgat(0, row, self.shape.colSize, curses.A_REVERSE)
    #curses.use_default_colors()
    #with global_display_lock:
    self.win.refresh()
    return "Hover Message"
  
  # Called when UIManager tells the cursor to leave your item
  def onHoverLeave(self):
    self.hovering = False
    for row in range(0, self.shape.rowSize):
      self.win.chgat(0, row, self.shape.colSize, curses.A_NORMAL)
    curses.use_default_colors()
    #with global_display_lock:
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
  
  def updateValue(self, value, refresh = True):
    self.setText(self.name + "=" + str(value), refresh = refresh)
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