import subprocess
import sys
import cmd
import shutil

# I had too much trouble getting pyaudio to install as
# a dependency to calcwave, due to it needing portaudio. I decided to
# make it try to install the required packages at runtime instead if needed.
# If you decide to fork this repo, don't forget to change the links to your github
# page in this file.
# Runs a command. Prints the failMsg and exits if it fails.
def runCmdWithFailMsg(command, failMsg):
  try:
    subprocess.run(command, check = True)
  except subprocess.SubprocessError:
    sys.stdout.write(str(failMsg) + "\n")
    sys.exit(1)
    
# Checks if the specified command exists on your system.
def commandExists(command):
  if not isinstance(command, str):
    raise TypeError(command)
  return shutil.which(command) is not None

# Mac install sequence
def installPyaudio_mac():
  sys.stderr.write("Detected Darwin operating system.\n")
  sys.stderr.write("\nDependencyWizard: You will need to install the portaudio libraries, and the pyaudio Python module before continuing. Would you like me to install it for you? I will invoke these shell commands:\n\n")
  sys.stderr.write("brew install --HEAD portaudio\n")
  sys.stderr.write("python3 -m pip install pyaudio\n\n")
  text = input("Please type \"y\" or \"n\": ")
  if text == 'n':
    sys.stderr.write("Quitting.\n")
    sys.exit(1)
  elif text == 'y':
    runCmdWithFailMsg(['brew', 'install', '--HEAD', 'portaudio'], "DependencyWizard: Error invoking \"brew install --HEAD portaudio\". Please ensure that Homebrew is installed from https://brew.sh, or open an issue on github: https://github.com/zenarcher007/calcwave")
    runCmdWithFailMsg(['python3', '-m', 'pip', 'install', 'pyaudio'], "DependencyWizard: Error invoking \"python3 -m pip install pyaudio\". Please ensure that portaudio is installed, or open an issue on github: https://github.com/zenarcher007/calcwave")
  else:
    sys.stderr.write("I'm not sure what you mean by \"" + text + "\". Quitting.\n")
    sys.exit(1)
    
# Windows install sequence
def installPyaudio_windows():
  sys.stderr.write("Detected Windows operating system.\n")
  sys.stderr.write("\nDependencyWizard: You will need to install the pyaudio Python module before continuing. Would you like me to install these for you? I will invoke these shell commands:\n\n")
  sys.stderr.write("python3 -m pip install pipwin\n")
  sys.stderr.write("python3 -m pipwin install pyaudio\n\n")
  text = input("Please type \"y\" or \"n\": ")
  if text == 'n':
    sys.stderr.write("Quitting.\n")
    sys.exit(1)
  elif text == 'y':
    runCmdWithFailMsg(['python3', '-m', 'pip', 'install', 'pipwin'], "DependencyWizard: Error invoking \"python3 -m pip install pipwin\". If you believe that this is an error, please open an issue on github: https://github.com/zenarcher007/calcwave")
    runCmdWithFailMsg(['python3', '-m', 'pipwin', 'install', 'pyaudio'], "DependencyWizard: Error invoking \"python3 -m pip install pyaudio\". If you believe that this is an error, please open an issue on github: https://github.com/zenarcher007/calcwave")
  else:
    sys.stderr.write("I'm not sure what you mean by \"" + text + "\". Quitting.\n")
    sys.exit(1)
    
