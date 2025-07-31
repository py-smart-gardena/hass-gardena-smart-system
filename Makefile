# Makefile for Gardena Smart System Integration
# Automatic virtual environment management and development tasks

.PHONY: help setup install test test-auth clean ha-start ha-stop ha-reset ha-logs

# Variables
VENV_NAME := venv
VENV_PATH := $(VENV_NAME)/bin
PYTHON := $(VENV_PATH)/python
PIP := $(VENV_PATH)/pip
PYTEST := $(VENV_PATH)/pytest

# Home Assistant variables
HA_CONFIG_DIR := .homeassistant
HA_CUSTOM_COMPONENTS := $(HA_CONFIG_DIR)/custom_components
HA_LOGS := $(HA_CONFIG_DIR)/home-assistant.log
HA_PID_FILE := .ha.pid

# Colors for messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Shows help
	@echo "$(GREEN)Gardena Smart System Integration - Makefile$(NC)"
	@echo ""
	@echo "$(YELLOW)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Environment variables:$(NC)"
	@echo "  GARDENA_CLIENT_ID     - Your Gardena Client ID"
	@echo "  GARDENA_CLIENT_SECRET - Your Gardena Client Secret"
	@echo "  GARDENA_API_KEY       - Your Gardena API Key (optional)"
	@echo ""
	@echo "$(YELLOW)Home Assistant commands:$(NC)"
	@echo "  ha-start              - Start Home Assistant with the integration"
	@echo "  ha-stop               - Stop Home Assistant"
	@echo "  ha-reset              - Reset Home Assistant environment"
	@echo "  ha-logs               - Show Home Assistant logs"

setup: ## Sets up complete development environment
	@echo "$(GREEN)🔧 Setting up development environment...$(NC)"
	@if [ ! -d "$(VENV_NAME)" ]; then \
		python3 -m venv $(VENV_NAME) 2>/dev/null || python -m venv $(VENV_NAME) 2>/dev/null || (echo "$(RED)❌ Python not found. Install Python 3.6+$(NC)" && exit 1); \
		echo "$(GREEN)✅ Virtual environment created$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Virtual environment already exists$(NC)"; \
	fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Environment configured successfully!$(NC)"
	@echo "$(YELLOW)💡 Use 'make test-auth' to test authentication$(NC)"

install: ## Installs development dependencies
	@echo "$(GREEN)📥 Installing dependencies...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Virtual environment not found$(NC)"; \
		echo "$(YELLOW)💡 Run 'make setup' to create the environment$(NC)"; \
		exit 1; \
	fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

test: ## Runs all tests
	@echo "$(GREEN)🧪 Running all tests...$(NC)"
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "$(RED)❌ Virtual environment not found$(NC)"; \
		echo "$(YELLOW)💡 Run 'make setup' to create the environment$(NC)"; \
		exit 1; \
	fi
	@$(PYTEST) custom_components/gardena_smart_system/ -v

test-auth: ## Runs authentication tests only
	@echo "$(GREEN)🔐 Authentication tests...$(NC)"
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "$(RED)❌ Virtual environment not found$(NC)"; \
		echo "$(YELLOW)💡 Run 'make setup' to create the environment$(NC)"; \
		exit 1; \
	fi
	@$(PYTEST) custom_components/gardena_smart_system/test_auth.py -v

test-real: ## Real-world authentication test
	@echo "$(GREEN)🧪 Real-world authentication test...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Virtual environment not found$(NC)"; \
		echo "$(YELLOW)💡 Run 'make setup' to create the environment$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(GARDENA_CLIENT_ID)" ] || [ -z "$(GARDENA_CLIENT_SECRET)" ]; then \
		echo "$(RED)❌ Missing environment variables$(NC)"; \
		echo "$(YELLOW)💡 Set GARDENA_CLIENT_ID and GARDENA_CLIENT_SECRET$(NC)"; \
		echo "$(YELLOW)   Example: export GARDENA_CLIENT_ID='your-client-id'$(NC)"; \
		exit 1; \
	fi
	@$(PYTHON) scripts/test_auth.py

clean: ## Cleans temporary files and virtual environment
	@echo "$(GREEN)🧹 Cleaning...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf $(VENV_NAME)
	@echo "$(GREEN)✅ Cleaning completed$(NC)"

# Home Assistant targets

