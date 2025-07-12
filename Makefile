.PHONY: help install install-dev format format-check lint test validate validate-all clean context-save context-load context-update context build-cpp clean-cpp test-cpp

help: ## Show this help message
	@echo "OSED Development Commands"
	@echo "========================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt

format: ## Format all code files
	@echo "Formatting Python files with Black..."
	black .
	@echo "Formatting other files with Prettier..."
	prettier --write "*.{json,md}" "schema/**/*.{yaml,yml}" "tests/data/**/*.{yaml,yml}" "examples/**/*.{json,md}"

format-check: ## Check formatting without making changes
	@echo "Checking Python formatting with Black..."
	black --check .
	@echo "Checking other files with Prettier..."
	prettier --check "*.{json,md}" "schema/**/*.{yaml,yml}" "tests/data/**/*.{yaml,yml}" "examples/**/*.{json,md}"

lint: ## Lint Python code
	git ls-files '*.py' | xargs pylint --indent-string='  ' --max-line-length=80

test: ## Run Python tests and npm tests
	pytest tests/ -v
	@echo ""
	@echo "Running npm tests in examples..."
	@if [ -d "examples/mongoose-mongo-server" ]; then \
		cd examples/mongoose-mongo-server && npm test; \
	else \
		echo "No npm tests found in examples/mongoose-mongo-server"; \
	fi

build-cpp: ## Build C++ components using CMake
	@echo "Building C++ components..."
	cd src/cpp && cmake -B build -S . && cmake --build build

clean-cpp: ## Clean C++ build artifacts
	@echo "Cleaning C++ build artifacts..."
	cd src/cpp && rm -rf build/

test-cpp: build-cpp ## Run C++ tests
	@echo "Running C++ tests..."
	# Add C++ test commands here when implemented

validate: ## Validate OSED documents
	osed validate -f osed.yaml --schema 0.3.0
	osed validate -f metadata/osed.metadata.mongoose-mongo.v0.3.0.yaml --schema 0.3.0 --metadata-schema 0.3.0

validate-all: ## Validate all OSED documents
	find . -name "*.yaml" -o -name "*.yml" | grep -v ".git" | while read file; do \
		echo "Validating $$file"; \
		osed validate -f "$$file" --schema 0.3.0 || exit 1; \
	done

clean: clean-cpp ## Clean all build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

check-line-length: ## Check line lengths in all files
	@echo "Checking line lengths..."
	@git ls-files '*.yaml' '*.yml' '*.txt' '*.md' '*.sh' '*.cpp' '*.h' Makefile | while read file; do \
		if awk 'length > 80 {exit 1}' "$$file" 2>/dev/null; then \
			echo "  ✅ $$file (lines <= 80 chars)"; \
		else \
			echo "  ❌ $$file (has lines > 80 chars)"; \
			awk 'length > 80 {print "    Line " NR ": " $$0}' "$$file"; \
		fi; \
	done

setup: install-dev ## Set up development environment
	@echo "Development environment setup complete!"
	@echo "Note: Install global tools manually:"
	@echo "  npm install -g prettier"
	@echo "  pip install conan  # for C++ development"
	@echo ""
	@echo "Run 'make format' to format code"
	@echo "Run 'make lint' to check code quality"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make build-cpp' to build C++ components"

context-save: ## Save current development context
	python3 scripts/ai_context.py save

context-load: ## Load saved development context
	python3 scripts/ai_context.py load

context-update: ## Update session state timestamp
	python3 scripts/ai_context.py update

context: context-load ## Load context and show current state
	@echo ""
	@echo "📋 Current Session State:"
	@if [ -f .cursor-session-state.yaml ]; then \
		echo "✅ Session state file exists"; \
		grep "current_task:" .cursor-session-state.yaml || echo "   No current task defined"; \
	else \
		echo "❌ No session state file found"; \
	fi
	@echo ""
	@echo "📝 Recent Development Log:"
	@if [ -f DEVELOPMENT_LOG.md ]; then \
		head -20 DEVELOPMENT_LOG.md; \
	else \
		echo "❌ No development log found"; \
	fi
