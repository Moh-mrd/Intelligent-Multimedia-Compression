"""Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality.

Streamlit application with a built-in compression engine (engine.py):
images are compressed with pre-trained neural codecs (CompressAI), videos are re-encoded with
ffmpeg (H.265 / H.264). Everything runs on the server that hosts this app. No external API.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import components as ui
import engine
from formatting import compression_ratio, fmt_num, format_size, space_saved
from styles import APP_CSS

IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
VIDEO_TYPES = ["mp4", "mov", "webm", "mkv"]

# label -> (value passed to the engine, short description)
IMAGE_MODELS = {
    "Fast": ("fast", "Hyperprior model. Fastest, good for large images."),
    "Better": ("better", "Minnen mean-scale model. Better compression, a little slower."),
    "Best": ("best", "Cheng model. Highest quality, slowest (quality 1 to 6)."),
}
VIDEO_LEVELS = {  # label -> value passed as `level`
    "Near Original": "near",
    "High (recommended)": "high",
    "Balanced": "balanced",
    "Maximum Compression": "max",
}
VIDEO_CODECS = {  # label -> (value passed as `codec`, short description)
    "H.265 / HEVC": ("h265", "Smaller files. Most browsers cannot play it in the page, so download it to watch."),
    "H.264": ("h264", "Larger files, but plays in every browser."),
}

METRIC_GUIDE = [
    ("Space Saved", "How much smaller the compressed file is than the original, as a percentage."),
    ("Compression Ratio", "Original size divided by compressed size. A ratio of 4× means the file is four times smaller."),
    ("Bitrate (bpp)", "Bits used per pixel of the image. Lower means a smaller file."),
    ("PSNR (dB)", "Peak signal-to-noise ratio. Higher means the reconstruction is closer to the original pixels."),
    ("MS-SSIM", "Multi-scale structural similarity, from 0 to 1. Closer to 1 means the image structure looks more like the original."),
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def max_upload_mb() -> int:
    """Upload limit, read from the Streamlit configuration (server.maxUploadSize)."""
    try:
        return int(st.get_option("server.maxUploadSize"))
    except Exception:
        return 50


def init_state() -> None:
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("image_result", None)
    st.session_state.setdefault("video_result", None)


def card(name: str):
    """A rounded surface container (styled in styles.py through its key)."""
    return st.container(key=f"card_{name}")


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def history_row(name: str, kind: str, res: dict, saved, psnr) -> dict:
    return {
        "File": name,
        "Type": kind,
        "Original": format_size(res.get("original_bytes")),
        "Compressed": format_size(res.get("compressed_bytes")),
        "Space Saved (%)": round(saved, 1) if saved is not None else None,
        "PSNR (dB)": round(float(psnr), 2) if isinstance(psnr, (int, float)) and not isinstance(psnr, bool) else None,
    }


def history_stats() -> tuple[int, str, str]:
    history = st.session_state.history
    savings = [h["Space Saved (%)"] for h in history if h["Space Saved (%)"] is not None]
    psnrs = [h["PSNR (dB)"] for h in history if h["PSNR (dB)"] is not None]
    avg_saved = f"{sum(savings) / len(savings):.1f}%" if savings else "—"
    avg_psnr = f"{sum(psnrs) / len(psnrs):.2f} dB" if psnrs else "—"
    return len(history), avg_saved, avg_psnr


# ---------------------------------------------------------------------------
# Engine status
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Starting the compression engine...")
def engine_status() -> dict:
    return engine.health()


def engine_pill(status: dict) -> tuple[str, str, str]:
    """(kind, label, detail) for the status pill, from the real health check."""
    if status["image_ok"] and status["video_ok"]:
        return "ok", "Engine ready", f"Device: {status['device']}"
    if status["image_ok"] or status["video_ok"]:
        return "bad", "Engine partly available", "See the message below"
    return "bad", "Engine unavailable", "See the message below"


def render_header(status: dict) -> None:
    kind, label, detail = engine_pill(status)
    html(ui.brand_header(ui.pill(kind, label, detail)))
    for problem in status["problems"]:
        st.error(problem)


# ---------------------------------------------------------------------------
# Image compression
# ---------------------------------------------------------------------------
def compress_image(uploaded, model: str, quality: int) -> None:
    st.session_state.image_result = None
    raw = uploaded.getvalue()
    try:
        with st.status("Compressing your image...", expanded=True) as status:
            if engine.is_busy():
                st.write("Another file is being processed. Yours starts as soon as it finishes.")
            st.write("Running the neural codec on the server CPU. The first use of a model also downloads "
                     "its weights, which can take up to a minute.")
            res = engine.compress_image(raw, model, quality)
            status.update(label="Compression complete", state="complete", expanded=False)
    except engine.EngineError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # keep the UI alive on anything unexpected
        st.error(f"Unexpected error: {exc}")
        return

    saved = space_saved(res)
    st.session_state.image_result = {"name": uploaded.name, "raw": raw, "res": res, "saved": saved}
    st.session_state.history.append(history_row(uploaded.name, "Image", res, saved, res.get("psnr")))
    st.toast("Image compressed successfully.", icon=":material/check_circle:")


def render_image_result(r: dict) -> None:
    res = r["res"]
    preview, nic = res["files"]["preview"], res["files"]["nic"]
    html(ui.section_header("Results", "Side-by-side comparison and the quality metrics measured by the codec."))
    html(ui.banner("ok", "Compression complete", r["name"]))
    if res.get("resized_from"):
        w0, h0 = res["resized_from"]
        st.info(
            f"The image was scaled down from {w0} × {h0} to {res['width']} × {res['height']} px so the server "
            f"stays responsive. Size and quality figures are measured on the scaled image."
        )
    with card("image_compare"):
        left, right = st.columns(2, gap="large")
        left.markdown(ui.tag("Original"), unsafe_allow_html=True)
        left.image(r["raw"])
        right.markdown(ui.tag("Reconstructed", out=True), unsafe_allow_html=True)
        right.image(preview, caption="Compressed, then decoded")

    saved, ratio = r["saved"], compression_ratio(res)
    width, height = res.get("width"), res.get("height")
    cards = [
        ui.metric_card("Space Saved", f"{saved:.1f}%" if saved is not None else "—", "percent",
                       "How much smaller the compressed file is than the original.", accent=True),
        ui.metric_card("Original Size", format_size(res.get("original_bytes")), "file", "File size before compression."),
        ui.metric_card("Compressed Size", format_size(res.get("compressed_bytes")), "shrink", "File size after compression."),
        ui.metric_card("Compression Ratio", f"{ratio:.1f}×" if ratio else "—", "ratio", "Original size divided by compressed size."),
        ui.metric_card("Bitrate", fmt_num(res.get("bpp"), ".3f", " bpp"), "signal", "Bits per pixel of the compressed file."),
        ui.metric_card("PSNR", fmt_num(res.get("psnr"), ".2f", " dB"), "signal",
                       "Peak signal-to-noise ratio. Higher means closer to the original."),
    ]
    if res.get("msssim") is not None:  # shown only when it could be computed
        cards.append(ui.metric_card("MS-SSIM", fmt_num(res.get("msssim"), ".4f"), "eye",
                                    "Structural similarity from 0 to 1. Closer to 1 is better."))
    cards.append(ui.metric_card("Encoding Time", fmt_num(res.get("encode_s"), ".2f", " s"), "clock",
                                "Time the codec needed to encode and decode the image."))
    cards.append(ui.metric_card("Dimensions", f"{width} × {height} px" if width and height else "—", "frame",
                                "Image width and height in pixels."))
    cards.append(ui.metric_card("Model", f"{res.get('model', '—')} · q{res.get('quality', '—')}", "image",
                                "Codec model and quality level used."))
    if res.get("device"):
        cards.append(ui.metric_card("Processing Device", str(res["device"]), "cpu", "Hardware used for compression."))
    html(ui.metric_grid(cards))

    jpeg = res.get("jpeg")
    if isinstance(jpeg, dict) and jpeg.get("psnr") is not None and res.get("psnr") is not None:
        st.info(
            f"For comparison, a JPEG of about the same size ({format_size(jpeg.get('bytes'))}, quality "
            f"{jpeg.get('quality')}) reaches {fmt_num(jpeg['psnr'], '.2f')} dB PSNR, "
            f"against {fmt_num(res['psnr'], '.2f')} dB for this codec."
        )

    stem = Path(r["name"]).stem or "image"
    d1, d2 = st.columns(2)
    d1.download_button(
        "Download Reconstructed Image (PNG)", preview, file_name=f"{stem}_reconstructed.png",
        mime="image/png", icon=":material/download:", key="download_png",
    )
    d2.download_button(
        "Download Compressed File (.nic)", nic, file_name=f"{stem}.nic",
        mime="application/octet-stream", icon=":material/download:", key="download_nic",
    )
    with st.expander("What do these metrics mean?"):
        html(ui.glossary(METRIC_GUIDE))


def render_image_tab(status: dict) -> None:
    html(ui.section_header(
        "Image compression",
        "A neural-network codec turns your image into a compact .nic file, then reconstructs it "
        "so you can compare visual quality with the original.",
    ))
    if not status["image_ok"]:
        st.error("The image engine is not available on this server.")
        return
    col_upload, col_settings = st.columns([1.15, 1], gap="medium")
    with col_upload:
        with card("image_upload"):
            html(ui.card_title(
                "Upload",
                f"JPG, JPEG, PNG or WebP. Up to {max_upload_mb()} MB. "
                f"Images larger than {engine.MAX_IMAGE_SIDE} px are scaled down.",
            ))
            image_file = st.file_uploader("Image file", type=IMAGE_TYPES, key="image_file", label_visibility="collapsed")
            if image_file is not None:
                st.image(image_file, caption=f"{image_file.name} ({format_size(image_file.size)})", width=260)
    with col_settings:
        with card("image_settings"):
            html(ui.card_title("Settings", "Choose a model and how much quality to keep."))
            model_label = st.radio("Compression model", list(IMAGE_MODELS), horizontal=True, key="image_model")
            model = IMAGE_MODELS[model_label][0]
            st.caption(IMAGE_MODELS[model_label][1])
            top = engine.max_quality(model)
            quality = st.slider(  # one key per model, because the allowed range differs
                f"Quality (1 to {top})", 1, top, min(6, top), key=f"image_quality_{model}",
                help="Higher values keep more visual quality and produce a larger file.",
            )
    run = st.button(
        "Compress Image", type="primary", icon=":material/bolt:",
        disabled=image_file is None, key="run_image",
    )

    if run and image_file is not None:
        compress_image(image_file, model, quality)

    if st.session_state.image_result:
        render_image_result(st.session_state.image_result)
    elif image_file is None:
        html(ui.empty_state(
            "image", "No image yet",
            "Upload an image above to compress it. The before-and-after comparison and metrics will appear here.",
        ))


# ---------------------------------------------------------------------------
# Video compression
# ---------------------------------------------------------------------------
def compress_video(uploaded, level: str, codec: str) -> None:
    st.session_state.video_result = None
    raw = uploaded.getvalue()
    try:
        with st.status("Encoding your video...", expanded=True) as status:
            if engine.is_busy():
                st.write("Another file is being processed. Yours starts as soon as it finishes.")
            bar = st.progress(0.0, text="Starting...")

            def on_progress(fraction: float) -> None:
                bar.progress(min(max(fraction, 0.0), 1.0), text=f"Encoding... {fraction * 100:.0f}%")

            res = engine.compress_video(raw, uploaded.name, level, codec, on_progress)
            status.update(label="Compression complete", state="complete", expanded=False)
    except engine.EngineError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return

    saved = space_saved(res)
    mime = uploaded.type if (uploaded.type or "").startswith("video/") else "video/mp4"
    st.session_state.video_result = {"name": uploaded.name, "raw": raw, "res": res, "saved": saved, "mime": mime}
    st.session_state.history.append(history_row(uploaded.name, "Video", res, saved, None))
    st.toast("Video compressed successfully.", icon=":material/check_circle:")


def render_video_result(r: dict) -> None:
    res = r["res"]
    video = res["files"]["video"]
    html(ui.section_header("Results", "Side-by-side playback and the figures measured during encoding."))
    html(ui.banner("ok", "Compression complete", r["name"]))
    with card("video_compare"):
        left, right = st.columns(2, gap="large")
        left.markdown(ui.tag("Original"), unsafe_allow_html=True)
        left.video(r["raw"], format=r["mime"])
        right.markdown(ui.tag("Compressed", out=True), unsafe_allow_html=True)
        right.video(video)
        if res.get("codec") == "h265":
            st.caption("H.265 / HEVC does not play in every browser (Safari and Edge usually do). "
                       "If the compressed video stays black, download it and open it with VLC, "
                       "or compress again with H.264.")
        if Path(r["name"]).suffix.lower() == ".mkv":
            st.caption("Some browsers cannot play MKV files. If the original does not play, the result is unaffected.")

    saved, ratio = r["saved"], compression_ratio(res)
    w, h = res.get("width"), res.get("height")
    cards = [
        ui.metric_card("Space Saved", f"{saved:.1f}%" if saved is not None else "—", "percent",
                       "How much smaller the compressed file is than the original.", accent=True),
        ui.metric_card("Original Size", format_size(res.get("original_bytes")), "file", "File size before compression."),
        ui.metric_card("Compressed Size", format_size(res.get("compressed_bytes")), "shrink", "File size after compression."),
        ui.metric_card("Compression Ratio", f"{ratio:.1f}×" if ratio else "—", "ratio", "Original size divided by compressed size."),
        ui.metric_card("Encoder", str(res.get("engine") or "—"), "cpu", "Encoder used on the server."),
        ui.metric_card("Encoding Duration", fmt_num(res.get("seconds"), ".1f", " s"), "clock", "Time spent encoding."),
        ui.metric_card("Output Resolution", f"{w} × {h} px" if w and h else "—", "frame", "Width and height of the output."),
        ui.metric_card("Clip Length", fmt_num(res.get("duration"), ".1f", " s"), "film", "Length of the video."),
    ]
    html(ui.metric_grid(cards))
    if saved is not None and saved <= 0:
        st.warning("The output is not smaller than the original. The video may already be compressed; "
                   "try a preset with stronger compression.")

    stem = Path(r["name"]).stem or "video"
    st.download_button(
        "Download Compressed Video", video, file_name=f"{stem}_compressed.mp4",
        mime="video/mp4", icon=":material/download:", key="download_video",
    )


def render_video_tab(status: dict) -> None:
    html(ui.section_header(
        "Video compression",
        "Re-encodes a short video with a classical codec (HEVC or H.264) as a baseline for comparison "
        "with the learned image codec.",
    ))
    if not status["video_ok"]:
        st.error("The video engine is not available on this server.")
        return
    col_upload, col_settings = st.columns([1.15, 1], gap="medium")
    with col_upload:
        with card("video_upload"):
            html(ui.card_title(
                "Upload",
                f"MP4, MOV, WebM or MKV. Up to {max_upload_mb()} MB and {engine.MAX_VIDEO_SECONDS} seconds.",
            ))
            video_file = st.file_uploader("Video file", type=VIDEO_TYPES, key="video_file", label_visibility="collapsed")
            if video_file is not None:
                st.caption(f"Selected: {video_file.name} ({format_size(video_file.size)})")
    with col_settings:
        with card("video_settings"):
            html(ui.card_title("Settings", "Pick a quality preset and the output codec."))
            level_label = st.selectbox("Quality preset", list(VIDEO_LEVELS), index=1, key="video_level")
            codec_label = st.radio("Output codec", list(VIDEO_CODECS), horizontal=True, key="video_codec")
            st.caption(VIDEO_CODECS[codec_label][1])
    run = st.button(
        "Compress Video", type="primary", icon=":material/bolt:",
        disabled=video_file is None, key="run_video",
    )

    if run and video_file is not None:
        compress_video(video_file, VIDEO_LEVELS[level_label], VIDEO_CODECS[codec_label][0])

    if st.session_state.video_result:
        render_video_result(st.session_state.video_result)
    elif video_file is None:
        html(ui.empty_state(
            "film", "No video yet",
            "Upload a video above to compress it. Playback and the encoding figures will appear here.",
        ))


# ---------------------------------------------------------------------------
# History and overview
# ---------------------------------------------------------------------------
def render_history_tab() -> None:
    html(ui.section_header("Results history", "Results from the current browser session. They are cleared when the session ends."))
    count, avg_saved, avg_psnr = history_stats()
    html(ui.metric_grid([
        ui.metric_card("Processed Files", str(count), "files"),
        ui.metric_card("Average Space Saved", avg_saved, "percent"),
        ui.metric_card("Average PSNR (images)", avg_psnr, "signal"),
    ]))
    if st.session_state.history:
        st.dataframe(st.session_state.history, hide_index=True)
    else:
        html(ui.empty_state("inbox", "Nothing here yet", "Compress an image or a video and the result will be listed here."))


def render_overview_tab(status: dict) -> None:
    kind, label, detail = engine_pill(status)
    count, avg_saved, avg_psnr = history_stats()
    html(ui.section_header("Session overview", "A quick look at the engine and this session."))
    html(ui.metric_grid([
        ui.metric_card("Engine", label, "plug", detail),
        ui.metric_card("Files Processed", str(count), "files"),
        ui.metric_card("Average Space Saved", avg_saved, "percent"),
        ui.metric_card("Average PSNR (images)", avg_psnr, "signal"),
    ]))
    html(ui.section_header("How it works"))
    html(ui.steps([
        ("Upload", "Choose an image or a short video in the matching tab."),
        ("Configure and compress", "Pick the model and quality, or the preset and codec, then start."),
        ("Compare and download", "Review the metrics side by side, then download the output."),
    ]))
    html(ui.section_header("Understanding the metrics"))
    html(ui.glossary(METRIC_GUIDE))
    html(ui.section_header("About this project"))
    with card("about"):
        st.markdown(
            "**Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality.** "
            "Images are compressed by pre-trained neural-network codecs (CompressAI: hyperprior, Minnen and "
            "Cheng models). Videos are re-encoded with HEVC or H.264 through ffmpeg as a classical baseline. "
            "Everything runs on the server that hosts this app, on CPU. This is an inference-only prototype: "
            "no model is trained here, and no benchmark is reported."
        )


# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Intelligent Multimedia Compression",
        page_icon=":material/compress:",
        layout="wide",
    )
    st.markdown(f"<style>{APP_CSS}</style>", unsafe_allow_html=True)
    init_state()

    status = engine_status()
    render_header(status)

    tab_overview, tab_image, tab_video, tab_history = st.tabs([
        ":material/dashboard: Overview",
        ":material/image: Image Compression",
        ":material/movie: Video Compression",
        ":material/history: History",
    ])
    # Fill the working tabs first so the overview and history always reflect the latest result.
    with tab_image:
        render_image_tab(status)
    with tab_video:
        render_video_tab(status)
    with tab_history:
        render_history_tab()
    with tab_overview:
        render_overview_tab(status)

    html(ui.footer())


main()
