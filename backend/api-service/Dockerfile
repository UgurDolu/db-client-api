# Build UI stage
FROM node:18-alpine as ui-builder
WORKDIR /app

# Install dependencies first (better caching)
COPY web/package*.json ./
# Clean install with no package-lock to ensure fresh dependencies
RUN rm -rf node_modules package-lock.json && \
    npm install --no-package-lock --exact

# Copy source files
COPY web/ .

# Set production environment
ENV NODE_ENV=production

# Build the application
RUN npm run build

# Build Python dependencies stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uvicorn

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libpq.so* /usr/lib/x86_64-linux-gnu/
COPY backend/api-service /app/
COPY backend/shared /app/shared

# Copy UI build files
COPY --from=ui-builder /app/dist /app/static

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 