import os
import subprocess
import configparser
import tkinter as tk
from tkinter import filedialog, ttk
import re
import json
import threading

from time import perf_counter
from datetime import datetime
from datetime import timedelta


# Definisci una palette di colori in stile Material Design
PRIMARY_COLOR = "#1e3a8a"  # Blu
PRIMARY_VARIANT_COLOR = "#1e2a47"  # Blu scuro
SECONDARY_COLOR = "#03dac6"
BACKGROUND_COLOR = "#121212"
SURFACE_COLOR = "#1d1d1d"
TEXT_COLOR = "#ffffff"
TEXT_SECONDARY_COLOR = "#b0b0b0"


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
            self.config["Settings"] = {"crf_value": "27"}
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
        self.root.geometry("800x850")
        self.root.configure(bg=BACKGROUND_COLOR)
        self.quality_mode = tk.StringVar(value="crf")  # Default to CRF
        # Variabili di configurazione
        self.ffmpeg_path = self.config.get(
            "Paths", "ffmpeg_path", fallback="ffmpeg_files/ffmpeg.exe"
        )
        self.ffprobe_path = self.config.get(
            "Paths", "ffprobe_path", fallback="ffmpeg_files/ffprobe.exe"
        )
        self.input_folder = self.config.get("Paths", "input_folder", "")
        self.output_folder = self.config.get("Paths", "output_folder", "")
        self.crf_value = tk.IntVar(
            value=int(self.config.get("Settings", "crf_value", "27"))
        )
        if not os.path.isfile(self.ffmpeg_path) or not os.path.isfile(
            self.ffprobe_path
        ):
            raise FileNotFoundError(
                "Assicurati che i file ffmpeg.exe e ffprobe.exe siano nei percorsi specificati."
            )
        # Inizializza i componenti dell'interfaccia
        self.create_widgets()
        self.root.mainloop()

    def create_widgets(self):
        # Frame per la selezione della cartella
        folder_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        folder_frame.pack(pady=10, fill="x", padx=20)

        self.folder_label = tk.Label(
            folder_frame,
            text="Nessuna cartella selezionata",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        )
        self.folder_label.pack(side=tk.LEFT, expand=True)
        if self.input_folder:
            self.folder_label.config(text=self.input_folder)
        select_button = tk.Button(
            folder_frame,
            text="Seleziona cartella",
            command=self.select_folder,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=10,
            pady=5,
        )
        select_button.pack(side=tk.RIGHT)

        # Stato e progress bar
        self.status_label = tk.Label(
            self.root,
            text="Pronto per la conversione",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        )
        self.status_label.pack(pady=10)
        self.file_label = tk.Label(
            self.root, text="", fg=TEXT_COLOR, bg=BACKGROUND_COLOR
        )
        self.file_label.pack(pady=5)
        self.progress_bar = ttk.Progressbar(
            self.root, orient="horizontal", length=700, mode="determinate"
        )
        self.progress_bar.pack(pady=20)

        # Log Text Area
        self.log_text_area = tk.Text(
            self.root,
            wrap="word",
            height=15,
            bg=SURFACE_COLOR,
            fg=TEXT_COLOR,
            bd=0,
            padx=10,
            pady=10,
        )
        self.log_text_area.pack(pady=10, padx=10, fill="both", expand=True)

        # Frame per la selezione della cartella di output
        output_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        output_frame.pack(pady=10, fill="x", padx=20)

        self.output_label = tk.Label(
            output_frame,
            text="Nessuna cartella di output selezionata",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        )
        self.output_label.pack(side=tk.LEFT, expand=True)
        if self.output_folder:
            self.output_label.config(text=self.output_folder)
        select_output_button = tk.Button(
            output_frame,
            text="Seleziona cartella di output",
            command=self.select_output_folder,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=10,
            pady=5,
        )
        select_output_button.pack(side=tk.RIGHT)

        # Selezione della modalità qualità (CRF o CQ) con il relativo slider
        quality_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        quality_frame.pack(pady=10, fill="x", padx=20)

        tk.Label(
            quality_frame,
            text="Seleziona Modalità di Qualità:",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        ).pack(side=tk.TOP)

        # Creazione dei RadioButton (CRF e CQ)
        radio_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        radio_frame.pack(pady=10)

        crf_radio = tk.Radiobutton(
            radio_frame,
            text="CRF",
            variable=self.quality_mode,
            value="crf",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            activeforeground=SECONDARY_COLOR,
            relief="flat",
        )
        crf_radio.pack(side=tk.LEFT, padx=10)

        cq_radio = tk.Radiobutton(
            radio_frame,
            text="CQ",
            variable=self.quality_mode,
            value="cq",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            activeforeground=SECONDARY_COLOR,
            relief="flat",
        )
        cq_radio.pack(side=tk.LEFT)

        # Frame per il CRF slider
        crf_slider_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        crf_slider_frame.pack(pady=10, fill="x", padx=20)

        crf_slider_label = tk.Label(
            crf_slider_frame, text="Valore:", fg=TEXT_COLOR, bg=BACKGROUND_COLOR
        )
        crf_slider_label.pack(side=tk.TOP, padx=(10, 0))

        crf_slider = tk.Scale(
            crf_slider_frame,
            from_=0,
            to=51,
            orient="horizontal",
            variable=self.crf_value,
            bg=BACKGROUND_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_COLOR,
            troughcolor=PRIMARY_VARIANT_COLOR,
            sliderlength=20,  # Aumenta la dimensione del cursore per il Material Design
            length=300,  # Larghezza dello slider
            tickinterval=5,
            highlightthickness=0,  # Rimuove il bordo di default
        )
        crf_slider.pack(side=tk.TOP)

        # Pulsante Avvia conversione
        start_button = tk.Button(
            self.root,
            text="Avvia conversione",
            command=self.start_conversion,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=20,
            pady=10,
        )
        start_button.pack(pady=10)
        # Pulsante per fermare ffmpeg
        self.stop_button = tk.Button(
            self.root,
            text="Ferma FFMPEG",
            command=self.stop_ffmpeg,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=20,
            pady=10,
            state=tk.DISABLED,
        )
        self.stop_button.pack(pady=20)

    def log_message(self, message):
        self.log_text_area.insert(tk.END, message + "\n")
        self.log_text_area.see(tk.END)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_label.config(text=folder_selected)
            self.input_folder = folder_selected
            self.config.update("Paths", "input_folder", folder_selected)

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_label.config(text=folder_selected)
            self.output_folder = folder_selected
            self.config.update("Paths", "output_folder", folder_selected)

    def get_dynamic_cq(
        self, width, height, min_cq=16, max_cq=30, output_resolution=(1280, 720)
    ):
        if width is None or height is None or width <= 0 or height <= 0:
            print("Larghezza o altezza video non valide.")
            return None

        output_width, output_height = output_resolution
        output_area = output_width * output_height
        video_area = width * height

        # Se la risoluzione del video è maggiore o uguale a quella di output
        if video_area >= output_area:
            # Per video con risoluzioni maggiori, aumentiamo il CQ (per ridurre la qualità)
            dynamic_cq = min(
                max_cq, int(min_cq + (video_area / output_area) * (max_cq - min_cq))
            )
        else:
            # Per video con risoluzioni minori, riduciamo il CQ, ma con una riduzione più moderata
            scaling_factor = (output_area / video_area) ** 0.5
            dynamic_cq = max(min_cq, min(int(min_cq / scaling_factor), max_cq))

            # Limitiamo l'aumento per non migliorare troppo la qualità
            dynamic_cq = max(min_cq, dynamic_cq)

        return dynamic_cq

    def get_dynamic_crf(
        self, width, height, min_crf=18, max_crf=28, output_resolution=(1280, 720)
    ):
        if width is None or height is None or width <= 0 or height <= 0:
            print("Larghezza o altezza video non valide.")
            return None

        output_width, output_height = output_resolution
        output_area = output_width * output_height
        video_area = width * height

        # Se la risoluzione del video è maggiore o uguale a quella di output
        if video_area >= output_area:
            # Per video con risoluzioni maggiori, aumentiamo il CRF (per ridurre la qualità)
            dynamic_crf = min(
                max_crf, int(min_crf + (video_area / output_area) * (max_crf - min_crf))
            )
        else:
            # Per video con risoluzioni minori, riduciamo il CRF, ma con una riduzione più moderata
            scaling_factor = (output_area / video_area) ** 0.5
            dynamic_crf = max(min_crf, min(int(min_crf / scaling_factor), max_crf))

            # Limitiamo l'aumento per non migliorare troppo la qualità
            dynamic_crf = max(min_crf, dynamic_crf)

        return dynamic_crf

    def get_mediainfo(self, video_path):
        """Ottieni dettagli mediainfo (video e audio) del file utilizzando ffprobe."""
        command = [
            self.ffprobe_path,
            "-v", "error",  # Disabilita i log di errore
            "-show_entries",
            "format=filename,format_name,format_long_name,bit_rate,duration,streams",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,bit_rate,channels,sample_rate,duration,frame_rate,frame_count,bit_depth",
            "-of", "json",  # Output in formato JSON
            video_path,
        ]

        try:
            # Esegui il comando e cattura l'output e gli errori
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            stdout, stderr = process.communicate()

            # Verifica se il comando è stato eseguito correttamente
            if process.returncode != 0:
                self.log_message(
                    f"Errore ottenendo mediainfo per {video_path}: {stderr}"
                )
                return {}

            # Decodifica l'output JSON
            try:
                info = json.loads(stdout)
            except json.JSONDecodeError:
                self.log_message(f"Errore di decodifica JSON per {video_path}")
                return {}

            # Estrai informazioni generali e sui flussi
            media_info = {                
                "media": {
                    "@ref": video_path,
                    "track": []
                }
            }

            # Aggiungi informazioni generali sul formato
            format_info = info.get("format", {})
            general_info = {
                "@type": "General",
                "VideoCount": len([stream for stream in info["streams"] if stream["codec_type"] == "video"]),
                "AudioCount": len([stream for stream in info["streams"] if stream["codec_type"] == "audio"]),
                "FileExtension": video_path.split('.')[-1],
                "Format": format_info.get("format_name", "N/A"),
                "Duration": format_info.get("duration", "N/A"),
                "FileSize": format_info.get("bit_rate", "N/A"),
                "OverallBitRate": format_info.get("bit_rate", "N/A"),
                "Recorded_Date": datetime.now().year,
                "File_Created_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f UTC"),
                "File_Modified_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f UTC"),
            }

            media_info["media"]["track"].append(general_info)

            # Aggiungi informazioni sui flussi video e audio
            for stream in info["streams"]:
                stream_info = {
                    "@type": stream.get("codec_type", "N/A").capitalize(),
                    "StreamOrder": str(stream.get("index", "N/A")),
                    "ID": str(stream.get("index", "N/A")),
                    "Format": stream.get("codec_name", "N/A"),
                    "Duration": stream.get("duration", "N/A"),
                    "BitRate": stream.get("bit_rate", "N/A"),
                }

                if stream["codec_type"] == "video":
                    stream_info.update({
                        "Width": stream.get("width", "N/A"),
                        "Height": stream.get("height", "N/A"),
                        "FrameRate": stream.get("r_frame_rate", "N/A"),
                        "FrameCount": stream.get("nb_frames", "N/A"),
                        "BitDepth": stream.get("bit_depth", "8"),
                    })
                elif stream["codec_type"] == "audio":
                    stream_info.update({
                        "Channels": stream.get("channels", "N/A"),
                        "SamplingRate": stream.get("sample_rate", "N/A"),
                    })

                media_info["media"]["track"].append(stream_info)

            return media_info

        except subprocess.SubprocessError as e:
            # Cattura eventuali errori del subprocess
            self.log_message(f"Errore eseguendo ffprobe per {video_path}: {str(e)}")
            return {}

    def get_video_info(self, input_path):
        command = [self.ffmpeg_path, "-i", input_path]
        process = subprocess.Popen(
            command,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        stdout, stderr = process.communicate()

        # Trova le informazioni sulla risoluzione
        match = re.search(r"(\d{2,5})x(\d{2,5})", stderr)
        if match:
            width_str, height_str = match.groups()
            try:
                width = int(width_str.strip())
                height = int(height_str.strip())
            except ValueError:
                self.log_message(
                    f"Errore nel parsing della risoluzione del video: {width_str}x{height_str}"
                )
                return None, None, None
        else:
            self.log_message("Risoluzione del video non trovata.")
            return None, None, None

        # Trova la durata del video
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", stderr)
        if duration_match:
            hours, minutes, seconds = map(float, duration_match.groups())
            duration = hours * 3600 + minutes * 60 + seconds
        else:
            duration = None  # Durata non trovata

        return width, height, duration
    
    def stop_ffmpeg(self):
        # Se il processo ffmpeg è attivo, lo fermiamo
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()  # Invia il comando per terminare il processo
            self.ffmpeg_process = None  # Reset del processo
            self.log_message("Ffmpeg fermato.")
            
            # Disabilita il pulsante di stop
            self.stop_button.config(state=tk.DISABLED)
    
    def convert_video(self, input_path, output_path, file_index, total_files):
        width, height, duration = self.get_video_info(input_path)
        if duration is None or width is None or height is None:
            self.log_message(
                f"Impossibile ottenere informazioni video per {input_path}."
            )
            return

        # Scale filter for resolution
        scale_filter = (
            "scale=1280:720,format=yuv420p"
            if (width > 1280 or height > 720)
            else "scale=-1:-1,format=yuv420p"
        )

        # Set command based on selected quality mode
        if self.quality_mode.get() == "crf":
            quality_option = "-crf"
            quality_value = self.crf_value.get()  # Get the value from the slider
        else:
            quality_option = "-cq"
            quality_value = (
                self.crf_value.get()
            )  # Use the same slider value for CQ for simplicity
        mediainfo_before = self.get_mediainfo(input_path)
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
            quality_option,
            str(quality_value),
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
        self.log_message(
            f"Parametri impostati: {quality_option.upper()}={quality_value},{scale_filter}"
        )
        start_time = perf_counter()
        process = subprocess.Popen(
            command,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=self.creationflags,
            startupinfo=self.startupinfo,
            encoding="utf-8",
        )
        self.ffmpeg_process = process
        # Abilita il pulsante di stop
        self.stop_button.config(state=tk.NORMAL)
        try:
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
            end_time = perf_counter()
            elapsed_time = end_time - start_time
            self.log_message(
                f"Conversione completata in {timedelta(seconds=int(elapsed_time))}"
            )
            mediainfo_after = self.get_mediainfo(output_path)
            # Save both mediainfo data to a JSON file
            report = {
                "input_file": input_path,
                "output_file": output_path,
                "mediainfo_before": mediainfo_before,
                "mediainfo_after": mediainfo_after,
            }
            json_report_path = os.path.splitext(output_path)[0] + "_mediainfo.json"
            with open(json_report_path, "w") as json_file:
                json.dump(report, json_file, indent=4)

            # Log the completion message with JSON report path
            self.log_message(f"Rapporto mediainfo salvato in: {json_report_path}")

        except Exception as e:
            self.log_message(f"Errore durante la conversione di {input_path}: {str(e)}")
        finally:
            if process.poll() is None:  # Controlla se il processo è ancora attivo
                process.terminate()  # Tenta di chiuderlo in modo pulito
                try:
                    process.wait(timeout=5)  # Attendi la chiusura
                except subprocess.TimeoutExpired:
                    process.kill()  # Forza la chiusura
                self.log_message("Processo FFmpeg terminato.")

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
            filenm = (
                f"{os.path.splitext(os.path.basename(input_path))[0]}.mp4"
                if self.output_folder
                else f"{os.path.splitext(os.path.basename(input_path))[0]}_nw.mp4"
            )
            output_folder = (
                self.output_folder
                if self.output_folder
                else os.path.dirname(input_path)
            )
            output_path = os.path.join(output_folder, filenm)
            self.convert_video(input_path, output_path, index, total_files)

        self.status_label.config(text="Conversione batch completata!")
        self.progress_bar["value"] = 0

    def start_conversion(self):
        threading.Thread(target=self.batch_convert, daemon=True).start()


if __name__ == "__main__":
    VideoConverterApp()
