"""
Gestionnaire de configuration persistante de l'application.

Stocke les préférences dans un fichier JSON au côté du projet (``app_config.json``).
Offre une API simple : ``get`` / ``set`` / ``reset`` avec valeurs par défaut.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Fichier de configuration ─────────────────────────────────────
_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "app_config.json"

# ── Valeurs par défaut ───────────────────────────────────────────
_DEFAULTS: dict[str, Any] = {
    # ═══ Général ═══
    "general.scan_on_start": True,  # Scanner les partages au démarrage
    "general.description_profil": "",  # Description du profil utilisateur
    "general.photo_profil": "",  # Chemin vers la photo de profil
    "general.interets_aimes": "",  # Centres d'intérêt appréciés (séparés par des virgules)
    "general.interets_detestes": "",  # Centres d'intérêt détestés (séparés par des virgules)
    "general.connexion_automatique": False,  # Connexion automatique au démarrage
    # ═══ Réseau ═══
    "reseau.nom_utilisateur": "",  # Nom d'utilisateur Soulseek (pour reconnexion auto)
    "reseau.mot_de_passe": "",  # Mot de passe Soulseek (pour reconnexion auto)
    "reseau.upnp": False,
    "reseau.port_ecoute": 60000,
    "reseau.port_obfusque": 60001,
    "reseau.obfuscation_p2p": False,
    "reseau.mode_connexion_peer": "race",
    "reseau.limite_upload_kbps": 0,
    "reseau.limite_download_kbps": 0,
    "reseau.reconnexion_auto": False,
    "reseau.reconnexion_timeout": 10,
    "reseau.hote_serveur": "server.slsknet.org",  # Hôte du serveur Soulseek
    "reseau.port_serveur": 2416,  # Port du serveur Soulseek
    "reseau.mode_erreur_ecoute": "clear",  # Mode d'erreur d'écoute (clear|any|all)
    "reseau.duree_bail_upnp": 21600,  # Durée de bail UPnP (secondes)
    "reseau.intervalle_upnp": 600,  # Intervalle de vérification UPnP (secondes)
    "reseau.timeout_upnp": 10,  # Timeout de découverte UPnP (secondes)
    # ═══ Recherche ═══
    "recherche.nb_resultats_max": 100,  # Nombre maximum de résultats par recherche
    "recherche.nb_max_memoire": 500,  # Nombre maximum de résultats stockés en mémoire
    "recherche.stocker_resultats": True,  # Stocker les résultats de recherche localement
    "recherche.timeout_requete": 0,  # Timeout des requêtes de recherche (0 = pas de timeout)
    "recherche.timeout_souhaits": -1,  # Timeout des requêtes de souhaits (-1 = désactivé)
    "recherche.souhaits": "",  # Souhaits de recherche (séparés par des virgules)
    # ═══ Téléchargement ═══
    "telechargement.slots_upload": 2,  # Slots d'upload simultanés
    "telechargement.dossier_destination": "",  # Dossier de destination des téléchargements
    "telechargement.intervalle_rapport": 250,  # Intervalle de rapport de progression (ms)
    # ═══ Utilisateurs ═══
    "utilisateurs.liste_amis": "",  # Liste d'amis (séparés par des virgules)
    "utilisateurs.liste_bloques": "",  # Utilisateurs bloqués (séparés par des virgules)
    # ═══ Partages ═══
    "partages.dossier_1_chemin": "",  # Chemin du 1er dossier partagé
    "partages.dossier_1_mode": "everyone",  # Mode de partage du 1er dossier (everyone|friends|users)
    "partages.dossier_1_utilisateurs": "",  # Utilisateurs autorisés pour le 1er dossier (séparés par des virgules)
    "partages.dossier_2_chemin": "",  # Chemin du 2e dossier partagé
    "partages.dossier_2_mode": "everyone",  # Mode de partage du 2e dossier (everyone|friends|users)
    "partages.dossier_2_utilisateurs": "",  # Utilisateurs autorisés pour le 2e dossier (séparés par des virgules)
    # ═══ Salons ═══
    "salons.auto_join": True,  # Rejoindre les salons automatiquement au démarrage
    "salons.invitations_privees": True,  # Accepter les invitations aux salons privés
    "salons.favoris": "",  # Salons favoris à rejoindre automatiquement (séparés par des virgules)
    # ═══ Debug ═══
    "debug.search_for_parent": False,  # Rechercher un parent lors de la connexion
    "debug.ip_overrides": "",  # Surcharges IP (format JSON: {"username": "ip"})
    "debug.log_connection_count": False,  # Journaliser le nombre de connexions
}

# ── Singleton interne ────────────────────────────────────────────
_config: dict[str, Any] | None = None


# ═════════════════════════════════════════════════════════════════
#  API publique
# ═════════════════════════════════════════════════════════════════


def get(key: str, default: Any = None) -> Any:
    """Récupère une valeur de configuration.

    ``key`` utilise la notation pointée : ``"reseau.upnp"``
    Si la clé n'existe pas, retourne la valeur par défaut du fichier
    ou ``default`` si fourni.
    """
    config = _ensure_loaded()
    return config.get(key, _DEFAULTS.get(key, default))


def set(key: str, value: Any) -> None:
    """Définit une valeur et sauvegarde immédiatement."""
    config = _ensure_loaded()
    config[key] = value
    _save()


def reset(key: str | None = None) -> None:
    """Remet une clé (ou toutes les clés) à leurs valeurs par défaut."""
    config = _ensure_loaded()
    if key is None:
        config.clear()
        config.update(_DEFAULTS.copy())
    elif key in config:
        config[key] = _DEFAULTS.get(key)
    else:
        logger.warning("Tentative de reset d'une clé inconnue : %s", key)
    _save()


def dictionary() -> dict[str, Any]:
    """Retourne une copie du dictionnaire de configuration complet."""
    config = _ensure_loaded()
    return dict(config)


# ═════════════════════════════════════════════════════════════════
#  Interne — chargement / sauvegarde
# ═════════════════════════════════════════════════════════════════


def _ensure_loaded() -> dict[str, Any]:
    global _config
    if _config is None:
        _config = _load()
    assert _config is not None
    return _config


def _load() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        logger.info("Aucun fichier de config trouvé, création avec les valeurs par défaut.")
        data = _DEFAULTS.copy()
        _write_file(data)
        return data

    try:
        raw = _CONFIG_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)

        # Fusionner avec les défauts pour les clés manquantes (mise à jour)
        merged = _DEFAULTS.copy()
        merged.update(data)
        return merged

    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Impossible de lire %s : %s. Utilisation des valeurs par défaut.", _CONFIG_FILE, exc)
        return _DEFAULTS.copy()


def _save() -> None:
    if _config is None:
        return
    try:
        _write_file(_config)
    except OSError as exc:
        logger.error("Impossible d'écrire la configuration : %s", exc)


def _write_file(data: dict[str, Any]) -> None:
    # Écriture atomique : fichier temporaire → rename
    tmp = _CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_CONFIG_FILE)
