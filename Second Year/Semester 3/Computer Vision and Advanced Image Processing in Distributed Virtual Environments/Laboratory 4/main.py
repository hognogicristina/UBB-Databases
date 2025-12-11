import os
import cv2
import numpy as np
import csv
import tkinter as tk
from tkinter import ttk, messagebox, font
from PIL import Image, ImageTk

DEFAULT_IMAGES_ROOT = "input"
OUTPUT_ROOT = "output"
BIN_COUNTS = [256, 64, 32]

COLOR_SIDEBAR_BG = "#2b2b2b"
COLOR_MAIN_BG = "#1e1e1e"
COLOR_TEXT = "#ffffff"
COLOR_ACCENT = "#3498db"
COLOR_ACCENT_HOVER = "#2980b9"
COLOR_DANGER = "#e74c3c"
COLOR_COMBO_BG = "#ffffff"

os.makedirs(DEFAULT_IMAGES_ROOT, exist_ok=True)
os.makedirs(OUTPUT_ROOT, exist_ok=True)


def get_available_metrics():
    metrics = {}

    def add(name, const_name, higher_better):
        if hasattr(cv2, const_name):
            metrics[name] = (getattr(cv2, const_name), higher_better)

    add("CORRELATION", "HISTCMP_CORREL", True)
    add("CHI_SQUARE", "HISTCMP_CHISQR", False)
    add("INTERSECTION", "HISTCMP_INTERSECT", True)
    add("BHATTACHARYYA", "HISTCMP_BHATTACHARYYA", False)
    return metrics


def load_image_paths(images_root):
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    all_paths = []
    for root, _, files in os.walk(images_root):
        for fname in files:
            if os.path.splitext(fname)[1].lower() in exts:
                all_paths.append(os.path.join(root, fname))
    all_paths.sort()
    return all_paths


def compute_grayscale_histogram(img_bgr, num_bins):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [num_bins], [0, 256])
    cv2.normalize(hist, hist, alpha=1.0, beta=0.0, norm_type=cv2.NORM_L1)
    return hist.flatten()


def normalize_scores(raw_scores, higher_is_better, q_index):
    scores = np.array(raw_scores, dtype=np.float64)
    q_val = scores[q_index]
    eps = 1e-12

    if higher_is_better:
        denom = scores.max() + eps if abs(q_val) < eps else q_val
        normalized = scores / denom
    else:
        d_min = q_val
        d_max = scores.max()
        if abs(d_max - d_min) < eps:
            normalized = np.ones_like(scores)
        else:
            normalized = 1.0 - (scores - d_min) / (d_max - d_min)

    normalized = np.clip(normalized, 0.0, 1.0)
    normalized[q_index] = 1.0
    return normalized


