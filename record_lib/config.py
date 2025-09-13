import json
from os.path import isfile

import pyaudio

DEFAULT_CONFIG = {}


class Config:
    audio_format = pyaudio.paInt24
    audio_output_format = "adts"
    audio_file_format = "aac"
    audio_channels = 1
    audio_rate = 44100
    audio_chunk = 1024
    audio_seg_duration = 15 * 60
    audio_bitrate = "400k"
    audio_save_path = r"D:\BSR-Data"
    rec_start_failed_stop = 0
    rec_start_failed_wait = 20
    recording_failed_stop = 10
    recording_failed_wait = 1
    shutdown_listener_title = "BackSoundRec Shutdown Listener"
    record_save_join_timeout = 60

    def __init__(self):
        self.load()
        self.save()

    def load(self):
        config_data = {}
        if isfile("config.json"):
            with open("config.json", "r") as f:
                config_data = json.loads(f.read())
        for name in self.get_all_config_names():
            if name in config_data:
                setattr(self, name, config_data[name])

    def save(self):
        config_data = {}
        for name in self.get_all_config_names():
            config_data[name] = getattr(self, name)
        with open("config.json", "w") as f:
            f.write(json.dumps(config_data, indent=4))

    def get_all_config_names(self):
        names = []
        for attr_name in dir(self):
            if attr_name.startswith("__"):
                continue
            if "method" in str(getattr(self, attr_name)):
                continue
            names.append(attr_name)
        return names


config: Config = Config()
