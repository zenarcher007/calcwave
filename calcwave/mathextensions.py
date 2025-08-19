import math
import random
from collections import deque
import numpy as np
from numpy import linalg

tri = lambda t: (2*(t%(2*math.pi)))/(2*math.pi)-1
saw = lambda t: 2*abs(tri(t))-1
sqr = lambda t: 1.0 if math.sin(t) > 0 else -1.0
def avg(x):
  return sum(x) / len(x)

# Base class for memory classes
class MemoryClass:
  # Any variables added for all MemoryClasses when compiled with the MemoryClassCompiler will be passed here as a dictionary
  def __init__(self, vars: dict):
    pass

  # This function will be called by the Evaluator. It must be called "evaluate", and can take any number of arguments,
  # which will be provided by the user.
  def evaluate(self):
    pass

  # This is the function name the user will literally type in the interpereter, specifying the arguments within "evaluate"
  @staticmethod
  def __callname__():
    "MemoryClass"

# A tone generator of a constant frequency. The step parameter will not affect this.
class Frequency(MemoryClass):
  def __init__(self, vars: dict):
    self.rate = vars.get("rate", 44100)
    self.phase = 0.0  # keep track of running phase
  
  def evaluate(self, hz, fn=math.sin):
    # increment phase by correct amount per sample
    self.phase += 2 * math.pi * hz / self.rate
    # wrap phase to avoid float overflow
    if self.phase > 2 * math.pi:
      self.phase -= 2 * math.pi
    return fn(self.phase)

  @staticmethod
  def __callname__():
    return "freq"


# A memory class that returns a new random number every n steps
class Random(MemoryClass):
  def __init__(self, vars: dict):
    self.steps = 1
    self.num = random.random() * 2 - 1
  
  def evaluate(self, n = 1):
    self.steps = self.steps + 1
    if self.steps > n:
      self.steps = 1
      self.num = random.random() * 2 - 1
    return self.num
  
  @staticmethod
  def __callname__():
    return "rand"
  
class Integral(MemoryClass):
  # __init__ must take no arguments
  def __init__(self, vars: dict):
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


class Derivative(MemoryClass):
  def __init__(self, vars: dict):
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
  


class ExponentialMovingAverage(MemoryClass):
  def __init__(self, vars: dict):
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
class Constant(MemoryClass):
  def __init__(self, vars: dict):
    self._initialized = False
    self.cachedY = None
    self.vars = {}

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
class Convolution(MemoryClass):
  def __init__(self, vars: dict):
    self.length = 0
    self.history = deque(maxlen = self.length)

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
    return np.convolve(self.history, filter, mode='valid')
    #return sum([a*b for a, b in zip(filter, self.history)])
 
  @staticmethod
  def __callname__():
    return "conv"

# Question: is it possible to get the start, end, and step attributes from a constructed range() object?
# Answer: Yes.
# Question: How?
# Answer: The start and end are attributes of the range object itself. The step is an attribute of the iterator returned by calling __iter__() on the range object.
# Example:
# r = range(5)
# print(r.start, r.stop, r.__iter__().step) # prints "0 5 1"



# A simple history, that returns a deque of the last [length] values. You may want to convert this into a list.
class History(MemoryClass):
  def __init__(self, vars: dict):
    self.history = None
    self.initalized = False

  def evaluate(self, y, length):
    if self.initalized == False:
      self.initalized = True
      self.history = deque(maxlen = length)
      self.history.extend(0.0 for _ in range(length))
    self.history.append(y)
    return self.history
 
  @staticmethod
  def __callname__():
    return "history"
    
