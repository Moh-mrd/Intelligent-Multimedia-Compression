---
title: Intelligent Multimedia Compression
emoji: 🗜️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality

A single Streamlit application that compresses images and short videos. There is no external API:
the compression engine runs inside the app, on the server that hosts it (CPU).

- **Images:** pre-trained neural codecs from [CompressAI](https://github.com/InterDigitalInc/CompressAI)
  (`fast` = hyperprior, `better` = Minnen mean-scale, `best` = Cheng anchor). The latent code is stored
  in a small `.nic` file and decoded back to a PNG for comparison.
- **Videos:** classical baseline, H.265/HEVC or H.264 through ffmpeg.
- **Metrics (measured, never invented):** size, space saved, compression ratio, bitrate (bpp), PSNR,
  MS-SSIM, and a JPEG of about the same size for comparison.

Scope: inference with pre-trained models. Training and benchmarking are out of scope for this prototype.

## Project files

```
app.py                  Pages, layout and session state
engine.py               Compression engine (CompressAI for images, ffmpeg for video)
formatting.py           Number and size formatting helpers
components.py           HTML builders: header, metric cards, pills, empty states, footer
styles.py               Dark navy theme (CSS tokens and components)
requirements.txt        Python packages (CPU PyTorch, CompressAI, Streamlit)
Dockerfile              Image used by the Hugging Face Space (adds ffmpeg)
.streamlit/config.toml  Theme and upload limit
```

## Run locally

Requirements: Python 3.10 to 3.12 and ffmpeg (with libx265 and libx264) on your PATH.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The first use of each model downloads its weights (one time).

## Limits (CPU server)

| Setting | Default | Change with |
|---|---|---|
| Upload size | 50 MB | `.streamlit/config.toml` -> `server.maxUploadSize` (and `--server.maxUploadSize` in the Dockerfile) |
| Image longest side | 1600 px, larger images are scaled down | environment variable `MAX_IMAGE_SIDE` |
| Video length | 30 s | environment variable `MAX_VIDEO_SECONDS` |
| Video height | 1080 px, taller videos are scaled down | environment variable `MAX_VIDEO_HEIGHT` |

One file is processed at a time; other visitors wait in line.
Environment variables can be set in the Space under Settings -> Variables and secrets.

## Notes

1. `best` supports quality 1 to 6; `fast` and `better` support 1 to 8.
2. H.265/HEVC does not play inside every browser. The result can always be downloaded; H.264 plays everywhere.
3. PSNR and MS-SSIM are measured on the decoded 8-bit image against the (possibly scaled) input.
4. The JPEG comparison is the best JPEG that fits the same byte size as the `.nic` file.
