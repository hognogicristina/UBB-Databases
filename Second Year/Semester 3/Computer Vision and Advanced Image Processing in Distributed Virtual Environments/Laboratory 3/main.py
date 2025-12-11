import cv2
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
diamond = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
x_shape = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
square = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))


def extract_corners(image, threshold=35):
    R1 = cv2.dilate(image, cross)
    R1 = cv2.erode(R1, diamond)
    R2 = cv2.dilate(image, x_shape)
    R2 = cv2.erode(R2, square)
    R = cv2.absdiff(R2, R1)
    _, R_thresh = cv2.threshold(R, threshold, 255, cv2.THRESH_BINARY)
    return R_thresh


def overlay_corners_on_image(image, corners, color=(0, 255, 0), point_size=3):
    overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    contours, _ = cv2.findContours(corners, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        for point in cnt:
            center = tuple(point[0])
            cv2.circle(overlay, center, point_size, color, -1)
    return overlay


def label_tile(bgr, text):
    out = bgr.copy()
    h, w = out.shape[:2]
    bar_h = max(28, h // 12)
    cv2.rectangle(out, (0, 0), (w, bar_h), (0, 0, 0), -1)
    cv2.putText(out, text, (10, int(bar_h * 0.70)), cv2.FONT_HERSHEY_SIMPLEX, max(0.5, bar_h / 40), (255, 255, 255), 2, cv2.LINE_AA)
    return out


def to_bgr(img):
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img


def resize_height_keep_aspect(bgr, target_h):
    h, w = bgr.shape[:2]
    scale = target_h / h
    new_w = max(1, int(w * scale))
    return cv2.resize(bgr, (new_w, target_h), interpolation=cv2.INTER_AREA)


def make_row(tiles_bgr, target_h=400):
    resized = [resize_height_keep_aspect(t, target_h) for t in tiles_bgr]
    return cv2.hconcat(resized)


def process_single_image(path):
    fname = path.name
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, cross)
    gradient_inverted = cv2.bitwise_not(gradient)

    corners = extract_corners(gray)
    overlay = overlay_corners_on_image(gray, corners)

    original_tile = label_tile(img, "Original")
    edge_tile = label_tile(to_bgr(gradient_inverted), "Edges (Morph Grad)")
    corners_tile = label_tile(overlay, "Corners Detected")

    row = make_row([original_tile, edge_tile, corners_tile], target_h=400)

    base = path.stem
    out_filename = f"{base}_row.png"
    out_path = OUTPUT_DIR / out_filename

    if not out_path.exists():
        cv2.imwrite(str(out_path), row)
        print(f"Saved: output/{out_filename}")
    else:
        print("")

    return row


def resize_and_convert(cv_img, max_w, max_h):
    if cv_img is None: return None
    rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    img_w, img_h = pil_img.size
    ratio = min(max_w / img_w, max_h / img_h)
    new_size = (int(img_w * ratio), int(img_h * ratio))
    resized = pil_img.resize(new_size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(resized)


class CornerGalleryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Morphological Corner Detection")
        self.root.geometry("1300x600")

        self.image_files = sorted([f for f in INPUT_DIR.iterdir() if f.suffix.lower() in ('.jpg', '.png', '.jpeg', '.bmp')])
        self.current_index = 0
        self.current_collage = None

        nav_frame = tk.Frame(root, pady=10)
        nav_frame.pack(side=tk.TOP, fill=tk.X)

        self.lbl_status = tk.Label(nav_frame, text="Loading...", font=("Arial", 12, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=20)

        btn_frame = tk.Frame(nav_frame)
        btn_frame.pack(side=tk.RIGHT, padx=20)

        tk.Button(btn_frame, text="Previous", command=self.prev_image, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Next", command=self.next_image, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="QUIT", command=root.destroy, font=("Arial", 10)).pack(side=tk.LEFT, padx=20)

        self.content_frame = tk.Frame(root, bg="#222")
        self.content_frame.pack(expand=True, fill=tk.BOTH)

        self.lbl_display = tk.Label(self.content_frame, bg="#222", text="No Images Found in 'input/'", fg="white")
        self.lbl_display.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.content_frame.bind("<Configure>", self.on_resize)

        if not self.image_files:
            messagebox.showwarning("No Images", "Please add .jpg or .png files to the 'input' folder.")
        else:
            self.load_current()

    def load_current(self):
        if not self.image_files: return
        path = self.image_files[self.current_index]
        self.lbl_status.config(text=f"Image {self.current_index + 1} of {len(self.image_files)}: {path.name}")
        self.current_collage = process_single_image(path)
        self.refresh_display()

    def prev_image(self):
        if not self.image_files: return
        self.current_index = (self.current_index - 1) % len(self.image_files)
        self.load_current()

    def next_image(self):
        if not self.image_files: return
        self.current_index = (self.current_index + 1) % len(self.image_files)
        self.load_current()

    def on_resize(self, event):
        if self.current_collage is None: return

        w = event.width - 20
        h = event.height - 20
        if w < 10 or h < 10: return

        tk_img = resize_and_convert(self.current_collage, w, h)
        self.lbl_display.config(image=tk_img, text="")
        self.lbl_display.image = tk_img

    def refresh_display(self):
        w = self.content_frame.winfo_width() - 20
        h = self.content_frame.winfo_height() - 20
        if w > 10 and h > 10:
            tk_img = resize_and_convert(self.current_collage, w, h)
            self.lbl_display.config(image=tk_img, text="")
            self.lbl_display.image = tk_img


if __name__ == "__main__":
    root = tk.Tk()
    app = CornerGalleryApp(root)
    root.mainloop()
