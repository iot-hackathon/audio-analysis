#!/usr/bin/env python

# http://stackoverflow.com/questions/26478315/getting-volume-levels-from-pyaudio-for-use-in-arduino

from __future__ import print_function

import pyaudio
import wave
import audioop
import signal
import sys

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)

def find_input_device(pa):
    device_index = None
    for i in range( pa.get_device_count() ):
        devinfo = pa.get_device_info_by_index(i)
        print( "Found device %d: %s" % (i, devinfo["name"]) )

        for keyword in ["mic", "input"]:
            if keyword in devinfo["name"].lower():
                print( "Matching device: %d - %s"%(i,devinfo["name"]) )
                device_index = i
            if device_index != None:
                return device_index

    if device_index == None:
        print( "No preferred input found; using default input device." )

    return device_index

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

# http://stackoverflow.com/questions/6169217/replace-console-output-in-python
def drawBar(title, value=0, maxValue=100, end=False):
    width = 200
    l = int(value * width // maxValue)
    if l > width:
        l = width
    r = width - l;

    sys.stdout.write(title + ": [" + ("#"*l) + ("-"*r) + "]\r")
    if end:
        sys.stdout.write("\n")
    sys.stdout.flush()

if __name__ == "__main__":
    pa = pyaudio.PyAudio()

    device_index = find_input_device(pa)

    stream = pa.open(
        format             = FORMAT,
        channels           = CHANNELS,
        rate               = RATE,
        input              = True,
        input_device_index = device_index,
        frames_per_buffer  = CHUNK
    )


    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            data = stream.read(CHUNK)
            rms  = audioop.rms(data, 2)
            drawBar("Volume", rms, 10000)
        except IOError as e:
            print( "Error recording: %s" % (e) )
            break

    stream.stop_stream()
    stream.close()
    pa.terminate()
