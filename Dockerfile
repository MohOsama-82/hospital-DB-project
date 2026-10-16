FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (better Docker layer caching - only re-installs
# when requirements.txt actually changes, not on every code edit)
COPY requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the project - includes app/, static/ (the GUI),
# scripts/, everything needed to run.
COPY . .

# Render/Railway/most platforms inject a PORT env var and expect the app to
# listen on it. Defaulting to 8000 covers local `docker run` too.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]