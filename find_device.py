#!/usr/bin/env python

import pyaudio
import json

def print_input_devices(pa):
    device_index = None
    for i in range( pa.get_device_count() ):
        devinfo = pa.get_device_info_by_index(i)
        print( "Found device #%d: %s" % (i, devinfo["name"]) )

    #     for keyword in ["usb"]:
    #         if keyword in devinfo["name"].lower():
    #             print( "Matching device: %d - %s"%(i,devinfo["name"]) )
    #             device_index = i
    #         if device_index != None:
    #             return device_index
    #
    # if device_index == None:
    #     print( "No preferred input found; using default input device." )


def get_device_config(pa, device_index, device_name):
    devinfo = pa.get_device_info_by_index(device_index)
    return {
        "index"   : device_index,
        "rate"    : devinfo["defaultSampleRate"],
        "channels": devinfo["maxInputChannels"],
        "name"    : device_name
    }

# CHUNK = 1024
# FORMAT = pyaudio.paInt16
# CHANNELS = 1
# RATE = 44100

if __name__ == "__main__":
    pa = pyaudio.PyAudio()

    print_input_devices(pa)

    config = []
    while True:
        try:
            c = raw_input("Pick your device, q to exit: ")
            if c == "q":
                break
            device_name = raw_input("Name your device: ")
            device_index = int(c)
        except ValueError:
            print "Not a number or q"
            continue

        config.append( get_device_config(pa, device_index, device_name) )


    with open('config.json', 'w') as f:
        json.dump(config, f)
