# Guide de développement - Gardena Smart System Integration

Ce guide explique comment configurer et utiliser l'environnement de développement pour l'intégration Gardena Smart System.

## 🚀 Configuration rapide

### 1. Configuration initiale

```bash
# Configuration complète de l'environnement
make setup
```

Cette commande va :
- Créer un environnement virtuel Python 3.11
- Installer toutes les dépendances de développement

### 2. Vérification de l'installation

```bash
# Vérifier que tout fonctionne
make help
```

## 🛠️ Commandes de développement

### Commandes principales

| Commande | Description |
|----------|-------------|
| `make help` | Affiche l'aide complète |
| `make setup` | Configure l'environnement complet |
| `make install` | Réinstalle les dépendances |
| `make test` | Lance tous les tests |
| `make test-auth` | Lance les tests d'authentification |
| `make test-real` | Test en conditions réelles |
| `make clean` | Nettoie tout (fichiers + environnement) |

### Tests

```bash
# Tests d'authentification uniquement
make test-auth

# Test en conditions réelles (nécessite les variables d'environnement)
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"
make test-real
```

## 🔧 Configuration des variables d'environnement

### Variables requises

```bash
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"
```

### Variables optionnelles

```bash
export GARDENA_API_KEY="your-api-key"
```

### Fichier .env (recommandé)

Créez un fichier `.env` à la racine du projet :

```bash
GARDENA_CLIENT_ID=your-client-id
GARDENA_CLIENT_SECRET=your-client-secret
GARDENA_API_KEY=your-api-key
```

Puis chargez-le :

```bash
source .env
```

## 📁 Structure du projet

```
hass-gardena-smart-system/
├── custom_components/gardena_smart_system/
│   ├── __init__.py              # Point d'entrée principal
│   ├── auth.py                  # Gestionnaire d'authentification
│   ├── gardena_client.py        # Client API
│   ├── coordinator.py           # Coordinateur de données
│   ├── config_flow.py           # Flux de configuration
│   ├── const.py                 # Constantes
│   ├── lawn_mower.py           # Entités tondeuses
│   ├── sensor.py               # Entités capteurs
│   ├── binary_sensor.py        # Entités capteurs binaires
│   ├── switch.py               # Entités interrupteurs
│   ├── valve.py                # Entités vannes
│   ├── test_auth.py            # Tests d'authentification
│   ├── manifest.json           # Métadonnées
│   ├── strings.json            # Traductions
│   └── services.yaml           # Services
├── docs/
│   └── AUTHENTICATION.md       # Documentation d'authentification
├── scripts/
│   └── test_auth.py            # Script de test en conditions réelles
├── Makefile                    # Commandes de développement
├── requirements.txt            # Dépendances de production
├── requirements-dev.txt        # Dépendances de développement
├── .pre-commit-config.yaml     # Configuration pre-commit
└── .gitignore                  # Fichiers ignorés
```

## 🧪 Tests

### Tests unitaires

```bash
# Tous les tests
make test

# Tests d'authentification uniquement
make test-auth
```

### Tests en conditions réelles

```bash
# Configuration des variables d'environnement
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"

# Test d'authentification
make test-real
```

### Exécution manuelle des tests

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Exécuter les tests
pytest custom_components/gardena_smart_system/test_auth.py -v
```

## 🚀 Workflow de développement

### 1. Démarrage quotidien

```bash
# Vérifier l'environnement
make help
```

### 2. Développement

```bash
# Éditer le code...

# Lancer les tests
make test-auth
```

### 3. Tests en conditions réelles

```bash
# Configurer les variables d'environnement
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"

# Tester l'authentification
make test-real
```

## 🧹 Nettoyage

### Remise à zéro complète

```bash
make clean
```

Cette commande nettoie :
- Fichiers temporaires Python
- Cache de tests
- Environnement virtuel
- Rapports de couverture

## 🔧 Dépannage

### Problèmes courants

#### Environnement virtuel non trouvé

```bash
# Recréer l'environnement
make setup
```

#### Dépendances manquantes

```bash
# Réinstaller les dépendances
make install
```

#### Erreurs de tests

```bash
# Nettoyer et relancer
make clean
make setup
make test-auth
```

### Logs détaillés

```bash
# Activer les logs de debug
export PYTHONPATH=.
source venv/bin/activate
python -m pytest custom_components/gardena_smart_system/test_auth.py -v -s
```

## 📚 Ressources

- [Documentation d'authentification](docs/AUTHENTICATION.md)
- [API Gardena Smart System v2](iapi-v2.yml)
- [Guide des intégrations Home Assistant](https://developers.home-assistant.io/)

## 🤝 Contribution

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité
3. Suivez le workflow de développement
4. Ajoutez des tests pour votre code
5. Soumettez une pull request

### Checklist avant commit

- [ ] Tests passent (`make test`)
- [ ] Tests d'authentification passent (`make test-auth`)
- [ ] Documentation mise à jour si nécessaire 