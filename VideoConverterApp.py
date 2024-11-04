import os
import subprocess
import configparser
import tkinter as tk
from tkinter import filedialog, ttk
import re
import threading
from time import perf_counter
from datetime import timedelta


class ConfigManager:
    """Gestisce la configurazione per il convertitore video."""

    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        if not os.path.isfile(self.config_file):
            self.config["Paths"] = {"ffmpeg_path": "ffmpeg", "ffprobe_path": "ffprobe"}
            self.config["Settings"] = {"input_folder": "", "crf_value": "23"}
            with open(self.config_file, "w") as configfile:
                self.config.write(configfile)
        self.config.read(self.config_file)

    def get(self, section, option, fallback=None):
        return self.config.get(section, option, fallback=fallback)

    def update(self, section, option, value):
        self.config.set(section, option, value)
        with open(self.config_file, "w") as configfile:
            self.config.write(configfile)


class VideoConverterApp:
    def __init__(self):
        self.creationflags = 0
        self.startupinfo = None
        if os.name == "nt":  # Solo per Windows
            self.creationflags = subprocess.CREATE_NO_WINDOW
            self.startupinfo = subprocess.STARTUPINFO()
            self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.config = ConfigManager()
        self.root = tk.Tk()
        self.root.title("Video Converter")
        self.root.geometry("800x600")

        # Variabili di configurazione
        self.ffmpeg_path = self.config.get("Paths", "ffmpeg_path", "ffmpeg")
        self.ffprobe_path = self.config.get("Paths", "ffprobe_path", "ffprobe")
        self.input_folder = self.config.get("Settings", "input_folder", "")
        self.crf_value = int(self.config.get("Settings", "crf_value", "23"))

        # Inizializza i componenti dell'interfaccia
        self.create_widgets()
        self.root.mainloop()

    def create_widgets(self):
        self.folder_label = tk.Label(self.root, text="Nessuna cartella selezionata")
        self.folder_label.pack(pady=10)
        select_button = tk.Button(
            self.root, text="Seleziona cartella", command=self.select_folder
        )
        select_button.pack(pady=5)
        self.status_label = tk.Label(self.root, text="Pronto per la conversione")
        self.status_label.pack(pady=10)
        self.file_label = tk.Label(self.root, text="")
        self.file_label.pack(pady=5)
        self.progress_bar = ttk.Progressbar(
            self.root, orient="horizontal", length=700, mode="determinate"
        )
        self.progress_bar.pack(pady=20)
        self.log_text_area = tk.Text(self.root, wrap="word", height=15)
        self.log_text_area.pack(pady=10, padx=10, fill="both", expand=True)
        start_button = tk.Button(
            self.root, text="Avvia conversione", command=self.start_conversion
        )
        start_button.pack(pady=5)

    def log_message(self, message):
        self.log_text_area.insert(tk.END, message + "\n")
        self.log_text_area.see(tk.END)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_label.config(text=folder_selected)
            self.input_folder = folder_selected
            self.config.update("Settings", "input_folder", folder_selected)

    def get_video_info(self, input_path):
        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "csv=p=0",
            input_path,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                creationflags=self.creationflags,
                startupinfo=self.startupinfo,
            )

            # Pulisce l'output utilizzando espressioni regolari per trovare solo i numeri
            values = re.findall(r"[\d.]+", result.stdout.strip())

            # Controlla se abbiamo ottenuto esattamente tre valori per larghezza, altezza e durata
            if len(values) < 3:
                raise ValueError("Output di ffprobe incompleto o non valido")

            width, height, duration = map(float, values[:3])
            return int(width), int(height), duration

        except Exception as e:
            self.log_message(f"Errore: {str(e)}")
            return None, None, None

    def convert_video(self, input_path, output_path, file_index, total_files):
        width, height, duration = self.get_video_info(input_path)
        if duration is None:
            return

        scale_filter = (
            "scale=1280:720,format=yuv420p"
            if (width > 1280 or height > 720)
            else "scale=-1:-1,format=yuv420p"
        )
        command = [
            self.ffmpeg_path,
            "-y",
            "-hwaccel",
            "cuda",
            "-i",
            input_path,
            "-vf",
            scale_filter,
            "-c:v",
            "h264_nvenc",
            "-crf",
            str(self.crf_value),
            "-preset",
            "fast",
            "-movflags",
            "faststart",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]

        start_time = perf_counter()
        process = subprocess.Popen(
            command,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=self.creationflags,
            startupinfo=self.startupinfo,
        )
        
        self.file_label.config(text=f"Converting: {os.path.basename(input_path)}")
        self.status_label.config(text=f"Conversione {file_index}/{total_files}: 0%")

        for line in process.stderr:
            time_match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
            if time_match:
                current_time = self.parse_time_to_seconds(time_match.group(1))
                progress = (current_time / duration) * 100
                self.progress_bar["value"] = progress
                remaining_time = max(duration - current_time, 0)
                estimated_time = str(timedelta(seconds=int(remaining_time)))

                self.status_label.config(
                    text=f"Conversione {file_index}/{total_files}: {int(progress)}% - Rimanente: {estimated_time}"
                )
                self.status_label.update_idletasks()

        process.wait()
        
        if process.returncode != 0:
            error_message = process.stderr.read()
            self.log_message(f"Errore durante la conversione: {error_message}")
            return
        
        end_time = perf_counter()
        elapsed_time = end_time - start_time
        self.log_message(
            f"Conversione completata per '{os.path.basename(output_path)}' in {timedelta(seconds=int(elapsed_time))}"
        )


    def parse_time_to_seconds(self, time_str):
        h, m, s = map(float, time_str.split(":"))
        return h * 3600 + m * 60 + s

    def batch_convert(self):
        allowed_extensions = (".mp4", ".mov", ".avi", ".mkv", ".flv", ".webm", ".wmv")
        if not self.input_folder:
            self.log_message("Seleziona una cartella valida.")
            return

        file_paths = [
            os.path.join(self.input_folder, filename)
            for filename in os.listdir(self.input_folder)
            if filename.endswith(allowed_extensions)
        ]
        total_files = len(file_paths)

        if not file_paths:
            self.log_message("Nessun file video trovato.")
            return

        for index, input_path in enumerate(file_paths, start=1):
            output_path = os.path.join(
                self.input_folder,
                f"{os.path.splitext(os.path.basename(input_path))[0]}_nw{os.path.splitext(input_path)[1]}",
            )
            self.convert_video(input_path, output_path, index, total_files)

        self.status_label.config(text="Conversione batch completata!")
        self.progress_bar["value"] = 0

    def start_conversion(self):
        threading.Thread(target=self.batch_convert, daemon=True).start()


if __name__ == "__main__":
    VideoConverterApp()
