FROM node:22-bookworm-slim

# Install Python for the recommendation engine.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 \
       python3-venv \
       python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create an isolated Python environment for the recommender.
RUN python3 -m venv /opt/venv

# Install Python dependencies separately for better Docker layer caching.
COPY recommender/requirements.txt ./recommender/requirements.txt

RUN /opt/venv/bin/pip install --no-cache-dir \
    -r recommender/requirements.txt

# Install backend Node dependencies separately for caching.
COPY server/package.json server/package-lock.json ./server/

WORKDIR /app/server

RUN npm ci

# Copy the backend and recommendation engine into the image.
WORKDIR /app

COPY server ./server
COPY recommender ./recommender

# Use the Docker Python environment instead of the local macOS .venv.
ENV PYTHON_EXECUTABLE=/opt/venv/bin/python

WORKDIR /app/server

CMD ["npm", "start"]