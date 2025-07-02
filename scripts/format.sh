#!/bin/bash

# OSED Project Formatting Script
# Formats comments in source files and plain text files with 2-space indentation
# and 80-character hard-wrapping. Defaults to dry-run mode.

set -o errexit -o pipefail -o noclobber -o nounset

# Constants
DEFAULT_LINE_LENGTH=80
DEFAULT_INDENT_SIZE=2
TEMP_SUFFIX=".tmp"
BACKUP_SUFFIX=".bak"

# Global variables
DRY_RUN=true
VERBOSE=false
SPECIFIC_FILE=""
SPECIFIC_FILES=()
CHANGES_SUMMARY=()

# Colors for output (GNU/Linux enhancement)
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  NC='\033[0m' # No Color
else
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  NC=''
fi

# Logging functions
log_info() {
  echo -e "${BLUE}ℹ️  ${NC}$1"
}

log_success() {
  echo -e "${GREEN}✅ ${NC}$1"
}

log_warning() {
  echo -e "${YELLOW}⚠️  ${NC}$1"
}

log_error() {
  echo -e "${RED}❌ ${NC}$1"
}

log_verbose() {
  if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}🔍 ${NC}$1"
  fi
}

# Enhanced argument parsing
parse_arguments() {
  while getopts "hvaf:" opt; do
    case $opt in
      h)
        show_help
        exit 0
        ;;
      v)
        VERBOSE=true
        ;;
      a)
        DRY_RUN=false
        ;;
      f)
        SPECIFIC_FILE="$OPTARG"
        ;;
      \?)
        log_error "Invalid option: -$OPTARG"
        show_help
        exit 1
        ;;
      :)
        log_error "Option -$OPTARG requires an argument"
        show_help
        exit 1
        ;;
    esac
  done

  # Handle additional arguments as specific files
  shift $((OPTIND-1))
  if [ $# -gt 0 ]; then
    SPECIFIC_FILES=("$@")
  fi
}

# Show help message
show_help() {
  cat << EOF
Usage: $0 [OPTIONS] [file1 file2 ...]

Options:
  -h              Show this help message
  -v              Verbose output
  -a              Apply changes (default: dry run)
  -f FILE         Specify a file to format

If no files are given, all tracked files are formatted.

Examples:
  $0                    # Format all tracked files
  $0 -v                 # Verbose formatting of all files
  $0 -a *.py           # Apply formatting to Python files
  $0 -f file.py        # Format specific file
  $0 file1.py file2.py # Format specific files

EOF
}

# Get list of files to format
get_files_to_format() {
  local files=()

  if [ -n "$SPECIFIC_FILE" ]; then
    files=("$SPECIFIC_FILE")
  elif [ ${#SPECIFIC_FILES[@]} -gt 0 ]; then
    files=("${SPECIFIC_FILES[@]}")
  else
    log_verbose "No files specified, using all tracked files"
    # Get all tracked files from git
    if command -v git >/dev/null 2>&1; then
      while IFS= read -r -d '' file; do
        files+=("$file")
      done < <(git ls-files -z 2>/dev/null || true)
    else
      log_warning "Git not available, no files to format"
      return 1
    fi
  fi

  # Filter files by type
  local source_files=()
  local text_files=()

  for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
      continue
    fi

    case "$file" in
      *.c|*.cpp|*.h|*.hpp|*.cc|*.cxx|*.sh|*.py|*.js|*.ts|*.java|*.go|*.rs)
        source_files+=("$file")
        ;;
      *.txt|*.md|*.rst|*.adoc|*.tex|*.log)
        text_files+=("$file")
        ;;
    esac
  done

  SOURCE_FILES=("${source_files[@]}")
  TEXT_FILES=("${text_files[@]}")
}

# Create backup of file
create_backup() {
  local file="$1"
  local backup_file="${file}${BACKUP_SUFFIX}"

  if [ "$DRY_RUN" = true ]; then
    return 0
  fi

  if ! cp "$file" "$backup_file" 2>/dev/null; then
    log_error "Failed to create backup: $file"
    return 1
  fi
  log_verbose "Created backup: $backup_file"
}

# Restore backup
restore_backup() {
  local file="$1"
  local backup_file="${file}${BACKUP_SUFFIX}"

  if [ "$DRY_RUN" = true ]; then
    return 0
  fi

  if [ -f "$backup_file" ]; then
    mv "$backup_file" "$file"
    log_verbose "Restored backup for $file"
  fi
}

