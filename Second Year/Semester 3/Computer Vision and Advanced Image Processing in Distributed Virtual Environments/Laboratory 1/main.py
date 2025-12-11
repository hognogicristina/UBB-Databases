import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

SCENE_PATH = INPUT_DIR / "image.jpg"
LOGO_PATH = INPUT_DIR / "opencv_logo.jpg"
VIDEO_PATH = INPUT_DIR / "video.mp4"

OUT_IMAGE = OUTPUT_DIR / "image_with_logo.jpg"
OUT_VIDEO = OUTPUT_DIR / "video_with_logo.mp4"

TOP_LEFT = (20, 20)
LOGO_WIDTH = 200
THRESH = 245


def load_image(path: Path, as_color=True):
    flag = cv2.IMREAD_COLOR if as_color else cv2.IMREAD_GRAYSCALE
    img = cv2.imread(str(path), flag)
    if img is None:
        raise FileNotFoundError(f"Could not read: {path.resolve()}")
    return img


def make_logo_masks(logo_bgr, thresh=245):
    gray = cv2.cvtColor(logo_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
    inv_mask = cv2.bitwise_not(mask)
    return mask, inv_mask


def overlay_logo(scene_bgr, logo_bgr, top_left=(20, 20), logo_width=200, thresh=245):
    h, w = logo_bgr.shape[:2]
    scale = logo_width / float(w)
    new_size = (int(w * scale), int(h * scale))
    logo_resized = cv2.resize(logo_bgr, new_size, interpolation=cv2.INTER_AREA)

    mask, inv_mask = make_logo_masks(logo_resized, thresh=thresh)

    lh, lw = logo_resized.shape[:2]
    x, y = top_left
    H, W = scene_bgr.shape[:2]
    x = max(0, min(W - lw, x))
    y = max(0, min(H - lh, y))

    roi = scene_bgr[y:y + lh, x:x + lw]
    fg = cv2.bitwise_and(logo_resized, logo_resized, mask=mask)
    bg = cv2.bitwise_and(roi, roi, mask=inv_mask)
    out = cv2.add(bg, fg)

    result = scene_bgr.copy()
    result[y:y + lh, x:x + lw] = out
    return result


class FullScreenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Logo Overlay")
        self.root.geometry("1200x800")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.logo = load_image(LOGO_PATH)
        self.static_scene = load_image(SCENE_PATH)

        self.cap = None
        self.writer = None
        self.is_video_playing = False
        self.skip_video_save = False

        self.current_before = None
        self.current_after = None

        nav_frame = tk.Frame(root, pady=10)
        nav_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Button(nav_frame, text="Page 1: Image", command=self.show_image_page, fg="black").pack(side=tk.LEFT, padx=20)
        tk.Button(nav_frame, text="Page 2: Video", command=self.show_video_page, fg="black").pack(side=tk.LEFT, padx=20)

        tk.Button(nav_frame, text="QUIT", command=self.quit_app, fg="black", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=20)

        self.content_frame = tk.Frame(root, bg="#222")
        self.content_frame.pack(expand=True, fill=tk.BOTH)

        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.columnconfigure(1, weight=1)
        self.content_frame.rowconfigure(1, weight=1)

        tk.Label(self.content_frame, text="BEFORE", fg="white", bg="#222", font=("Arial", 12, "bold")).grid(row=0, column=0, pady=5)
        tk.Label(self.content_frame, text="AFTER", fg="white", bg="#222", font=("Arial", 12, "bold")).grid(row=0, column=1, pady=5)

        self.lbl_before = tk.Label(self.content_frame, bg="#222")
        self.lbl_before.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        self.lbl_after = tk.Label(self.content_frame, bg="#222")
        self.lbl_after.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)

        self.content_frame.bind("<Configure>", self.on_resize)
        self.show_image_page()

    def cleanup_video(self):
        self.is_video_playing = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.writer:
            self.writer.release()
            self.writer = None
            if not self.skip_video_save:
                print(f"Video saved to: output/{OUT_VIDEO.name}")
            else:
                print("")

    def quit_app(self):
        self.cleanup_video()
        self.root.destroy()

    def resize_and_convert(self, cv_img, target_width, target_height):
        if cv_img is None: return None
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        img_w, img_h = pil_img.size
        ratio = min(target_width / img_w, target_height / img_h)
        new_size = (int(img_w * ratio), int(img_h * ratio))

        resized = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(resized)

    def on_resize(self, event):
        if self.current_before is None: return
        w = (event.width // 2) - 10
        h = event.height - 40
        if w < 10 or h < 10: return
        self.update_display_images(w, h)

    def update_display_images(self, width, height):
        tk_before = self.resize_and_convert(self.current_before, width, height)
        tk_after = self.resize_and_convert(self.current_after, width, height)

        self.lbl_before.config(image=tk_before)
        self.lbl_before.image = tk_before
        self.lbl_after.config(image=tk_after)
        self.lbl_after.image = tk_after

    def refresh_current_view(self):
        w = (self.content_frame.winfo_width() // 2) - 10
        h = self.content_frame.winfo_height() - 40
        if w > 10 and h > 10:
            self.update_display_images(w, h)

    def show_image_page(self):
        self.cleanup_video()

        self.current_before = self.static_scene
        self.current_after = overlay_logo(self.static_scene, self.logo, top_left=TOP_LEFT, logo_width=LOGO_WIDTH, thresh=THRESH)

        if not OUT_IMAGE.exists():
            cv2.imwrite(str(OUT_IMAGE), self.current_after)
            print(f"Image saved to: output/{OUT_IMAGE.name}")
        else:
            print("")

        self.refresh_current_view()

    def show_video_page(self):
        if self.is_video_playing: return

        self.cap = cv2.VideoCapture(str(VIDEO_PATH))
        if not self.cap.isOpened():
            print("Error opening video file")
            return

        if OUT_VIDEO.exists():
            self.skip_video_save = True
            self.writer = None
        else:
            self.skip_video_save = False
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.writer = cv2.VideoWriter(str(OUT_VIDEO), fourcc, fps, (width, height))

        self.is_video_playing = True
        self.video_loop()

    def video_loop(self):
        if not self.is_video_playing or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if self.writer:
                self.writer.release()
                self.writer = None

        processed = overlay_logo(frame, self.logo, top_left=TOP_LEFT, logo_width=LOGO_WIDTH, thresh=THRESH)

        if self.writer:
            self.writer.write(processed)

        self.current_before = frame
        self.current_after = processed
        self.refresh_current_view()

        self.root.after(33, self.video_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = FullScreenApp(root)
    root.mainloop()
