FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

RUN if [ -f /usr/lib/chromium/chromedriver ] && [ ! -f /usr/bin/chromedriver ]; then \
    ln -s /usr/lib/chromium/chromedriver /usr/bin/chromedriver; \
fi

RUN chmod +x /usr/bin/chromedriver 2>/dev/null || \
    chmod +x /usr/lib/chromium/chromedriver 2>/dev/null || \
    echo "ChromeDriver will be handled by webdriver-manager if needed"

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
