from random import random

# This file is used for custom functions and macros available to calcwave.
# Calcwave imports this as a module on start-up.
# You may use these functions within calcwave's interpreter, like a normal
# Python function. (For example, "rand()/2")


# Returns a random number between -1 and 1. Can be used to generate fuzz noises.
def rand():
  return random() * 2 - 1
