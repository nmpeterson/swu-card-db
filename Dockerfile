# Get python image and install uv
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.30 /uv /uvx /bin/

# Install the project into /build
RUN mkdir /build
WORKDIR /build

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
RUN uv sync --frozen --no-cache

# Place executables in the environment at the front of the path
ENV PATH="/build/.venv/bin:$PATH"

# Run the application
EXPOSE 8080
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]