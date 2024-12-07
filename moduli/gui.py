import os
import subprocess
import re
import json
import threading

from moduli.config_manager import ConfigManager
from moduli.utils import Utils
from moduli.utils import Logger
from moduli.ffmpeg import FFmpegDownloader
from moduli.icon import ICON_APP

import tkinter as tk
from tkinter import messagebox
from time import perf_counter
from datetime import datetime
from datetime import timedelta
from tkinter import filedialog, ttk
import base64
from io import BytesIO
from PIL import Image, ImageTk
from send2trash import send2trash

# Definisci una palette di colori in stile Material Design
PRIMARY_COLOR = "#1e3a8a"  # Blu
PRIMARY_VARIANT_COLOR = "#1e2a47"  # Blu scuro
SECONDARY_COLOR = "#03dac6"
BACKGROUND_COLOR = "#121212"
SURFACE_COLOR = "#1d1d1d"
TEXT_COLOR = "#ffffff"
TEXT_SECONDARY_COLOR = "#b0b0b0"


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
        """Imposta l'icona della finestra da una stringa Base64."""
        # Decodifica la stringa Base64 e ottieni l'immagine
        img = self.base64_to_image(ICON_APP)
        icon = ImageTk.PhotoImage(img)

        # Imposta l'icona della finestra
        self.root.iconphoto(False, icon)
        # Imposta la finestra principale
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 1200
        window_height = 900
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.root.geometry(
            f"{window_width}x{window_height}+{position_right}+{position_top}"
        )

        self.root.configure(bg=BACKGROUND_COLOR)
        self.quality_mode = tk.StringVar(value="crf")  # Default to CRF

        # Variabili di configurazione
        self.target_dir = self.config.get(
            "Paths", "ffmpeg_dir", fallback="ffmpeg_files/"
        )
        self.ffmpeg_exe = "ffmpeg.exe"
        self.ffprobe_exe = "ffprobe.exe"
        self.ffmpeg_path = os.path.join(self.target_dir, self.ffmpeg_exe)
        self.ffprobe_path = os.path.join(self.target_dir, self.ffprobe_exe)
        self.input_folder = self.config.get("Paths", "input_folder", "")
        self.output_folder = self.config.get("Paths", "output_folder", "")
        self.crf_value = tk.IntVar(
            value=int(self.config.get("Settings", "crf_value", "25"))
        )
        self.ffmpeg_process = False
        self.time_files = []
        self.utls = Utils(ffprobe_path=self.ffprobe_path)
        self.downloader = FFmpegDownloader(target_dir=self.target_dir)
        # Creazione del tema personalizzato
        self.create_style()

        # Creazione del notebook (container per le schede)
        self.notebook = ttk.Notebook(self.root, style="TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # Scheda 1: Conversione video
        self.create_widgets()

        # Scheda 2: Impostazioni
        self.create_setting()

        # Scheda 3: Impostazioni
        self.create_download_ffmpeg_tab()

        # Verifica la presenza dei file ffmpeg
        self.check_ffmpeg_files()

        self.root.mainloop()

    def base64_to_image(self, base64_string):
        """Converte una stringa Base64 in un'immagine."""
        img_data = base64.b64decode(base64_string)
        img = Image.open(BytesIO(img_data))
        return img

    def create_style(self):
        """Crea il tema personalizzato per il notebook."""
        style = ttk.Style()
        style.theme_use("default")  # Usa un tema base modificabile
        style.configure(
            "TNotebook",
            background=BACKGROUND_COLOR,
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=SURFACE_COLOR,
            foreground=TEXT_COLOR,
            padding=[10, 5],  # Margini interni della tab
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", PRIMARY_COLOR)],  # Colore tab attiva
            foreground=[("selected", TEXT_COLOR)],  # Colore testo tab attiva
        )
        style.configure(
            "TCombobox",
            fieldbackground=BACKGROUND_COLOR,
            background=BACKGROUND_COLOR,
            foreground=TEXT_COLOR,
            selectbackground=PRIMARY_VARIANT_COLOR,
        )

    def check_ffmpeg_files(self):
        """Verifica se i file ffmpeg sono presenti e disabilita il tab di conversione se necessario."""
        self.check_versions()
        if not os.path.isfile(self.ffmpeg_path) or not os.path.isfile(
            self.ffprobe_path
        ):
            # Se i file non esistono, seleziona la scheda "Scarica FFmpeg"
            self.notebook.select(
                self.notebook.tabs()[1]
            )  # Seleziona la seconda scheda (indice 1)
            self.notebook.tab(
                self.notebook.tabs()[0], state="disabled"
            )  # Disabilita il tab "Conversione Video"
            messagebox.showerror(
                "FFmpeg mancanti",
                "FFmpeg non trovato. Per favore, scarica FFmpeg per continuare.",
            )

    def create_widgets(self):
        # Frame per la selezione della cartella
        """Crea la scheda per la conversione video."""
        conversion_tab = ttk.Frame(self.notebook, style="TNotebook")
        self.notebook.add(conversion_tab, text="Conversione Video")

        folder_frame = tk.Frame(conversion_tab, bg=BACKGROUND_COLOR)
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
            conversion_tab,
            text="Pronto per la conversione",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        )
        self.status_label.pack(pady=10)
        self.file_label = tk.Label(
            conversion_tab, text="", fg=TEXT_COLOR, bg=BACKGROUND_COLOR
        )
        self.file_label.pack(pady=5)
        self.progress_bar = ttk.Progressbar(
            conversion_tab, orient="horizontal", length=700, mode="determinate"
        )
        self.progress_bar.pack(pady=20)

        # Log Text Area
        self.log_text_area = tk.Text(
            conversion_tab,
            wrap="word",
            height=15,
            bg=SURFACE_COLOR,
            fg=TEXT_COLOR,
            bd=0,
            padx=10,
            pady=10,
        )
        self.log_text_area.pack(pady=10, padx=10, fill="both", expand=True)

        self.conversion_txt = Logger(self.log_text_area)

        # Frame per la selezione della cartella di output
        output_frame = tk.Frame(conversion_tab, bg=BACKGROUND_COLOR)
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

        # Pulsante Avvia conversione
        self.start_button = tk.Button(
            conversion_tab,
            text="Avvia conversione",
            command=self.start_conversion,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=20,
            pady=10,
        )
        self.start_button.pack(pady=10)

        # Pulsante per fermare ffmpeg
        self.stop_button = tk.Button(
            conversion_tab,
            text="Ferma conversione",
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

    def create_setting(self):
        """Crea la scheda per il download di FFmpeg."""

        setting_tab = ttk.Frame(self.notebook, style="TNotebook")
        self.notebook.add(setting_tab, text="Impostazioni")

        # Selezione della modalità qualità (CRF o CQ) con il relativo slider
        quality_frame = tk.Frame(setting_tab, bg=BACKGROUND_COLOR)
        quality_frame.pack(pady=10, fill="x", padx=20)

        tk.Label(
            quality_frame,
            text="Seleziona Modalità di Qualità:",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        ).pack(side=tk.TOP)

        # Creazione dei RadioButton (CRF e CQ)
        radio_frame = tk.Frame(setting_tab, bg=BACKGROUND_COLOR)
        radio_frame.pack(pady=10, anchor="center")  # Centrato con margine verticale

        crf_radio = tk.Radiobutton(
            radio_frame,
            text="CRF",
            variable=self.quality_mode,
            value="crf",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            activeforeground=SECONDARY_COLOR,  # Colore quando il RadioButton è attivo
            selectcolor=PRIMARY_VARIANT_COLOR,  # Colore di selezione
            relief="flat",
        )
        crf_radio.pack(side=tk.LEFT, padx=20)

        cq_radio = tk.Radiobutton(
            radio_frame,
            text="CQ",
            variable=self.quality_mode,
            value="cq",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            activeforeground=SECONDARY_COLOR,  # Colore quando il RadioButton è attivo
            selectcolor=PRIMARY_VARIANT_COLOR,  # Colore di selezione
            relief="flat",
        )
        cq_radio.pack(side=tk.LEFT)

        # Frame per il CRF slider
        crf_slider_frame = tk.Frame(setting_tab, bg=BACKGROUND_COLOR)
        crf_slider_frame.pack(
            pady=10, anchor="center"
        )  # Centrato con margine verticale

        crf_slider_label = tk.Label(
            crf_slider_frame, text="Valore:", fg=TEXT_COLOR, bg=BACKGROUND_COLOR
        )
        crf_slider_label.pack(pady=5)

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
            sliderlength=20,  # Dimensione del cursore
            length=300,  # Larghezza dello slider
            tickinterval=5,
            highlightthickness=0,  # Rimuove il bordo di default
        )
        crf_slider.pack()

        # Aggiungi l'etichetta prima del codec
        codec_frame = tk.Frame(setting_tab, bg=BACKGROUND_COLOR)
        codec_frame.pack(pady=10, anchor="center")  # Centra il frame

        # Etichetta per il codec
        tk.Label(
            codec_frame,
            text="Seleziona Codec:",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        ).pack(
            anchor="w", pady=5
        )  # Etichetta allineata a sinistra

        # Menu a discesa per la selezione del codec
        self.codec = tk.StringVar(value="h264_nvenc")
        codec_menu = ttk.Combobox(
            codec_frame,
            textvariable=self.codec,
            values=[
                "libx264",  # Codifica video con H.264 (x264)
                "libx265",  # Codifica video con HEVC (H.265)
                "h264_nvenc",  # Codifica video H.264 usando GPU NVIDIA (accelerazione hardware)
                "hevc_nvenc",  # Codifica video HEVC (H.265) usando GPU NVIDIA (accelerazione hardware)
                "vp8",  # Codifica video con VP8
                "vp9",  # Codifica video con VP9
                "mpeg4",  # Codifica video con MPEG-4
                "libaom-av1",  # Codifica video con AV1
            ],
            state="normal",  # Permette la selezione
            width=20,  # Imposta la larghezza del menu a discesa
            background=BACKGROUND_COLOR,
            foreground=TEXT_COLOR,
        )
        codec_menu.pack(pady=5)

        # Caselle di spunta affiancate
        checkbox_frame = tk.Frame(setting_tab, bg=BACKGROUND_COLOR)
        checkbox_frame.pack(pady=30, padx=20, anchor="center")

        tk.Label(
            checkbox_frame,
            text="Opzioni di conversione:",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        ).pack(anchor="center", pady=5)

        # Variabile per salvare i MediaInfo
        self.save_mediainfo = tk.BooleanVar(value=False)
        # Casella di spunta: Salva MediaInfo
        mediainfo_checkbox = tk.Checkbutton(
            checkbox_frame,
            text="Salva MediaInfo",
            variable=self.save_mediainfo,
            onvalue=True,
            offvalue=False,
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            selectcolor=PRIMARY_COLOR,
        )
        mediainfo_checkbox.pack(side="left", padx=10)

        # Variabile per sovrascrivere
        self.save_overwrte = tk.BooleanVar(value=True)

        # Casella di spunta: Sovrascrivi originale
        overwrte_checkbox = tk.Checkbutton(
            checkbox_frame,
            text="Sovrascrivi originale",
            variable=self.save_overwrte,
            onvalue=True,
            offvalue=False,
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            selectcolor=PRIMARY_COLOR,
        )
        overwrte_checkbox.pack(side="left", padx=10)

        # Variabile per Grandezza
        self.if_big_del = tk.BooleanVar(value=True)

        # Casella di spunta: Se più grande elimina
        if_big_del_checkbox = tk.Checkbutton(
            checkbox_frame,
            text="Se più grande elimina",
            variable=self.if_big_del,
            onvalue=True,
            offvalue=False,
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            selectcolor=PRIMARY_COLOR,
        )
        if_big_del_checkbox.pack(side="left", padx=10)

        # Input box per il bitrate soglia
        bitrate_frame = tk.Frame(setting_tab, bg=BACKGROUND_COLOR)
        bitrate_frame.pack(pady=20, fill="x", padx=20)

        tk.Label(
            bitrate_frame,
            text="Bitrate Soglia (kbps) per la scansione:",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        ).pack(side=tk.TOP, anchor="center", padx=5)

        self.bitrate_max = tk.IntVar(value=2500)  # Default: 2500 kbps

        def validate_bitrate(new_value):
            if new_value.isdigit():  # Controlla che sia un numero
                value = int(new_value)
                return 100 <= value <= 100000  # Ritorna True se è nel range
            return False  # Altrimenti False

        # Configura la validazione del bitrate
        vcmd = bitrate_frame.register(
            validate_bitrate
        )  # Registra la funzione di validazione

        bitrate_input = tk.Spinbox(
            bitrate_frame,
            from_=0,
            to=100000,  # Range personalizzabile
            increment=100,
            textvariable=self.bitrate_max,
            width=10,
            fg=TEXT_COLOR,
            bg=PRIMARY_VARIANT_COLOR,
            highlightthickness=0,
            validate="key",  # Abilita la validazione durante la digitazione
            validatecommand=(vcmd, "%P"),  # Passa il nuovo valore come argomento
        )
        bitrate_input.pack(anchor="center", padx=10)

    def create_download_ffmpeg_tab(self):
        """Crea la scheda per il download di FFmpeg."""

        download_tab = ttk.Frame(self.notebook, style="TNotebook")
        self.notebook.add(download_tab, text="Scarica FFmpeg")

        # Stato e progress bar
        # Etichetta per la versione installata
        self.installed_version_label = tk.Label(
            download_tab,
            text=f"Versione installata: {self.downloader.get_installed_ffmpeg_version()}",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        )
        self.installed_version_label.pack(pady=5)

        # Etichetta per l'ultima versione disponibile
        self.latest_version_label = tk.Label(
            download_tab,
            text=f"Ultima versione disponibile: {self.downloader.get_latest_ffmpeg_version()}",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        )
        self.latest_version_label.pack(pady=5)

        self.progress_bar_2 = ttk.Progressbar(
            download_tab, orient="horizontal", length=700, mode="determinate"
        )
        self.progress_bar_2.pack(pady=20)

        # Log Text Area per il download
        self.log_text_area_ffmpeg = tk.Text(
            download_tab,
            wrap="word",
            height=15,
            bg=SURFACE_COLOR,
            fg=TEXT_COLOR,
            bd=0,
            padx=10,
            pady=10,
        )
        self.log_text_area_ffmpeg.pack(pady=10, padx=10, fill="both", expand=True)

        # Pulsante Aggiorna
        self.update_button = tk.Button(
            download_tab,
            text="Aggiorna",
            command=self.update_ffmpeg,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=20,
            pady=10,
        )
        self.update_button.pack(pady=10)

        # Pulsante per avviare il download
        download_button = tk.Button(
            download_tab,
            text="Scarica FFmpeg",
            command=self.download_ffmpeg,
            bg=PRIMARY_COLOR,
            fg=TEXT_COLOR,
            activebackground=PRIMARY_VARIANT_COLOR,
            relief="flat",
            padx=20,
            pady=10,
        )
        download_button.pack(pady=10)
        self.downloader = FFmpegDownloader(
            target_dir=self.target_dir,
            text_area=self.log_text_area_ffmpeg,
            progress=self.progress_bar_2,
        )

    def check_versions(self):
        """Verifica se le versioni sono uguali e disabilita il pulsante Aggiorna."""
        installed_version = self.downloader.get_installed_ffmpeg_version()
        latest_version = self.downloader.get_latest_ffmpeg_version()
        if installed_version == None:
            self.update_button.config(state=tk.DISABLED)
        if installed_version and latest_version:
            if installed_version == latest_version:
                self.update_button.config(
                    state=tk.DISABLED
                )  # Disabilita il pulsante "Aggiorna" se le versioni coincidono
            else:
                self.update_button.config(
                    state=tk.NORMAL
                )  # Abilita il pulsante "Aggiorna" se le versioni sono diverse

    def download_ffmpeg(self):
        threading.Thread(target=self.download_ffmpeg_deamon, daemon=True).start()

    def update_ffmpeg(self):
        if os.path.exists(self.ffmpeg_path):
            os.remove(self.ffmpeg_path)
        if os.path.exists(self.ffprobe_path):
            os.remove(self.ffprobe_path)
        threading.Thread(
            target=self.download_ffmpeg_deamon, args=(False,), daemon=True
        ).start()

    def download_ffmpeg_deamon(self, redirect=True):
        if self.downloader.download_ffmpeg():
            if redirect:
                self.notebook.tab(self.notebook.tabs()[0], state="normal")
                self.notebook.select(self.notebook.tabs()[0])
            installed_version = self.downloader.get_installed_ffmpeg_version()
            self.installed_version_label.config(
                text=f"Versione installata: {installed_version}"
            )
            self.check_versions()

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
                self.conversion_txt.log(
                    f"Errore nel parsing della risoluzione del video: {width_str}x{height_str}",
                    level="error",
                )
                return None, None, None
        else:
            self.conversion_txt.log(
                "Risoluzione del video non trovata.", level="warning"
            )
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
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def run_ffmpeg_command(self, command):
        try:
            process = subprocess.Popen(
                command,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=self.creationflags,
                startupinfo=self.startupinfo,
                encoding="utf-8",
            )
            return process
        except Exception as e:
            self.logger.log(
                f"Errore durante l'esecuzione del comando FFmpeg: {e}", level="error"
            )
            return None

    def convert_video(self, input_path, output_path):
        width, height, duration = self.get_video_info(input_path)
        if duration is None or width is None or height is None:
            self.conversion_txt.log(
                f"Impossibile ottenere informazioni video per {input_path}.",
                level="error",
            )
            return

        scale_filter = (
            "scale=1280:720,format=yuv420p"
            if (width > 1280 or height > 720)
            else "scale=-1:-1,format=yuv420p"
        )

        quality_option = "-crf" if self.quality_mode.get() == "crf" else "-cq"
        quality_value = self.crf_value.get()

        mediainfo_before = (
            self.utls.get_mediainfo(input_path) if self.save_mediainfo.get() else {}
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
            self.codec.get(),
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

        try:
            process = self.run_ffmpeg_command(command)
        except FileNotFoundError:
            self.logger.log(
                "FFmpeg non trovato. Assicurati che sia installato correttamente.",
                level="error",
            )
        except RuntimeError as e:
            self.logger.log(str(e), level="error")
        except Exception as e:
            self.logger.log(f"Errore inaspettato: {e}", level="error")

        self.ffmpeg_process = process

        self.conversion_txt.log(
            f"Conversione di {os.path.basename(input_path)} avviata"
        )

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        try:
            self.file_label.config(text=f"{os.path.basename(input_path)}: 0%")
            for line in process.stderr:
                time_match = re.search(r"time=(\d+:\d+:\d+(?:\.\d+)?)", line)
                # Estrazione della velocità
                speed_match = re.search(r"speed=(\d+\.?\d*)x", line)
                if time_match:
                    current_time = self.utls.parse_time_to_seconds(time_match.group(1))
                    progress = (current_time / duration) * 100
                    self.progress_bar["value"] = progress
                    remaining_time_current_file = max(duration - current_time, 0)
                if speed_match and time_match:
                    estimated_speed = float(speed_match.group(1))
                    remaining_time_current_file = (
                        duration - current_time
                    ) / estimated_speed
                    self.file_label.config(
                        text=f"{os.path.basename(input_path)}: {int(progress)}% - Rimanente: {self.convert_seconds(remaining_time_current_file)}"
                    )
                self.file_label.update_idletasks()

            process.wait()

            # Azioni post-processo
            if self.ffmpeg_process:
                self._post_process_conversion(input_path, output_path, mediainfo_before)

        except Exception as e:
            self.conversion_txt.log(
                f"Errore durante la conversione di {input_path}: {str(e)}",
                level="error",
            )
        finally:
            if process.poll() is None:  # Controlla se il processo è ancora attivo
                process.terminate()  # Tenta di chiuderlo in modo pulito
                try:
                    process.wait(timeout=5)  # Attendi la chiusura
                except subprocess.TimeoutExpired:
                    process.kill()  # Forza la chiusura
                self.conversion_txt.log("Processo FFmpeg terminato.")

    def _post_process_conversion(self, input_path, output_path, mediainfo_before):
        if self.save_mediainfo.get():
            mediainfo_after = self.utls.get_mediainfo(output_path)
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
            self.conversion_txt.log(
                f"Rapporto mediainfo salvato in: {json_report_path}"
            )

        if self.if_big_del.get():
            try:
                # Confronta le dimensioni e rimuovi il file più grande
                if os.path.getsize(output_path) >= os.path.getsize(input_path):
                    os.remove(output_path)
                    self.conversion_txt.log(
                        f"Il file '{output_path}' è stato eliminato perché è più grande."
                    )
            except FileNotFoundError as e:
                self.conversion_txt.log(f"Errore: {e}", level="error")
            except Exception as e:
                self.conversion_txt.log(
                    f"Si è verificato un errore: {e}", level="error"
                )

        if self.save_overwrte.get() and os.path.exists(output_path):
            try:
                send2trash(os.path.normpath(input_path))
                self.conversion_txt.log(
                    f"Il file originale è stato spostato nel cestino."
                )
            except FileNotFoundError:
                self.conversion_txt.log(
                    f"Il file '{input_path}' non esiste.", level="error"
                )
            except Exception as e:
                self.conversion_txt.log(
                    f"Errore durante lo spostamento del file nel cestino: {e}",
                    level="error",
                )
            try:
                os.rename(output_path, input_path)
            except FileNotFoundError:
                self.conversion_txt.log(
                    f"Il file '{output_path}' non esiste.", level="error"
                )
            except PermissionError:
                self.conversion_txt.log(
                    "Permessi insufficienti per rinominare il file.", level="error"
                )
            except Exception as e:
                self.conversion_txt.log(
                    f"Errore durante la rinomina del file: {e}", level="error"
                )

    def convert_seconds(self, seconds):
        t = timedelta(seconds=seconds)
        hours, remainder = divmod(t.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def batch_convert(self):
        allowed_extensions = (
            ".3gp",
            ".avi",
            ".flv",
            ".h264",
            ".hevc",
            ".mkv",
            ".mov",
            ".mp4",
            ".mpeg",
            ".mpg",
            ".mpeg4",
            ".mts",
            ".ogv",
            ".ts",
            ".vob",
            ".webm",
            ".wmv",
            ".divx",
            ".xvid",
            ".m4v",
            ".rm",
            ".rmvb",
            ".mxf",
            ".amv",
        )
        self.ffmpeg_process = False
        if not self.input_folder:
            self.conversion_txt.log("Seleziona una cartella valida.")
            return

        file_paths = [
            os.path.join(root, filename)
            for root, _, files in os.walk(self.input_folder)
            for filename in files
            if filename.endswith(allowed_extensions)
        ]

        if not file_paths:
            self.conversion_txt.log("Nessun file video trovato.")
            return

        total_files = len(file_paths)
        avg_tm = 0
        eta = 0

        for index, input_path in enumerate(file_paths, start=1):
            if self.ffmpeg_process is None:
                break

            if self.time_files:
                avg_tm = sum(self.time_files) / len(self.time_files)
                eta = avg_tm * (total_files - index)

            self.status_label.config(
                text=f"Conversione: {index}/{total_files} - TMV: {self.convert_seconds(avg_tm)} - ETA: {self.convert_seconds(eta)}"
            )

            bitrate = (
                self.utls.get_bitrate(input_path) if self.bitrate_max.get() else None
            )
            if bitrate and bitrate < self.bitrate_max.get():
                self.conversion_txt.log(
                    f"{os.path.basename(input_path)} è stato saltato perché ha un bitrate minore della soglia ({bitrate})/({self.bitrate_max.get()})."
                )
                continue

            file_name, _ = os.path.splitext(os.path.basename(input_path))
            filenm = f"{file_name}.mp4" if self.output_folder else f"{file_name}_nw.mp4"
            output_folder = self.output_folder or os.path.dirname(input_path)
            output_path = os.path.join(output_folder, filenm)

            start_time = perf_counter()
            self.convert_video(
                input_path, output_path
            )  # Esegui la conversione del video
            elapsed_time = perf_counter() - start_time
            self.time_files.append(elapsed_time)

            if self.ffmpeg_process:
                self.conversion_txt.log(
                    f"Conversione di {os.path.basename(input_path)} completata in {self.convert_seconds(elapsed_time)}"
                )
            else:
                os.remove(output_path)
                self.conversion_txt.log(
                    f"Conversione di {os.path.basename(input_path)} interrotta."
                )
                

        self.progress_bar["value"] = 0
        self.start_button.config(state=tk.NORMAL)
        self.file_label.config(text="")
        self.status_label.config(
            text=(
                f"Conversione batch completata in {self.convert_seconds(sum(self.time_files))}"
                if self.ffmpeg_process
                else "Conversione batch interrotta."
            )
        )

    def start_conversion(self):
        threading.Thread(target=self.batch_convert, daemon=True).start()
