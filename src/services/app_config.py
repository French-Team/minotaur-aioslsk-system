"""
Gestionnaire de configuration persistante de l'application.

Stocke les préférences dans un fichier JSON au côté du projet (``app_config.json``).
Offre une API simple : ``get`` / ``set`` / ``reset`` avec valeurs par défaut.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Fichier de configuration ─────────────────────────────────────
_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "app_config.json"

# ── Valeurs par défaut ───────────────────────────────────────────
_DEFAULTS: dict[str, Any] = {
    # ═══ Général ═══
    "general.langue": "fr",
    "general.demarrage_minimise": False,

    # ═══ Réseau ═══
    "reseau.upnp": False,
    "reseau.port_ecoute": 60000,
    "reseau.proxy": "",

    # ═══ Recherche ═══
    "recherche.filtre_min_resultats": 0,
    "recherche.mots_exclus": "",

    # ═══ Téléchargement ═══
    "telechargement.dossier_destination": "~/Downloads/Soulseek",
    "telechargement.limite_vitesse": 0,       # 0 = illimité
    "telechargement.max_simultanes": 3,
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
    _ensure_loaded()
    return _config.get(key, _DEFAULTS.get(key, default))


def set(key: str, value: Any) -> None:
    """Définit une valeur et sauvegarde immédiatement."""
    _ensure_loaded()
    _config[key] = value
    _save()


def reset(key: str | None = None) -> None:
    """Remet une clé (ou toutes les clés) à leurs valeurs par défaut."""
    _ensure_loaded()
    if key is None:
        _config.clear()
        _config.update(_DEFAULTS.copy())
    elif key in _config:
        _config[key] = _DEFAULTS.get(key)
    else:
        logger.warning("Tentative de reset d'une clé inconnue : %s", key)
    _save()


def dictionary() -> dict[str, Any]:
    """Retourne une copie du dictionnaire de configuration complet."""
    _ensure_loaded()
    return dict(_config)


# ═════════════════════════════════════════════════════════════════
#  Interne — chargement / sauvegarde
# ═════════════════════════════════════════════════════════════════


def _ensure_loaded() -> None:
    global _config
    if _config is None:
        _config = _load()


def _load() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        logger.info("Aucun fichier de config trouvé, création avec les valeurs par défaut.")
        data = _DEFAULTS.copy()
        _write_file(data)
        return data

    try:
        raw = _CONFIG_FILE.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(raw)

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
