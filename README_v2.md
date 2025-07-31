# Gardena Smart System Integration v2.0.0

Une intégration Home Assistant moderne pour le système Gardena Smart System, basée sur l'API v2 de Gardena.

## 🚀 Nouveautés de la v2

- **Architecture moderne** : Utilisation des patterns recommandés par Home Assistant
- **Framework standardisé** : Basé sur le framework d'intégration officiel
- **Python 3.11+** : Support des versions récentes de Python
- **API v2** : Utilisation de la nouvelle API Gardena Smart System
- **Gestion d'état centralisée** : Coordinateur pour la synchronisation des données
- **Tests automatisés** : Tests unitaires avec mocks

## 📋 Fonctionnalités

### Entités supportées

- **Tondeuses** (`lawn_mower`) : Contrôle des tondeuses automatiques
- **Capteurs** (`sensor`) : Capteurs de température, humidité, etc.
- **Capteurs binaires** (`binary_sensor`) : Statut en ligne/hors ligne
- **Interrupteurs** (`switch`) : Prises électriques intelligentes
- **Vannes** (`valve`) : Vannes d'arrosage

### Fonctionnalités des tondeuses

- Démarrer la tonte
- Mettre en pause
- Retourner à la station de charge
- Surveillance de l'état et de l'activité

## 🛠️ Installation

### Installation manuelle

1. Copiez le dossier `custom_components/gardena_smart_system` dans votre dossier `config/custom_components/`
2. Redémarrez Home Assistant
3. Allez dans **Configuration** > **Intégrations**
4. Cliquez sur **+ Ajouter une intégration**
5. Recherchez **Gardena Smart System**
6. Entrez vos identifiants API

### Configuration

Vous aurez besoin de :
- **Client ID** : Votre clé d'application Gardena
- **Client Secret** : Votre secret d'application Gardena

Ces identifiants peuvent être obtenus via le [portail développeur Gardena](https://developer.husqvarnagroup.cloud/).

## 🔧 Architecture technique

### Structure des fichiers

```
custom_components/gardena_smart_system/
├── __init__.py              # Point d'entrée principal
├── config_flow.py           # Flux de configuration UI
├── const.py                 # Constantes de l'intégration
├── coordinator.py           # Coordinateur de données
├── gardena_client.py        # Client API Gardena
├── lawn_mower.py           # Entités tondeuses
├── sensor.py               # Entités capteurs
├── binary_sensor.py        # Entités capteurs binaires
├── switch.py               # Entités interrupteurs
├── valve.py                # Entités vannes
├── manifest.json           # Métadonnées de l'intégration
├── strings.json            # Chaînes de traduction
├── services.yaml           # Services personnalisés
└── translations/           # Traductions
```

### Composants principaux

#### Coordinateur (`coordinator.py`)
- Gère la synchronisation des données avec l'API
- Met à jour automatiquement les entités
- Gère les erreurs et la reconnexion

#### Client API (`gardena_client.py`)
- Communication avec l'API Gardena v2
- Authentification OAuth2
- Gestion des requêtes HTTP

#### Entités
- Chaque type d'appareil a sa propre entité
- Utilisation des patterns modernes Home Assistant
- Support des fonctionnalités spécifiques

## 🧪 Tests

### Exécution des tests

```bash
# Installer les dépendances de test
pip install pytest pytest-asyncio

# Exécuter les tests
pytest custom_components/gardena_smart_system/test_init.py -v
```

### Tests disponibles

- **Configuration** : Test du flux de configuration
- **Authentification** : Test des identifiants invalides
- **Installation** : Test de l'installation de l'intégration
- **Désinstallation** : Test de la désinstallation

## 🔄 Mise à jour

Pour mettre à jour vers la v2 :

1. Sauvegardez votre configuration actuelle
2. Désinstallez l'ancienne version
3. Installez la nouvelle version
4. Reconfigurez l'intégration

## 🐛 Dépannage

### Problèmes courants

**Erreur d'authentification**
- Vérifiez vos identifiants API
- Assurez-vous que votre compte a accès à l'API v2

**Aucun appareil détecté**
- Vérifiez que vos appareils sont connectés au Smart System
- Assurez-vous qu'ils sont visibles dans l'app Gardena

**Entités non disponibles**
- Vérifiez la connexion Internet
- Consultez les logs Home Assistant pour plus de détails

### Logs

Activez les logs détaillés dans `configuration.yaml` :

```yaml
logger:
  default: info
  logs:
    custom_components.gardena_smart_system: debug
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité
3. Ajoutez des tests pour votre code
4. Soumettez une pull request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🔗 Liens utiles

- [API Gardena Smart System v2](https://developer.husqvarnagroup.cloud/)
- [Documentation Home Assistant](https://developers.home-assistant.io/)
- [Guide des intégrations](https://developers.home-assistant.io/docs/creating_integration_manifest/) 