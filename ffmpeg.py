import os
import urllib.request
import zipfile
import tempfile
import shutil
import platform
import time


class FFmpegDownloader:
    def __init__(self, target_dir="ffmpeg_files"):
        """Inizializza l'istanza del downloader con la cartella di destinazione."""
        self.target_dir = target_dir  # La cartella target ora è "ffmpeg_files"
        self.ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        self.zip_filename = "ffmpeg-release-essentials.zip"
        self.ffmpeg_exe = "ffmpeg.exe"
        self.ffprobe_exe = "ffprobe.exe"

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
            print(f"Scaricando {self.zip_filename} da {self.ffmpeg_url}...")
            start_time = time.time()
            urllib.request.urlretrieve(self.ffmpeg_url, temp_filepath)
            print(f"Download completato in {time.time() - start_time:.2f} secondi.")
            return temp_filepath
        except Exception as e:
            print(f"Errore durante il download: {e}")
            return ""

    def _extract_zip(self, zip_path: str) -> str:
        """Estrai il contenuto del file ZIP in una cartella temporanea."""
        try:
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            return temp_dir
        except Exception as e:
            print(f"Errore durante l'estrazione: {e}")
            return ""

    def _move_files(self, temp_dir: str) -> bool:
        """Cerca e sposta i file ffmpeg.exe e ffprobe.exe nella cartella di destinazione."""
        files_to_move = [self.ffmpeg_exe, self.ffprobe_exe]
        moved = True  # Flag che indica se tutti i file sono stati spostati correttamente

        for file_name in files_to_move:
            file_found = False
            for root, dirs, files in os.walk(temp_dir):
                if file_name in files:
                    src = os.path.join(root, file_name)
                    dest = os.path.join(self.target_dir, file_name)
                    shutil.move(src, dest)
                    print(f"Spostato {file_name} in {self.target_dir}")
                    file_found = True
                    break  # Uscire dal ciclo appena trovato il file
            if not file_found:
                print(f"Errore: {file_name} non trovato.")
                moved = False  # Se almeno uno dei file non è stato trovato, setta il flag a False

        return moved

    def download_ffmpeg(self):
        """Funzione principale per scaricare e installare FFmpeg."""
        if platform.system() != "Windows":
            print("Questo script è compatibile solo con Windows.")
            return

        # Controlla se i file sono già presenti nella cartella di destinazione
        if self._is_installed():
            print("I file ffmpeg.exe e ffprobe.exe sono già presenti nella cartella di destinazione.")
            return

        # Scarica il file ZIP di ffmpeg
        zip_path = self._download_zip()
        if not zip_path:
            print("Errore nel download del file ZIP. Aborting...")
            return

        # Estrai il contenuto del file ZIP
        temp_dir = self._extract_zip(zip_path)
        if not temp_dir:
            print("Errore nell'estrazione del file ZIP. Aborting...")
            return

        # Sposta i file ffmpeg.exe e ffprobe.exe nella cartella di destinazione
        if self._move_files(temp_dir):
            print(f"File spostati correttamente: {self.ffmpeg_exe}, {self.ffprobe_exe}")
        else:
            print("Errore: uno o entrambi i file non sono stati trovati nel pacchetto.")

        # Verifica che i file siano stati spostati correttamente
        print(f"Contenuto della cartella {self.target_dir}: {os.listdir(self.target_dir)}")

        # Pulizia della cartella temporanea
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Esegui il download e l'installazione di FFmpeg
    downloader = FFmpegDownloader(target_dir="ffmpeg_files")  # Imposta la cartella "ffmpeg_files"
    downloader.download_ffmpeg()
