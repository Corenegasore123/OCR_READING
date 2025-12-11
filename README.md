# OCR Text Reader

A simple GUI tool to extract text from images or a live camera feed using OpenCV and Tesseract OCR.

## Features

- Load images from disk or capture live frames from a camera
- Draw a rectangular ROI (click and drag) to constrain OCR
- Run OCR and preview detected text with bounding-box annotations
- Copy, save, clear, and search extracted text from the GUI

## Requirements

- Python 3.8+
- Tesseract OCR installed on the system (Windows instructions below)
- Python packages:

```bash
pip install opencv-python pytesseract pillow numpy
```

Note: `tkinter` is required for the GUI. On most Windows Python installs, `tkinter` is included. If it's missing, install the appropriate Python distribution that bundles Tk.

## Tesseract (Windows)

The script expects the Tesseract executable at:

```
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If you installed Tesseract to a different location, either:

- Update the `tesseract_path` variable at the top of [text-reader.py](text-reader.py), or
- Add the Tesseract installation folder to your system `PATH` so `tesseract --version` works from a terminal.

Recommended Windows build: UB Mannheim builds (https://github.com/UB-Mannheim/tesseract/wiki).

If you see DLL or startup errors, ensure the Visual C++ 2015-2022 Redistributable (x64) is installed.

## Usage

1. Install Python packages (see Requirements).
2. Ensure Tesseract is installed and reachable (see Tesseract section).
3. Run the app:

```bash
python text-reader.py
```

4. In the GUI:

- Click **Load Image** to open an image, or **Start Camera** to stream from a webcam.
- Click and drag on the image to draw an ROI (optional).
- Click **Run OCR** to extract text within the ROI (or the full image if no ROI).
- Use **Copy Text**, **Save Text**, **Clear Text**, and the search box to manage results.

## Notes & Troubleshooting

- The script uses OpenCV's `VideoCapture(1)` by default. If your camera isn't detected, change the index in `start_camera()` to `0` or another index.
- If Tesseract runs but OCR quality is poor, try better lighting, a larger ROI, or increase image resolution.
- To test Tesseract independently, run:

```bash
tesseract --version
```

- If you receive an error about missing DLLs, reinstall Tesseract and ensure its directory is in the system `PATH`.

## Files

- [text-reader.py](text-reader.py) — main GUI application.

## Next steps (optional)

- Add a `requirements.txt` file for exact package versions.
- Add command-line options for headless OCR mode.
- Add unit tests for preprocessing and ROI extraction functions.

---

Made from reading `text-reader.py`. If you'd like, I can also add `requirements.txt` or adjust the camera/tesseract defaults.

## Text Reader (GUI OCR with ROI and Camera)

GUI-based OCR tool built with Tkinter, OpenCV, and PyTesseract. Features:

- Load image from disk.
- Live camera input with start/stop controls.
- ROI selection via click-and-drag.
- Run OCR on full image or ROI.
- Overlay preview with detected text boxes.
- Extracted text display in a scrollable panel.

### Requirements

- Python 3.12+ (matches repo venv).
- System Tesseract OCR installed and on PATH (`tesseract` binary).
- Tkinter (usually included with system Python).
- Python libs: `opencv-python`, `pytesseract`, `Pillow`, `numpy`.
  - Already present in the included `venv`; otherwise install with:
    ```bash
    pip install opencv-python pytesseract Pillow numpy
    ```

### Run

```bash
python text-reader.py
```

### Usage

1. Launch the app.
2. Choose either:
   - `Load Image` to open a file, or
   - `Start/Resume Camera` for live feed (use `Stop Camera` to release).
3. (Optional) Drag on the image to set an ROI. Click `Clear ROI` to reset.
4. Click `Run OCR` to extract text.
   - Overlay shows green boxes with detected text labels.
   - Extracted text appears in the lower text area.
5. If OCR returns empty, try better lighting, move closer, or select a larger ROI.

### Notes

- Preprocessing: bilateral denoise + adaptive threshold; Tesseract `--psm 6`.
- Overlay is drawn on the last frame; live preview pauses after OCR—press `Start/Resume Camera` to continue.
