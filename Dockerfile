FROM python:3.11-slim

COPY --from=denoland/deno:alpine-2.6.3 /bin/deno /usr/local/bin/deno

# Install FFmpeg
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .

CMD ["python", "main.py"]
