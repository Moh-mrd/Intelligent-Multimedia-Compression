# Intelligent Multimedia Compression Using Machine Learning to Preserve Visual Quality

A Streamlit interface for a remote compression API. Images are compressed with a neural-network
codec (`.nic` files). Videos are re-encoded by the backend. This app only uploads files and displays
what the API returns; it performs no compression and needs no PyTorch or CompressAI.

## Project files

```
app.py                  Pages, layout and session state
client.py               Backend client (health, upload, download) and number formatting
components.py           HTML builders: header, metric cards, pills, empty states, footer
styles.py               Dark navy theme (CSS tokens and components)
requirements.txt        streamlit, requests
.streamlit/config.toml  Dark theme and upload limit
```

`config.toml` must live inside a folder named `.streamlit`, next to `app.py`.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

1. Start the backend notebook on Colab and copy the `https://xxxx.trycloudflare.com` URL from its last cell.
2. Open http://localhost:8501, paste the URL into **API URL** and click **Test Connection**.
3. The badge in the top bar turns green ("Backend online") and shows the processing device
   reported by `/health`.

The tunnel URL changes every session, so paste the new one each time you restart the notebook.

## Pages

- **Overview:** backend status, session totals, a three-step guide and a short metric glossary.
- **Image Compression:** upload, model and quality settings, before-and-after comparison, metric cards
  and downloads (reconstructed PNG and `.nic`).
- **Video Compression:** upload, quality preset and engine, side-by-side playback, metric cards and download.
- **History:** files processed, average space saved, average PSNR (images only) and a session table.

## Backend contract used

| Purpose | Request | Parameters |
|---|---|---|
| Connectivity | `GET /health` | reads `device` |
| Image | `POST /api/image` | multipart `file`; form fields `model` (`fast`/`better`/`best`), `quality` (1-8) |
| Video | `POST /api/video` | multipart `file`; form fields `level` (`near`/`high`/`balanced`/`max`), `engine` (`gpu`/`cpu`) |
| Output files | `GET <files.preview / files.nic / files.video>` | relative URLs, appended to the API URL |

Response fields read: `original_bytes`, `compressed_bytes`, `psnr`, `msssim`, `width`, `height`,
`encode_s`, `device`, `engine`, `seconds`, `files.*`, and the optional `jpeg.psnr`.

Rules the interface follows:
- Space saved and compression ratio are calculated from the two byte counts. Nothing else is derived.
- MS-SSIM and Processing Device cards appear only when the backend returns them.
- Other missing values show "—". Progress text shows only real stages (uploading and encoding, then downloading).
- If `/api/image` or `/api/video` answers 404, 405 or 501, the app says the feature is unavailable on that backend.

## Configuration

| Setting | Where | Default |
|---|---|---|
| Upload limit (MB) | `.streamlit/config.toml` -> `server.maxUploadSize` (the app reads it too) | 100 |
| Timeouts | constants at the top of `client.py` | health 15 s, processing 900 s, download 600 s |
| Colors and spacing | `:root` tokens at the top of `styles.py` | dark navy and cyan |

No API keys or credentials are stored in the frontend.

## Deploy on Streamlit Community Cloud

Push all files, including `.streamlit/config.toml`, to GitHub. At https://share.streamlit.io choose the repo,
branch `main` and main file `app.py`, then paste the current API URL in the deployed app.

## Compatibility notes

1. The old interface used `res["jpeg"]["psnr"]`, which is outside your documented fields. It stays an optional note.
2. `psnr`, `width` and `height` are optional now. The video label "HEVC" from the old UI was removed because it
   could not be verified; the app says only that the backend encodes the video.
3. File URLs are assumed to be relative paths starting with `/`, as in the old code.
4. Errors are read from a JSON `detail` key, otherwise the raw text is shown.
5. Results are kept in `st.session_state`, so they stay visible after a download click.

## Testing checklist

- [ ] Test Connection with a wrong URL shows "Backend unreachable" and an error; the right URL shows "Backend online" and the device.
- [ ] Image: JPG, PNG and WebP upload; each model and a few quality values; comparison and cards appear; both downloads open.
- [ ] Video: MP4, MOV, WebM and MKV upload; each preset on GPU and CPU; both videos play; download plays.
- [ ] Stop the notebook, compress again: a clear connection error appears and the app keeps running.
- [ ] History and Overview totals match the table; the PSNR average ignores videos.
- [ ] Resize the browser to phone width: cards stack, tabs scroll, buttons fill the width.
