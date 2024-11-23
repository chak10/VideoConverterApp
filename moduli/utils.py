import subprocess, json, os
from datetime import datetime

class Utils:

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
            "-v",
            "error",  # Disabilita i log di errore
            "-show_entries",
            "format=filename,format_name,format_long_name,bit_rate,duration,streams",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,bit_rate,channels,sample_rate,duration,frame_rate,frame_count,bit_depth",
            "-of",
            "json",  # Output in formato JSON
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
                #self.log_message(f"Errore ottenendo mediainfo per {video_path}: {stderr}")
                return {}

            # Decodifica l'output JSON
            try:
                info = json.loads(stdout)
            except json.JSONDecodeError:
                #self.log_message(f"Errore di decodifica JSON per {video_path}")
                return {}

            # Estrai informazioni generali e sui flussi
            media_info = {"media": {"@ref": video_path, "track": []}}

            # Aggiungi informazioni generali sul formato
            format_info = info.get("format", {})
            general_info = {
                "@type": "General",
                "VideoCount": len(
                    [
                        stream
                        for stream in info["streams"]
                        if stream["codec_type"] == "video"
                    ]
                ),
                "AudioCount": len(
                    [
                        stream
                        for stream in info["streams"]
                        if stream["codec_type"] == "audio"
                    ]
                ),
                "FileExtension": video_path.split(".")[-1],
                "Format": format_info.get("format_name", "N/A"),
                "Duration": format_info.get("duration", "N/A"),
                "FileSize": os.path.getsize(video_path),
                "OverallBitRate": format_info.get("bit_rate", "N/A"),
                "Recorded_Date": datetime.now().year,
                "File_Created_Date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S.%f UTC"
                ),
                "File_Modified_Date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S.%f UTC"
                ),
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
                    stream_info.update(
                        {
                            "Width": stream.get("width", "N/A"),
                            "Height": stream.get("height", "N/A"),
                            "FrameRate": stream.get("r_frame_rate", "N/A"),
                            "FrameCount": stream.get("nb_frames", "N/A"),
                            "BitDepth": stream.get("bit_depth", "8"),
                        }
                    )
                elif stream["codec_type"] == "audio":
                    stream_info.update(
                        {
                            "Channels": stream.get("channels", "N/A"),
                            "SamplingRate": stream.get("sample_rate", "N/A"),
                        }
                    )

                media_info["media"]["track"].append(stream_info)

            return media_info

        except subprocess.SubprocessError as e:
            # Cattura eventuali errori del subprocess
            #self.log_message(f"Errore eseguendo ffprobe per {video_path}: {str(e)}")
            return {}
    
    def parse_time_to_seconds(self, time_str):
        h, m, s = map(float, time_str.split(":"))
        return h * 3600 + m * 60 + s