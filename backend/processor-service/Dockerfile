FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./main.py /app/main.py
COPY ./alembic.ini /app/alembic.ini
COPY ./alembic /app/alembic

ENV PYTHONPATH=/app

# Create directories for exports and temporary files
RUN mkdir -p /app/exports /app/tmp/exports

CMD ["python", "main.py"] 