def installPyaudio_linux():
  sys.stderr.write("Detected Linux operating system.\n")
  # Find the correct install command for your package manager
  sys.stderr.write("Checking your package manager...\n")
  
  # This is by no means a complete, or necessarily accurate list.
  # I had no means to test all of these distros. However, feel free to
  # open a pull request on Github about anything that needs to be added or changed.
  installCmds = None
  if commandExists('apt-get'): # Debian
    installCmds = [['sudo', 'apt-get', 'update', '-y']]
    installCmds.append(['sudo', 'apt-get', 'install', 'portaudio19-dev'])
  elif commandExists('apk'): # Alpine
    installCmds = [['sudo', 'apk', 'update']]
    installCmds.append(['sudo', 'apk', 'add', 'portaudio-dev'])
  elif commandExists('pacman'): # Arch
    installCmds = [['sudo', 'pacman', '-Syu']]
    installCmds.append(['sudo', 'pacman', '-S', 'portaudio'])
  elif commandExists('eopkg'): # Solus
    installCmds = [['sudo', 'eopkg', 'install', 'portaudio']]
  elif commandExists('dnf'): # Fedora
    installCmds = [['sudo', 'dnf', 'install', 'portaudio']]
  elif commandExists('yum'): # Fedora and other RPM-based
    installCmds = [['sudo', 'yum', 'install', 'portaudio']]
  elif commandExists('zypper'): # OpenSUSE
    installCmds = [['sudo', 'zypper', 'install', 'portaudio-devel']]
  else:
    sys.stderr.write("DependencyWizard: Failed to find a compatible package manager on your system.\n")
    sys.stderr.write("You will need to install the portaudio libraries, as well as the pyaudio Python module before starting calcwave again.\n")
    sys.stderr.write("This may be done with a command similar to \"<package manager> install portaudio\"\n")
    sys.stderr.write("This may also be called portaudio19-dev, portaudio, or a similar name depending on your package manager.\n")
    sys.stderr.write("You should then be able to install pyaudio, using a command similar to \"python3 -m pip install pyaudio\"\n")
    sys.stderr.write("Please open an issue about this on github, describing your operating system and package manager types, or else feel free to contribute via a pull-request: https://github.com/zenarcher007/calcwave\n")
    sys.stderr.write("Quitting...\n")
    sys.exit(1)
  
  sys.stderr.write("\nDependencyWizard: You will need to install additional libraries before continuing. Would you like me to install them for you? I will invoke these shell commands. Your password may be necessary. Note that the automatic installer for Linux is in beta, and not all distros were tested.\n\n")
  for cmd in installCmds:
    sys.stderr.write(' '.join(cmd) + '\n')
  sys.stderr.write("python3 -m pip install pyaudio\n\n")
  text = input("Please type \"y\" or \"n\": ")
  if text == 'n':
    sys.stderr.write("Quitting.\n")
    sys.exit(1)
  elif text == 'y':
    
    for cmd in installCmds:
      runCmdWithFailMsg(cmd, "DependencyWizard: Error invoking " + ' '.join(cmd) + ". Please install portaudio manually, and run calcwave again. Feel free to open an issue about this on github: https://github.com/zenarcher007/calcwave")
    runCmdWithFailMsg(['python3', '-m', 'pip', 'install', 'pyaudio'], "DependencyWizard: Error invoking \"python3 -m pip install pyaudio\". Please install \"portaudio\" through your package manager, and run calcwave again. Feel free to open an issue about ths on github: https://github.com/zenarcher007/calcwave")
  else:
    sys.stderr.write("I'm not sure what you mean by \"" + text + "\". Quitting.\n")
    sys.exit(1)
    
    
def main(argv = None):
  sys.stderr.write("A missing module was detected. DependencyWizard will try to resolve these missing dependencies for you.\n")
  try: # Is it pyaudio?
    import pyaudio
    sys.stderr.write("DependencyWizard: Nothing seems to be wrong with pyaudio. I'm not sure what the problem is. Continuing anyways...\n")
  except ModuleNotFoundError:
    pform = sys.platform
    if "darwin" in pform:
      installPyaudio_mac()
    elif "win" in pform:
      installPyaudio_windows()
    elif "linux" in pform:
      installPyaudio_linux()
    else:
      sys.stderr.write("DependencyWizard was unable to dermine your type of operating system. (sys.platform=" + pform +"). Please install pyaudio and/or portaudio manually, and open an issue about this on github: https://github.com/zenarcher007/calcwave")
    sys.stderr.write("DependencyWizard completed sucessfully!\n")
      
  


if __name__ == "__main__":
  main()
