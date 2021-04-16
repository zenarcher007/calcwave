# calcwave
A simple cross-platform utility for generating and playing audio using a mathematical formula
<br>


<br/>


&nbsp;&nbsp;&nbsp;&nbsp;Have you ever looked at a graph in math class and wondered what that would sound like as a sound wave? Well, at least I did... 

&nbsp;&nbsp;&nbsp;&nbsp;Calcwave is a user-friendly, open-source, and cross-platform Python script for generating audio using a mathematical function. It has minimal dependencies, and is designed to run on almost any operating system. It functions like a mini GUI-based audio studio using Curses, with live updates to the audio as you type. Type a function in terms of x that outputs anything within the range of -1 to 1. The independent variable is "x" from the specified start to end range, and the dependent variable is the position of the speaker from -1 to 1. X is incremented by 1 at the audio baud rate (default is 44100 per second). You may use any of the functions listed in Python's Math module to create sound. If the output for your function goes below -1 or above 1, it will be clipped. You can navigate the windows using the arrow keys, and change certain settings in real time. Use this program just for fun, or for generating cool sound effects. Press ESC to exit the program. Be sure to keep your volume low to avoid damage to hearing or equipment.

<br>


<br/>


### Install instructions for any platform:
* Make sure you have Python 3 installed
* Install calcwave: ```python3 -m pip install calcwave```
* Enjoy! ```python3 -m calcwave``` or ```calcwave```

<br>

<br/>
Remember to check for updates every so often with:
```python3 -m pip install -U calcwave```

<br>

<br/>

Create any sound you wish, whether it sounds like music,  
```sin(x/(15+round(sin(x/5000))*(x/(30000+sin(x/1000)*70))))```  
...or just complete chaos.  
```sin((sin(x/(250+(abs(x/100))))*5+5)*(1/sin(x/(60-abs(x/10000))+sin(x/(700+abs(x/100000)*300))))**-abs(round(x/10000)))```
 

Either way, a simple sin wave is a good place to start.
```sin(x/30)```

<br>

<br/>
Optionally, you may also use Calcwave in terminal mode, or specify extra options upon starting the GUI. Use ./calcwave -h for help. Please open an issue in Github if you experience any bugs or operating system incompatibilities, and feel free to contribute to Calcwave's development if you wish!
