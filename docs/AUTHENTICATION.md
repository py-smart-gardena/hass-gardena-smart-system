# Authentification Gardena Smart System

Ce document décrit l'implémentation de l'authentification OAuth2 pour l'API Gardena Smart System v2.

## Architecture d'authentification

### Composants principaux

1. **`GardenaAuthenticationManager`** : Gestionnaire centralisé de l'authentification
2. **`GardenaSmartSystemClient`** : Client API avec gestion d'erreurs avancée
3. **Gestion des erreurs** : Exceptions spécialisées pour différents types d'erreurs

### Flux d'authentification

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client ID     │───▶│  Authenticate    │───▶│  Access Token   │
│ Client Secret   │    │  (OAuth2)        │    │  Refresh Token  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Token Expired?  │
                       └──────────────────┘
                                │
                        ┌───────┴───────┐
                        ▼               ▼
              ┌─────────────────┐ ┌─────────────────┐
              │   Use Token     │ │  Refresh Token  │
              └─────────────────┘ └─────────────────┘
```

## Types d'authentification supportés

### 1. OAuth2 Bearer Token

L'authentification principale utilise le standard OAuth2 avec :
- **Grant Type** : `client_credentials`
- **Token Type** : Bearer Token
- **Endpoint** : `/oauth2/token`

### 2. X-Api-Key (Optionnel)

Pour les applications nécessitant des permissions supplémentaires :
- **Header** : `X-Api-Key`
- **Usage** : Complémentaire au Bearer Token

## Gestion des erreurs

### Codes d'erreur HTTP

| Code | Description | Action |
|------|-------------|---------|
| 401 | Unauthorized | Clear tokens, retry authentication |
| 403 | Forbidden | Check API key and permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Retry with exponential backoff |
| 502 | Bad Gateway | Retry with exponential backoff |

### Exceptions personnalisées

#### `GardenaAuthError`
- **Usage** : Erreurs d'authentification
- **Propriétés** : `status_code`, `response_data`
- **Exemple** : Token expiré, identifiants invalides

#### `GardenaAPIError`
- **Usage** : Erreurs API générales
- **Propriétés** : `status_code`, `response_data`
- **Exemple** : Erreurs réseau, erreurs serveur

## Logs détaillés

### Niveaux de log

- **DEBUG** : Requêtes/réponses détaillées, gestion des tokens
- **INFO** : Authentification réussie, mises à jour de données
- **WARNING** : Échecs de refresh token, erreurs temporaires
- **ERROR** : Erreurs d'authentification, erreurs API

### Exemples de logs

```
DEBUG: Making auth request to https://api.smart.gardena.dev/v2/oauth2/token
INFO: Authentication successful, token expires at 2024-01-15 10:30:00
WARNING: Token refresh failed: Invalid refresh token
ERROR: Authentication error during data update: Invalid credentials (status: 401)
```

## Configuration

### Paramètres requis

```yaml
# configuration.yaml
gardena_smart_system:
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  # api_key: "your-api-key"  # Optionnel
```

### Variables d'environnement

```bash
export GARDENA_CLIENT_ID="your-client-id"
export GARDENA_CLIENT_SECRET="your-client-secret"
export GARDENA_API_KEY="your-api-key"  # Optionnel
```

## Tests

### Tests unitaires

Les tests couvrent :
- Authentification initiale
- Refresh de tokens
- Gestion des erreurs (401, 403, 404, 500, 502)
- Validation des tokens
- Nettoyage des ressources

### Exécution des tests

```bash
# Tests d'authentification uniquement
pytest custom_components/gardena_smart_system/test_auth.py -v

# Tests avec couverture
pytest custom_components/gardena_smart_system/test_auth.py --cov=. --cov-report=html
```

## Sécurité

### Bonnes pratiques

1. **Stockage sécurisé** : Les tokens ne sont jamais persistés sur disque
2. **Rotation automatique** : Refresh automatique des tokens expirés
3. **Nettoyage** : Suppression automatique des tokens invalides
4. **Logs sécurisés** : Les tokens ne sont jamais loggés en clair

### Gestion des tokens

- **Access Token** : Durée de vie limitée (1 heure par défaut)
- **Refresh Token** : Utilisé pour renouveler l'access token
- **Buffer de sécurité** : 5 minutes avant expiration pour éviter les échecs

## Dépannage

### Problèmes courants

#### Erreur 401 - Unauthorized
```bash
# Vérifier les identifiants
curl -X POST https://api.smart.gardena.dev/v2/oauth2/token \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

#### Erreur 403 - Forbidden
- Vérifier que l'API key est correcte
- Contrôler les permissions de l'application

#### Erreur 500/502 - Server Error
- Attendre quelques minutes avant de réessayer
- Vérifier le statut de l'API Gardena

### Debug avancé

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.gardena_smart_system: debug
    custom_components.gardena_smart_system.auth: debug
```

## Intégration avec Home Assistant

### Flux de configuration

1. **Validation des identifiants** lors de la configuration
2. **Test de connexion** avec l'API
3. **Vérification des permissions** et des locations
4. **Gestion des erreurs** avec messages utilisateur appropriés

### Messages d'erreur utilisateur

- `invalid_auth` : Identifiants incorrects
- `insufficient_permissions` : Permissions insuffisantes
- `no_locations` : Aucune location trouvée
- `server_error` : Erreur serveur temporaire

## Évolutions futures

### Fonctionnalités prévues

1. **Support OAuth2 Authorization Code** pour les applications web
2. **Cache de tokens** pour améliorer les performances
3. **Métriques d'authentification** pour le monitoring
4. **Support multi-tenant** pour plusieurs comptes

### Améliorations de sécurité

1. **Chiffrement des tokens** en mémoire
2. **Rotation automatique** des refresh tokens
3. **Détection d'anomalies** dans les patterns d'authentification 