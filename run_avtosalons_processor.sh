#!/bin/bash

# Load environment variables from .env.local
if [ -f .env.local ]; then
    set -a
    source .env.local
    set +a
else
    echo "Error: .env.local file not found"
    exit 1
fi

# Run the Python script
python3 process_avtosalons.py
