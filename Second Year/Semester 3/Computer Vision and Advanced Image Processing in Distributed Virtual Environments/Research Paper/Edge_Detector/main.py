import tkinter as tk
from tkinter import filedialog, Label, Frame, Button, Scale, HORIZONTAL
import cv2
import numpy as np
from PIL import Image, ImageTk


def apply_roberts(gray):
    """
    Applies Roberts Cross operator to detect edges
    gray: Grayscale image as a numpy array
    """
    img = gray.astype('float64') / 255.0
    v = cv2.filter2D(img, -1, np.array([[1, 0], [0, -1]]))
    h = cv2.filter2D(img, -1, np.array([[0, 1], [-1, 0]]))
    mag = np.sqrt(np.square(v) + np.square(h)) * 255
    return np.clip(mag, 0, 255).astype('uint8')


def apply_sobel(gray):
    """
    Applies Sobel operator to detect edges
    gray: Grayscale image as a numpy array
    """
    gx = cv2.filter2D(gray, cv2.CV_64F, np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]))
    gy = cv2.filter2D(gray, cv2.CV_64F, np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]]))
    mag = cv2.normalize(np.sqrt(gx ** 2 + gy ** 2), None, 0, 255, cv2.NORM_MINMAX)
    return mag.astype('uint8')


def apply_prewitt(gray):
    """
    Applies Prewitt operator to detect edges
    gray: Grayscale image as a numpy array
    """
    gx = cv2.filter2D(gray, cv2.CV_64F, np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]]))
    gy = cv2.filter2D(gray, cv2.CV_64F, np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]]))
    mag = cv2.normalize(np.sqrt(gx ** 2 + gy ** 2), None, 0, 255, cv2.NORM_MINMAX)
    return mag.astype('uint8')


def apply_canny(gray, kernel_size=5):
    """
    Applies Gaussian Blur manually before Canny edge detection
    gray: Grayscale image as a numpy array
    kernel_size: Must be an odd number (1, 3, 5...)
    """
    if kernel_size > 1:
        processed_img = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
    else:
        processed_img = gray

    v_median = np.median(processed_img)
    sigma = 0.33
    lower = int(max(0, (1.0 - sigma) * v_median))
    upper = int(min(255, (1.0 + sigma) * v_median))

    return cv2.Canny(processed_img, lower, upper)


def display_image_on_label(img_array, label):
    w_box = label.winfo_width()
    h_box = label.winfo_height()

    if w_box < 50 or h_box < 50: return

    im = Image.fromarray(img_array)

    im_ratio = im.width / im.height
    box_ratio = w_box / h_box

    if im_ratio > box_ratio:
        new_w = w_box
        new_h = int(w_box / im_ratio)
    else:
        new_h = h_box
        new_w = int(h_box * im_ratio)

    im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    imgtk = ImageTk.PhotoImage(image=im)
    label.config(image=imgtk, text="")
    label.image = imgtk


