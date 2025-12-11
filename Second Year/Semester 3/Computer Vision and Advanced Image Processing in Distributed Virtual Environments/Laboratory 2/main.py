import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
INPUT_PATH = INPUT_DIR / "image.jpg"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_binary(im):
    vals = np.unique(im)
    return len(vals) <= 3 and set(vals.tolist()).issubset({0, 255})


def keep_largest(bin_u8):
    num, labels, stats, _ = cv2.connectedComponentsWithStats(bin_u8, connectivity=8)
    if num <= 1:
        return bin_u8
    lab = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return np.where(labels == lab, 255, 0).astype(np.uint8)


def fill_holes(bin_u8):
    inv = cv2.bitwise_not(bin_u8)
    marker = np.zeros_like(inv, np.uint8)
    marker[0, :] = inv[0, :]
    marker[-1, :] = inv[-1, :]
    marker[:, 0] = inv[:, 0]
    marker[:, -1] = inv[:, -1]

    se = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

    while True:
        prev = marker
        marker = cv2.dilate(marker, se, iterations=1)
        marker = cv2.bitwise_and(marker, inv)
        if np.array_equal(marker, prev):
            break

    holes = cv2.bitwise_and(inv, cv2.bitwise_not(marker))
    filled = cv2.bitwise_or(bin_u8, holes)
    return filled, holes


def to_rgb(img):
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def hstack_same_height(images):
    h_min = min(im.shape[0] for im in images)
    scaled = [cv2.resize(im, (int(im.shape[1] * h_min / im.shape[0]), h_min)) for im in images]
    return cv2.hconcat(scaled)


def smart_save(filename, img):
    path = OUTPUT_DIR / filename
    if not path.exists():
        cv2.imwrite(str(path), img)
        print(f"Saved: output/{filename}")
    else:
        print("")


def run_processing_pipeline(input_path):
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    src = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
    if src is None:
        raise ValueError("Failed to load image")

    if is_binary(src):
        bin_u8 = src.copy()
    else:
        _, bin_u8 = cv2.threshold(src, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opened = cv2.morphologyEx(bin_u8, cv2.MORPH_OPEN, k, iterations=1)
    if not np.array_equal(opened, bin_u8):
        bin_u8 = opened

    largest = keep_largest(bin_u8)
    if not np.array_equal(largest, bin_u8):
        bin_u8 = largest

    smart_save("binary_used.png", bin_u8)

    filled, holes = fill_holes(bin_u8)
    smart_save("filled.png", filled)
    smart_save("holes_mask.png", holes)

    holes_on_bin = to_rgb(bin_u8)
    contours, _ = cv2.findContours(holes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(holes_on_bin, contours, -1, (0, 255, 0), 2)
    smart_save("holes_contours.png", holes_on_bin)

    collage = hstack_same_height([to_rgb(src), to_rgb(holes), holes_on_bin, to_rgb(filled)])
    smart_save("collage.png", collage)

    return to_rgb(bin_u8), to_rgb(holes), holes_on_bin, to_rgb(filled)


def resize_and_convert(cv_img, target_width, target_height):
    if cv_img is None: return None
    rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    img_w, img_h = pil_img.size
    ratio = min(target_width / img_w, target_height / img_h)
    new_size = (int(img_w * ratio), int(img_h * ratio))

    resized = pil_img.resize(new_size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(resized)


class GridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Morphological Operations")
        self.root.geometry("1200x900")

        self.images = [None, None, None, None]
        self.titles = [
            "1. Binary Mask (Largest)",
            "2. Detected Holes Mask",
            "3. Holes Contours (Vis)",
            "4. Final Filled Result"
        ]

        nav_frame = tk.Frame(root, pady=10)
        nav_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(nav_frame, text="Morphological Pipeline (Input Hidden)", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Button(nav_frame, text="QUIT", command=root.destroy, font=("Arial", 10)).pack(side=tk.RIGHT, padx=20)

        self.content_frame = tk.Frame(root, bg="#222")
        self.content_frame.pack(expand=True, fill=tk.BOTH)

        for i in range(2):
            self.content_frame.columnconfigure(i, weight=1)
            self.content_frame.rowconfigure(i * 2 + 1, weight=1)

        self.lbl_images = []
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]

        for idx, (r, c) in enumerate(positions):
            tk.Label(self.content_frame, text=self.titles[idx], fg="white", bg="#222",
                     font=("Arial", 11, "bold")).grid(row=r * 2, column=c, pady=(10, 5))

            lbl = tk.Label(self.content_frame, bg="#333")
            lbl.grid(row=r * 2 + 1, column=c, sticky="nsew", padx=5, pady=5)
            self.lbl_images.append(lbl)

        self.content_frame.bind("<Configure>", self.on_resize)
        self.load_and_process()

    def load_and_process(self):
        try:
            imgs = run_processing_pipeline(INPUT_PATH)
            self.images = list(imgs)

            self.root.update_idletasks()
            self.refresh_display()

        except Exception as e:
            print(f"Error: {e}")

    def on_resize(self, event):
        if self.images[0] is None: return

        w = (event.width // 2) - 15
        h = (event.height // 2) - 30

        if w < 10 or h < 10: return

        self.update_images(w, h)

    def refresh_display(self):
        w = (self.content_frame.winfo_width() // 2) - 15
        h = (self.content_frame.winfo_height() // 2) - 30
        if w > 10 and h > 10:
            self.update_images(w, h)

    def update_images(self, w, h):
        for i, img in enumerate(self.images):
            tk_img = resize_and_convert(img, w, h)
            self.lbl_images[i].config(image=tk_img)
            self.lbl_images[i].image = tk_img


if __name__ == "__main__":
    root = tk.Tk()
    app = GridApp(root)
    root.mainloop()
