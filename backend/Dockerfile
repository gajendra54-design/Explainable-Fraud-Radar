FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade pip==26.2.2 && pip install -r backend/requirements.txt && pip uninstall -y setuptools pip
COPY backend /app/backend
COPY ml /app/ml
RUN useradd --create-home radar && mkdir -p /app/artifacts && chown -R radar:radar /app
USER radar
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.app.cli init && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
