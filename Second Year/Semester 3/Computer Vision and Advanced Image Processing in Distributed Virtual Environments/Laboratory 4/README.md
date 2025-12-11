# Histogram-Based Image Retrieval

## Project Overview

This project implements a **content-based image retrieval (CBIR)** system using **grayscale histograms** and **OpenCV’s histogram comparison
metrics**.
Given a dataset of images and a query image, the system identifies the most similar images by comparing histogram signatures.

The program:

1. Loads all images from the dataset
2. Computes grayscale histograms using:

    * **256 bins**
    * **64 bins**
    * **32 bins**
3. Compares every image histogram with the query image histogram using all OpenCV comparison metrics
4. Normalizes the results relative to `comp(Q,Q)` (perfect similarity)
5. Saves numerical results (CSV) and visual results (collages)
6. Prints formatted tables in the terminal

The system can be executed with **one command**:

```bash
python3 main.py
```

## Dependencies

Install them with:

```bash
pip install opencv-python numpy
```

## Dataset Structure

Place your dataset inside a folder called `input/`:

```
input/
    banana/
        image_0001.jpg
        image_0002.jpg
        ...
    giraffe/
        image_0001.jpg
        ...
    tennis_ball/
        image_0001.jpg
        ...
    zebra/
        image_0001.jpg
        ...
```

Each category contains at least **20 images** downloaded from the internet (landscapes, objects, animals, etc.).

## How It Works

### 1. Histogram Computation

Images are converted to **grayscale**, and a **1D histogram** is computed with:

* 256 bins
* 64 bins (color reduction)
* 32 bins (strong color reduction)

Histograms are **L1-normalized** → sum of bins = 1.

### 2. Histogram Comparison Metrics

The following OpenCV metrics are automatically detected and used if available:

| Metric Name    | OpenCV Constant         | Meaning                        | Best Similarity |
|----------------|-------------------------|--------------------------------|-----------------|
| CORRELATION    | `HISTCMP_CORREL`        | Statistical correlation        | **Higher**      |
| CHI-SQUARE     | `HISTCMP_CHISQR`        | χ² distance                    | **Lower**       |
| INTERSECTION   | `HISTCMP_INTERSECT`     | Bin-wise overlap               | **Higher**      |
| BHATTACHARYYA  | `HISTCMP_BHATTACHARYYA` | Distance between distributions | **Lower**       |
| CHI-SQUARE ALT | `HISTCMP_CHISQR_ALT`    | Alternative chi-square         | **Lower**       |
| KL-DIV         | `HISTCMP_KL_DIV`        | Kullback-Leibler divergence    | **Lower**       |

### 3. Normalization

Since metrics behave differently, all scores are normalized into the range **[0, 1]**,
with:

* `1.0` → perfect similarity (`comp(Q,Q)`)
* `0.0` → least similar image

### 4. Output

After each experiment, the script prints a table like:

```
METRIC: CORRELATION | BINS: 64
Idx  Image                                      Raw        Norm
0    banana/image_0001.jpg (Q)                  1.000000   1.000000
8    banana/image_0009.jpg                      0.912341   0.912341
...
```

And generates output files:

```
output/
    bins_256/
        scores_CORRELATION_bins256.csv
        top_matches_CORRELATION_bins256.jpg
        ...
    bins_64/
        ...
    bins_32/
        ...
```

Each collage highlights the query image and the top matches for that metric.

## Example Output (Collage)

*(Your actual collages will be saved to `output/bins_xx/`)*

The collage displays:

* Query image (marked as “Q:”)
* Top 5 most similar images
* Similarity score (normalized)


| Input                      | Output                                                   |
|----------------------------|----------------------------------------------------------|
| 32 Bins with BHATTACHARYYA | ![](output/bins_32/top_matches_BHATTACHARYYA_bins32.jpg) |

## Interpretation of Results

### Effect of Different Metrics

* **CORRELATION** and **INTERSECTION** behave similarly → high when histograms match.
* **CHI-SQUARE**, **BHATTACHARYYA**, and **KL-DIV** capture **differences** → low means similar.
* KL-DIV is sensitive to zero bins; L1 normalization reduces issues.

### Effect of Reducing Bins (256 → 64 → 32)

* 256 bins: most precise matching
* 64 bins: smoother, more tolerant to noise or lighting variations
* 32 bins: strongest generalization, but may lose fine image details

### Can Histogram Comparison Be Used for CBIR?

**Yes — but only for very coarse similarity.**
Histogram-based retrieval:

✔ Works well for images dominated by similar color/brightness
✘ Fails for structural differences (e.g., same colors but different objects)
✘ Cannot detect shapes, edges, textures, or spatial structure

Therefore, histogram comparison is a **baseline CBIR method**, useful but limited.