"""Compression engine. It runs inside the Streamlit process, so no external API is needed.

Images : pre-trained neural codecs from CompressAI (hyperprior, Minnen mean-scale, Cheng anchor).
         The latent code is written to a small `.nic` file that `decode_nic` can read back.
Video  : classical baseline, H.265/HEVC or H.264 through ffmpeg (CPU).

This module has no Streamlit dependency. Heavy libraries (torch, compressai) are imported lazily,
so the app can start and report a clear problem if one of them is missing.
"""

from __future__ import annotations

import functools
import io
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Limits (override with environment variables if your server is bigger)
# ---------------------------------------------------------------------------
MAX_IMAGE_SIDE = int(os.environ.get("MAX_IMAGE_SIDE", "1600"))      # px, longest side
MAX_VIDEO_SECONDS = int(os.environ.get("MAX_VIDEO_SECONDS", "30"))  # clip length
MAX_VIDEO_HEIGHT = int(os.environ.get("MAX_VIDEO_HEIGHT", "1080"))  # px, larger videos are scaled down
VIDEO_TIMEOUT_S = int(os.environ.get("VIDEO_TIMEOUT_S", "900"))
PRETRAINED = os.environ.get("NIC_PRETRAINED", "1") != "0"           # "0" is only used by tests

# UI model name -> (CompressAI model, highest available quality)
MODEL_SPECS = {
    "fast": ("bmshj2018_hyperprior", 8),    # Ballé et al., hyperprior
    "better": ("mbt2018_mean", 8),          # Minnen et al., mean-scale hyperprior
    "best": ("cheng2020_anchor", 6),        # Cheng et al., anchor
}

# Video preset -> CRF (lower CRF = higher quality, larger file)
VIDEO_CRF = {
    "h265": {"near": 18, "high": 23, "balanced": 28, "max": 34},
    "h264": {"near": 17, "high": 22, "balanced": 27, "max": 33},
}
VIDEO_ENCODERS = {"h265": ("libx265", "x265 · CPU"), "h264": ("libx264", "x264 · CPU")}

MAGIC = b"NIC1"

# Only one heavy job at a time: a small free CPU server stays stable this way.
_JOB_LOCK = threading.Lock()


class EngineError(Exception):
    """A problem with a message that is safe to show to the user."""


def is_busy() -> bool:
    """True while another file is being processed."""
    return _JOB_LOCK.locked()


def max_quality(model: str) -> int:
    return MODEL_SPECS[model][1]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def _ffmpeg_encoders() -> str:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20)
        return out.stdout
    except Exception:
        return ""


def health() -> dict:
    """What works on this server. Nothing is assumed: each part is really checked."""
    info = {"image_ok": False, "video_ok": False, "device": "CPU", "torch": None, "problems": []}
    try:
        import compressai  # noqa: F401
        import torch
        info["torch"] = torch.__version__
        info["device"] = "CPU"
        info["image_ok"] = True
    except Exception as exc:
        info["problems"].append(f"Image engine unavailable (PyTorch / CompressAI): {exc}")
    encoders = _ffmpeg_encoders()
    if not encoders:
        info["problems"].append("Video engine unavailable: ffmpeg / ffprobe was not found on the server.")
    elif "libx265" not in encoders or "libx264" not in encoders:
        info["problems"].append("Video engine unavailable: this ffmpeg build has no libx265 / libx264.")
    else:
        info["video_ok"] = True
    return info


# ---------------------------------------------------------------------------
# Image compression
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=3)
def _load_model(model: str, quality: int):
    """Load (and cache) one network. The first call downloads the pre-trained weights."""
    from compressai import zoo

    name, _ = MODEL_SPECS[model]
    net = getattr(zoo, name)(quality=quality, pretrained=PRETRAINED).eval()
    net.update(force=True)
    return net


def warmup() -> None:
    """Download the default weights ahead of time (used while building the Docker image)."""
    for model, (_, top) in MODEL_SPECS.items():
        q = min(6, top)
        print(f"Loading {model} (quality {q}) ...", flush=True)
        _load_model(model, q)


def _psnr_uint8(a, b) -> float | None:
    import numpy as np

    mse = float(np.mean((a.astype("float64") - b.astype("float64")) ** 2))
    return None if mse == 0 else 10 * math.log10(255.0**2 / mse)


