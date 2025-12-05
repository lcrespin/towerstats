#!/bin/bash
set -e

# Cloud Run définit automatiquement PORT, utiliser 8080 par défaut
PORT=${PORT:-8080}

echo "Starting functions-framework on port $PORT..."

# Lancer functions-framework
exec functions-framework --target=display_stats --port=$PORT --host=0.0.0.0