class EdgeDetectorApp:
    def __init__(self, root):
        self.view_frame = None
        self.root = root
        self.root.title("Edge Detection Studio - 2x2 Collage")

        self.colors = {
            "bg": "#121212",
            "panel_bg": "#1e1e1e",
            "text": "#ffffff",
            "accent": "#4a69bd",
            "border": "#333333",
            "quad_titles": "#b0b0b0"
        }

        self.processed_images = {}
        self.collage_views = {}
        self.current_gray_image = None

        self.canny_blur_val = tk.IntVar(value=5)

        try:
            self.root.state('zoomed')
        except:
            w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry(f"{w}x{h}")

        self.root.configure(bg=self.colors["bg"])

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.setup_header()
        self.setup_main_view()

    def setup_header(self):
        header = Frame(self.root, bg=self.colors["bg"], pady=15, padx=20)
        header.grid(row=0, column=0, sticky="ew")

        Label(header, text="Edge Detection Studio", font=("Segoe UI", 20, "bold"),
              bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left")

        btn_quit = Button(header, text="EXIT", command=self.root.destroy,
                          font=("Segoe UI", 10, "bold"), bg="#e74c3c", fg="#000000",
                          padx=20, pady=8, borderwidth=0, cursor="hand2", relief="flat")
        btn_quit.pack(side="right", padx=(10, 0))

        btn_load = Button(header, text="OPEN IMAGE", command=self.load_image,
                          font=("Segoe UI", 10, "bold"), bg=self.colors["accent"], fg="#000000",
                          padx=20, pady=8, borderwidth=0, cursor="hand2", relief="flat")
        btn_load.pack(side="right", padx=(20, 0))

        slider_frame = Frame(header, bg=self.colors["bg"])
        slider_frame.pack(side="right", padx=20)

        Label(slider_frame, text="Canny Blur Size", font=("Segoe UI", 9),
              bg=self.colors["bg"], fg="#bbbbbb").pack(side="top", anchor="w")

        self.blur_slider = Scale(slider_frame, from_=1, to=21, orient=HORIZONTAL,
                                 variable=self.canny_blur_val, command=self.on_blur_change,
                                 bg=self.colors["bg"], fg="white", highlightthickness=0,
                                 troughcolor="#333", length=150)
        self.blur_slider.pack(side="bottom")

    def setup_main_view(self):
        self.view_frame = Frame(self.root, bg=self.colors["bg"], padx=10, pady=10)
        self.view_frame.grid(row=1, column=0, sticky="nsew")

        self.view_frame.grid_rowconfigure(0, weight=1)
        self.view_frame.grid_rowconfigure(1, weight=1)
        self.view_frame.grid_columnconfigure(0, weight=1)
        self.view_frame.grid_columnconfigure(1, weight=1)

        def create_quadrant(row, col, title, map_key, color_scheme):
            frame = Frame(self.view_frame, bg=self.colors["panel_bg"], bd=2, relief="flat")
            frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            frame.pack_propagate(False)

            # Header for the quadrant
            head_frame = Frame(frame, bg=self.colors["panel_bg"])
            head_frame.pack(side="top", fill="x", pady=(5, 5))

            lbl = Label(head_frame, text=title, font=("Segoe UI", 11, "bold"),
                        bg=self.colors["panel_bg"], fg=color_scheme)
            lbl.pack(side="left", padx=5)

            if map_key == "Canny":
                self.canny_info_lbl = Label(head_frame, text="(Blur: 5)", font=("Segoe UI", 9),
                                            bg=self.colors["panel_bg"], fg="#888")
                self.canny_info_lbl.pack(side="right", padx=5)

            img_lbl = Label(frame, bg="#000000")
            img_lbl.pack(expand=True, fill="both", padx=2, pady=(0, 2))

            self.collage_views[map_key] = img_lbl
            return frame

        create_quadrant(0, 0, "1. Roberts", "Roberts", "#f6b93b")
        create_quadrant(0, 1, "2. Sobel", "Sobel", "#78e08f")
        create_quadrant(1, 0, "3. Prewitt", "Prewitt", "#e55039")
        create_quadrant(1, 1, "4. Canny", "Canny", "#a55eea")

        for lbl in self.collage_views.values():
            lbl.config(text="Load image...", fg="#555", font=("Segoe UI", 12))

        self.view_frame.bind('<Configure>', self.on_resize)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.jpeg *.bmp")])
        if not file_path: return

        img_bgr = cv2.imread(file_path)
        if img_bgr is None: return

        self.current_gray_image = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        self.processed_images["Original"] = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        self.processed_images["Roberts"] = apply_roberts(self.current_gray_image)
        self.processed_images["Sobel"] = apply_sobel(self.current_gray_image)
        self.processed_images["Prewitt"] = apply_prewitt(self.current_gray_image)

        self.on_blur_change(self.canny_blur_val.get())

        self.update_all_views()

    def on_blur_change(self, val):
        if self.current_gray_image is None:
            return

        k_size = int(val)
        if k_size % 2 == 0:
            k_size += 1

        self.canny_info_lbl.config(text=f"(Blur: {k_size})")
        self.processed_images["Canny"] = apply_canny(self.current_gray_image, kernel_size=k_size)

        if "Canny" in self.collage_views:
            display_image_on_label(self.processed_images["Canny"], self.collage_views["Canny"])

    def on_resize(self, event):
        if self.processed_images:
            self.update_all_views()

    def update_all_views(self):
        targets = ["Roberts", "Sobel", "Prewitt", "Canny"]
        for key in targets:
            if key in self.processed_images and key in self.collage_views:
                display_image_on_label(self.processed_images[key], self.collage_views[key])


if __name__ == "__main__":
    root = tk.Tk()
    app = EdgeDetectorApp(root)
    root.mainloop()
