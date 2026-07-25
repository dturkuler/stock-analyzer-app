FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    yfinance \
    pandas \
    numpy \
    apscheduler \
    python-dotenv \
    beautifulsoup4 \
    curl_cffi

COPY . /app

EXPOSE 6031

CMD ["python", "-m", "uvicorn", "3_web_server.main:app", "--host", "0.0.0.0", "--port", "6031"]