def _msssim(x, y):
    """MS-SSIM of two float tensors in [0, 1]; None when the image is too small for it."""
    try:
        from pytorch_msssim import ms_ssim

        return float(ms_ssim(x, y, data_range=1.0))
    except Exception:
        return None


def _jpeg_same_size(img, target_bytes: int, ref_arr) -> dict | None:
    """Best JPEG that fits in `target_bytes` (or quality 1 if none fits), and its PSNR."""
    import numpy as np
    from PIL import Image

    def encode(q):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)
        return buf.getvalue()

    lo, hi, best = 1, 95, None
    while lo <= hi:
        mid = (lo + hi) // 2
        data = encode(mid)
        if len(data) <= target_bytes:
            best, lo = (mid, data), mid + 1
        else:
            hi = mid - 1
    if best is None:
        best = (1, encode(1))
    q, data = best
    dec = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
    return {"psnr": _psnr_uint8(ref_arr, dec), "quality": q, "bytes": len(data)}


def _pack_nic(model: str, quality: int, h: int, w: int, out: dict) -> bytes:
    streams = []
    for group in out["strings"]:
        if len(group) != 1:
            raise EngineError("Unexpected codec output.")
        streams.append(group[0])
    header = json.dumps({
        "model": model, "quality": quality, "height": h, "width": w,
        "shape": list(out["shape"]), "lengths": [len(s) for s in streams],
    }).encode()
    return MAGIC + struct.pack("<I", len(header)) + header + b"".join(streams)


def decode_nic(data: bytes):
    """Rebuild the image from a `.nic` file. Returns a PIL image."""
    import numpy as np
    import torch
    from PIL import Image

    if data[:4] != MAGIC:
        raise EngineError("This is not a valid .nic file.")
    (hlen,) = struct.unpack("<I", data[4:8])
    head = json.loads(data[8:8 + hlen])
    pos, strings = 8 + hlen, []
    for n in head["lengths"]:
        strings.append([data[pos:pos + n]])
        pos += n
    net = _load_model(head["model"], head["quality"])
    with torch.inference_mode():
        rec = net.decompress(strings, head["shape"])["x_hat"]
    rec = rec[:, :, :head["height"], :head["width"]].clamp(0, 1)
    arr = (rec[0].permute(1, 2, 0).numpy() * 255).round().astype("uint8")
    return Image.fromarray(np.ascontiguousarray(arr))


