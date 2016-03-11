# Installation

## MacOS X:
```
brew install portaudio
sudo brew link portaudio
pip install pyaudio configparser ibmiotf numpy
```

## Raspbery Pi
To clone use `GIT_SSL_NO_VERIFY=false git clone https://github.com/iot-hackathon/audio-analysis.git` or set `git config --global http.sslVerify false` beforehand.

# Usage
First run `find_device.py` to create a devices config file.
Then run `audio.py` to start detecting hits using the configured devices. 
