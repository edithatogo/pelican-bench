# Supply an immutable base at build time, for example:
# docker build --build-arg PYTHON_IMAGE=python:3.13-slim@sha256:<digest> .
ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY envs/pelican-canvas-openenv/app.py ./app.py
RUN pip install --no-cache-dir .
CMD ["python", "-c", "from app import environment; print(environment.reset())"]
