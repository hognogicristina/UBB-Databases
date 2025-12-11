import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import matplotlib.pyplot as plt
import itertools
import os
import threading

OUTPUT_ROOT = "output"
INPUT_ROOT = "input"
SUBFOLDERS = ['lines', 'segments', 'circles']

COLOR_SIDEBAR_BG = "#2b2b2b"
COLOR_MAIN_BG = "#1e1e1e"
COLOR_TEXT_WHITE = "#ffffff"
COLOR_TEXT_GRAY = "#cccccc"
COLOR_ACCENT = "#3498db"
COLOR_ACCENT_HOVER = "#2980b9"
COLOR_SUCCESS = "#2ecc71"
COLOR_WARNING = "#f1c40f"
COLOR_DANGER = "#e74c3c"

plt.switch_backend('Agg')

os.makedirs(INPUT_ROOT, exist_ok=True)
os.makedirs(OUTPUT_ROOT, exist_ok=True)

for folder in SUBFOLDERS:
    path = os.path.join(OUTPUT_ROOT, folder)
    if not os.path.exists(path):
        os.makedirs(path)


def detect_lines(image, threshold):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold)
    line_image = image.copy()
    if lines is not None:
        for line in lines:
            rho, theta = line[0]
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            x1 = int(x0 + 2000 * (-b))
            y1 = int(y0 + 2000 * a)
            x2 = int(x0 - 2000 * (-b))
            y2 = int(y0 - 2000 * a)
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
    return line_image


def detect_segments(image, threshold, min_line_length, max_line_gap):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    segments = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold,
        minLineLength=min_line_length, maxLineGap=max_line_gap
    )
    segment_image = image.copy()
    if segments is not None:
        for segment in segments:
            x1, y1, x2, y2 = segment[0]
            cv2.line(segment_image, (x1, y1), (x2, y2), (0, 255, 0), 5)
    return segment_image


def detect_circles(image, min_radius, max_radius, param1, param2):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
        param1=param1, param2=param2, minRadius=min_radius, maxRadius=max_radius
    )
    circle_image = image.copy()
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            cv2.circle(circle_image, (x, y), r, (255, 0, 0), 4)
            cv2.rectangle(circle_image, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)
    return circle_image


def save_row_collage(results, titles, folder_name, filename):
    output_path = os.path.join(OUTPUT_ROOT, folder_name, filename)

    if os.path.exists(output_path):
        return False, output_path

    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 5))
    if n == 1: axes = [axes]

    for i, ax in enumerate(axes):
        img_rgb = cv2.cvtColor(results[i], cv2.COLOR_BGR2RGB)
        ax.imshow(img_rgb)
        ax.set_title(titles[i], fontsize=10)
        ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return True, output_path


class HoughApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hough Transform")
        self.root.geometry("1400x800")
        self.root.configure(bg=COLOR_MAIN_BG)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground="#ffffff", background="#dddddd", arrowcolor="black", borderwidth=0)

        self.cv_image = None
        self.generated_files = []

        self.sidebar = tk.Frame(root, bg=COLOR_SIDEBAR_BG, width=320, padx=20, pady=20)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="Configuration", bg=COLOR_SIDEBAR_BG, fg=COLOR_TEXT_WHITE,
                 font=("Helvetica", 18, "bold")).pack(anchor="w", pady=(0, 20))

        self.create_header("1. Current Image")
        self.lbl_filename = tk.Label(self.sidebar, text="Searching input/...", bg=COLOR_SIDEBAR_BG, fg="#888", anchor="w")
        self.lbl_filename.pack(fill=tk.X, pady=(5, 15))

        self.create_header("2. Run Experiments")
        self.create_button("DETECT LINES", lambda: self.start_thread(self.run_line_batch))
        self.create_button("OPTIMIZE SEGMENTS", lambda: self.start_thread(self.run_segment_batch))
        self.create_button("OPTIMIZE CIRCLES", lambda: self.start_thread(self.run_circle_batch))

        self.create_header("3. View Results")
        tk.Label(self.sidebar, text="Select output file:", bg=COLOR_SIDEBAR_BG, fg=COLOR_TEXT_GRAY).pack(anchor="w")
        self.cb_results = ttk.Combobox(self.sidebar, state="readonly", font=("Arial", 10))
        self.cb_results.pack(fill=tk.X, pady=(5, 10), ipady=4)
        self.cb_results.bind("<<ComboboxSelected>>", self.on_result_select)

        self.create_button("QUIT", root.destroy, bg=COLOR_DANGER, fg="black", side=tk.BOTTOM)

        self.main_area = tk.Frame(root, bg=COLOR_MAIN_BG)
        self.main_area.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.lbl_status = tk.Label(self.main_area, text="Ready", bg=COLOR_MAIN_BG, fg=COLOR_TEXT_GRAY, font=("Helvetica", 11, "italic"))
        self.lbl_status.pack(side=tk.TOP, pady=10)

        self.lbl_display = tk.Label(self.main_area, bg=COLOR_MAIN_BG, text="Looking for image...")
        self.lbl_display.pack(expand=True)

        self.attempt_auto_load()

    def create_header(self, text):
        tk.Label(self.sidebar, text=text, bg=COLOR_SIDEBAR_BG, fg=COLOR_TEXT_GRAY,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10, 5))

    def create_button(self, text, command, bg=COLOR_ACCENT, fg="black", side=tk.TOP):
        btn = tk.Button(self.sidebar, text=text, command=command, bg=bg, fg=fg,
                        font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2", pady=8)
        btn.pack(side=side, fill=tk.X, pady=5)
        return btn

    def set_status(self, text, color=COLOR_TEXT_GRAY):
        self.lbl_status.config(text=text, fg=color)

    def attempt_auto_load(self):
        default_specific = os.path.join(INPUT_ROOT, "image.jpg")
        if os.path.exists(default_specific):
            self.load_image_from_path(default_specific)
            return

        if os.path.exists(INPUT_ROOT):
            for f in os.listdir(INPUT_ROOT):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif')):
                    full_path = os.path.join(INPUT_ROOT, f)
                    self.load_image_from_path(full_path)
                    return

        self.lbl_display.config(text="No image found in 'input/' folder.")
        self.lbl_filename.config(text="No Image Found", fg=COLOR_DANGER)

    def load_image_from_path(self, path):
        self.cv_image = cv2.imread(path)
        if self.cv_image is None:
            messagebox.showerror("Error", "Could not read image.")
            return

        self.lbl_filename.config(text=f"Loaded: {os.path.basename(path)}", fg=COLOR_SUCCESS)
        self.show_image(self.cv_image)
        self.set_status("Image loaded automatically. Ready to process.", COLOR_SUCCESS)

    def start_thread(self, target_func):
        if self.cv_image is None:
            messagebox.showwarning("Warning", "No image loaded. Please add an image to 'input/'.")
            return
        threading.Thread(target=target_func, daemon=True).start()

    def update_result_list(self, files):
        self.generated_files = files
        display_names = [f"{os.path.basename(os.path.dirname(f))}/{os.path.basename(f)}" for f in files]
        self.cb_results['values'] = display_names
        if display_names:
            self.cb_results.current(0)
            self.on_result_select(None)

    def on_result_select(self, event):
        idx = self.cb_results.current()
        if idx >= 0 and idx < len(self.generated_files):
            path = self.generated_files[idx]
            img = cv2.imread(path)
            if img is not None:
                self.show_image(img)

    def show_image(self, cv_img):
        h, w = cv_img.shape[:2]
        disp_w = self.main_area.winfo_width()
        disp_h = self.main_area.winfo_height() - 60

        if disp_w < 100: disp_w = 800
        if disp_h < 100: disp_h = 600

        scale = min(disp_w / w, disp_h / h)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        tk_img = ImageTk.PhotoImage(pil_img)

        self.lbl_display.config(image=tk_img, text="")
        self.lbl_display.image = tk_img

    def run_line_batch(self):
        self.set_status("Running Line Detection...", COLOR_WARNING)
        thresholds = [100, 130, 150, 200]
        results = []
        titles = []

        for thresh in thresholds:
            res = detect_lines(self.cv_image, thresh)
            results.append(res)
            titles.append(f"Thresh: {thresh}")

        is_new, path = save_row_collage(results, titles, 'lines', 'lines_collage.png')

        msg = "Saved new result" if is_new else "Loaded existing result"
        self.set_status(f"Line Detection Complete. {msg}.", COLOR_SUCCESS)
        self.root.after(0, lambda: self.update_result_list([path]))

    def run_segment_batch(self):
        self.set_status("Running Segment Optimization...", COLOR_WARNING)
        thresholds = [80, 100, 120]
        min_lengths = [50, 100, 150]
        max_gaps = [10, 15, 20]

        generated_paths = []

        for thresh in thresholds:
            for min_len in min_lengths:
                results = []
                titles = []
                for gap in max_gaps:
                    res = detect_segments(self.cv_image, thresh, min_len, gap)
                    results.append(res)
                    titles.append(f"Gap: {gap}")

                fname = f"segments_th{thresh}_len{min_len}.png"
                _, path = save_row_collage(results, titles, 'segments', fname)
                generated_paths.append(path)

        self.set_status(f"Segment Optimization Complete. {len(generated_paths)} files processed.", COLOR_SUCCESS)
        self.root.after(0, lambda: self.update_result_list(generated_paths))

    def run_circle_batch(self):
        self.set_status("Running Circle Optimization...", COLOR_WARNING)
        min_radii = [30, 50, 80]
        max_radii = [100, 200, 300]
        param1_vals = [50, 100]
        param2_vals = [60, 80]

        generated_paths = []

        for min_r in min_radii:
            for max_r in max_radii:
                results = []
                titles = []
                combos = list(itertools.product(param1_vals, param2_vals))

                for (p1, p2) in combos:
                    res = detect_circles(self.cv_image, min_r, max_r, p1, p2)
                    results.append(res)
                    titles.append(f"p1:{p1} p2:{p2}")

                fname = f"circles_min{min_r}_max{max_r}.png"
                _, path = save_row_collage(results, titles, 'circles', fname)
                generated_paths.append(path)

        self.set_status(f"Circle Optimization Complete. {len(generated_paths)} files processed.", COLOR_SUCCESS)
        self.root.after(0, lambda: self.update_result_list(generated_paths))


if __name__ == "__main__":
    root = tk.Tk()
    app = HoughApp(root)
    root.mainloop()
