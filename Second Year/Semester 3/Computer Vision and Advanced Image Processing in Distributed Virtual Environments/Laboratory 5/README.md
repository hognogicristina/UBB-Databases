# Hough Transform Shape Detection

This project demonstrates how to detect **lines**, **line segments**, and **circles** in an image using OpenCV’s Hough Transform
functions.  
It also explores how changing different parameters affects the detection results by generating **collage images** for easy visual
comparison.

## Features

- Detect **infinite lines** using the **Standard Hough Transform**
- Detect **line segments** using the **Probabilistic Hough Transform**
- Detect **circles** using the **Hough Circle Transform**
- Automatically generate **row collages** of results for different parameter combinations:
    - Different thresholds for line detection
    - Different combinations of threshold, minimum line length, and maximum gap for segment detection
    - Different radius and sensitivity parameters for circle detection
- Results are saved in structured folders under `output/`

## Requirements

- Python 3.x
- The following Python packages:
    - `opencv-python`
    - `numpy`
    - `matplotlib`

Install them with:

```bash
pip install opencv-python numpy matplotlib
````

## Project Structure

Expected folder layout:

```text
.
├── input/
│   └── image.jpg
├── output/
│   ├── lines/
│   ├── segments/
│   └── circles/
└── main.py
```

## How It Works

### 1. Line Detection – Standard Hough Transform

Function: `detect_lines(image, threshold)`

* Converts the image to grayscale
* Runs Canny edge detection
* Uses `cv2.HoughLines` to detect **infinite lines**
* Draws red lines (thickness 2) over the original image

In `run_line_detection(image)`:

* Uses several threshold values: `[100, 130, 150, 200]`
* For each threshold, runs `detect_lines`
* Puts all results into a **single row collage**
* Saves as:

```text
output/lines/lines_collage.png
```

### 2. Line Segment Detection – Probabilistic Hough Transform

Function:
`detect_segments(image, threshold, min_line_length, max_line_gap)`

* Grayscale + Canny edge detection
* Uses `cv2.HoughLinesP` to detect **finite line segments**
* Draws green segments (thickness 5) on the original image

In `optimize_segment_detection(image)`:

* Fixed parameters:

    * `thresholds = [80, 100, 120]`
    * `min_lengths = [50, 100, 150]`
* Variable parameter for each row:

    * `max_gaps = [10, 15, 20]`

For each `(threshold, min_line_length)` combination:

* Varies `max_line_gap` over all values in `max_gaps`
* Creates a row collage with:

    * 1 image per `max_line_gap`
    * Titles like `Gap: 10`, `Gap: 15`, etc.
* Saves as:

```text
output/segments/segments_th{threshold}_len{min_length}.png
```

Example filenames:

* `segments_th80_len50.png`
* `segments_th100_len100.png`
* `segments_th120_len150.png`

### 3. Circle Detection – Hough Circle Transform

Function:
`detect_circles(image, min_radius, max_radius, param1, param2)`

* Converts to grayscale
* Applies Gaussian blur
* Uses `cv2.HoughCircles` with:

    * `minRadius = min_radius`
    * `maxRadius = max_radius`
    * `param1`, `param2` as sensitivity / edge thresholds
* Draws:

    * Blue circle outline (thickness 4)
    * Orange square at the circle center

In `optimize_circle_detection(image)`:

* Fixed radius ranges:

    * `min_radii = [30, 50, 80]`
    * `max_radii = [100, 200, 300]`
* Variable parameters per row:

    * `param1_values = [50, 100]`
    * `param2_values = [60, 80]`
* For each `(min_r, max_r)` pair:

    * Tries all combinations of `(param1, param2)`
    * Creates a row collage of circle detections
    * Titles like: `p1:50 p2:60`

Results saved as:

```text
output/circles/circles_min{min_r}_max{max_r}.png
```

Example filenames:

* `circles_min30_max100.png`
* `circles_min50_max200.png`
* `circles_min80_max300.png`

## Collage Generation

Function: `save_row_collage(results, titles, folder_name, filename)`

* Takes a list of images (`results`) and their titles
* Displays them in a **single row** using Matplotlib
* Converts BGR (OpenCV) → RGB (Matplotlib) before plotting
* Disables axes and adds small titles
* Saves the figure under:

```text
output/{folder_name}/{filename}
```

Examples:

* `output/lines/lines_collage.png`
* `output/segments/segments_th80_len50.png`
* `output/circles/circles_min50_max200.png`

## Running the Script

1. Place your input image at:

```text
input/image.jpg
```

2. Run the script:

```bash
python3 main.py
```

3. If the image can’t be loaded, you’ll see:

```text
Error: Could not find image at input/image.jpg
```

4. If everything works, you’ll see messages like:

```text
Created directory: output/lines
Created directory: output/segments
Created directory: output/circles
Running Line Detection...
Running Segment Detection optimization...
Running Circle Detection optimization...
Processing complete. Images saved to 'output/' subfolders.
```

Check the `output/` folder for the generated collages.