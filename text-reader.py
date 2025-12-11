"""
GUI-based OCR tool with:
- Image load and camera capture
- ROI (click + drag) selection
- Run OCR button with overlay preview of detected text
- Live camera input with start/stop controls
- Text display of extracted content
"""

import cv2
import pytesseract
from pytesseract import Output
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import os
import subprocess
import sys

# Configure Tesseract path for Windows
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Validate Tesseract installation and test execution
if not os.path.exists(tesseract_path):
    raise FileNotFoundError(f"Tesseract executable not found at: {tesseract_path}\n"
                            f"Please install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki "
                            f"and ensure it's at the default path, or update the path variable above.")

pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Test Tesseract launch to catch DLL/dependency issues early
try:
    result = subprocess.run([tesseract_path, '--version'], capture_output=True, text=True, timeout=10, check=True)
    print(f"Tesseract initialized successfully: {result.stdout.strip()}")
except subprocess.TimeoutExpired:
    raise RuntimeError("Tesseract process timed out. Check for resource issues or reinstall.")
except subprocess.CalledProcessError as e:
    raise RuntimeError(f"Tesseract failed to run: {e.stderr}. Likely missing DLLs (e.g., libleptonica, libtesseract). "
                       f"Reinstall Tesseract as Administrator and ensure VC++ 2015-2022 Redist x64 is installed.")
except FileNotFoundError as e:
    raise RuntimeError(f"Cannot execute Tesseract despite file existing: {e}. "
                       f"Missing DLLs? Add 'C:\\Program Files\\Tesseract-OCR' to system PATH, "
                       f"or copy DLLs to Python's dir. Run from CMD to test: tesseract --version")


class OCRApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Text Reader - OCR with ROI and Camera")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)

        # Canvas/display settings
        self.canvas_width = 900
        self.canvas_height = 500  # Slightly reduced to give more space to controls

        # State
        self.current_image = None  # OpenCV BGR image currently displayed/used
        self.video_capture = None
        self.running_camera = False
        self.pause_live_preview = False
        self.display_image_meta = None  # For coordinate transforms
        self.roi_start = None
        self.roi_box = None  # (x1, y1, x2, y2) in image coords
        self.photo_image = None  # Keep reference to avoid GC

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        # Menu bar for additional options
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Image...", command=self.load_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Title
        title_frame = tk.Frame(self.root, bg="darkblue", height=50)
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        title_label = tk.Label(title_frame, text="📖 OCR Text Reader - Extract Text from Images", 
                               font=("Arial", 14, "bold"), fg="white", bg="darkblue")
        title_label.pack(pady=10)

        # Enhanced status display with progress style
        status_frame = tk.Frame(self.root, bg="lightyellow", relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, padx=8, pady=4)
        self.status_var = tk.StringVar(value="👉 Step 1: Load an image or start the camera\n👉 Step 2: Draw a box around text (ROI)\n👉 Step 3: Click 'Run OCR' to extract text")
        status_label = tk.Label(status_frame, textvariable=self.status_var, fg="darkgreen", 
                                font=("Arial", 10), justify=tk.LEFT, bg="lightyellow", wraplength=900, anchor="w")
        status_label.pack(fill=tk.X, padx=8, pady=4)

        # Improved control frame with better spacing and tooltips
        control_frame = tk.Frame(self.root, relief=tk.RAISED, bd=1)
        control_frame.pack(fill=tk.X, padx=8, pady=4)

        # Use grid for better alignment
        tk.Button(control_frame, text="📁 Load Image", command=self.load_image, 
                  bg="steelblue", fg="white", font=("Arial", 10, "bold"), width=12,
                  relief=tk.RAISED, bd=2).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        tk.Button(control_frame, text="📷 Start Camera", command=self.start_camera,
                  bg="steelblue", fg="white", font=("Arial", 10, "bold"), width=12,
                  relief=tk.RAISED, bd=2).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(control_frame, text="⏹ Stop Camera", command=self.stop_camera,
                  bg="orangered", fg="white", font=("Arial", 10, "bold"), width=12,
                  relief=tk.RAISED, bd=2).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        tk.Button(control_frame, text="🔍 Run OCR", command=self.run_ocr,
                  bg="darkgreen", fg="white", font=("Arial", 10, "bold"), width=12,
                  relief=tk.RAISED, bd=2).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        tk.Button(control_frame, text="❌ Clear ROI", command=self.clear_roi,
                  bg="indianred", fg="white", font=("Arial", 10, "bold"), width=12,
                  relief=tk.RAISED, bd=2).grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        control_frame.columnconfigure((0,1,2,3,4), weight=1)

        # Canvas frame with scrollbar if needed (for large images)
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="black",
            cursor="crosshair",
            relief=tk.SUNKEN, bd=2
        )
        # Add scrollbars
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")

        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<Configure>", self.on_canvas_resize)  # Handle resize

        # Enhanced text output area with better styling and search
        output_frame = tk.Frame(self.root, bg="lightgray", relief=tk.SUNKEN, bd=2)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        tk.Label(output_frame, text="📝 Extracted Text", font=("Arial", 12, "bold"), 
                bg="lightgray", fg="darkblue").pack(anchor="w", padx=8, pady=(5,0))
        
        # Add a search entry for text
        search_frame = tk.Frame(output_frame, bg="lightgray")
        search_frame.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(search_frame, text="Search: ", font=("Arial", 9), bg="lightgray", fg="gray50").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 9), width=20)
        search_entry.pack(side=tk.LEFT, padx=(5,0))
        tk.Button(search_frame, text="Find", command=self.search_text,
                  bg="lightblue", font=("Arial", 9), width=8).pack(side=tk.LEFT, padx=5)
        self.search_entry = search_entry
        
        self.text_output = scrolledtext.ScrolledText(output_frame, height=15, wrap=tk.WORD,
                                                     font=("Consolas", 10), bg="white", 
                                                     fg="black", relief=tk.FLAT, bd=1,
                                                     selectbackground="lightblue", selectforeground="black")
        self.text_output.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        
        # Improved button frame with more options
        button_frame = tk.Frame(output_frame, bg="lightgray")
        button_frame.pack(fill=tk.X, padx=8, pady=(0,5))
        tk.Button(button_frame, text="📋 Copy Text", command=self.copy_text,
                 bg="steelblue", fg="white", font=("Arial", 10), width=12,
                 relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=4)
        tk.Button(button_frame, text="🗑 Clear Text", command=self.clear_text,
                 bg="lightcoral", fg="white", font=("Arial", 10), width=12,
                 relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=4)
        tk.Button(button_frame, text="💾 Save Text", command=self.save_text,
                 bg="darkgoldenrod", fg="white", font=("Arial", 10), width=12,
                 relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=4)

    def on_canvas_resize(self, event):
        """Handle canvas resize to maintain image scaling."""
        if self.current_image is not None:
            self.display_image(self.current_image)

    def show_about(self):
        messagebox.showinfo("About", "OCR Text Reader v1.0\n\nA simple GUI tool for extracting text from images and live camera feeds using OpenCV and Tesseract OCR.\n\nBuilt with ❤️ using Python.")

    def search_text(self):
        search_term = self.search_var.get().lower()
        if not search_term:
            return
        self.text_output.tag_remove("highlight", "1.0", tk.END)
        idx = "1.0"
        while True:
            idx = self.text_output.search(search_term, idx, nocase=True, stopindex=tk.END)
            if not idx:
                break
            last_idx = f"{idx}+{len(search_term)}c"
            self.text_output.tag_add("highlight", idx, last_idx)
            idx = last_idx
        self.text_output.tag_config("highlight", background="yellow")

    def clear_text(self):
        self.text_output.delete("1.0", tk.END)
        self.status_var.set("✅ Text cleared.")

    def save_text(self):
        text = self.text_output.get("1.0", tk.END).strip()
        if not text or text == "[No text detected]":
            messagebox.showwarning("Empty", "No text to save. Run OCR first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Success", f"✅ Text saved to {file_path}")

    # ----------------- Utility functions -----------------
    def _cv_to_tk_image(self, cv_img: np.ndarray):
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        img_h, img_w = pil_img.height, pil_img.width

        # Fit to current canvas size
        canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else self.canvas_width
        canvas_h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else self.canvas_height
        scale = min(canvas_w / img_w, canvas_h / img_h) if img_w > 0 and img_h > 0 else 1.0
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        resized = pil_img.resize((new_w, new_h), Image.LANCZOS)

        offset_x = (canvas_w - new_w) // 2
        offset_y = (canvas_h - new_h) // 2

        self.display_image_meta = {
            "scale": scale,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "img_w": img_w,
            "img_h": img_h,
        }
        self.photo_image = ImageTk.PhotoImage(resized)
        return self.photo_image, offset_x, offset_y

    def _canvas_to_image_coords(self, x: float, y: float):
        if not self.display_image_meta:
            return None
        m = self.display_image_meta
        img_x = int((x - m["offset_x"]) / m["scale"])
        img_y = int((y - m["offset_y"]) / m["scale"])
        if 0 <= img_x < m["img_w"] and 0 <= img_y < m["img_h"]:
            return img_x, img_y
        return None

    def _image_to_canvas_coords(self, x: float, y: float):
        if not self.display_image_meta:
            return x, y
        m = self.display_image_meta
        canvas_x = x * m["scale"] + m["offset_x"]
        canvas_y = y * m["scale"] + m["offset_y"]
        return canvas_x, canvas_y

    def display_image(self, cv_img: np.ndarray) -> None:
        if cv_img is None:
            return
        tk_img, offset_x, offset_y = self._cv_to_tk_image(cv_img)
        self.canvas.delete("all")
        self.canvas.create_image(offset_x, offset_y, image=tk_img, anchor=tk.NW, tags="img")
        self.draw_roi_box()

    def draw_roi_box(self) -> None:
        self.canvas.delete("roi")
        if not self.roi_box or not self.display_image_meta:
            return
        x1, y1, x2, y2 = self.roi_box
        c1 = self._image_to_canvas_coords(x1, y1)
        c2 = self._image_to_canvas_coords(x2, y2)
        self.canvas.create_rectangle(*c1, *c2, outline="yellow", width=2, tags="roi")

    # ----------------- Event handlers -----------------
    def on_mouse_press(self, event) -> None:
        coords = self._canvas_to_image_coords(event.x, event.y)
        if coords:
            self.roi_start = coords
            self.roi_box = None
            self.draw_roi_box()

    def on_mouse_drag(self, event) -> None:
        if not self.roi_start:
            return
        coords = self._canvas_to_image_coords(event.x, event.y)
        if coords:
            x0, y0 = self.roi_start
            x1, y1 = coords
            self.roi_box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            self.draw_roi_box()

    def on_mouse_release(self, event) -> None:
        if not self.roi_start:
            return
        coords = self._canvas_to_image_coords(event.x, event.y)
        if coords:
            x0, y0 = self.roi_start
            x1, y1 = coords
            self.roi_box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        self.roi_start = None
        self.draw_roi_box()

    # ----------------- Camera handling -----------------
    def start_camera(self) -> None:
        if self.video_capture is None:
            # Use camera index 0 as specified
            self.video_capture = cv2.VideoCapture(1)
            if not self.video_capture.isOpened():
                self.video_capture.release()
                self.video_capture = None
                messagebox.showerror("Camera Error", "Cannot open default camera (index 0). Check device connections and permissions.")
                return
            # Set some properties for better performance
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.video_capture.set(cv2.CAP_PROP_FPS, 30)
        self.running_camera = True
        self.pause_live_preview = False
        self.status_var.set("✅ Camera is running! Draw a box around text (click & drag), then click 'Run OCR'")
        self.update_camera_frame()

    def stop_camera(self) -> None:
        self.running_camera = False
        self.pause_live_preview = False
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        self.status_var.set("⏹ Camera stopped.")

    def update_camera_frame(self) -> None:
        if not self.running_camera or self.pause_live_preview:
            return
        if self.video_capture is None:
            return
        ret, frame = self.video_capture.read()
        if not ret:
            self.status_var.set("Failed to read from camera.")
            return
        self.current_image = frame
        self.display_image(frame)
        # Schedule next frame
        self.root.after(30, self.update_camera_frame)

    # ----------------- OCR handling -----------------
    def _preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """Lightweight preprocessing to boost OCR quality."""
        if len(img.shape) == 2:  # If already grayscale, skip conversion
            gray = img
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Reduce noise and improve contrast
        gray = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
        # Adaptive threshold to handle uneven lighting
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            10,
        )
        return binary

    def _prepare_roi(self):
        if self.current_image is None:
            return None, None
        h, w = self.current_image.shape[:2]
        if not self.roi_box:
            return self.current_image.copy(), (0, 0)
        x1, y1, x2, y2 = self.roi_box
        x1 = max(0, min(w - 1, int(x1)))
        x2 = max(x1 + 1, min(w, int(x2)))  # Ensure x2 > x1
        y1 = max(0, min(h - 1, int(y1)))
        y2 = max(y1 + 1, min(h, int(y2)))  # Ensure y2 > y1
        if x2 <= x1 or y2 <= y1:
            return self.current_image.copy(), (0, 0)
        roi_img = self.current_image[y1:y2, x1:x2].copy()
        return roi_img, (x1, y1)

    def run_ocr(self) -> None:
        if self.current_image is None:
            messagebox.showwarning("No Image", "Load an image or start the camera first.")
            return

        # Freeze live preview to keep overlay visible
        if self.running_camera:
            self.pause_live_preview = True

        roi_img, (offset_x, offset_y) = self._prepare_roi()
        if roi_img is None:
            messagebox.showwarning("No Image", "Load an image or start the camera first.")
            return

        try:
            # Preprocess to improve OCR quality
            processed = self._preprocess_for_ocr(roi_img)

            # Run OCR with error handling
            ocr_config = "--psm 6"
            ocr_text = pytesseract.image_to_string(processed, config=ocr_config)
            data = pytesseract.image_to_data(processed, output_type=Output.DICT, config=ocr_config)

            annotated = self.current_image.copy()
            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                conf = float(data["conf"][i]) if data["conf"][i] != "-1" else -1.0
                if not text or conf < 10:
                    continue
                x = data["left"][i] + offset_x
                y = data["top"][i] + offset_y
                w = data["width"][i]
                h = data["height"][i]
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    annotated,
                    text,
                    (x, max(0, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    1,
                    cv2.LINE_AA,
                )

            self.text_output.delete("1.0", tk.END)
            stripped = ocr_text.strip()
            if stripped:
                self.text_output.insert(tk.END, stripped)
                self.status_var.set("✅ OCR complete! Extracted text is shown below. Resume camera if needed.")
            else:
                self.text_output.insert(tk.END, "[No text detected]")
                self.status_var.set("❌ No text detected. Try a larger ROI, better lighting, or move closer.")
            self.display_image(annotated)

        except Exception as e:
            messagebox.showerror("OCR Error", f"Failed to run OCR: {str(e)}\n\n"
                                              f"Ensure Tesseract is properly installed and in PATH.\n"
                                              f"Test in CMD: tesseract --version")
            self.status_var.set("❌ OCR failed. Check console for details.")

    # ----------------- Misc helpers -----------------
    def clear_roi(self) -> None:
        self.roi_box = None
        self.draw_roi_box()
        self.status_var.set("✅ ROI cleared. Draw a new box or run OCR on the full image.")

    def copy_text(self) -> None:
        text = self.text_output.get("1.0", tk.END).strip()
        if text and text != "[No text detected]":
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            messagebox.showinfo("Success", "✅ Text copied to clipboard!")
        else:
            messagebox.showwarning("Empty", "No text to copy. Run OCR first.")

    def load_image(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return
        img = cv2.imread(file_path)
        if img is None:
            messagebox.showerror("Load Error", "Could not load the selected image.")
            return
        self.current_image = img
        self.pause_live_preview = False
        self.running_camera = False
        self.display_image(img)
        self.status_var.set("✅ Image loaded. Select ROI (optional) or click 'Run OCR'.")

    def on_close(self) -> None:
        self.stop_camera()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()