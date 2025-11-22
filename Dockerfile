# Dockerfile for Streamlit frontend (Cloud Run deployment)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY streamlit_app/ ./streamlit_app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Streamlit will use the PORT environment variable set by Cloud Run
# Cloud Run sets PORT automatically, but we provide a default
CMD streamlit run streamlit_app/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true

