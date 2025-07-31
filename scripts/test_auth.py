#!/usr/bin/env python3
"""Script de test pour l'authentification Gardena Smart System."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.gardena_smart_system.auth import GardenaAuthError, GardenaAuthenticationManager
from custom_components.gardena_smart_system.gardena_client import GardenaAPIError, GardenaSmartSystemClient


# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_authentication():
    """Test complet de l'authentification."""
    print("🔐 Test d'authentification Gardena Smart System")
    print("=" * 50)
    
    # Récupération des identifiants depuis les variables d'environnement
    client_id = os.getenv("GARDENA_CLIENT_ID")
    client_secret = os.getenv("GARDENA_CLIENT_SECRET")
    api_key = os.getenv("GARDENA_API_KEY")
    
    if not client_id or not client_secret:
        print("❌ Erreur: Variables d'environnement manquantes")
        print("   Définissez GARDENA_CLIENT_ID et GARDENA_CLIENT_SECRET")
        return False
    
    print(f"✅ Client ID: {client_id[:8]}...")
    print(f"✅ Client Secret: {'*' * len(client_secret)}")
    if api_key:
        print(f"✅ API Key: {api_key[:8]}...")
    else:
        print("ℹ️  API Key: Non définie (optionnel)")
    
    print("\n🚀 Test du gestionnaire d'authentification...")
    
    try:
        # Test du gestionnaire d'authentification
        auth_manager = GardenaAuthenticationManager(client_id, client_secret, api_key)
        
        # Test d'authentification initiale
        print("   📡 Authentification initiale...")
        token = await auth_manager.authenticate()
        print(f"   ✅ Token obtenu: {token[:20]}...")
        
        # Test de validation du token
        print("   🔍 Validation du token...")
        is_valid = auth_manager._is_token_valid()
        print(f"   ✅ Token valide: {is_valid}")
        
        # Test des headers d'authentification
        print("   📋 Headers d'authentification...")
        headers = auth_manager.get_auth_headers()
        print(f"   ✅ Headers générés: {list(headers.keys())}")
        
        print("\n🚀 Test du client API...")
        
        # Test du client API
        client = GardenaSmartSystemClient(client_id, client_secret, api_key)
        
        # Test de récupération des locations
        print("   📍 Récupération des locations...")
        locations = await client.get_locations()
        print(f"   ✅ {len(locations)} location(s) trouvée(s)")
        
        if locations:
            location_id = locations[0]["id"]
            location_name = locations[0].get("attributes", {}).get("name", "Sans nom")
            print(f"   📍 Location: {location_name} ({location_id})")
            
            # Test de récupération des détails de la location
            print("   🔍 Détails de la location...")
            location_data = await client.get_location(location_id)
            devices = location_data.get("included", [])
            print(f"   ✅ {len(devices)} appareil(s) trouvé(s)")
            
            # Affichage des types d'appareils
            device_types = {}
            for device in devices:
                device_type = device.get("type", "UNKNOWN")
                device_types[device_type] = device_types.get(device_type, 0) + 1
            
            print("   📊 Types d'appareils:")
            for device_type, count in device_types.items():
                print(f"      - {device_type}: {count}")
        
        # Test de création d'URL WebSocket
        print("   🔌 Test WebSocket...")
        try:
            websocket_data = await client.create_websocket_url(location_id)
            print("   ✅ URL WebSocket créée avec succès")
        except Exception as e:
            print(f"   ⚠️  Erreur WebSocket: {e}")
        
        # Nettoyage
        await client.close()
        await auth_manager.close()
        
        print("\n🎉 Tous les tests d'authentification ont réussi!")
        return True
        
    except GardenaAuthError as e:
        print(f"\n❌ Erreur d'authentification: {e}")
        if e.status_code:
            print(f"   Code d'erreur: {e.status_code}")
        if e.response_data:
            print(f"   Données de réponse: {e.response_data}")
        return False
        
    except GardenaAPIError as e:
        print(f"\n❌ Erreur API: {e}")
        if e.status_code:
            print(f"   Code d'erreur: {e.status_code}")
        if e.response_data:
            print(f"   Données de réponse: {e.response_data}")
        return False
        
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        logger.exception("Erreur détaillée:")
        return False


async def test_error_scenarios():
    """Test des scénarios d'erreur."""
    print("\n🧪 Test des scénarios d'erreur...")
    print("=" * 50)
    
    # Test avec des identifiants invalides
    print("🔍 Test avec identifiants invalides...")
    try:
        auth_manager = GardenaAuthenticationManager("invalid", "invalid")
        await auth_manager.authenticate()
        print("   ❌ Erreur: L'authentification aurait dû échouer")
        return False
    except GardenaAuthError as e:
        print(f"   ✅ Erreur d'authentification attendue: {e}")
    
    # Test avec des identifiants vides
    print("🔍 Test avec identifiants vides...")
    try:
        auth_manager = GardenaAuthenticationManager("", "")
        await auth_manager.authenticate()
        print("   ❌ Erreur: L'authentification aurait dû échouer")
        return False
    except Exception as e:
        print(f"   ✅ Erreur attendue: {e}")
    
    print("✅ Tous les tests d'erreur ont réussi!")
    return True


async def main():
    """Fonction principale."""
    print("🧪 Script de test d'authentification Gardena Smart System")
    print("=" * 60)
    
    # Test principal
    auth_success = await test_authentication()
    
    # Test des scénarios d'erreur
    error_success = await test_error_scenarios()
    
    print("\n" + "=" * 60)
    if auth_success and error_success:
        print("🎉 Tous les tests ont réussi!")
        return 0
    else:
        print("❌ Certains tests ont échoué.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur fatale: {e}")
        logger.exception("Erreur détaillée:")
        sys.exit(1) 