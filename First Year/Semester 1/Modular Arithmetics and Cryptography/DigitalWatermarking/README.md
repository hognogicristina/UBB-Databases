# Watermarking Service - README

## Overview

This repository implements an **image watermarking application** using Node.js with Express. It provides functionality for adding both **invisible (modular)** and **visible (text/image-based)** watermarks to images. The application includes an interactive client-side interface to
demonstrate the watermarking capabilities.

---

## Features

1. **Invisible Watermark**:
    - Applies a modular transformation watermark to the image.
    - Encodes watermark data using mathematical operations `(pixel_value + K) % N`.
    - Displays the original pixel value (M) and the watermarked pixel value (W).

2. **Visible Watermark**:
    - Adds a visible watermark to an image, which can be:
        - **Text-based**, with customizable font, size, and color.
        - **Image-based**, with options for positioning, scaling, and opacity.

3. **Revert Functionality**:
    - Enables users to view the original image by removing the visible watermark.

---

## Technologies Used

- **Backend**:
    - [Node.js](https://nodejs.org)
    - [Express](https://expressjs.com)
    - [Multer](https://github.com/expressjs/multer) for file uploads.
    - [Sharp](https://sharp.pixelplumbing.com) for image processing.
- **Frontend**:
    - Vanilla JavaScript for client-side interactivity.
    - Responsive, user-friendly HTML/CSS interface.

---

## Setup Instructions

### Prerequisites

- Node.js (v14 or higher)
- npm (Node Package Manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hognogicristina/DigitalWatermarking.git
   cd DigitalWatermarking
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the server:
   ```bash
   npm start
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

---

## API Endpoints

### 1. **Invisible Watermark**

- **Endpoint**: `POST /watermark`
- **Request**:
    - Form-Data:
        - `image` (required): The image file.
        - `key` (optional): Watermark key `K` (default: 0).
        - `modulus` (optional): Modulus value `N` (default: 256).
- **Response**:
    - `mValue`: Original pixel value.
    - `wValue`: Watermarked pixel value.
    - `imageBase64`: Base64 string of the watermarked image.

### 2. **Visible Watermark**

- **Endpoint**: `POST /encode-visible`
- **Request**:
    - Form-Data:
        - `image` (required): Main image file.
        - `watermark` (optional): Watermark image file.
        - `text` (optional): Text for the watermark.
        - `left`, `top`: Positioning of the watermark (default: `0`).
        - `wmWidth`, `wmHeight`: Dimensions of the watermark (default: original size).
        - `opacity`: Opacity of the watermark (default: `0.3`).
- **Response**:
    - `watermarked`: Base64 string of the watermarked image.

---

## Usage

### Invisible Watermark

1. Select an image and upload it.
2. Provide optional parameters:
    - **Key (K)**: An integer value for the watermark encoding.
    - **Modulus (N)**: Modulus for the watermark encoding.
3. Click **Apply Invisible Watermark** to generate a watermarked image.

### Visible Watermark

1. Select the **main image** and optionally:
    - Upload a watermark image **OR** enter text for the watermark.
    - Customize the position, size, and opacity.
2. Click **Add Visible Watermark** to generate a watermarked image.

### Preview & Revert

- View previews of watermarked images.
- Revert visible watermark to the original image.

---

## File Structure

```
.
├── server.js          # Main application server
├── client/            # Static assets (HTML, CSS, JS)
├── node_modules/      # npm dependencies
├── package.json       # Project metadata
└── README.md          # Documentation
```

---

## Future Improvements

1. **Download Watermarked Images**:
    - Add functionality to download the processed images directly.

2. **Custom Watermark Shapes**:
    - Add more shapes (e.g., rectangles, polygons) for visible watermarks.

3. **Enhanced Security**:
    - Encrypt watermark data for invisible watermarks.

4. **Cloud Integration**:
    - Store watermarked images on cloud services like AWS S3 or Google Cloud.

---

Happy watermarking! 😊