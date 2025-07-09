# Use a slim Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only requirements first to leverage cache
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Set environment variables (override with Docker secrets in prod)
ENV PYTHONUNBUFFERED=1

# Expose port (optional)
EXPOSE 8000

# Start the app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
