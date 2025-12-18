# Use Python 3.10 Slim (Lightweight Debian)
FROM python:3.10-slim

# 1. Install System Dependencies (libeccodes)
# This library is the engine required to read GRIB2 files
RUN apt-get update && apt-get install -y \
    libeccodes0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set Working Directory
WORKDIR /app

# 3. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Source Code
COPY app ./app

# 5. Command to Run the Server
# We use port 8000 internally
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]