import os
import urllib.request
import zipfile
import tempfile
import shutil
import platform
import time
import tkinter as tk

class FFmpegDownloader:
    def __init__(self, target_dir="ffmpeg_files", text_area=False, progress = False):
        """Inizializza l'istanza del downloader con la cartella di destinazione."""
        self.target_dir = target_dir  # La cartella target ora è "ffmpeg_files"
        self.ffmpeg_url = (
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        )
        self.zip_filename = "ffmpeg-release-essentials.zip"
        self.ffmpeg_exe = "ffmpeg.exe"
        self.ffprobe_exe = "ffprobe.exe"
        self.text_area = text_area
        self.progress_bar = progress
        # Crea la cartella ffmpeg_files se non esiste
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

    def _is_installed(self) -> bool:
        """Verifica se ffmpeg.exe e ffprobe.exe sono già presenti nella cartella di destinazione."""
        ffmpeg_path = os.path.join(self.target_dir, self.ffmpeg_exe)
        ffprobe_path = os.path.join(self.target_dir, self.ffprobe_exe)
        return os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path)

    def _download_zip(self) -> str:
        """Scarica il file ZIP contenente ffmpeg nella cartella temporanea."""
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_filepath = temp_file.name
            self.log_message(f"Scaricando {self.zip_filename} da {self.ffmpeg_url}...")
            start_time = time.time()
            urllib.request.urlretrieve(self.ffmpeg_url, temp_filepath)
            try:
                with urllib.request.urlopen(self.ffmpeg_url, timeout=5) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0

                    with open(temp_filepath, 'wb') as file:
                        while chunk := response.read(1048576):
                            downloaded += len(chunk)
                            file.write(chunk)
                            percent = (downloaded / total_size) * 100
                            self.progress2(percent)
                            #self.log_message(f"Download: {percent:.2f}%")
            except Exception as e:
                self.log_message(f"Errore durante il download: {str(e)}")
            self.log_message(f"Download completato in {time.time() - start_time:.2f} secondi.")
            return temp_filepath
        except Exception as e:
            self.log_message(f"Errore durante il download: {e}")
            return ""

    def _extract_zip(self, zip_path: str) -> str:
        """Estrai il contenuto del file ZIP in una cartella temporanea."""
        try:
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
            return temp_dir
        except Exception as e:
            self.log_message(f"Errore durante l'estrazione: {e}")
            return ""

    def _move_files(self, temp_dir: str) -> bool:
        """Cerca e sposta i file ffmpeg.exe e ffprobe.exe nella cartella di destinazione."""
        files_to_move = [self.ffmpeg_exe, self.ffprobe_exe]
        moved = (
            True  # Flag che indica se tutti i file sono stati spostati correttamente
        )

        for file_name in files_to_move:
            file_found = False
            for root, dirs, files in os.walk(temp_dir):
                if file_name in files:
                    src = os.path.join(root, file_name)
                    dest = os.path.join(self.target_dir, file_name)
                    shutil.move(src, dest)
                    self.log_message(f"Spostato {file_name} in {self.target_dir}")
                    file_found = True
                    break  # Uscire dal ciclo appena trovato il file
            if not file_found:
                self.log_message(f"Errore: {file_name} non trovato.")
                moved = False  # Se almeno uno dei file non è stato trovato, setta il flag a False

        return moved

    def download_ffmpeg(self):
        """Funzione principale per scaricare e installare FFmpeg."""
        if platform.system() != "Windows":
            self.log_message("Questo script è compatibile solo con Windows.")
            return False

        # Controlla se i file sono già presenti nella cartella di destinazione
        if self._is_installed():
            self.log_message(
                "I file ffmpeg.exe e ffprobe.exe sono già presenti nella cartella di destinazione."
            )
            return False

        # Scarica il file ZIP di ffmpeg
        zip_path = self._download_zip()
        if not zip_path:
            self.log_message("Errore nel download del file ZIP. Aborting...")
            return False

        # Estrai il contenuto del file ZIP
        temp_dir = self._extract_zip(zip_path)
        if not temp_dir:
            self.log_message("Errore nell'estrazione del file ZIP. Aborting...")
            return False

        # Sposta i file ffmpeg.exe e ffprobe.exe nella cartella di destinazione
        if self._move_files(temp_dir):
            self.log_message(f"File spostati correttamente: {self.ffmpeg_exe}, {self.ffprobe_exe}")            
        else:
            self.log_message("Errore: uno o entrambi i file non sono stati trovati nel pacchetto.")
            return False

        # Verifica che i file siano stati spostati correttamente
        self.log_message(
            f"Contenuto della cartella {self.target_dir}: {os.listdir(self.target_dir)}"
        )
        # Pulizia della cartella temporanea
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True

    def log_message(self, message):
        """Log dei messaggi (da aggiungere nel conversion tab)."""
        if self.text_area:
            self.text_area.insert(tk.END, message + "\n")
            self.text_area.see(tk.END)
        else:
            print(message)
    
    def progress2(self, percent):
        """Aggiorna la barra di avanzamento."""
        if self.progress_bar:
            self.progress_bar["value"] = percent

if __name__ == "__main__":
    # Esegui il download e l'installazione di FFmpeg
    downloader = FFmpegDownloader(
        target_dir="ffmpeg_files"
    )  # Imposta la cartella "ffmpeg_files"
    downloader.download_ffmpeg()