ha-start: ## Start Home Assistant with the integration
	@echo "$(GREEN)🏠 Starting Home Assistant...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Virtual environment not found$(NC)"; \
		echo "$(YELLOW)💡 Run 'make setup' to create the environment$(NC)"; \
		exit 1; \
	fi
	@if [ -f "$(HA_PID_FILE)" ]; then \
		echo "$(YELLOW)⚠️  Home Assistant is already running (PID: $$(cat $(HA_PID_FILE)))$(NC)"; \
		echo "$(YELLOW)💡 Use 'make ha-stop' to stop it first$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)📦 Installing Home Assistant dependencies...$(NC)"
	@$(PIP) install -q mutagen gtts PyMetno radios
	@echo "$(GREEN)📁 Setting up Home Assistant configuration...$(NC)"
	@mkdir -p $(HA_CONFIG_DIR)
	@mkdir -p $(HA_CUSTOM_COMPONENTS)
	@if [ ! -L "$(HA_CUSTOM_COMPONENTS)/gardena_smart_system" ]; then \
		ln -sf ../../custom_components/gardena_smart_system $(HA_CUSTOM_COMPONENTS)/; \
		echo "$(GREEN)✅ Integration linked to Home Assistant$(NC)"; \
	fi
	@if [ ! -f "$(HA_CONFIG_DIR)/configuration.yaml" ]; then \
		echo "homeassistant:" > $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  name: Gardena Test" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  latitude: 48.8566" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  longitude: 2.3522" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  elevation: 35" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  unit_system: metric" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  time_zone: Europe/Paris" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "logger:" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  default: warning" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "  logs:" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "    custom_components.gardena_smart_system: debug" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "    gardena_smart_system: debug" >> $(HA_CONFIG_DIR)/configuration.yaml; \
		echo "$(GREEN)✅ Configuration file created$(NC)"; \
	fi
	@echo "$(GREEN)🚀 Starting Home Assistant...$(NC)"
	@GARDENA_DEV_MODE=true $(PYTHON) -m homeassistant --config $(HA_CONFIG_DIR) > $(HA_LOGS) 2>&1 & \
	echo $$! > $(HA_PID_FILE); \
	sleep 5; \
	if ps -p $$(cat $(HA_PID_FILE)) > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Home Assistant started (PID: $$(cat $(HA_PID_FILE)))$(NC)"; \
		echo "$(YELLOW)💡 Access Home Assistant at: http://localhost:8123$(NC)"; \
		echo "$(YELLOW)💡 View logs with: make ha-logs$(NC)"; \
		echo "$(YELLOW)💡 Stop with: make ha-stop$(NC)"; \
	else \
		echo "$(RED)❌ Home Assistant failed to start$(NC)"; \
		echo "$(YELLOW)💡 Check logs with: make ha-logs$(NC)"; \
		rm -f $(HA_PID_FILE); \
		exit 1; \
	fi

ha-stop: ## Stop Home Assistant
	@echo "$(GREEN)🛑 Stopping Home Assistant...$(NC)"
	@if [ -f "$(HA_PID_FILE)" ]; then \
		PID=$$(cat $(HA_PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			kill $$PID; \
			echo "$(GREEN)✅ Home Assistant stopped (PID: $$PID)$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  Home Assistant process not found (PID: $$PID)$(NC)"; \
		fi; \
		rm -f $(HA_PID_FILE); \
	else \
		echo "$(YELLOW)⚠️  No PID file found$(NC)"; \
	fi

ha-reset: ## Reset Home Assistant environment
	@echo "$(GREEN)🔄 Resetting Home Assistant environment...$(NC)"
	@make ha-stop > /dev/null 2>&1 || true
	@if [ -d "$(HA_CONFIG_DIR)" ]; then \
		rm -rf $(HA_CONFIG_DIR); \
		echo "$(GREEN)✅ Home Assistant configuration removed$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  No Home Assistant configuration found$(NC)"; \
	fi
	@rm -f $(HA_PID_FILE)
	@echo "$(GREEN)✅ Home Assistant environment reset$(NC)"
	@echo "$(YELLOW)💡 Run 'make ha-start' to start fresh$(NC)"

ha-logs: ## Show Home Assistant logs
	@echo "$(GREEN)📋 Home Assistant logs:$(NC)"
	@if [ -f "$(HA_LOGS)" ]; then \
		echo "$(YELLOW)💡 Press Ctrl+C to stop following logs$(NC)"; \
		echo "$(YELLOW)💡 Last 20 lines:$(NC)"; \
		tail -20 $(HA_LOGS); \
		echo ""; \
		echo "$(YELLOW)💡 Following new logs (Ctrl+C to stop):$(NC)"; \
		tail -f $(HA_LOGS); \
	else \
		echo "$(YELLOW)⚠️  No log file found$(NC)"; \
		echo "$(YELLOW)💡 Start Home Assistant first with: make ha-start$(NC)"; \
	fi 