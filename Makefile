# Makefile pour Gardena Smart System Integration
# Gestion automatique de l'environnement virtuel et des tâches de développement

.PHONY: help setup install test test-auth clean

# Variables
PYTHON_VERSION := 3.11
VENV_NAME := venv
VENV_PATH := $(VENV_NAME)/bin
PYTHON := $(VENV_PATH)/python
PIP := $(VENV_PATH)/pip
PYTEST := $(VENV_PATH)/pytest

# Couleurs pour les messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Affiche l'aide
	@echo "$(GREEN)Gardena Smart System Integration - Makefile$(NC)"
	@echo ""
	@echo "$(YELLOW)Commandes disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Variables d'environnement:$(NC)"
	@echo "  GARDENA_CLIENT_ID     - Votre Client ID Gardena"
	@echo "  GARDENA_CLIENT_SECRET - Votre Client Secret Gardena"
	@echo "  GARDENA_API_KEY       - Votre API Key Gardena (optionnel)"

setup: ## Configure l'environnement de développement complet
	@echo "$(GREEN)🔧 Configuration de l'environnement de développement...$(NC)"
	@if [ ! -d "$(VENV_NAME)" ]; then \
		python$(PYTHON_VERSION) -m venv $(VENV_NAME); \
		echo "$(GREEN)✅ Environnement virtuel créé$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  L'environnement virtuel existe déjà$(NC)"; \
	fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Environnement configuré avec succès!$(NC)"
	@echo "$(YELLOW)💡 Utilisez 'make test-auth' pour tester l'authentification$(NC)"

install: ## Installe les dépendances de développement
	@echo "$(GREEN)📥 Installation des dépendances...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Environnement virtuel non trouvé$(NC)"; \
		echo "$(YELLOW)💡 Exécutez 'make setup' pour créer l'environnement$(NC)"; \
		exit 1; \
	fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Dépendances installées$(NC)"

test: ## Lance tous les tests
	@echo "$(GREEN)🧪 Lancement de tous les tests...$(NC)"
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "$(RED)❌ Environnement virtuel non trouvé$(NC)"; \
		echo "$(YELLOW)💡 Exécutez 'make setup' pour créer l'environnement$(NC)"; \
		exit 1; \
	fi
	@$(PYTEST) custom_components/gardena_smart_system/ -v

test-auth: ## Lance uniquement les tests d'authentification
	@echo "$(GREEN)🔐 Tests d'authentification...$(NC)"
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "$(RED)❌ Environnement virtuel non trouvé$(NC)"; \
		echo "$(YELLOW)💡 Exécutez 'make setup' pour créer l'environnement$(NC)"; \
		exit 1; \
	fi
	@$(PYTEST) custom_components/gardena_smart_system/test_auth.py -v

test-real: ## Test d'authentification en conditions réelles
	@echo "$(GREEN)🧪 Test d'authentification en conditions réelles...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Environnement virtuel non trouvé$(NC)"; \
		echo "$(YELLOW)💡 Exécutez 'make setup' pour créer l'environnement$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(GARDENA_CLIENT_ID)" ] || [ -z "$(GARDENA_CLIENT_SECRET)" ]; then \
		echo "$(RED)❌ Variables d'environnement manquantes$(NC)"; \
		echo "$(YELLOW)💡 Définissez GARDENA_CLIENT_ID et GARDENA_CLIENT_SECRET$(NC)"; \
		echo "$(YELLOW)   Exemple: export GARDENA_CLIENT_ID='your-client-id'$(NC)"; \
		exit 1; \
	fi
	@$(PYTHON) scripts/test_auth.py

clean: ## Nettoie les fichiers temporaires et l'environnement virtuel
	@echo "$(GREEN)🧹 Nettoyage...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf $(VENV_NAME)
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)" 