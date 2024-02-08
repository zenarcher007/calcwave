import math
import random
from collections import deque

tri = lambda t: (2*(t%(2*math.pi)))/(2*math.pi)-1
saw = lambda t: 2*abs(tri(t))-1
sqr = lambda t: 1.0 if math.sin(t) > 0 else -1.0

def rand():
  return random.random() * 2 - 1

class Integral:
  # __init__ must take no arguments
  def __init__(self):
    self.prevY = 0

  # This function will be called by the Evaluator. It must be called "evaluate", and can take any number of arguments,
  # which will be provided by the user.
  def evaluate(self, y, clip = True):
    newY = self.prevY + y
    if clip:
      if newY > 1:
        newY = 1
      elif newY < -1:
        newY = -1
    self.prevY = newY
    return newY
  
  # Only the "evaluate" function will be callable by the user per class, by this name.
  # This helps simplify computation and design of memory classes, as one class instance will exist per function call anyways.
  @staticmethod
  def __callname__():
    return "intg"

  ## These functions will be available to the user. Their names must be globally unique.
  #def getFunctionTable(self):
  #  return {"itgl": self.itgl}


class Derivative:
  def __init__(self):
    self.prevY = 0

  def evaluate(self, y, clip = True):
    newY = y - self.prevY
    if clip:
      if newY > 1:
        newY = 1
      elif newY < -1:
        newY = -1
    self.prevY = y
    return newY

  @staticmethod
  def __callname__():
    return "derv"
  


class ExponentialMovingAverage:
  def __init__(self):
    self.prevY = 0

  def evaluate(self, y, n):
    b = n-1
    v = 2/b
    newY = y*(v) + self.prevY*(1-v)
    self.prevY = newY
    return newY
 
  @staticmethod
  def __callname__():
    return "ema"

# A cache to avoid recomputing values that are known to not change.
# This can greatly improve performance for user-defined values that would be
# Recomputed at every iteration. This will update at every recompilation.
class Constant:
  def __init__(self):
    self._initialized = False
    self.cachedY = None

  # Y should be any lambda that returns a value and takes no arguments
  def evaluate(self, y):
    if self._initialized == False:
      self._initialized = True
      self.cachedY = y()
    return self.cachedY
    
  @staticmethod
  def __callname__():
    return "const"

# A memistic convolution over the last number of values
class Convolution:
  def __init__(self):
    self.length = 0
    self.history = deque(maxlen = self.length)

  # Disable cache_filter if you will be using the scale parameter when filter values will be changing dynamically (likely uncommon)
  def evaluate(self, y, filter):
    filtlen = len(filter)
    if filtlen != self.length: # If the length of the filter is changed, recreate the deque with new maxlen
      oldh = self.history
      self.history = deque(maxlen = filtlen)
      self.history.extend(list(oldh))
    self.history.append(y)
    if filtlen != len(self.history):
      return y # There is not yet enough history to perform the convolution. Wait until there is.
    #return np.dot(self.history, filter)
    return sum([a*b for a, b in zip(filter, self.history)])
 
  @staticmethod
  def __callname__():
    return "conv"

# During compilation, a list of classes marked as having memistic capabilities.
# Any calls to functions mapped within their getFunctionTable() will be mapped to a unique
# instance of that class.
def getMemoryClasses():
  return [Integral, Derivative, ExponentialMovingAverage, Convolution, Constant]

# During compilation, a mapping of functions available to the user
def getFunctionTable():
  return {"tri": tri,
          "saw": saw,
          "sqr": sqr,
          "rand": rand}