# VideoConverterApp

**VideoConverterApp** is a Python-based graphical application designed to convert videos using **FFmpeg**. The app features a user-friendly GUI for video conversion and includes support for downloading FFmpeg automatically if it is not already available.

## Features

- Video conversion with support for **CRF** and **CQ** modes.
- Adjustable quality settings through an intuitive slider in the GUI.
- Automatic download of FFmpeg binaries when missing.
- Real-time progress tracking with a progress bar and log updates.
- Dark-themed GUI designed with Material Design principles for a modern look.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/chak10/VideoConverterApp.git
   cd VideoConverterApp
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure FFmpeg is available:
   - If FFmpeg is not installed, the app will prompt you to download it.
   - Alternatively, install FFmpeg manually from [FFmpeg's official site](https://ffmpeg.org/download.html).

4. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. Launch the application.
2. Select the input folder containing the videos to convert.
3. Adjust quality settings using the CRF/CQ slider in the "Conversion" tab.
4. Click the **"Start Conversion"** button to begin processing videos.
5. Monitor progress via the progress bar and log area.

### FFmpeg Download
If FFmpeg is missing, navigate to the **"Download FFmpeg"** tab:
1. Click **"Download FFmpeg"** to fetch the latest FFmpeg binaries.
2. Once downloaded, the conversion tab will become active.

## Requirements

- Python 3.8 or later
- FFmpeg (automatic download available)
- Dependencies listed in `requirements.txt`

## Screenshots

**Conversion Tab**

![Immagine 2024-11-21 215533](https://github.com/user-attachments/assets/345e65d4-8b36-4de6-b0f6-37be2f62dbc4)


**Download FFmpeg Tab**

![Immagine 2024-11-21 215518](https://github.com/user-attachments/assets/8ea3cecf-253b-4046-99a8-46a91ad0d218)


## Contributing

Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request with your changes.

## License

This project is licensed under the [GPL3.0](LICENSE).

---
