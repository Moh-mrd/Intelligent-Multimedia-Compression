"""Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality.

Streamlit front end for the remote compression API (Google Colab / Kaggle behind a tunnel).
The app only sends files to the API and shows what the API returns. It performs no compression.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import components as ui
from client import (
    ApiError, api_compress, api_health, compression_ratio, fetch_file, fmt_num,
    format_size, normalize_api_url, result_url, space_saved,
)
from styles import APP_CSS

IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
VIDEO_TYPES = ["mp4", "mov", "webm", "mkv"]

# label -> (value sent to the API, short description)
IMAGE_MODELS = {
    "Fast": ("fast", "Fast and light."),
    "Better": ("better", "Better compression."),
    "Best": ("best", "Highest quality, slower."),
}
VIDEO_LEVELS = {  # label -> value sent as `level`
    "Near Original": "near",
    "High (recommended)": "high",
    "Balanced": "balanced",
    "Maximum Compression": "max",
}
VIDEO_ENGINES = {  # label -> (value sent as `engine`, short description)
    "GPU": ("gpu", "Faster encoding."),
    "CPU": ("cpu", "Smaller files, slower encoding."),
}

METRIC_GUIDE = [
    ("Space Saved", "How much smaller the compressed file is than the original, as a percentage."),
    ("Compression Ratio", "Original size divided by compressed size. A ratio of 4× means the file is four times smaller."),
    ("PSNR (dB)", "Peak signal-to-noise ratio. Higher means the reconstruction is closer to the original pixels."),
    ("MS-SSIM", "Multi-scale structural similarity, from 0 to 1. Closer to 1 means the image structure looks more like the original."),
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def max_upload_mb() -> int:
    """Upload limit, read from .streamlit/config.toml (server.maxUploadSize)."""
    try:
        return int(st.get_option("server.maxUploadSize"))
    except Exception:
        return 100


def init_state() -> None:
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("connection", None)
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
# Header and connection
# ---------------------------------------------------------------------------
def run_connection_test() -> None:
    """Button callback. It runs before the page re-renders, so the status updates at once."""
    api_url = normalize_api_url(st.session_state.get("api_url", ""))
    try:
        info = api_health(api_url)
        st.session_state.connection = {"url": api_url, "ok": True, "device": info.get("device")}
    except ApiError as exc:
        st.session_state.connection = {"url": api_url, "ok": False, "message": str(exc)}


def connection_status(api_url: str) -> tuple[str, str, str]:
    """(kind, label, detail) for the status pill, based only on the real /health result."""
    conn = st.session_state.connection
    if conn and conn["url"] == api_url:
        if conn["ok"]:
            return "ok", "Backend online", f"Device: {conn.get('device') or 'not reported'}"
        return "bad", "Backend unreachable", ""
    return "idle", "Not connected", "Run a connection test"


def render_header(api_url: str) -> None:
    kind, label, detail = connection_status(api_url)
    html(ui.brand_header(ui.pill(kind, label, detail)))


def render_connection() -> str:
    api_url = normalize_api_url(st.session_state.get("api_url", ""))
    with card("connection"):
        html(ui.card_title(
            "API connection",
            "Paste the temporary HTTPS URL printed by the last cell of your Colab or Kaggle notebook. "
            "It changes every session.",
        ))
        col_url, col_btn = st.columns([4, 1], vertical_alignment="bottom")
        col_url.text_input("API URL", key="api_url", placeholder="https://xxxx.trycloudflare.com")
        col_btn.button(
            "Test Connection", icon=":material/wifi_tethering:", key="test_connection",
            on_click=run_connection_test,
        )
        conn = st.session_state.connection
        if conn and conn["url"] == api_url and not conn["ok"]:
            st.error(conn["message"])
    return api_url


# ---------------------------------------------------------------------------
# Image compression
# ---------------------------------------------------------------------------
def compress_image(api_url: str, uploaded, model: str, quality: int) -> None:
    st.session_state.image_result = None
    try:
        with st.status("Uploading and compressing your image...", expanded=True) as status:
            st.write("Sending the file to the backend. Larger images take longer.")
            raw, res = api_compress(api_url, "/api/image", uploaded, {"model": model, "quality": quality}, max_upload_mb())
            status.update(label="Downloading the results...")
            preview = fetch_file(api_url, result_url(res, "preview"))
            nic = fetch_file(api_url, result_url(res, "nic"))
            status.update(label="Compression complete", state="complete", expanded=False)
    except ApiError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # keep the UI alive on anything unexpected
        st.error(f"Unexpected error: {exc}")
        return

    saved = space_saved(res)
    st.session_state.image_result = {
        "name": uploaded.name, "raw": raw, "preview": preview, "nic": nic, "res": res, "saved": saved,
    }
    st.session_state.history.append(history_row(uploaded.name, "Image", res, saved, res.get("psnr")))
    st.toast("Image compressed successfully.", icon=":material/check_circle:")


def render_image_result(r: dict) -> None:
    res = r["res"]
    html(ui.section_header("Results", "Side-by-side comparison and the quality metrics reported by the backend."))
    html(ui.banner("ok", "Compression complete", r["name"]))
    with card("image_compare"):
        left, right = st.columns(2, gap="large")
        left.markdown(ui.tag("Original"), unsafe_allow_html=True)
        left.image(r["raw"])
        right.markdown(ui.tag("Reconstructed", out=True), unsafe_allow_html=True)
        right.image(r["preview"], caption="Compressed, then decoded")

    saved, ratio = r["saved"], compression_ratio(res)
    width, height = res.get("width"), res.get("height")
    cards = [
        ui.metric_card("Space Saved", f"{saved:.1f}%" if saved is not None else "—", "percent",
                       "How much smaller the compressed file is than the original.", accent=True),
        ui.metric_card("Original Size", format_size(res.get("original_bytes")), "file", "File size before compression."),
        ui.metric_card("Compressed Size", format_size(res.get("compressed_bytes")), "shrink", "File size after compression."),
        ui.metric_card("Compression Ratio", f"{ratio:.1f}×" if ratio else "—", "ratio", "Original size divided by compressed size."),
        ui.metric_card("PSNR", fmt_num(res.get("psnr"), ".2f", " dB"), "signal",
                       "Peak signal-to-noise ratio. Higher means closer to the original."),
    ]
    if res.get("msssim") is not None:  # shown only when the backend returns it
        cards.append(ui.metric_card("MS-SSIM", fmt_num(res.get("msssim"), ".4f"), "eye",
                                    "Structural similarity from 0 to 1. Closer to 1 is better."))
    cards.append(ui.metric_card("Encoding Time", fmt_num(res.get("encode_s"), ".2f", " s"), "clock",
                                "Time the backend reported for compressing the image."))
    cards.append(ui.metric_card("Dimensions", f"{width} × {height} px" if width and height else "—", "frame",
                                "Image width and height in pixels."))
    if res.get("device"):  # shown only when available
        cards.append(ui.metric_card("Processing Device", str(res["device"]), "cpu", "Hardware used by the backend."))
    html(ui.metric_grid(cards))

    jpeg = res.get("jpeg")  # optional field used by the original interface
    if isinstance(jpeg, dict) and jpeg.get("psnr") is not None and res.get("psnr") is not None:
        st.info(
            f"For comparison, a JPEG of the same file size reaches {fmt_num(jpeg['psnr'], '.2f')} dB PSNR, "
            f"against {fmt_num(res['psnr'], '.2f')} dB for this codec."
        )

    stem = Path(r["name"]).stem or "image"
    d1, d2 = st.columns(2)
    d1.download_button(
        "Download Reconstructed Image (PNG)", r["preview"], file_name=f"{stem}_reconstructed.png",
        mime="image/png", icon=":material/download:", key="download_png",
    )
    d2.download_button(
        "Download Compressed File (.nic)", r["nic"], file_name=f"{stem}.nic",
        mime="application/octet-stream", icon=":material/download:", key="download_nic",
    )
    with st.expander("What do these metrics mean?"):
        html(ui.glossary(METRIC_GUIDE))


def render_image_tab(api_url: str) -> None:
    html(ui.section_header(
        "Image compression",
        "A neural-network codec turns your image into a compact .nic file, then reconstructs it "
        "so you can compare visual quality with the original.",
    ))
    col_upload, col_settings = st.columns([1.15, 1], gap="medium")
    with col_upload:
        with card("image_upload"):
            html(ui.card_title("Upload", f"JPG, JPEG, PNG or WebP. Up to {max_upload_mb()} MB."))
            image_file = st.file_uploader("Image file", type=IMAGE_TYPES, key="image_file", label_visibility="collapsed")
            if image_file is not None:
                st.image(image_file, caption=f"{image_file.name} ({format_size(image_file.size)})", width=260)
    with col_settings:
        with card("image_settings"):
            html(ui.card_title("Settings", "Choose a model and how much quality to keep."))
            model_label = st.radio("Compression model", list(IMAGE_MODELS), horizontal=True, key="image_model")
            st.caption(IMAGE_MODELS[model_label][1])
            quality = st.slider(
                "Quality (1 to 8)", 1, 8, 6, key="image_quality",
                help="Higher values keep more visual quality and produce a larger file.",
            )
    run = st.button(
        "Compress Image", type="primary", icon=":material/bolt:",
        disabled=image_file is None, key="run_image",
    )

    if run and image_file is not None:
        compress_image(api_url, image_file, IMAGE_MODELS[model_label][0], quality)

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
def compress_video(api_url: str, uploaded, level: str, engine: str) -> None:
    st.session_state.video_result = None
    try:
        with st.status("Uploading and encoding your video...", expanded=True) as status:
            st.write("Sending the file to the backend. Encoding can take several minutes.")
            raw, res = api_compress(api_url, "/api/video", uploaded, {"level": level, "engine": engine}, max_upload_mb())
            status.update(label="Downloading the compressed video...")
            video = fetch_file(api_url, result_url(res, "video"))
            status.update(label="Compression complete", state="complete", expanded=False)
    except ApiError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return

    saved = space_saved(res)
    mime = uploaded.type if (uploaded.type or "").startswith("video/") else "video/mp4"
    st.session_state.video_result = {
        "name": uploaded.name, "raw": raw, "video": video, "res": res, "saved": saved, "mime": mime,
    }
    st.session_state.history.append(history_row(uploaded.name, "Video", res, saved, None))
    st.toast("Video compressed successfully.", icon=":material/check_circle:")


def render_video_result(r: dict) -> None:
    res = r["res"]
    html(ui.section_header("Results", "Side-by-side playback and the figures reported by the backend."))
    html(ui.banner("ok", "Compression complete", r["name"]))
    with card("video_compare"):
        left, right = st.columns(2, gap="large")
        left.markdown(ui.tag("Original"), unsafe_allow_html=True)
        left.video(r["raw"], format=r["mime"])
        right.markdown(ui.tag("Compressed", out=True), unsafe_allow_html=True)
        right.video(r["video"])
        if Path(r["name"]).suffix.lower() == ".mkv":
            st.caption("Some browsers cannot play MKV files. If the original does not play, the result is unaffected.")

    saved, ratio = r["saved"], compression_ratio(res)
    cards = [
        ui.metric_card("Space Saved", f"{saved:.1f}%" if saved is not None else "—", "percent",
                       "How much smaller the compressed file is than the original.", accent=True),
        ui.metric_card("Original Size", format_size(res.get("original_bytes")), "file", "File size before compression."),
        ui.metric_card("Compressed Size", format_size(res.get("compressed_bytes")), "shrink", "File size after compression."),
        ui.metric_card("Compression Ratio", f"{ratio:.1f}×" if ratio else "—", "ratio", "Original size divided by compressed size."),
        ui.metric_card("Encoding Engine", str(res.get("engine") or "—"), "cpu", "Engine the backend used to encode the video."),
        ui.metric_card("Encoding Duration", fmt_num(res.get("seconds"), ".1f", " s"), "clock", "Time the backend reported for encoding."),
    ]
    html(ui.metric_grid(cards))
    if saved is not None and saved <= 0:
        st.warning("The output is not smaller than the original. The video may already be compressed; "
                   "try a preset with stronger compression.")

    stem = Path(r["name"]).stem or "video"
    st.download_button(
        "Download Compressed Video", r["video"], file_name=f"{stem}_compressed.mp4",
        mime="video/mp4", icon=":material/download:", key="download_video",
    )


def render_video_tab(api_url: str) -> None:
    html(ui.section_header(
        "Video compression",
        "Re-encodes a short video on the remote server. Larger files take longer.",
    ))
    col_upload, col_settings = st.columns([1.15, 1], gap="medium")
    with col_upload:
        with card("video_upload"):
            html(ui.card_title("Upload", f"MP4, MOV, WebM or MKV. Up to {max_upload_mb()} MB."))
            video_file = st.file_uploader("Video file", type=VIDEO_TYPES, key="video_file", label_visibility="collapsed")
            if video_file is not None:
                st.caption(f"Selected: {video_file.name} ({format_size(video_file.size)})")
    with col_settings:
        with card("video_settings"):
            html(ui.card_title("Settings", "Pick a quality preset and the processing engine."))
            level_label = st.selectbox("Quality preset", list(VIDEO_LEVELS), index=1, key="video_level")
            engine_label = st.radio("Processing engine", list(VIDEO_ENGINES), horizontal=True, key="video_engine")
            st.caption(VIDEO_ENGINES[engine_label][1])
    run = st.button(
        "Compress Video", type="primary", icon=":material/bolt:",
        disabled=video_file is None, key="run_video",
    )

    if run and video_file is not None:
        compress_video(api_url, video_file, VIDEO_LEVELS[level_label], VIDEO_ENGINES[engine_label][0])

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


def render_overview_tab(api_url: str) -> None:
    kind, label, detail = connection_status(api_url)
    count, avg_saved, avg_psnr = history_stats()
    html(ui.section_header("Session overview", "A quick look at the backend and this session."))
    html(ui.metric_grid([
        ui.metric_card("Backend", label, "plug", detail),
        ui.metric_card("Files Processed", str(count), "files"),
        ui.metric_card("Average Space Saved", avg_saved, "percent"),
        ui.metric_card("Average PSNR (images)", avg_psnr, "signal"),
    ]))
    html(ui.section_header("How it works"))
    html(ui.steps([
        ("Connect", "Paste the API URL from your notebook and test the connection."),
        ("Upload and configure", "Choose an image or a video, then pick the model or preset."),
        ("Compare and download", "Review the metrics side by side, then download the output."),
    ]))
    html(ui.section_header("Understanding the metrics"))
    html(ui.glossary(METRIC_GUIDE))
    html(ui.section_header("About this project"))
    with card("about"):
        st.markdown(
            "**Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality.** "
            "Images are compressed by a neural-network codec that runs on a remote GPU backend, and videos "
            "are re-encoded by the same backend. This interface only uploads files and displays the "
            "measured results; no compression happens in the browser or on this machine."
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

    api_url = normalize_api_url(st.session_state.get("api_url", ""))
    render_header(api_url)
    api_url = render_connection()

    tab_overview, tab_image, tab_video, tab_history = st.tabs([
        ":material/dashboard: Overview",
        ":material/image: Image Compression",
        ":material/movie: Video Compression",
        ":material/history: History",
    ])
    # Fill the working tabs first so the overview and history always reflect the latest result.
    with tab_image:
        render_image_tab(api_url)
    with tab_video:
        render_video_tab(api_url)
    with tab_history:
        render_history_tab()
    with tab_overview:
        render_overview_tab(api_url)

    html(ui.footer())


main()