def generate_collage(image_paths, image_labels, q_index, scores, top_k=6):
    sorted_idx = np.argsort(-np.array(scores))[:top_k]

    tiles = []
    for idx in sorted_idx:
        img = cv2.imread(image_paths[idx])
        if img is None: continue

        img = cv2.resize(img, (200, 200))

        label_text = ("Q: " + image_labels[idx]) if idx == q_index else image_labels[idx]
        score_text = f"{scores[idx]:.3f}"

        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (200, 40), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        cv2.putText(img, label_text, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img, score_text, (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        tiles.append(img)

    if not tiles: return None
    return cv2.hconcat(tiles)


class HistogramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CBIR: Histogram Comparison")
        self.root.geometry("1300x750")
        self.root.configure(bg=COLOR_MAIN_BG)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.style.configure("TCombobox", fieldbackground=COLOR_COMBO_BG, background="#dddddd", arrowcolor="black", borderwidth=0)
        self.image_paths = load_image_paths(DEFAULT_IMAGES_ROOT)
        self.image_labels = [os.path.relpath(p, DEFAULT_IMAGES_ROOT) for p in self.image_paths]
        self.metrics = get_available_metrics()

        self.images_bgr = []
        self.hist_cache = {}

        control_frame = tk.Frame(root, bg=COLOR_SIDEBAR_BG, width=320, padx=25, pady=25)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        control_frame.pack_propagate(False)

        header_font = font.Font(family="Helvetica", size=18, weight="bold")
        lbl_title = tk.Label(control_frame, text="Configuration",
                             bg=COLOR_SIDEBAR_BG, fg=COLOR_TEXT, font=header_font)
        lbl_title.pack(pady=(0, 30), anchor="w")

        self.create_label(control_frame, "1. Select Query Image:")
        self.cb_query = ttk.Combobox(control_frame, values=self.image_labels, state="readonly", font=("Arial", 11))
        if self.image_labels: self.cb_query.current(0)
        self.cb_query.pack(fill=tk.X, pady=(5, 25), ipady=4)

        self.create_label(control_frame, "2. Select Metric:")
        self.cb_metric = ttk.Combobox(control_frame, values=list(self.metrics.keys()), state="readonly", font=("Arial", 11))
        self.cb_metric.current(0)
        self.cb_metric.pack(fill=tk.X, pady=(5, 25), ipady=4)

        self.create_label(control_frame, "3. Bin Count:")
        self.cb_bins = ttk.Combobox(control_frame, values=[str(b) for b in BIN_COUNTS], state="readonly", font=("Arial", 11))
        self.cb_bins.current(0)
        self.cb_bins.pack(fill=tk.X, pady=(5, 25), ipady=4)

        self.btn_run = tk.Button(control_frame, text="RUN SEARCH", command=self.run_search, bg=COLOR_ACCENT, fg="black",
                                 font=("Helvetica", 11, "bold"), relief="flat", cursor="hand2", activebackground=COLOR_ACCENT_HOVER,
                                 activeforeground="black", pady=12)
        self.btn_run.pack(fill=tk.X, pady=(20, 10))

        self.btn_quit = tk.Button(control_frame, text="QUIT", command=root.destroy, bg=COLOR_DANGER, fg="black",
                                  font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2", activebackground="#c0392b",
                                  activeforeground="black", pady=8)
        self.btn_quit.pack(side=tk.BOTTOM, fill=tk.X)

        self.display_frame = tk.Frame(root, bg=COLOR_MAIN_BG)
        self.display_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.lbl_status = tk.Label(self.display_frame, text="Ready", bg=COLOR_MAIN_BG, fg="#888", font=("Helvetica", 10, "italic"))
        self.lbl_status.pack(side=tk.TOP, pady=15)

        self.lbl_result = tk.Label(self.display_frame, bg=COLOR_MAIN_BG, text="Results will appear here", fg="#555")
        self.lbl_result.pack(expand=True)

        self.preload_images()

    def create_label(self, parent, text):
        lbl = tk.Label(parent, text=text, bg=COLOR_SIDEBAR_BG, fg="#cccccc",
                       font=("Helvetica", 10, "bold"), anchor="w")
        lbl.pack(fill=tk.X)

    def preload_images(self):
        if not self.image_paths:
            messagebox.showerror("Error", f"No images found in '{DEFAULT_IMAGES_ROOT}'")
            return

        for p in self.image_paths:
            img = cv2.imread(p)
            self.images_bgr.append(img)

    def get_histogram(self, idx, bins):
        key = (idx, bins)
        if key not in self.hist_cache:
            img = self.images_bgr[idx]
            if img is None: return None
            self.hist_cache[key] = compute_grayscale_histogram(img, bins)
        return self.hist_cache[key]

    def run_search(self):
        if not self.images_bgr: return

        query_idx = self.cb_query.current()
        metric_name = self.cb_metric.get()
        bins = int(self.cb_bins.get())

        query_label = self.image_labels[query_idx]
        safe_q_name = os.path.splitext(os.path.basename(query_label))[0]

        out_subdir = os.path.join(OUTPUT_ROOT, f"bins_{bins}")
        os.makedirs(out_subdir, exist_ok=True)

        collage_filename = f"top_{metric_name}_{safe_q_name}.jpg"
        collage_path = os.path.join(out_subdir, collage_filename)
        csv_filename = f"scores_{metric_name}_{safe_q_name}.csv"
        csv_path = os.path.join(out_subdir, csv_filename)

        if os.path.exists(collage_path):
            self.lbl_status.config(text=f"Loaded cached result from: {collage_filename}", fg="#2ecc71")
            final_collage = cv2.imread(collage_path)
            self.show_image(final_collage)
            return

        self.lbl_status.config(text="Computing...", fg="#f1c40f")
        self.root.update_idletasks()

        cv_method, higher_is_better = self.metrics[metric_name]
        q_hist = self.get_histogram(query_idx, bins)

        raw_scores = []
        for i in range(len(self.images_bgr)):
            hist = self.get_histogram(i, bins)
            if hist is None or q_hist is None:
                raw_scores.append(0.0)
            else:
                score = cv2.compareHist(q_hist, hist, cv_method)
                raw_scores.append(float(score))

        norm_scores = normalize_scores(raw_scores, higher_is_better, query_idx)

        final_collage = generate_collage(self.image_paths, self.image_labels, query_idx, norm_scores)

        if final_collage is not None:
            cv2.imwrite(collage_path, final_collage)

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "image", "raw_score", "normalized_score"])
            for i, label in enumerate(self.image_labels):
                writer.writerow([i, label, f"{raw_scores[i]:.6f}", f"{norm_scores[i]:.6f}"])

        self.lbl_status.config(text=f"Saved to: output/{os.path.relpath(collage_path, OUTPUT_ROOT)}", fg="#2ecc71")
        self.show_image(final_collage)

    def show_image(self, cv_img):
        if cv_img is None: return

        disp_w = self.display_frame.winfo_width()
        disp_h = self.display_frame.winfo_height() - 50

        if disp_w < 50: disp_w = 800
        if disp_h < 50: disp_h = 400

        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        img_w, img_h = pil_img.size
        ratio = min(disp_w / img_w, disp_h / img_h)
        new_size = (int(img_w * ratio), int(img_h * ratio))

        resized = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized)

        self.lbl_result.config(image=tk_img, text="")
        self.lbl_result.image = tk_img


if __name__ == "__main__":
    root = tk.Tk()
    app = HistogramApp(root)
    root.mainloop()
