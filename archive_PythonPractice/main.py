from PythonPractice.echo import Echo
from PythonPractice.signals import EncoderVendor1
import time

echo = Echo()

for i in range(5):
    print(echo.repeat('Hello, World!'))
    enc = EncoderVendor1(amplitude=1000, frequency_hz=0.5)
 
    print(f"{'t (s)':>6} {'position':>10} {'velocity':>10}   waveform")
    print("-" * 60)
 
    for i in range(40):
        enc.read()                      # sample the encoder
        t = i * 0.1
 
        # simple ASCII bar: map position (-A..+A) onto a 0..40 column
        col = int((enc.position / enc._amplitude + 1) * 20)
        bar = " " * col + "*"
 
        print(f"{t:6.1f} {enc.position:10d} {enc.velocity:10d}   {bar}")
        time.sleep(0.1)

# create a run forever loop with two async nodes
# 1. for the main state machine
# 2. one for the IO handling


# App that has two async properties. One loop for accepting IO and the other for handling IO