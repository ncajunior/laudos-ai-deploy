#!/bin/bash
sudo apt update && sudo apt install -y docker.io docker-compose git
docker-compose up -d
echo "✅ Laudos AI rodando – http://localhost:8000/health"
