# Logging Configuration

## Vue d'ensemble

L'intégration Gardena Smart System utilise différents niveaux de logging pour optimiser le débogage et le monitoring.

## Niveaux de Logging

### DEBUG
- **Utilisation** : Informations détaillées pour le débogage
- **Exemples** :
  - Création d'entités
  - État des propriétés (is_open, is_closed, etc.)
  - Messages WebSocket reçus
  - Tentatives de reconnexion
  - Détails de configuration

### INFO
- **Utilisation** : Informations importantes sur le fonctionnement
- **Exemples** :
  - Connexion WebSocket réussie
  - Commandes envoyées avec succès
  - Actions utilisateur (start, stop, pause)
  - Événements de déconnexion/reconnexion

### WARNING
- **Utilisation** : Situations anormales mais non critiques
- **Exemples** :
  - Tentatives de reconnexion échouées
  - Données manquantes mais non critiques
  - Configurations non optimales

### ERROR
- **Utilisation** : Erreurs critiques nécessitant une attention
- **Exemples** :
  - Échec d'authentification
  - Erreurs de communication API
  - Services non disponibles
  - Erreurs de configuration

## Configuration dans le Makefile

Le Makefile configure automatiquement le logging pour le développement :

```yaml
logger:
  default: info
  logs:
    custom_components.gardena_smart_system: debug
    gardena_smart_system: debug
    homeassistant.components.websocket_api: warning
    homeassistant.components.camera: warning
```

## Optimisations Récentes

### Logs Passés en DEBUG
- Création d'entités
- État des propriétés des valves
- Messages WebSocket détaillés
- Tentatives de reconnexion
- Configuration des entités

### Logs Gardés en INFO
- Connexion WebSocket réussie
- Actions utilisateur importantes
- Commandes envoyées avec succès
- Événements de déconnexion

### Logs Gardés en ERROR
- Erreurs d'authentification
- Échecs de communication
- Services non disponibles

## Utilisation en Développement

Pour voir tous les logs de débogage :
```bash
make ha-logs
```

Pour filtrer les logs de l'intégration :
```bash
tail -f .homeassistant/home-assistant.log | grep gardena_smart_system
```

## Performance

Les logs DEBUG sont désactivés par défaut en production pour optimiser les performances. Ils ne sont activés que dans l'environnement de développement via le Makefile. 