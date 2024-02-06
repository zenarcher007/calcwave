import math
import random
tri = lambda t: (2*(t%(2*math.pi)))/(2*math.pi)-1
saw = lambda t: 2*abs(tri(t))-1
sqr = lambda t: 1.0 if math.sin(t) > 0 else -1.0
def rand():
  return random.random() * 2 - 1


def getFunctionTable():
  return {"tri": tri,
          "saw": saw,
          "sqr": sqr,
          "rand": rand}