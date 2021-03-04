import subprocess
import sys
import cmd

# I had too much trouble getting pyaudio to install as
# a dependency to calcwave, due to needing portaudio. I decided to
# make it try to install the required packages at runtime instead if needed.

# Runs a command. Prints the failMsg and exits if it fails.
def runCmdWithFailMsg(command, failMsg):
  try:
    subprocess.run(command, check = True)
  except subprocess.SubprocessError:
    sys.stdout.write(str(failMsg) + "\n")
    sys.exit(1)

# Mac install sequence
def installPyaudio_mac():
  sys.stderr.write("\nYou will need to install portaudio. Would you like me to install it for you? I will invoke these shell commands:\n\n")
  sys.stderr.write("brew install --HEAD portaudio\n")
  sys.stderr.write("python3 -m pip install pyaudio\n\n")
  text = input("Please type \"y\" or \"n\": ")
  if text == 'n':
    sys.stderr.write("Quitting.\n")
    sys.exit(1)
  elif text == 'y':
    runCmdWithFailMsg(['brew', 'install', '--HEAD', 'portaudio'], "DependencyWizard: Error invoking \"brew install --HEAD portaudio\". Please ensure that Homebrew is installed from https://brew.sh")
    runCmdWithFailMsg(['python3', '-m', 'pip', 'install', 'pyaudio'], "DependencyWizard: Error invoking \"python3 -m pip install pyaudio\". Please ensure that portaudio is installed.")
  else:
    sys.stderr.write("I'm not sure what you mean by \"" + text + "\". Quitting.\n")
    sys.exit(1)
    
# Windows install sequence
def installPyaudio_windows():
  sys.stderr.write("\nWould you like me to install these for you? I will invoke these shell commands:\n\n")
  sys.stderr.write("python3 -m pip install pipwin\n")
  sys.stderr.write("python3 -m pipwin install pyaudio\n\n")
  text = input("Please type \"y\" or \"n\": ")
  if text == 'n':
    sys.stderr.write("Quitting.\n")
    sys.exit(1)
  elif text == 'y':
    runCmdWithFailMsg(['python3', '-m', 'pip', 'install', 'pipwin'], "DependencyWizard: Error invoking \"python3 -m pip install pipwin\".")
    runCmdWithFailMsg(['python3', '-m', 'pipwin', 'install', 'pyaudio'], "DependencyWizard: Error invoking \"python3 -m pip install pyaudio\".")
  else:
    sys.stderr.write("I'm not sure what you mean by \"" + text + "\". Quitting.\n")
    sys.exit(1)
    
def installPyaudio_linux():
  sys.stderr.write("\nWould you like me to install pyaudio for you? I will invoke these shell commands, but I may need help installing portaudio if needed:\n\n")
  sys.stderr.write("python3 -m pip install pyaudio\n\n")
  text = input("Please type \"y\" or \"n\": ")
  if text == 'n':
    sys.stderr.write("Quitting.\n")
    sys.exit(1)
  elif text == 'y':
    # There are many different package managers for linux. Either add support for each of them,
    # or give up and ask you to install portaudio yourself.
    runCmdWithFailMsg(['python3', '-m', 'pip', 'install', 'pyaudio'], "DependencyWizard: Error invoking \"python3 -m pip install pyaudio\". Please install \"portaudio19-dev\" through your package manager or manually, and run calcwave again.")
  else:
    sys.stderr.write("I'm not sure what you mean by \"" + text + "\". Quitting.\n")
    sys.exit(1)
    
    
def main(argv = None):
  sys.stderr.write("A missing module was detected. DependencyWizard will try to resolve missing dependencies for you.\n")
  try: # Is it pyaudio?
    import pyaudio
    sys.stderr.write("Nothing seems to be wrong with pyaudio. I'm not sure what is wrong. Continuing.")
  except ModuleNotFoundError:
    pform = sys.platform
    if "darwin" in pform:
      installPyaudio_mac()
    elif "win" in pform:
      installPyaudio_windows()
    elif "linux" in pform:
      installPyaudio_linux()
    else:
      sys.stderr.write("Sorry, DependencyWizard does not support your operating system. Please install pyaudio and/or portaudio manually.")
  
  sys.stderr.write("DependencyWizard completed sucessfully!\n")
      
  


if __name__ == "__main__":
  main()
