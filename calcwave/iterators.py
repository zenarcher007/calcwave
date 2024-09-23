import numpy as np
import itertools

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
    


# Accepts a generator, and returns chunk arrays of size n until depleted
def chunker(generator, n):
  while True:
    chunk = list(itertools.islice(generator, n))
    if not chunk:
      break
    yield chunk

# Functions like the chunker iterator, but returns chunks as numpy arrays
def npchunker(generator, n, arrsize, dtype = None):
  while True:
    # Note that audio length will be clipped to multiples of arrsize
    chunk = None
    try:
      chunk = np.fromiter(generator, count = n, dtype = (dtype, arrsize)) # Requires numpy version >=1.23
    except ValueError:
      break
    yield chunk

# Functions like the npchunker iterator, but attempts to flatten the arrays on the fly.
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