FROM python:3.10-slim

LABEL maintainer="FreqTrade Team"
LABEL description="FreqTrade Web Management Interface"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 freqtrade && \
    chown -R freqtrade:freqtrade /app

USER freqtrade

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start the application
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "5000"]
