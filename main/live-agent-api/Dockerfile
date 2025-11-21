FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . /app/

# Install dependencies using uv
RUN uv sync --no-dev

# Expose port
EXPOSE 8080

# Run the application
CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

