# Stage 1: Build Stage
FROM python:3.10-slim AS builder

WORKDIR /app

# Install heavy compilation tools
# Removing libx11-dev and libgtk-3-dev saves space/memory since they are strictly for GUI
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# CRITICAL FIX for Render's 8GB memory limit:
# Limits CMake to a single compilation thread so dlib compilation 
# does not spawn multiple GCC processes and exhaust RAM.
ENV CMAKE_BUILD_PARALLEL_LEVEL=1

# Install python dependencies (including dlib which will compile safely)
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime Stage
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies ONLY
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libopenblas0 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application using gunicorn with uvicorn workers
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
