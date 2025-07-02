#!/bin/bash

set -e

# Allow IP and PORT to be set via env or args
IP="${IP:-localhost}"
PORT="${PORT:-3000}"

function help() {
  echo "Usage: $0 [all|root|health|list|create|update|delete] [--ip <ip>] [--port <port>] [--id <user_id>]"
  echo "  all: run all tests"
  echo "  root: test the root endpoint"
  echo "  health: test the health endpoint"
  echo "  list: test the list users endpoint"
  echo "  create: test the create user endpoint"
  echo "  update: test the update user endpoint (requires --id)"
  echo "  delete: test the delete user endpoint (requires --id)"
}

# Parse command-line arguments for IP and PORT
POSITIONAL=()
USER_ID=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --ip)
      IP="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --id)
      USER_ID="$2"
      shift 2
      ;;
    root|health|list|create|update|delete|all)
      POSITIONAL+=("$1")
      shift
      ;;
    --help|-h)
      help
      exit 1
      ;;
    *)
      echo "Unknown argument: $1"
      help
      exit 1
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

BASE_URL="http://$IP:$PORT"

function test_root() {
  echo "/ (version):"
  curl -s "$BASE_URL/" | jq .
}

function test_health() {
  echo "/health:"
  curl -s "$BASE_URL/health" | jq .
}

function test_list_users() {
  echo "/users (GET):"
  curl -s "$BASE_URL/users" | jq .
}

function test_create_user() {
  echo "/users (POST):"
  curl -s -X POST "$BASE_URL/users" -H 'Content-Type: application/json' -d \
  '{
    "username": "testuser",
    "email":  "test@example.com",
    "password": "testpass123",
    "profile":  "507f1f77bcf86cd799439011"
  }' | jq .
}

function test_update_user() {
  if [[ -z "$USER_ID" ]]; then
    echo "Error: --id is required for update operation"
    help
    exit 1
  fi
  echo "/users/$USER_ID (PATCH):"
  curl -s -X PATCH "$BASE_URL/users/$USER_ID" -H 'Content-Type: application/json' -d \
  '{
    "email": "updated@example.com",
    "isActive": false
  }' | jq .
}

function test_delete_user() {
  if [[ -z "$USER_ID" ]]; then
    echo "Error: --id is required for delete operation"
    help
    exit 1
  fi
  echo "/users/$USER_ID (DELETE):"
  curl -s -X DELETE "$BASE_URL/users/$USER_ID" | jq .
}

function all() {
  test_root
  test_health
  test_list_users
  test_create_user
}

case "$1" in
  root) test_root ;;
  health) test_health ;;
  list) test_list_users ;;
  create) test_create_user ;;
  update) test_update_user ;;
  delete) test_delete_user ;;
  all | "") all ;;
  *) help; exit 1 ;;
esac
