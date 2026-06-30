#!/usr/bin/env bash
set -euo pipefail

case "$(uname -s)" in
  Linux*) ;;
  *)
    echo "This script is intended for Linux. Use scripts/deploy-stack.ps1 on Windows."
    exit 1
    ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

compose_cmd=()
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "Docker is not installed."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-plugin
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y docker docker-compose-plugin
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm docker docker-compose
  else
    echo "Install Docker Engine and the Compose plugin manually, then rerun this script."
    exit 1
  fi

  if docker compose version >/dev/null 2>&1; then
    compose_cmd=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    compose_cmd=(docker-compose)
  else
    echo "Docker was installed, but compose is still unavailable."
    exit 1
  fi
fi

if ! docker info >/dev/null 2>&1; then
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl enable --now docker
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker is installed, but the daemon is not reachable. Start Docker and rerun this script."
    exit 1
  fi
fi

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"

"${compose_cmd[@]}" --profile local-models up -d --build
"${compose_cmd[@]}" ps