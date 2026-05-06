FROM python:3.11-slim

# Install Chrome using modern method (no apt-key)
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip ca-certificates \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libgtk-3-0 libnspr4 libnss3 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repo using modern signed-by method
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
    http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p scraper_output logs

CMD ["python", "scrape_metals.py"]