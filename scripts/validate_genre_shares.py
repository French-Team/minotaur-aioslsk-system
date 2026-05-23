"""
Validation script — Mode Genre : récupération des partages d'un client.

Teste le flux asynchrone complet sans interface Qt :
  1. Charger les credentials depuis app_config.json
  2. Se connecter à Soulseek
  3. Rejoindre des salons pour découvrir des clients
  4. 🔥 PING : filtrer les clients "actif & joignable" via GetUserStatusCommand (lots de 10)
  5. Envoyer PeerGetSharesCommand UNIQUEMENT aux clients qui ont répondu au ping
  6. Analyser l'arborescence des dossiers reçus
  7. Filtrer par genre (ex: "techno", "house")

Usage :
    python scripts/validate_genre_shares.py [--genre techno] [--username client_name]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Configuration du logging ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("[VALIDATE-GENRE]")

# Réduire le bruit aioslsk
logging.getLogger("aioslsk.network.connection").setLevel(logging.WARNING)
logging.getLogger("aioslsk.network.network").setLevel(logging.WARNING)
logging.getLogger("aioslsk.protocol").setLevel(logging.WARNING)

from aioslsk.client import SoulSeekClient
from aioslsk.commands import (
    PeerGetSharesCommand,
    JoinRoomCommand,
    GetRoomListCommand,
    GetUserStatusCommand,
)
from aioslsk.settings import (
    CredentialsSettings,
    DebugSettings,
    InterestsSettings,
    ListeningSettings,
    NetworkLimitSettings,
    NetworkSettings,
    PeerConnectMode,
    PeerSettings,
    ReconnectSettings,
    RoomsSettings,
    SearchReceiveSettings,
    SearchSendSettings,
    SearchSettings,
    ServerSettings,
    Settings,
    SharesSettings,
    TransferLimitSettings,
    TransfersSettings,
    UpnpSettings,
    UserInfoSettings,
    UsersSettings,
)


# ── Paramètres de ping (copiés du ClientsActifsService) ───────────
_LOT_PING = 10       # Nombre de clients pingés par lot
_DELAI_INTER_LOTS = 2.0  # Secondes entre deux lots


# ── Salons à rejoindre pour découvrir des clients ──────────────
_SALONS_POPULAIRES = [
    "Soulseek",
    "music",
    "techno",
    "electronic",
    "hiphop",
    "jazz",
    "metal",
]


# ── Parsing des arguments ─────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validation du Mode Genre — récupération des partages d'un client",
    )
    parser.add_argument(
        "--genre",
        default="techno",
        help="Genre à rechercher dans les dossiers (défaut: techno)",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Nom du client à interroger (par défaut: premier client actif & joignable)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Nombre max de dossiers matchés à afficher (défaut: 20)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout en secondes pour PeerGetSharesCommand (défaut: 60)",
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=10,
        help="Secondes d'attente après join pour peupler le UserManager (défaut: 10)",
    )
    parser.add_argument(
        "--ping-timeout",
        type=float,
        default=10.0,
        help="Timeout par ping GetUserStatusCommand en secondes (défaut: 10)",
    )
    return parser.parse_args()


# ── Chargement des credentials depuis app_config.json ─────────────

def _load_credentials() -> dict[str, str]:
    """Charge les credentials depuis app_config.json.

    Returns:
        Dictionnaire avec les clés ``username`` et ``password``.
    """
    config_path = Path("app_config.json")
    if not config_path.exists():
        logger.error(
            "Fichier app_config.json introuvable à la racine du projet.\n"
            "Lance d'abord l'application GUI pour générer/compléter la config."
        )
        sys.exit(1)

    raw = config_path.read_text(encoding="utf-8")
    config = json.loads(raw)

    username = config.get("reseau.nom_utilisateur", "")
    password = config.get("reseau.mot_de_passe", "")

    if not username or not password:
        logger.error(
            "Credentials vides dans app_config.json.\n"
            "Connecte-toi d'abord via l'interface graphique pour les sauvegarder."
        )
        sys.exit(1)

    logger.info("Credentials chargés depuis app_config.json : %s", username)
    return {"username": username, "password": password}


# ── Construction des Settings aioslsk ────────────────────────────

def _build_settings(username: str, password: str) -> Settings:
    """Construit une configuration aioslsk minimale pour la validation."""
    return Settings(
        credentials=CredentialsSettings(
            username=username,
            password=password,
            info=UserInfoSettings(
                description="Mode Genre validation script",
                picture=None,
            ),
        ),
        network=NetworkSettings(
            upnp=UpnpSettings(enabled=False),
            listening=ListeningSettings(port=60000, obfuscated_port=60001),
            peer=PeerSettings(obfuscate=False, connect_mode=PeerConnectMode.RACE),
            limits=NetworkLimitSettings(upload_speed_kbps=0, download_speed_kbps=0),
            server=ServerSettings(
                hostname="server.slsknet.org",
                port=2242,
                reconnect=ReconnectSettings(auto=False, timeout=10),
            ),
        ),
        rooms=RoomsSettings(auto_join=False, private_room_invites=False, favorites=set()),
        interests=InterestsSettings(liked=set(), hated=set()),
        searches=SearchSettings(
            receive=SearchReceiveSettings(max_results=100, store_amount=500),
            send=SearchSendSettings(store_results=False, request_timeout=0, wishlist_request_timeout=-1),
            wishlist=[],
        ),
        shares=SharesSettings(scan_on_start=False, download="", directories=[]),
        transfers=TransfersSettings(
            limits=TransferLimitSettings(upload_slots=2),
            report_interval=1.0,
        ),
        debug=DebugSettings(
            search_for_parent=False,
            ip_overrides={},
            log_connection_count=False,
        ),
        users=UsersSettings(friends=set(), blocked={}),
    )


# ── Rejoindre des salons pour découvrir des clients ─────────────

async def _rejoindre_salons(client: SoulSeekClient) -> int:
    """Rejoint des salons populaires pour que le UserManager se peuple.

    Args:
        client: Instance du client Soulseek.

    Returns:
        Nombre de salons rejoints avec succès.
    """
    logger.info("  Rejoindre des salons pour découvrir des clients…")

    try:
        result = await asyncio.wait_for(
            client.execute(GetRoomListCommand()),
            timeout=15.0,
        )
        if isinstance(result, (list, tuple)):
            rooms = [r.name if hasattr(r, "name") else str(r) for r in result]
        elif hasattr(result, "rooms"):
            rooms = [r.name if hasattr(r, "name") else str(r) for r in result.rooms]
        else:
            rooms = _SALONS_POPULAIRES
        logger.info("  📋 %d salons disponibles sur le serveur", len(rooms))
    except Exception:
        logger.info("  ⚠️  Impossible de lister les salons, utilisation des salons par défaut")
        rooms = _SALONS_POPULAIRES

    rejoints = 0
    for salon in rooms[:5]:
        try:
            await asyncio.wait_for(
                client.execute(JoinRoomCommand(salon)),
                timeout=10.0,
            )
            rejoints += 1
            logger.info("  ✅ Salon rejoint : #%s", salon)
        except Exception as e:
            logger.debug("  ⚠️  Impossible de rejoindre #%s : %s", salon, e)

    logger.info("  %d salon(s) rejoint(s) avec succès", rejoints)
    return rejoints


# ── Extraction des clients ONLINE ──────────────────────────────

def _get_online_users(client: SoulSeekClient, exclude: str = "") -> list[str]:
    """Retourne la liste des usernames ONLINE dans le UserManager (hors soi-même).

    Args:
        client: Instance du client Soulseek.
        exclude: Username à exclure (notre propre compte).

    Returns:
        Liste triée des usernames ONLINE (autre que nous-même).
    """
    if not client.users or not client.users.users:
        logger.warning("  Aucun utilisateur dans UserManager.")
        return []

    online = [
        name for name, user in client.users.users.items()
        if user.status.name == "ONLINE" and name.lower() != exclude.lower()
    ]
    online.sort(key=str.lower)
    logger.info("  Clients ONLINE (autres que soi) : %d", len(online))
    if online:
        logger.info("    → %s", ", ".join(online[:20]))
        if len(online) > 20:
            logger.info("    … et %d autres", len(online) - 20)
    return online


# ══════════════════════════════════════════════════════════════════
#  PHASE DE PING — Filtre les clients "actif & joignable"
# ══════════════════════════════════════════════════════════════════

async def _ping_par_lots(
    client: SoulSeekClient,
    candidats: list[str],
    ping_timeout: float,
) -> list[str]:
    """Pinge les clients par lots et retourne ceux qui ont répondu.

    Reproduit exactement le pattern de ``ClientsActifsService._ping_par_lots()`` :
    lots de ``_LOT_PING`` clients, ``_DELAI_INTER_LOTS`` secondes entre les lots,
    ``GetUserStatusCommand`` comme sonde de joignabilité.

    Args:
        client: Instance du client Soulseek connecté.
        candidats: Liste des usernames à pinger.
        ping_timeout: Timeout par ping (secondes).

    Returns:
        Liste des usernames qui ont répondu au ping (actif & joignable).
    """
    total = len(candidats)
    if total == 0:
        return []

    lots_total = (total - 1) // _LOT_PING + 1
    reponses: list[str] = []
    start_time = time.time()

    logger.info("━━━ Ping par lots (%d client(s), lots de %d) ━━━", total, _LOT_PING)

    for i in range(0, total, _LOT_PING):
        lot = candidats[i:i + _LOT_PING]
        num_lot = i // _LOT_PING + 1

        for username in lot:
            try:
                await asyncio.wait_for(
                    client.execute(GetUserStatusCommand(username)),
                    timeout=ping_timeout,
                )
                reponses.append(username)
                logger.info("  ✅ %s — joignable", username)
            except asyncio.TimeoutError:
                logger.debug("  ⏱️  %s — timeout (pas de réponse)", username)
            except Exception:
                logger.debug("  ❌ %s — non joignable (exception)", username)

        logger.info("  Lot %d/%d : %d/%d répondu(s)", num_lot, lots_total, len(reponses), total)

        # Pause entre les lots (sauf dernier)
        if i + _LOT_PING < total:
            await asyncio.sleep(_DELAI_INTER_LOTS)

    duree = time.time() - start_time
    logger.info("━━━ Ping terminé : %d/%d joignable(s) (durée=%.1fs) ━━━",
                len(reponses), total, duree)
    return reponses


# ── Affichage de l'arborescence ──────────────────────────────────

def _afficher_arborescence(dirs: list, genre: str, max_results: int) -> None:
    """Affiche l'arborescence des dossiers et le filtrage par genre.

    Args:
        dirs: Liste de DirectoryData (de UserSharesReplyEvent.directories)
        genre: Terme à rechercher (insensible à la casse)
        max_results: Nombre max de dossiers matchés à afficher
    """
    total = len(dirs)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("📂 Arborescence reçue : %d dossiers", total)

    # Échantillon des premiers dossiers
    logger.info("━━━ Échantillon (10 premiers) ━━━")
    for i, d in enumerate(dirs[:10]):
        nom = d.name if hasattr(d, "name") else str(d)
        nb_files = len(d.files) if hasattr(d, "files") else "?"
        logger.info("  📁 %s  (%s fichiers)", nom, nb_files)
    if total > 10:
        logger.info("  … et %d autres dossiers", total - 10)

    # Filtrage par genre
    genre_lower = genre.lower()
    matched = [
        d for d in dirs
        if hasattr(d, "name") and genre_lower in d.name.lower()
    ]

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🔍 Filtre par genre '%s' : %d dossier(s) matché(s)", genre, len(matched))

    if matched:
        logger.info("━━━ Dossiers matchés (max %d) ━━━", max_results)
        for d in matched[:max_results]:
            nom = d.name
            nb_files = len(d.files) if hasattr(d, "files") else 0
            logger.info("  ✅ %s  (%d fichier(s))", nom, nb_files)
            if nb_files > 0:
                for f in d.files[:5]:
                    fname = f.filename if hasattr(f, "filename") else str(f)
                    fsize = f.filesize if hasattr(f, "filesize") else "?"
                    logger.info("      📄 %s  (%s bytes)", fname, fsize)
                if nb_files > 5:
                    logger.info("      … et %d autres fichiers", nb_files - 5)

    if len(matched) > max_results:
        logger.info("  … et %d autres dossiers matchés (limité à %d)",
                     len(matched) - max_results, max_results)


# ══════════════════════════════════════════════════════════════════
#  CŒUR DU SCRIPT
# ══════════════════════════════════════════════════════════════════

async def main() -> None:
    """Point d'entrée asynchrone du script de validation."""
    args = _parse_args()
    creds = _load_credentials()
    mon_username = creds["username"]

    logger.info("=" * 60)
    logger.info("🔬 VALIDATION MODE GENRE")
    logger.info("=" * 60)
    logger.info("Genre ciblé   : %s", args.genre)
    logger.info("Notre user    : %s", mon_username)
    logger.info("Serveur       : server.slsknet.org:2242")

    client = SoulSeekClient(_build_settings(mon_username, creds["password"]))

    try:
        # ── Étape 1 : Connexion ─────────────────────────────────
        logger.info("")
        logger.info("📡 Étape 1 — Connexion à Soulseek…")
        await client.start()
        logger.info("  ✅ client.start() — sockets ouvertes")
        await client.login()
        logger.info("  ✅ client.login() — authentifié en tant que %s", mon_username)

        # ── Étape 2 : Découverte clients via salons ──────────────
        logger.info("")
        logger.info("👥 Étape 2 — Découverte de clients via les salons…")
        await _rejoindre_salons(client)

        # ── Étape 3 : Attente peuplement UserManager ─────────────
        logger.info("")
        logger.info("⏳ Étape 3 — Attente de %d s pour peupler le UserManager…", args.wait_time)
        await asyncio.sleep(args.wait_time)

        candidats = _get_online_users(client, exclude=mon_username)
        if not candidats:
            logger.warning("  ⚠️  Aucun client ONLINE trouvé (autre que nous-même).")
            logger.info("  Clients connus (tous statuts) : %s",
                        ", ".join(sorted(client.users.users.keys())[:20]))
            return

        # ── Étape 4 : PING — Filtrer les actifs & joignables ────
        logger.info("")
        logger.info("🔥 Étape 4 — Ping des clients pour identifier les actifs & joignables…")
        logger.info("  (GetUserStatusCommand par lots de %d, délai %.1fs entre lots)",
                     _LOT_PING, _DELAI_INTER_LOTS)

        joignables = await _ping_par_lots(client, candidats, args.ping_timeout)
        if not joignables:
            logger.error("  ❌ Aucun client joignable parmi les %d ONLINE.", len(candidats))
            logger.info("  ℹ️  C'est normal sur Soulseek : peu de clients acceptent les")
            logger.info("      connexions P2P entrantes. Laisse tourner plus longtemps,")
            logger.info("      ou relance plus tard quand plus de clients seront disponibles.")
            return

        logger.info("")
        logger.info("  ✅ %d client(s) actif(s) & joignable(s) : %s",
                     len(joignables), ", ".join(joignables))

        # ── Étape 5 : PeerGetSharesCommand (uniquement joignables) ─
        logger.info("")
        logger.info("📂 Étape 5 — Récupération des partages (PeerGetSharesCommand)")
        logger.info("  Cible : %s (et jusqu'à 2 autres si timeout)",
                     joignables[0])

        # Si --username est spécifié, on le met en tête de liste
        cibles = list(joignables)
        if args.username and args.username in cibles:
            cibles.remove(args.username)
            cibles.insert(0, args.username)

        result = None
        tentatives = 0
        for candidat in cibles[:5]:  # max 5 tentatives
            tentatives += 1
            logger.info("")
            logger.info("  ── Tentative %d : PeerGetSharesCommand('%s') (timeout=%ds) ──",
                         tentatives, candidat, args.timeout)

            try:
                result = await asyncio.wait_for(
                    client.execute(PeerGetSharesCommand(candidat)),
                    timeout=float(args.timeout),
                )
                logger.info("  ✅ Réponse reçue de '%s' !", candidat)
                break
            except asyncio.TimeoutError:
                logger.warning("  ⏱️  Timeout (%ds) — '%s' n'a pas répondu au partage",
                                args.timeout, candidat)
                logger.info("      (pourtant joignable au ping — le partage est peut-être")
                logger.info("       volumineux ou le client est lent)")
            except Exception as e:
                logger.warning("  ❌ Erreur pour '%s' : %s", candidat, e)

        if result is None:
            logger.error("")
            logger.error("  ❌ Aucun client n'a envoyé ses partages après %d tentative(s) sur des clients JOIGNABLES.",
                         tentatives)
            logger.info("  ℹ️  Le ping a confirmé que ces clients sont joignables,")
            logger.info("      mais le transfert des partages peut prendre plus de temps.")
            return

        # ── Étape 6 : Analyse du résultat ────────────────────────
        logger.info("")

        if isinstance(result, tuple) and len(result) == 2:
            directories, locked_directories = result
        elif hasattr(result, "directories"):
            directories = result.directories
            locked_directories = getattr(result, "locked_directories", [])
        else:
            logger.warning("  ⚠️  Format de résultat inattendu : %s", type(result).__name__)
            logger.info("  Contenu brut : %s", result)
            return

        # ── Étape 7 : Affichage & filtrage ──────────────────────
        _afficher_arborescence(
            directories,
            genre=args.genre,
            max_results=args.max_results,
        )

        if locked_directories:
            logger.info("")
            logger.info("🔒 %d dossier(s) verrouillé(s) ignoré(s)", len(locked_directories))

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ VALIDATION TERMINÉE")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("Erreur générale : %s", e)
        logger.exception("Détails :")
    finally:
        logger.info("")
        logger.info("🔌 Déconnexion…")
        try:
            await asyncio.wait_for(client.stop(), timeout=5.0)
            logger.info("  ✅ Déconnecté")
        except Exception as e:
            logger.warning("  ⚠️  Erreur lors de la déconnexion : %s", e)


if __name__ == "__main__":
    asyncio.run(main())
