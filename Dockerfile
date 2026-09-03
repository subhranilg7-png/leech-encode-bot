FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start aria2c's RPC daemon, then the bot
CMD aria2c --enable-rpc --rpc-listen-all=false --rpc-secret="$ARIA2_RPC_SECRET" \
    -D --dir=/app/downloads && python bot.py
