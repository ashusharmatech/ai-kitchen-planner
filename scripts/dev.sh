#!/bin/bash
# Start all services locally with docker-compose
set -e
if [ ! -f .env ]; then
  echo "ERROR: .env file missing. Copy .env.example and fill in values."
  exit 1
fi
docker-compose up --build "$@"
