# Hugging Face Space (Docker SDK). Runs the Streamlit app with ffmpeg and CPU PyTorch.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face runs containers as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    TORCH_HOME=/home/user/.cache/torch
WORKDIR /home/user/app

# 1) CPU-only PyTorch  2) everything else
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Download the default model weights now, so the first visitor does not wait (never fails the build)
RUN python -c "import engine; engine.warmup()" || echo "Weight pre-download skipped"

EXPOSE 7860
# Options are repeated here so the app works even if .streamlit/config.toml was not uploaded
CMD ["streamlit", "run", "app.py", \
     "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true", \
     "--server.maxUploadSize=50", "--server.enableCORS=false", "--server.enableXsrfProtection=false", \
     "--browser.gatherUsageStats=false", "--client.toolbarMode=minimal", \
     "--theme.base=dark", "--theme.primaryColor=#22D3EE", "--theme.backgroundColor=#0A1424", \
     "--theme.secondaryBackgroundColor=#12233D", "--theme.textColor=#E7EEF8"]
