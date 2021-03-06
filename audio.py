#!/usr/bin/env python

# http://stackoverflow.com/questions/26478315/getting-volume-levels-from-pyaudio-for-use-in-arduino

# For Audio analysis
import pyaudio
import wave
import audioop
import signal
import sys
import time
import threading
import struct

# IoT service dependencies
import os
import json
import logging
import ibmiotf.device
import configparser

# Math
import numpy as np
import math

# Logging
logging.basicConfig(filename='output.log',level=logging.DEBUG,format='%(asctime)s %(module)s %(thread)s %(message)s')
logger = logging.getLogger(__name__)

# Config file for the IOT service
CFG = './config.cfg'
DEVICE_CFG = './config.json'
CHUNK = 4196
FORMAT = pyaudio.paInt16
RMS_THRESHOLD = 3000
PITCH_THRESHOLD = [900, 4000]

# INPUT_BLOCK_TIME = 0.05
# CHUNK = int(RATE * INPUT_BLOCK_TIME)

def read_config(cfg):
    logger.info('read_config()...')
    opts = ibmiotf.device.ParseConfigFile(cfg)
    return opts

def read_device_config():
    config = []
    with open(DEVICE_CFG, 'r') as f:
        config = json.load(f)
    return config

threads = []
killswitch = False
mutex = threading.Lock()

class Worker(threading.Thread):
    def __init__(self, name, device):
        threading.Thread.__init__(self)
        self.myName = name
        self.myDev = device
    def run(self):
        global killswitch
        print("Worker thread for %s online " % self.myName)
        print("Device description: " + str(self.myDev))
        stream = get_stream(self.myDev)

        while not killswitch:
            try:
                data = stream.read(CHUNK)
                rms  = audioop.rms(data, 2)
                pitch = find_pitch(data, self.myDev["rate"])
                timestamp = int(round(time.time()*1000))
                # pitch2 = max_frequency(data, self.myDev["rate"])
                if rms > RMS_THRESHOLD \
                   and pitch > PITCH_THRESHOLD[0]:
                #    and pitch < PITCH_THRESHOLD[1]:
                    with mutex:
                        print("\nName: %s" % self.myName)
                        print("RMS: %d" % rms)
                        print("Pitch: %d" % pitch)
                        print("TS: %s" % (timestamp % 1000))
                        # print("Pitch2: %d" % pitch2)
                        hit_add(rms, pitch, timestamp, self.myName)
                    # push_data_to_server(client, rms, pitch, timestamp, self.myName)
            except IOError as e:
                print( "Error recording: %s" % (e) )
                killswitch = True

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    global killswitch
    killswitch = True
    for t in threads:
        t.join()
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
        options = read_config(CFG)
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

hits = []
hits_mtx = threading.Lock()
def hit_add(volume, pitch, timestamp, id):
    with hits_mtx:
        hits.append({"volume": volume, "pitch": pitch, "ts": timestamp, "id": id})

def hits_processor():
    global killswitch
    while not killswitch:
        time.sleep(0.2)
        with hits_mtx:
            if len(hits) > 0:
                max_ts = hits[0]["ts"]
                max_vol = hits[0]["volume"]
                max_id = hits[0]["id"]
                max_pitch = hits[0]["pitch"]
                while len(hits) > 0 and abs(hits[0]["ts"] - max_ts) < 100:
                    if hits[0]["volume"] > max_vol:
                        max_vol = hits[0]["volume"]
                        max_id = hits[0]["id"]
                    hits.pop(0)
                print "Sending ID = %s, volume = %s" % (max_id, max_vol)
                if max_id == "0":
                    print "<" * 40
                else:
                    print ">" * 40
                push_data_to_server(client, max_vol, max_pitch, max_ts, max_id)

def push_data_to_server(client, volume, pitch, timestamp, id):
    jsondata = {
        "Microphone" : {"stream" : str(volume)},
        "Time" : {"timestamp" : timestamp},
        "Id" :{"microphoneId": id}
    }
    client.publishEvent("status", "json", jsondata)

# http://stackoverflow.com/questions/9082431/frequency-analysis-in-python
def find_pitch(signal, rate):
    signal = np.fromstring(signal, 'Int16');
    crossing = [math.copysign(1.0, s) for s in signal]
    index = np.count_nonzero(np.diff(crossing));
    f0=round(index * rate / (2 * np.prod(len(signal))))
    return f0;

def separator():
    global killswitch
    while not killswitch:
        time.sleep(1.0)
        with mutex:
            print "-"*20 + time.strftime("%H:%M:%S") + "-"*20

if __name__ == "__main__":
    pa = pyaudio.PyAudio()

    devices = read_device_config()
    client = get_client()

    signal.signal(signal.SIGINT, signal_handler)

    for i, device in enumerate(devices):
        threads.append(Worker(device["name"], device))
        threads[i].start()

    sep = threading.Thread(target = separator)
    threads.append(sep)
    sep.start()

    hp = threading.Thread(target = hits_processor)
    threads.append(hp)
    hp.start()

    while not killswitch:
        pass

    for t in threads:
        t.join()
    print "Exiting Main Thread"

    # stream.stop_stream()
    # stream.close()
    # pa.terminate()
