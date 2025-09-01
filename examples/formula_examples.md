These are some example formulae to showcase what sounds are possible.  
Some are given a recommended range. For instance, [0, inf] means that you might set "beg" to 0

---

### Musical melody
```python
sin(x/(15+round(sin(x/5000))*(x/(30000+sin(x/3000)*100))))
```
---
### Watery
```python
sin((x*2)/((x%3000)/10+round(x/8000)*50))
```
---
### Outer space alien
```python
sin(x/60%(x/660)%(15+sin(x/4000)*10))
```
Notes: surround in try / except to ignore ZeroDivisionError

---

### Bleep melody
Musical:  
```python
sin(x/(40)%(int(x/10000)%15))%sin(round(x/4000)*4)
```
Messy: 
```python
sin(x/(20+(x%(x%20000)%round(x/4000)))%(round(abs(x/10000%10))))
```
Notes: surround in try / except to ignore ZeroDivisionError

---

### Crazy bleeps [0, inf]
```python
sin(x/sqrt(x/150)%abs(6*round(sin(x/(4500+(x/50))),1)%3.5))
```
Notes: surround in try / except to ignore ZeroDivisionError and ValueError

---

### Bubbling Riser
Steppy:
```python
sin(x/(25+(x%(10000-abs(x/9)))/500))
```
Smooth:
```python
sin(0.4*((log(abs(0.001+x))*10000)/500)*sin((log(abs(0.001+x))*10000)/100))
```

---

### Kowwww [0, inf]
Normal:  
```python
sin(sqrt(x*60)+sin(x/(15+sqrt(x*0.005)))*3)
```
Goofy:  
```python
sin(sqrt(x*60)+sin(x/(15+sqrt(x*0.005)))*((sin(x/1000)*10)+3))
```
Turnaround:  
```python
sin(sqrt(x*60)+sin(x/(15+sqrt(x*0.005)))*((sin(x/(1000+sqrt(x*5)))*10)*(1.5-sqrt(x/1000)/4)))
```

---

### Musical Swishy Awakening
```python
sin(x/(5+sin(x/3000))/1000/(2+sin(x/50%round(x/1%2-1-round(x/15000)%10))))
```
Notes:
* Surround in try / except to ignore ZeroDivisionError

---

### Space Battle [0, inf]
```python
sin(sqrt(x*25000)+sin(x/(15+sqrt(x*0.005%179)))*((sin(x/(10+sqrt(x*10**(3-(x/35000%3)))))*10)*(1.5-sqrt(x/1000)%1.5)))
```
Notes: try a longer range

---

### BowBowBow [0, inf]
```python
sin(sqrt(x*20)+sin(x/(15+sqrt(x*0.005)))*((sin(x/(10+sqrt(x*10**(3-(x/35000)))))*10)*(1.5-sqrt(x/1000)%1.5)))
```
Notes: try a longer range

---

### Metallic Wires [0, inf]
Simplified:  
```python
sin(sqrt(x*20)+sin(x/(5+sqrt(x*0.0005)))*((sin(x/(6+sqrt(x*5**(3-(x/35000)))))*5)*(0.95-sqrt(x/1000)%0.5)))
```
With stepping:  
```python
sin(sqrt(x*20)+sin(x/(5+sqrt(x*0.0005)))*((sin(x/(6+round(log(min((x-5000)/120,50000)),1)*2%3+(sin(x/25000)/500)+sqrt(x*5**(3-(x/35000)))))*5)*(0.95-sqrt(x/1000)%0.5)))
```
Notes:
* Surround in try / except to ignore ValueError: math domain error
* Try a longer range

---

### Wahwah
```python
sin((sin(x/(250+(abs(x/100))))*5+5)*(1/sin(x/(60-abs(x/10000))+sin(x/(700+abs(x/100000)*300))))**-abs(round(x/10000)))
```
Notes: 
* best range is [-150000, 150000]

---
# Parametrizable

### Controllable wahwah:
```python
def wahwah(timbre, pitch, amp = 1, octave = 1):
  # Timbre: range [-1,1]
  # Pitch: in Hz
  # Octave: range: [1, inf] - varies between high and low pitch depending on even or odd integer
  try:
    return sin((timbre*5+5)*(1/freq(pitch))**-octave)*amp
  except ZeroDivisionError:
    return 0
```
<br>

### Controllable wowow:
```python
def wowow(timbre, pitch, amp = 1):
  # Timbre: range [-1, 1]
  # Pitch: in Hz
  return amp*sin(((10000+timbre*5000)/100000)**freq(pitch))
```
