"""
Traducteur d'erreurs aioslsk en langage naturel.

Catégorise chaque exception en trois niveaux de sévérité :
  - INFO    : Erreur normale du réseau P2P, sans conséquence
  - WARNING : Problème de configuration ou temporaire
  - ERROR   : Bug potentiel de notre code
"""

from __future__ import annotations

import asyncio
from enum import Enum

import aioslsk.exceptions as aioslsk_exc


class Severite(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCES = "SUCCES"


def traduire(exception: Exception) -> tuple[str, Severite]:
    """
    Traduit une exception aioslsk (ou générique) en message lisible.

    Retourne (message, sévérité).
    """
    # --- Erreurs asyncio / réseau bas niveau ---
    if isinstance(exception, asyncio.TimeoutError):
        return (
            "⏱ Timeout — un peer n'a pas répondu à temps, "
            "c'est normal sur le réseau P2P (l'utilisateur est peut-être hors ligne)",
            Severite.INFO,
        )
    if isinstance(exception, asyncio.CancelledError):
        return (
            "⏹ Tâche annulée — connexion interrompue proprement, rien à signaler",
            Severite.INFO,
        )

    # --- Erreurs de connexion directe / indirecte ---
    if isinstance(exception, aioslsk_exc.ConnectionFailedError):
        addr = str(exception).split(":")[0]
        return (
            f"🔴 Connexion P2P impossible vers {addr} — "
            "l'utilisateur est hors ligne, son firewall bloque, "
            "ou il n'est pas joignable (normal en P2P)",
            Severite.INFO,
        )

    if isinstance(exception, aioslsk_exc.PeerConnectionError):
        msg = str(exception)
        if "timed out" in msg.casefold():
            return (
                "⏱ Connexion indirecte interrompue (timeout) — "
                "le pair n'a pas répondu à temps, réessaie automatiquement",
                Severite.INFO,
            )
        return (
            "🔴 Connexion indirecte échouée — "
            "le pair n'est pas joignable par le serveur Soulseek "
            "(normal quand l'utilisateur se déconnecte)",
            Severite.INFO,
        )

    if isinstance(exception, aioslsk_exc.NoSuchUserError):
        return (
            "👤 Utilisateur introuvable — le pseudo n'existe pas sur Soulseek (vérifie l'orthographe)",
            Severite.WARNING,
        )

    # --- Erreurs de transfert / fichiers ---
    if isinstance(exception, aioslsk_exc.FileNotFoundError):
        return (
            "📁 Fichier introuvable sur le serveur distant — le fichier a été supprimé ou déplacé par l'utilisateur",
            Severite.INFO,
        )

    if isinstance(exception, aioslsk_exc.FileNotSharedError):
        return (
            "🚫 Fichier non partagé — l'utilisateur a retiré ce fichier de ses partages",
            Severite.INFO,
        )

    if isinstance(exception, aioslsk_exc.TransferException):
        return (
            "⬇ Erreur de transfert — "
            "la connexion de téléchargement a été interrompue "
            "(normal, reprise automatique possible)",
            Severite.INFO,
        )

    # --- Erreurs d'authentification ---
    if isinstance(exception, aioslsk_exc.AuthenticationError):
        return (
            "🔑 Échec d'authentification — nom d'utilisateur ou mot de passe incorrect",
            Severite.WARNING,
        )

    # --- Erreurs d'écoute / UPnP ---
    if isinstance(exception, aioslsk_exc.ListeningConnectionFailedError):
        return (
            "🔌 Impossible d'ouvrir le port d'écoute — "
            "vérifie qu'aucun autre client Soulseek ne tourne déjà, "
            "ou configure le port manuellement",
            Severite.WARNING,
        )

    # --- Erreurs réseau génériques ---
    if isinstance(exception, aioslsk_exc.NetworkError):
        return (
            "🌐 Erreur réseau — problème de connexion avec le serveur Soulseek (vérifie ta connexion Internet)",
            Severite.WARNING,
        )

    # --- Erreurs de session invalide ---
    if isinstance(exception, aioslsk_exc.InvalidSessionError):
        return (
            "🔄 Session invalide — la session a expiré ou a été réinitialisée, reconnecte-toi",
            Severite.WARNING,
        )

    # --- Erreurs d'état interne (souvent = bug) ---
    if isinstance(exception, aioslsk_exc.InvalidStateTransition):
        return (
            "❌ BUG INTERNE — transition d'état invalide dans aioslsk (signale ce bug au développeur)",
            Severite.ERROR,
        )

    # --- Erreurs de sérialisation (bug probable) ---
    if isinstance(exception, aioslsk_exc.MessageSerializationError):
        return (
            "❌ BUG — erreur de sérialisation d'un message Soulseek (signale ce bug au développeur)",
            Severite.ERROR,
        )

    if isinstance(exception, aioslsk_exc.MessageDeserializationError):
        return (
            "❌ BUG — erreur de désérialisation d'un message Soulseek "
            "(signale ce bug au développeur avec le log complet)",
            Severite.ERROR,
        )

    if isinstance(exception, aioslsk_exc.UnknownMessageError):
        return (
            "📡 Message inconnu reçu du serveur — normal si les versions du protocole diffèrent, sans conséquence",
            Severite.INFO,
        )

    # --- Erreurs de partage de dossiers ---
    if isinstance(exception, aioslsk_exc.SharedDirectoryError):
        return (
            "📂 Erreur de dossier partagé — vérifie que les dossiers partagés existent et sont accessibles",
            Severite.WARNING,
        )

    # --- Erreurs de placement de requête ---
    if isinstance(exception, aioslsk_exc.RequestPlaceFailedError):
        return (
            "📋 Échec de placement de requête — le serveur n'a pas pu placer ta demande de recherche, réessaie",
            Severite.INFO,
        )

    # --- Erreurs de lecture / écriture ---
    if isinstance(exception, aioslsk_exc.ConnectionReadError):
        return (
            "📖 Erreur de lecture sur une connexion P2P — le pair a fermé la connexion (normal)",
            Severite.INFO,
        )

    if isinstance(exception, aioslsk_exc.ConnectionWriteError):
        return (
            "✏ Erreur d'écriture sur une connexion P2P — le pair n'est plus joignable (normal)",
            Severite.INFO,
        )

    # --- Fallback pour toute autre exception ---
    return (
        f"⚠ Exception non catégorisée : {type(exception).__name__}: {exception}",
        Severite.ERROR if isinstance(exception, aioslsk_exc.AioSlskException) else Severite.WARNING,
    )


def emoji_pour(severite: Severite) -> str:
    return {
        Severite.INFO: "ℹ️",
        Severite.WARNING: "⚠️",
        Severite.ERROR: "🚨",
        Severite.SUCCES: "✅",
    }[severite]


def afficher(exception: Exception) -> str:
    """Retourne une chaîne prête à logger : [SÉVÉRITÉ] message."""
    message, severite = traduire(exception)
    return f"[{severite.value}] {message}"
