# calcwave
A simple cross-platform utility for generating and playing audio using a mathematical formula
<br>


<br/>


&nbsp;&nbsp;&nbsp;&nbsp;Have you ever looked at a graph in math class and wondered what that would sound like as a sound wave? Well, at least I did... 

&nbsp;&nbsp;&nbsp;&nbsp;Calcwave is a free, user-friendly, open-source, and cross-platform Python script for generating audio using a mathematical formula. It has minimal dependencies, and is designed to run on almost any operating system. It functions like a mini GUI-based audio studio using Curses, with live updates to the audio as you type. You may use any of the functions listed in Python's Math module to create sound. It works the same way as any normal graphing calculator, except that the dependent variable is the position of the speaker from -1 to 1, and the independent variable is "x" from the specified start to end range. Use this program just for fun, or for generating cool sound effects (I plan to implement the ability to export audio as a WAV file in the future). You can navigate the windows using the arrow keys, and change certain settings in real time. Be sure to keep your volume low to avoid damage to hearing or equipment.

Here are installation instructions for each platform.
You may omit any step where something is already installed.


###Install instructions for any platform:
* Make sure you have python3 installed
* Install calcwave: ```python3 -m pip install calcwave```
* Enjoy! ```python3 -m calcwave``` or ```calcwave```


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
