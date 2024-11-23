import os
import subprocess
import re
import json
import threading

from moduli.config_manager import ConfigManager
from moduli.utils import Utils
from moduli.ffmpeg import FFmpegDownloader

from moduli.icon import ICON_APP

import tkinter as tk
from tkinter import messagebox
from time import perf_counter
from datetime import timedelta
from tkinter import filedialog, ttk
import base64
from io import BytesIO
from PIL import Image, ImageTk


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
        self.utls = Utils()
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
        window_width = 800
        window_height = 1000
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
        self.downloader = FFmpegDownloader(target_dir=self.target_dir)
        # Creazione del tema personalizzato
        self.create_style()

        # Creazione del notebook (container per le schede)
        self.notebook = ttk.Notebook(self.root, style="TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # Scheda 1: Conversione video
        self.create_widgets()

        # Scheda 2: Impostazioni
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

        # Selezione della modalità qualità (CRF o CQ) con il relativo slider
        quality_frame = tk.Frame(conversion_tab, bg=BACKGROUND_COLOR)
        quality_frame.pack(pady=10, fill="x", padx=20)

        tk.Label(
            quality_frame,
            text="Seleziona Modalità di Qualità:",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
        ).pack(side=tk.TOP)

        # Creazione dei RadioButton (CRF e CQ)
        radio_frame = tk.Frame(conversion_tab, bg=BACKGROUND_COLOR)
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
        crf_slider_frame = tk.Frame(conversion_tab, bg=BACKGROUND_COLOR)
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

        # Caselle di spunta
        checkbox_frame = tk.Frame(conversion_tab, bg=BACKGROUND_COLOR)
        checkbox_frame.pack(pady=10, fill="x", padx=20)

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
        mediainfo_checkbox.pack(anchor="center", pady=5)

        # Pulsante Avvia conversione
        start_button = tk.Button(
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
        start_button.pack(pady=10)

        # Pulsante per fermare ffmpeg
        self.stop_button = tk.Button(
            conversion_tab,
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
            self.update_button.config(
                state=tk.DISABLED
            )  
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
        threading.Thread(target=self.download_ffmpeg_deamon, args=(False,), daemon=True).start()
    
    def download_ffmpeg_deamon(self, redirect = True):
        if self.downloader.download_ffmpeg():
            if(redirect):
                self.notebook.tab(self.notebook.tabs()[0], state="normal")
                self.notebook.select(self.notebook.tabs()[0])
            installed_version = self.downloader.get_installed_ffmpeg_version()    
            self.installed_version_label.config(text=f"Versione installata: {installed_version}")
            self.check_versions()

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
        if self.save_mediainfo.get():
            mediainfo_before = self.utls.get_mediainfo(input_path)
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

                    current_time = self.utls.parse_time_to_seconds(time_match.group(1))
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
            ".mxg",
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
            ".svq3",
            ".dvd",
            ".mxf",
            ".f4v",
            ".amv",
            ".roq",
            ".yuv",
            ".cine",
            ".bik",
            ".cpk",
            ".vdr",
            ".iso",
            ".iso9660",
            ".nsv",
            ".m2v",
            ".mp2",
            ".mpv",
            ".mod",
            ".tod",
            ".pmp",
            ".ivf",
            ".drc",
            ".bmv",
            ".svi",
            ".flv",
            ".vp8",
        )
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
