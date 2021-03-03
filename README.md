# calcwave
A simple cross-platform utility for generating and playing audio using a mathematical formula
<br>


<br/>


&nbsp;&nbsp;&nbsp;&nbsp;Have you ever looked at a graph in math class and wondered what that would sound like as a sound wave? Well, at least I did... 

&nbsp;&nbsp;&nbsp;&nbsp;Calcwave is a free, open-source, and cross-platform Python script for generating audio using a mathematical formula. It has minimal dependencies, and is designed to run on almost any operating system. It functions like a mini GUI-based audio studio using Curses, with live updates to the audio as you type. You may use any of the functions listed in Python's Math module to create sound. It works the same way as any normal graphing calculator, except that the dependent variable is the position of the speaker from -1 to 1, and the independent variable is "x" from the specified start to end range. Use this program just for fun, or for generating cool sound effects (I plan to implement the ability to export audio as a WAV file in the future). You can navigate the windows using the arrow keys, and change certain settings in real time. Be sure to keep your volume low to avoid damage to hearing or equipment.

Here are installation instructions for each platform.
You may omit any step where something is already installed.

#### Mac:

* Install Homebrew ```https://brew.sh```

* Install portaudio ```brew install --HEAD portaudio```

* Install pyaudio, curses, argparse, and numpy ```python3 -m pip install pyaudio curses numpy argparse```

* Enjoy! ```python3 <path>/calcwave.py```

#### Windows:
* Install python3 ```(Microsoft Store or elsewhere)```

* Install pipwin ```python3 -m pip install pipwin```

* Install pyaudio ```python3 -m pipwin install pyaudio```

* Install numpy, curses, and argparse ```python3 -m pip install numpy argparse windows-curses```

* Enjoy! ```python3 <path>/calcwave.py```

#### Linux:
* (Fetch updates ```sudo apt-get update```)

* Install python3 ```sudo apt-get install python3```

* Install portaudio ```sudo apt-get install portaudio-19 dev```

* Install numpy, curses, and argparse ```python3 -m pip install numpy curses argparse```

* Enjoy! ```python3 <path>/calcwave.py```
<br>

<br/>

Create any sound you wish, whether it sounds like music,  
```sin(x/(15+round(sin(x/5000))*(x/(30000+sin(x/3000)*100))))```  
...or just complete chaos.  
```sin(0.4*((log(abs(0.001+x))*10000)/500)*sin((log(abs(0.001+x))*10000)/100))```  

Either way, a simple sin wave is a good place to start.
```sin(x/30)```
<br>

<br/>
Optionally, you may also use Calcwave in terminal mode. Use ./calcwave -h for help. Please open an issue in Github if you experience any bugs or operating system incompatibilities, and feel free to contribute to Calcwave's development if you wish!