def compress_image(raw: bytes, model: str, quality: int) -> dict:
    """Compress one image. Returns the measured results plus the output files as bytes."""
    if model not in MODEL_SPECS:
        raise EngineError(f"Unknown model: {model}")
    quality = max(1, min(int(quality), max_quality(model)))
    try:
        import numpy as np
        import torch
        import torch.nn.functional as F
        from PIL import Image, ImageOps
    except Exception as exc:
        raise EngineError(f"The image engine is not installed correctly: {exc}") from exc

    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception as exc:
        raise EngineError("This file could not be read as an image.") from exc

    resized_from = None
    if max(img.size) > MAX_IMAGE_SIDE:
        resized_from = img.size
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
    arr = np.asarray(img)
    h, w = arr.shape[:2]

    x = torch.from_numpy(arr.copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
    pad_h, pad_w = (-h) % 64, (-w) % 64
    xp = F.pad(x, (0, pad_w, 0, pad_h), mode="replicate")

    with _JOB_LOCK:
        try:
            net = _load_model(model, quality)
            t0 = time.time()
            with torch.inference_mode():
                out = net.compress(xp)
                rec = net.decompress(out["strings"], out["shape"])["x_hat"]
            seconds = time.time() - t0
        except EngineError:
            raise
        except MemoryError as exc:
            raise EngineError("The server ran out of memory. Try a smaller image.") from exc
        except Exception as exc:
            raise EngineError(f"The codec failed: {exc}") from exc

    rec = rec[:, :, :h, :w].clamp(0, 1)
    rec_arr = (rec[0].permute(1, 2, 0).numpy() * 255).round().astype("uint8")
    nic = _pack_nic(model, quality, h, w, out)

    png = io.BytesIO()
    Image.fromarray(rec_arr).save(png, "PNG")

    return {
        "original_bytes": len(raw),
        "compressed_bytes": len(nic),
        "psnr": _psnr_uint8(arr, rec_arr),
        "msssim": _msssim(x, torch.from_numpy(rec_arr.copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)),
        "width": w, "height": h,
        "bpp": len(nic) * 8 / (w * h),
        "encode_s": seconds,
        "device": "CPU",
        "model": model, "quality": quality,
        "resized_from": resized_from,
        "jpeg": _jpeg_same_size(img, len(nic), arr),
        "files": {"preview": png.getvalue(), "nic": nic},
    }


# ---------------------------------------------------------------------------
# Video compression (ffmpeg)
# ---------------------------------------------------------------------------
def _probe_video(path: Path) -> dict:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration:format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(r.stdout or "{}")
    except Exception as exc:
        raise EngineError("The video could not be analysed.") from exc
    streams = data.get("streams") or []
    if not streams:
        raise EngineError("No video stream was found in this file.")
    s = streams[0]
    duration = None
    for value in (s.get("duration"), (data.get("format") or {}).get("duration")):
        try:
            duration = float(value)
            break
        except (TypeError, ValueError):
            continue
    if not duration or duration <= 0:
        raise EngineError("The video length could not be read.")
    return {"width": s.get("width"), "height": s.get("height"), "duration": duration}


def compress_video(raw: bytes, filename: str, level: str, codec: str = "h265", on_progress=None) -> dict:
    """Re-encode a short video. `on_progress(fraction)` is called while ffmpeg runs."""
    if codec not in VIDEO_ENCODERS or level not in VIDEO_CRF[codec]:
        raise EngineError("Unknown video setting.")
    if not shutil.which("ffmpeg"):
        raise EngineError("ffmpeg is not installed on the server.")
    suffix = Path(filename).suffix.lower()
    suffix = suffix if suffix in {".mp4", ".mov", ".webm", ".mkv"} else ".mp4"
    lib, label = VIDEO_ENCODERS[codec]

    with tempfile.TemporaryDirectory() as tmp:
        src, dst, errlog = Path(tmp, f"in{suffix}"), Path(tmp, "out.mp4"), Path(tmp, "err.log")
        src.write_bytes(raw)
        info = _probe_video(src)
        if info["duration"] > MAX_VIDEO_SECONDS + 0.5:
            raise EngineError(
                f"The video is {info['duration']:.0f} s long. This server accepts clips up to "
                f"{MAX_VIDEO_SECONDS} s. Trim the clip and try again."
            )

        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(src),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", f"scale=-2:'min({MAX_VIDEO_HEIGHT},ih)'",
            "-c:v", lib, "-preset", "veryfast", "-crf", str(VIDEO_CRF[codec][level]), "-pix_fmt", "yuv420p",
        ]
        if codec == "h265":
            cmd += ["-tag:v", "hvc1", "-x265-params", "log-level=error"]
        cmd += ["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                "-progress", "pipe:1", "-nostats", str(dst)]

        with _JOB_LOCK:
            t0 = time.time()
            with open(errlog, "wb") as err:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, text=True)
                try:
                    for line in proc.stdout:
                        if time.time() - t0 > VIDEO_TIMEOUT_S:
                            proc.kill()
                            raise EngineError("Encoding took too long and was stopped. Try a shorter clip.")
                        key, _, value = line.strip().partition("=")
                        if on_progress and key in ("out_time_us", "out_time_ms"):
                            try:
                                on_progress(min(float(value) / 1e6 / info["duration"], 1.0))
                            except ValueError:
                                pass
                    proc.wait()
                finally:
                    if proc.poll() is None:
                        proc.kill()
            seconds = time.time() - t0

        if proc.returncode != 0 or not dst.exists():
            tail = errlog.read_text(errors="replace").strip().splitlines()[-3:]
            raise EngineError("ffmpeg could not encode this video. " + " ".join(tail)[:300])
        data = dst.read_bytes()
        out = _probe_video(dst)

    if on_progress:
        on_progress(1.0)
    return {
        "original_bytes": len(raw), "compressed_bytes": len(data),
        "engine": label, "seconds": seconds,
        "width": out["width"], "height": out["height"], "duration": out["duration"],
        "codec": codec, "level": level,
        "files": {"video": data},
    }
