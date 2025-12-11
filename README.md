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
1) Launch the app.  
2) Choose either:
   - `Load Image` to open a file, or
   - `Start/Resume Camera` for live feed (use `Stop Camera` to release).  
3) (Optional) Drag on the image to set an ROI. Click `Clear ROI` to reset.  
4) Click `Run OCR` to extract text.  
   - Overlay shows green boxes with detected text labels.  
   - Extracted text appears in the lower text area.  
5) If OCR returns empty, try better lighting, move closer, or select a larger ROI.

### Notes
- Preprocessing: bilateral denoise + adaptive threshold; Tesseract `--psm 6`.
- Overlay is drawn on the last frame; live preview pauses after OCR—press `Start/Resume Camera` to continue.