# Format comments in source files
format_source_comments() {
  if [ ${#SOURCE_FILES[@]} -eq 0 ]; then
    log_info "No source files to format"
    return 0
  fi

  log_info "Processing ${#SOURCE_FILES[@]} source files..."

  for file in "${SOURCE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
      log_warning "File not found: $file"
      continue
    fi

    log_verbose "Processing source file: $file"

    if [ "$DRY_RUN" = true ]; then
      log_verbose "Would format comments in: $file"
      CHANGES_SUMMARY+=("Source: $file (comment formatting)")
      continue
    fi

    # Create backup
    create_backup "$file" || continue

    # Format comments with 2-space indentation and 80-char wrapping
    local temp_file="${file}${TEMP_SUFFIX}"

    # Process comments based on file type
    case "$file" in
      *.py)
        # Python comments: # and docstrings
        awk '
        BEGIN { line_length = 80; indent_size = 2 }
        {
          # Handle docstrings
          if ($0 ~ /^[[:space:]]*"""/) {
            # Start of docstring
            print $0
            in_docstring = 1
            next
          }
          if (in_docstring && $0 ~ /^[[:space:]]*"""/) {
            # End of docstring
            print $0
            in_docstring = 0
            next
          }
          if (in_docstring) {
            # Format docstring content
            format_comment($0, line_length, indent_size)
            next
          }

          # Handle # comments
          if ($0 ~ /[[:space:]]*#/) {
            # Split into code and comment
            match($0, /[[:space:]]*#/)
            code_part = substr($0, 1, RSTART - 1)
            comment_part = substr($0, RSTART)

            # Format the comment part
            formatted_comment = format_comment(comment_part, line_length, indent_size)
            print code_part formatted_comment
          } else {
            print $0
          }
        }

        function format_comment(comment, max_len, indent) {
          # Remove leading spaces from comment
          gsub(/^[[:space:]]*/, "", comment)

          # Add proper indentation
          indent_str = ""
          for (i = 0; i < indent; i++) {
            indent_str = indent_str " "
          }

          # Wrap long comments
          if (length(comment) > max_len - length(indent_str)) {
            result = ""
            remaining = comment
            while (length(remaining) > max_len - length(indent_str)) {
              # Find last space before max length
              split_pos = max_len - length(indent_str)
              for (i = split_pos; i > 0; i--) {
                if (substr(remaining, i, 1) == " ") {
                  split_pos = i
                  break
                }
              }
              result = result substr(remaining, 1, split_pos) "\n" indent_str
              remaining = substr(remaining, split_pos + 1)
            }
            return result remaining
          } else {
            return indent_str comment
          }
        }
        ' "$file" > "$temp_file"
        ;;
      *.sh)
        # Shell comments: #
        awk '
        BEGIN { line_length = 80; indent_size = 2 }
        {
          if ($0 ~ /[[:space:]]*#/) {
            match($0, /[[:space:]]*#/)
            code_part = substr($0, 1, RSTART - 1)
            comment_part = substr($0, RSTART)
            formatted_comment = format_comment(comment_part, line_length, indent_size)
            print code_part formatted_comment
          } else {
            print $0
          }
        }

        function format_comment(comment, max_len, indent) {
          gsub(/^[[:space:]]*/, "", comment)
          indent_str = ""
          for (i = 0; i < indent; i++) {
            indent_str = indent_str " "
          }
          if (length(comment) > max_len - length(indent_str)) {
            result = ""
            remaining = comment
            while (length(remaining) > max_len - length(indent_str)) {
              split_pos = max_len - length(indent_str)
              for (i = split_pos; i > 0; i--) {
                if (substr(remaining, i, 1) == " ") {
                  split_pos = i
                  break
                }
              }
              result = result substr(remaining, 1, split_pos) "\n" indent_str
              remaining = substr(remaining, split_pos + 1)
            }
            return result remaining
          } else {
            return indent_str comment
          }
        }
        ' "$file" > "$temp_file"
        ;;
      *.c|*.cpp|*.h|*.hpp|*.cc|*.cxx)
        # C/C++ comments: // and /* */
        awk '
        BEGIN { line_length = 80; indent_size = 2 }
        {
          if ($0 ~ /\/\//) {
            match($0, /\/\//)
            code_part = substr($0, 1, RSTART - 1)
            comment_part = substr($0, RSTART)
            formatted_comment = format_comment(comment_part, line_length, indent_size)
            print code_part formatted_comment
          } else {
            print $0
          }
        }

        function format_comment(comment, max_len, indent) {
          gsub(/^[[:space:]]*/, "", comment)
          indent_str = ""
          for (i = 0; i < indent; i++) {
            indent_str = indent_str " "
          }
          if (length(comment) > max_len - length(indent_str)) {
            result = ""
            remaining = comment
            while (length(remaining) > max_len - length(indent_str)) {
              split_pos = max_len - length(indent_str)
              for (i = split_pos; i > 0; i--) {
                if (substr(remaining, i, 1) == " ") {
                  split_pos = i
                  break
                }
              }
              result = result substr(remaining, 1, split_pos) "\n" indent_str
              remaining = substr(remaining, split_pos + 1)
            }
            return result remaining
          } else {
            return indent_str comment
          }
        }
        ' "$file" > "$temp_file"
        ;;
      *)
        # Default: just copy the file
        cp "$file" "$temp_file"
        ;;
    esac

    # Preserve original permissions
    local original_perms=$(stat -c "%a" "$file" 2>/dev/null || echo "644")
    chmod "$original_perms" "$temp_file"

    # Check if file changed
    if ! diff "$file" "$temp_file" >/dev/null 2>&1; then
      mv "$temp_file" "$file"
      log_success "Formatted comments in: $file"
    else
      log_verbose "No changes needed: $file"
      rm -f "$temp_file"
    fi

    cleanup_temp_files "$file"
  done
}

# Format text files
format_text_files() {
  if [ ${#TEXT_FILES[@]} -eq 0 ]; then
    log_info "No text files to format"
    return 0
  fi

  log_info "Formatting ${#TEXT_FILES[@]} text files..."

  for file in "${TEXT_FILES[@]}"; do
    if [ ! -f "$file" ]; then
      log_warning "File not found: $file"
      continue
    fi

    if [ ! -s "$file" ]; then
      log_warning "Empty file, skipping: $file"
      continue
    fi

    log_verbose "Processing text file: $file"

    if [ "$DRY_RUN" = true ]; then
      log_verbose "Would format: $file"
      CHANGES_SUMMARY+=("Text: $file (line wrapping)")
      continue
    fi

    # Create backup
    create_backup "$file" || continue

    # Apply 2-space indentation and 80-char wrapping
    local temp_file="${file}${TEMP_SUFFIX}"

    # Convert tabs to spaces, then apply 2-space indentation
    expand -t 4 "$file" | awk '{
      # Count leading spaces and convert to 2-space indentation
      spaces = 0
      while (substr($0, spaces + 1, 1) == " ") {
        spaces++
      }
      # Round down to nearest even number
      spaces = int(spaces / 2) * 2
      indent = ""
      for (i = 0; i < spaces; i += 2) {
        indent = indent "  "
      }
      print indent substr($0, spaces + 1)
    }' | fold -s -w $DEFAULT_LINE_LENGTH > "$temp_file"

    # Preserve original permissions
    local original_perms=$(stat -c "%a" "$file" 2>/dev/null || echo "644")
    chmod "$original_perms" "$temp_file"

    # Check if file changed
    if ! diff "$file" "$temp_file" >/dev/null 2>&1; then
      mv "$temp_file" "$file"
      log_success "Formatted: $file"
    else
      log_verbose "No changes needed: $file"
      rm -f "$temp_file"
    fi

    cleanup_temp_files "$file"
  done
}

# Clean up temporary files
cleanup_temp_files() {
  local file="$1"
  local temp_file="${file}${TEMP_SUFFIX}"
  local backup_file="${file}${BACKUP_SUFFIX}"

  if [ "$DRY_RUN" = true ]; then
    log_verbose "Would clean up temp files for $file"
    return 0
  fi

  rm -f "$temp_file" "$backup_file" 2>/dev/null || true
}

# Main function
main() {
  if [ "$DRY_RUN" = true ]; then
    log_info "🔍 Checking formatting (dry run)..."
  else
    log_info "🔧 Applying formatting changes..."
  fi

  # Parse arguments
  parse_arguments "$@"

  # Get files to format
  get_files_to_format

  # Format files
  format_source_comments
  format_text_files

  # Show summary
  if [ ${#CHANGES_SUMMARY[@]} -gt 0 ]; then
    log_info "Summary of changes that would be made:"
    for change in "${CHANGES_SUMMARY[@]}"; do
      echo "  $change"
    done
    if [ "$DRY_RUN" = true ]; then
      log_info "Run with -a or --apply to update files."
    fi
  else
    log_info "No formatting changes needed."
  fi
  if [ "$DRY_RUN" = true ]; then
    log_success "Dry run complete! No files were modified."
  else
    log_success "Formatting complete! Files updated."
  fi
}

# Run main function with all arguments
main "$@"
