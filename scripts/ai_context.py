#!/usr/bin/env python3
"""
AI context persistence script for OSED development.
Saves and loads development context across sessions.
"""

import datetime
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor
import yaml
import sys
from typing import Any, Dict, Optional


def run_git_command(cmd: str) -> str:
  """Run a git command and return the output."""
  try:
    result = subprocess.run(
        cmd.split(), capture_output=True, text=True, check=True
    )
    return result.stdout.strip()
  except subprocess.CalledProcessError:
    return ""


def get_git_context() -> Dict[str, str]:
  """Get current git context."""
  commands = {
      "current_branch": "git branch --show-current",
      "recent_commits": "git log --oneline -5",
      "status": "git status --porcelain",
      "last_commit_hash": "git rev-parse HEAD",
      "last_commit_message": "git log -1 --pretty=%B",
  }

  context = {}
  # Use a thread pool to run git commands in parallel for speed.
  with ThreadPoolExecutor() as executor:
    future_to_key = {
        executor.submit(run_git_command, cmd): key
        for key, cmd in commands.items()
    }
    for future in future_to_key:
      key = future_to_key[future]
      context[key] = future.result()
  return context


def get_file_context() -> Dict[str, Any]:
  """Get context about current files."""
  context = {}

  # Check for session state file
  session_state = Path(".ai-session-state.yaml")
  if session_state.exists():
    context["session_state_exists"] = True
    context["session_state_modified"] = datetime.datetime.fromtimestamp(
        session_state.stat().st_mtime
    ).isoformat()

  # Check for development log
  dev_log = Path("DEVELOPMENT_LOG.md")
  if dev_log.exists():
    context["dev_log_exists"] = True
    context["dev_log_modified"] = datetime.datetime.fromtimestamp(
        dev_log.stat().st_mtime
    ).isoformat()

  return context


def save_context() -> None:
  """Save current development context."""
  context = {
      "timestamp": datetime.datetime.now().isoformat(),
      "git": get_git_context(),
      "files": get_file_context(),
      "working_directory": str(Path.cwd()),
  }

  context_file = Path(".ai-context.json")
  with open(context_file, "w") as f:
    json.dump(context, f, indent=2)

  print(f"✅ Context saved to {context_file}")
  print(f"   Timestamp: {context['timestamp']}")
  print(f"   Branch: {context['git']['current_branch']}")
  print(
      f"   Status: {
          len(
              context['git']['status'].splitlines()) if context['git']['status'] else 0} changes"
  )


def load_context() -> Optional[Dict[str, Any]]:
  """Load saved development context."""
  context_file = Path(".ai-context.json")

  if not context_file.exists():
    print("❌ No saved context found")
    return None

  with open(context_file, "r") as f:
    context = json.load(f)

  print(f"📋 Loaded context from {context_file}")
  print(f"   Saved: {context['timestamp']}")
  print(f"   Branch: {context['git']['current_branch']}")
  print(f"   Working directory: {context['working_directory']}")

  # Check if we're in the same directory
  if context["working_directory"] != str(Path.cwd()):
    print(f"⚠️  Warning: Context was saved in different directory")
    print(f"   Saved: {context['working_directory']}")
    print(f"   Current: {Path.cwd()}")

  return context


def update_session_state() -> None:
  """Update the session state file with current information."""
  session_state = Path(".ai-session-state.yaml")

  if not session_state.exists():
    print("❌ No session state file found")
    return

  try:
    current_time = datetime.datetime.now().isoformat()
    with open(session_state, "r") as f:
      # Use safe_load to avoid arbitrary code execution
      data = yaml.safe_load(f) or {}

    # Update the timestamp
    data["last_updated"] = current_time

    # Write back, preserving YAML structure
    with open(session_state, "w") as f:
      # Use sort_keys=False to maintain original order as much as possible
      yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Updated session state timestamp: {current_time}")
  except (yaml.YAMLError, IOError) as e:
    print(f"❌ Error processing YAML file {session_state}: {e}")


def main():
  """Main entry point."""
  if len(sys.argv) < 2:
    print("Usage: python scripts/ai_context.py [save|load|update]")
    print("  save   - Save current context")
    print("  load   - Load saved context")
    print("  update - Update session state timestamp")
    sys.exit(1)

  command = sys.argv[1].lower()

  if command == "save":
    save_context()
  elif command == "load":
    load_context()
  elif command == "update":
    update_session_state()
  else:
    print(f"❌ Unknown command: {command}")
    sys.exit(1)


if __name__ == "__main__":
  main()
