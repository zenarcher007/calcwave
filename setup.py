import setuptools
from setuptools import setup
from setuptools.command.install import install
import subprocess
import os
import sys

# Help from https://stackoverflow.com/a/27953695 by 4Z4T4R
# For Windows, try to install pyaudio through pipwin rather than from pip.
class installScript(install):
  def run(self):
    if not sys.platform.startswith("win"):
      install.run(self)
      return
    try:
      sys.stderr.write("Attempting to install pyaudio through pipwin...")
      subprocess.check_output(['python3', '-m', 'pip', 'install', 'pipwin'])
      subprocess.check_output(['python3', '-m', 'pipwin', 'install', 'pyaudio'])
      sys.stderr.write("Pyaudio was installed successfully!")
    except:
      sys.stderr.write("********* Unable to install pipwin and pyaudio automatically. Here is what I tried. Please install them by commands similar to these:\n")
      sys.stderr.write("python3 -m pip install pipwin\n")
      sys.stderr.write("python3 -m pipwin install pyaudio\n")
    install.run(self)
      

setup(cmdclass={'install': installScript},
  name = 'calcwave',         # How you named your package folder (MyLib)
  packages = ['calcwave'], #setuptools.find_packages(),   # Chose the same as "name"
  version = '1.0.0b6',
  license='gpl-3.0',
  description = 'A simple cross-platform utility for generating and playing audio using a mathematical formula ',
  author = 'Justin Douty',                   # Type in your name
  url = 'https://github.com/zenarcher007/calcwave',   # Provide either the link to your github or to your website
  download_url = 'https://github.com/zenarcher007/calcwave/archive/v1.0.0b6.tar.gz',
  keywords = ['cross-platform', 'audio synthesis', 'terminal'],   # Keywords that define your package best
  install_requires=[
    'pyaudio',
    'numpy',
    'argparse',
    'windows-curses ; platform_system=="Windows"',
  ],
  entry_points={
    'console_scripts': [
      'calcwave = calcwave:audiostudio'
    ]
  },
  classifiers=[
    'Development Status :: 4 - Beta',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: End Users/Desktop',      # Define that your audience are developers
    'Topic :: Multimedia :: Sound/Audio :: Sound Synthesis',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',   # Again, pick a license
    'Programming Language :: Python :: 3',      #Specify which python versions that you want to support
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
  ],
  #packages=setuptools.find_packages(),
)
