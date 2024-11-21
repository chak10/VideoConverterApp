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
    
    def parse_time_to_seconds(self, time_str):
        h, m, s = map(float, time_str.split(":"))
        return h * 3600 + m * 60 + s