#!/usr/bin/env python

# http://stackoverflow.com/questions/26478315/getting-volume-levels-from-pyaudio-for-use-in-arduino

#For Audio analysis
import pyaudio
import wave
import audioop
import signal
import sys

#Iot service dependencies
import os, json, math, time, logging
import ibmiotf.device
import configparser

import numpy as np
import math
from matplotlib.mlab import find

#Logging
logging.basicConfig(filename='output.log',level=logging.DEBUG,format='%(asctime)s %(module)s %(thread)s %(message)s')
logger = logging.getLogger(__name__)

#Config file for the IOT service
CFG = './config.cfg'
DEVICE_CFG = './config.json'
CHUNK = 1024
FORMAT = pyaudio.paInt16
# INPUT_BLOCK_TIME = 0.05
# CHUNK = int(RATE * INPUT_BLOCK_TIME)

def readConfig(cfg):
    logger.info('readConfig()...')
    opts = ibmiotf.device.ParseConfigFile(cfg)
    return opts

def read_device_config():
    config = []
    with open(DEVICE_CFG, 'r') as f:
        config = json.load(f)
    return config

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

def get_stream(cfg):
    stream = pa.open(
        format             = FORMAT,
        channels           = int(cfg["channels"]),
        rate               = int(cfg["rate"]),
        input              = True,
        input_device_index = int(cfg["index"]),
        frames_per_buffer  = CHUNK
    )

    return stream

def get_client():
    try:
        options = readConfig(CFG)
        if options is None:
            options = {
                "org": vcap["iotf-service"][0]["credentials"]["org"],
                "id": vcap["iotf-service"][0]["credentials"]["iotCredentialsIdentifier"],
                "auth-method": "apikey",
                "auth-key": vcap["iotf-service"][0]["credentials"]["apiKey"],
                "auth-token": vcap["iotf-service"][0]["credentials"]["apiToken"]
            }
        client = ibmiotf.device.Client(options)
        logger.info("Client aquired")
        client.connect()
        return client
    except ibmiotf.ConnectionException as e:
        print(e)

def push_data(client, data, pitch):
    jsondata = {"Microphone" : { "stream" : str(data), "pitch": pitch }}
    client.publishEvent("status", "json", jsondata)

def find_pitch(signal, rate):
    signal = np.fromstring(signal, 'Int16');
    crossing = [math.copysign(1.0, s) for s in signal]
    index = find(np.diff(crossing));
    f0=round(len(index) * rate / (2 * np.prod(len(signal))))
    return f0;

if __name__ == "__main__":
    pa = pyaudio.PyAudio()

    devices = read_device_config()

    device = devices[0]
    print ("Using device: %s" % device["name"])

    client = get_client()
    stream = get_stream(device)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            data = stream.read(CHUNK)
            rms  = audioop.rms(data, 2)
            pitch = find_pitch(data, device["rate"])
            if rms > 5000:
                print("RMS: %d" % rms)
                print("Pitch: %d" % pitch)
                push_data(client, rms, pitch)
        except IOError as e:
            print( "Error recording: %s" % (e) )
            break

    stream.stop_stream()
    stream.close()
    pa.terminate()
