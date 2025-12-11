# Edge Detection

Edge Detection is a desktop application built with Python, Tkinter, and OpenCV that allows real-time visual comparison of four
fundamental edge detection algorithms: Roberts, Sobel, Prewitt, and Canny. The application loads a single image and displays the results of
all four filters simultaneously in a 2x2 collage layout. A dynamic blur slider is included to control the preprocessing stage of the Canny
algorithm.

## Features

* Real-time comparison of four edge detection algorithms:

    * Roberts
    * Sobel
    * Prewitt
    * Canny
* Dynamic Gaussian blur control for the Canny filter using a slider
* High-quality image resizing using Lanczos resampling
* Automatic adaptive thresholding for Canny using image median
* Fullscreen responsive interface
* Automatic image scaling for all window sizes

## Algorithms Implemented

### 1. Roberts Operator

A simple and fast gradient-based method using a 2x2 kernel to detect intensity changes. It is sensitive to noise but excellent for detecting
sharp edges in high-contrast images.

### 2. Sobel Operator

Uses two 3x3 convolution kernels to compute horizontal and vertical gradients. It provides strong noise resistance while maintaining good
edge localization.

### 3. Prewitt Operator

Similar to Sobel but with uniform kernel weights. It performs best on large, well-centered objects and produces slightly softer edges.

### 4. Canny Edge Detector

A multi-stage edge detection algorithm that includes:

* Gaussian smoothing
* Gradient computation
* Non-maximum suppression
* Double thresholding with hysteresis
  This implementation includes a dynamic blur control and automatic adaptive threshold selection.

## Requirements

Make sure you have Python 3.9 or newer installed.

Required Python packages:

```
opencv-python
numpy
Pillow
```

## Installation

1. Clone the repository or copy the source file into a local directory.

2. Create and activate a virtual environment (recommended):

```
python -m venv venv
source venv/bin/activate        (macOS/Linux)
venv\Scripts\activate          (Windows)
```

3. Install dependencies:

```
pip install opencv-python numpy pillow
```

## Running the Application

From the project directory, run:

```
python main.py
```

The application will start in fullscreen mode.

## How to Use

1. Click the "OPEN IMAGE" button to load a photo.
2. The four-edge detection results will be displayed immediately:

    * Top-left: Roberts
    * Top-right: Sobel
    * Bottom-left: Prewitt
    * Bottom-right: Canny
3. Use the "Canny Blur Size" slider to control the Gaussian blur kernel applied before edge detection.
4. The blur kernel size is always adjusted to remain an odd number.
5. Resize the window and the images will automatically scale correctly.
6. Click "EXIT" to close the application.