class Delay:
  def __init__(self, vars: dict):
    self.history = None
    self.initalized = False
    self.length = 0

  def evaluate(self, y, lengths, volumes = [1]):
    # Upgrade to list if lengths is a scalar
    if not hasattr(lengths, "__len__"):
      lengths = [lengths]
    #volumes = np.array(volumes)
    # Normalize volumes such that the sum of all its elements is 1
    sv = sum(volumes)
    volumes = [v / sv for v in volumes]
    list.reverse(volumes)

    if len(lengths) != len(volumes) and len(volumes) != 1:
      raise ValueError('"lengths" and "volumes" must be lists of the same length')

    if self.initalized == False:
      self.initalized = True
      maxlen = max(lengths)
      self.length = maxlen
      self.history = deque(maxlen = maxlen+1)
    self.history.append(y)
    #print(len(self.history), self.length+1)
    hl = len(self.history)
    if hl != self.length+1:
      return y # Wait until history is long enough
    
    #if hl == 1 or True:
    arr = self.history
    # This has actually shown to be significantly faster than using numpy in this case.
    if len(volumes) == 1:
      return sum( (arr[lengths[i]]*volumes[0] for i in range(len(lengths))) )
    else:
      return sum( (arr[lengths[i]]*volumes[i] for i in range(len(lengths))) )
    #else: # Convert to numpy array to prevent likely worse than O(n) computation time from many random lookups
    #  arr = np.array(self.history)
    #  return np.sum(arr[lengths] * volumes)

  
  @staticmethod
  def __callname__():
    return "delay"

# Normalizes the wave for the specific history length n in (generally) O(1) time and O(n) memory
# TODO: Even with optimizations, this is a bit compute-intensive in Python.
#       It might be a good idea to compile this into a C module
#       ... or wait until Numba supports deque
class Normalize:
  def __init__(self, vars: dict):
    self.length = 0
    self.history = None
    self.initalized = False

    self.mmax = 0
    self.mmin = 0
    self.msum = 0
    self.maxcount = 0
    self.mincount = 0

  def evaluate(self, y, length):
    if self.initalized == False:
      self.initalized = True
      self.history = deque(maxlen = length)

    msum, mmin, mmax, mincount, maxcount = (self.msum, self.mmin, self.mmax, self.mincount, self.maxcount)
    
    if len(self.history) == length:
      self.msum -= self.history[-1] # Subtract end from moving sum
    self.history.append(y)
    self.msum += y # Add to moving sum
    
    # Perform rolling min/max
    if y > mmax:
      maxcount = 0
      mmax = y
    if y < mmin:
      mincount = 0
      mmin = y
    
    # While the highest/lowest value is in the dequeue, it won't change. Once it leaves,
    # the next highest/lowest will need to be recomputed.
    if maxcount > length:
      mmax = max(self.history)
      maxcount = 0
    if mincount > length:
      mmin = min(self.history)
      mincount = 0
    
    mincount+=1
    maxcount+=1

    if self.mmax == self.mmin:
      self.msum, self.mmin, self.mmax, self.mincount, self.maxcount = (msum, mmin, mmax, mincount, maxcount)
      return 0
    
    mean = msum / length
    normalized = (y - mean) / (mmax - mmin)

    #mean = sum(self.history) / length
    #maxm, minm = (max(self.history), min(self.history))
    #if maxm - minm < 0.1:
    #  return 0
    #normalized = (y - mean) / (maxm - minm)
    self.msum, self.mmin, self.mmax, self.mincount, self.maxcount = (msum, mmin, mmax, mincount, maxcount)
    return normalized*2
 
  @staticmethod
  def __callname__():
    return "norm"


# During compilation, a list of classes marked as having memistic capabilities.
# Any calls to functions mapped within their getFunctionTable() will be mapped to a unique
# instance of that class.
def getMemoryClasses():
  return [Integral, Derivative, ExponentialMovingAverage, Convolution, Constant, History, Normalize, Delay, Random, Frequency]

# During compilation, a mapping of functions (not using the memory system) available to the user
def getFunctionTable():
  return {"tri": tri,
          "saw": saw,
          "sqr": sqr,
          "avg": avg}