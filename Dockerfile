# Get python image and install uv
FROM unit:1.34.1-python3.13
COPY --from=ghcr.io/astral-sh/uv:0.5.30 /uv /uvx /bin/
COPY ./config/config.json /docker-entrypoint.d/config.json

# Install the project into /build
RUN mkdir /build
RUN chown -R unit:unit /build
WORKDIR /build
COPY . .

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-cache --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/build/.venv/bin:$PATH"

# Run the application
EXPOSE 8080
ENTRYPOINT ["gunicorn", "app.main:app", "-b", "0.0.0.0:8080", "-w", "4", "-k", "uvicorn_worker.UvicornWorker"]
