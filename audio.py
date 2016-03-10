#!/usr/bin/env python

# http://stackoverflow.com/questions/26478315/getting-volume-levels-from-pyaudio-for-use-in-arduino

from __future__ import print_function

#For Audio analysis
import pyaudio
import wave
import audioop
import signal
import sys
import time
import threading
#import numpy as np
#import math

#Iot service dependencies
import os,json,math,time,logging
import ibmiotf.device
import configparser

#Logging
logging.basicConfig(filename='output.log',level=logging.DEBUG,format='%(asctime)s %(module)s %(thread)s %(message)s')
logger = logging.getLogger(__name__)

#Config file for the IOT service
cfg = './config.cfg'
def readConfig(cfg):
    logger.info('readConfig()...')
    opts = ibmiotf.device.ParseConfigFile(cfg)
    return opts


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
t = []

class Worker(threading.Thread):
    def __init__(self, name, id):
        threading.Thread.__init__(self)
        self.myName = name
        self.myID = id
    def run(self):
        print (self.myID)
        streamCollected = listen(self.myID)
        while True:
            try:
                data = streamCollected.read(CHUNK)
                rms  = audioop.rms(data, 2)
                if rms > 5000:
                    timeStamp = int(round(time.time()*1000))
                    pushData(rms,client,timeStamp)
            except IOError as e:
                print( "Error recording: %s" % (e) )
                break

def find_input_device(pa):
    device_index = None
    for i in range(pa.get_device_count() ):
        devinfo = pa.get_device_info_by_index(i)
        print( "Found device %d: %s" % (i, devinfo["name"]) )

        for keyword in ["usb"]:
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
    for i in range(4):
        t[i].exit()
    sys.exit(0)

def listen(id):
    stream = pa.open(
        format             = FORMAT,
        channels           = CHANNELS,
        rate               = RATE,
        input              = True,
        input_device_index = id,
        frames_per_buffer  = CHUNK
    )

    return stream

def initialize():
    try:
        options = readConfig(cfg)
        if options is None:
            options = {
                "org": vcap["iotf-service"][0]["credentials"]["org"],
                "id": vcap["iotf-service"][0]["credentials"]["iotCredentialsIdentifier"],
                "auth-method": "apikey",
                "auth-key": vcap["iotf-service"][0]["credentials"]["apiKey"],
                "auth-token": vcap["iotf-service"][0]["credentials"]["apiToken"]
            }
        cli = ibmiotf.device.Client(options)
        cli.connect()
        return cli
    except ibmiotf.ConnectionException as e:
        print(e)

def pushData(result , client, timeStamp):
    jsondata = {"Microphone" : { "stream" : str(result) }, "Time" :{"timestamp" : timeStamp}, "Id" :{"microphoneId": 1}}
    client.publishEvent("status","json",jsondata)

if __name__ == "__main__":
    pa = pyaudio.PyAudio()
    client=initialize()
    signal.signal(signal.SIGINT, signal_handler)
    device_index = find_input_device(pa)
    for i in range(4):
        t.append(Worker("Thread", i))
        t[i].start()

    # stream.stop_stream()
    # stream.close()
    # pa.terminate()
