import os
import configparser

class ConfigManager:
    """Gestisce la configurazione per il convertitore video."""

    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
        # Variabile per memorizzare il processo ffmpeg
        self.ffmpeg_process = None

    def load_config(self):
        if not os.path.isfile(self.config_file):
            self.config["Paths"] = {
                "ffmpeg_path": "ffmpeg_files/ffmpeg.exe",
                "ffprobe_path": "ffmpeg_files/ffprobe.exe",
                "input_folder": "",
                "output_folder": "",
            }
            self.config["Settings"] = {"crf_value": "25"}
            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
        with open(self.config_file, "r", encoding="utf-8") as configfile:
            self.config.read_file(configfile)

    def get(self, section, option, fallback=None):
        return self.config.get(section, option, fallback=fallback)

    def update(self, section, option, value):
        self.config.set(section, option, value)
        with open(self.config_file, "w", encoding="utf-8") as configfile:
            self.config.write(configfile)