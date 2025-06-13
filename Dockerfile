# ---------- Dockerfile (novopac-dashboard) ----------
FROM python:3.11-slim

# Avoid interactive prompts and keep image small
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# App code lives here
WORKDIR /app

# 1 — install deps first (for build-layer cache)
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2 — copy the rest of the code
COPY . .

# 3 — expose Streamlit port & run
EXPOSE 8507
CMD ["streamlit", "run", "streamlit_app/novopac_dashboard.py", "--server.port", "8507", "--server.address", "0.0.0.0"]

