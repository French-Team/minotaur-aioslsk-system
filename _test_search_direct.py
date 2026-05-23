#!/usr/bin/env python
"""
Test de recherche Soulseek — diagnostic autonome sans interface Qt.

Se connecte à Soulseek en utilisant les credentials stockés, lance une
recherche, attend les résultats, et affiche tout ce qui se passe avec
des timestamps précis.

Usage :
    python _test_search_direct.py                      # credentials app_config
    python _test_search_direct.py --new                 # nouveau compte aléatoire
    python _test_search_direct.py --query "techno"      # recherche personnalisée
    python _test_search_direct.py --wait 120            # attendre 120s max
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import secrets
import string
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Ajouter la racine du projet au PYTHONPATH ────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))


# ═════════════════════════════════════════════════════════════════
#  Configuration du logging
# ═════════════════════════════════════════════════════════════════

def _setup_logging(verbose: bool = False) -> None:
    """Configure le logging avec timestamps ISO et couleurs minimales."""
    fmt = "%(asctime)s.%(msecs)03d [%(levelname)-5s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, stream=sys.stdout)        # Réduire le bruit des logs internes aioslsk
    for noisy in (
        "aioslsk.network.connection",
        "aioslsk.network.network",
        "aioslsk.client",
        "async_upnp_client.traffic",
        "async_upnp_client.client",
        "aioslsk.search.manager",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger("[TEST-SEARCH]")


# ═════════════════════════════════════════════════════════════════
#  Chargement des credentials
# ═════════════════════════════════════════════════════════════════

def _load_credentials() -> tuple[str, str]:
    """Charge les credentials depuis app_config.json."""
    config_path = _HERE / "app_config.json"
    if not config_path.exists():
        logger.error("Fichier de config introuvable : %s", config_path)
        sys.exit(1)

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error("Erreur de parsing app_config.json : %s", e)
        sys.exit(1)

    username = data.get("reseau.nom_utilisateur", "")
    password = data.get("reseau.mot_de_passe", "")
    if not username or not password:
        logger.error("Aucun credentials trouvés dans app_config.json")
        sys.exit(1)

    return username, password


def _generate_account() -> tuple[str, str]:
    """Génère un compte aléatoire réaliste."""
    prenoms = ["Alex", "Ben", "Max", "Leo", "Jay", "Kim", "Sam", "Eli",
               "Tom", "Zoe", "Mia", "Noa", "Lou", "Amy", "Eden", "Sasha"]
    musiques = ["Electro", "Techno", "Wave", "Beats", "Bass", "Mix",
                "Groove", "Pulse", "Rhythm", "Sound", "Drop", "Loop",
                "Vibes", "Flow", "Trance", "Pop", "Rock", "Jazz"]

    username = f"{secrets.choice(prenoms)}{secrets.choice(musiques)}"
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return username, password


# ═════════════════════════════════════════════════════════════════
#  Statistiques de session
# ═════════════════════════════════════════════════════════════════

class SearchStats:
    """Collecte les statistiques de la session de test."""

    def __init__(self) -> None:
        self.results_received = 0
        self.peers_responded: set[str] = set()
        self.total_files = 0
        self.first_result_time: float | None = None
        self.last_result_time: float | None = None
        self.search_started: float | None = None

    @property
    def elapsed_to_first(self) -> float | None:
        if self.first_result_time is not None and self.search_started is not None:
            return self.first_result_time - self.search_started
        return None

    @property
    def elapsed_total(self) -> float | None:
        if self.last_result_time is not None and self.search_started is not None:
            return self.last_result_time - self.search_started
        return None

    def report(self, query: str) -> str:
        lines = [
            "═" * 60,
            f"  RAPPORT DE TEST — Recherche « {query} »",
            "═" * 60,
            f"  Résultats reçus         : {self.results_received} lots",
            f"  Pairs ayant répondu    : {len(self.peers_responded)}",
            f"  Fichiers total          : {self.total_files}",
        ]
        if self.elapsed_to_first is not None:
            lines.append(f"  Temps 1er résultat      : {self.elapsed_to_first:.1f}s")
        if self.elapsed_total is not None:
            lines.append(f"  Fenêtre totale          : {self.elapsed_total:.1f}s")
        if self.peers_responded:
            lines.append(f"  Pairs : {', '.join(sorted(self.peers_responded)[:10])}")
            if len(self.peers_responded) > 10:
                lines.append(f"    … et {len(self.peers_responded) - 10} autres")
        lines.append("═" * 60)
        return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════
#  Cœur du test
# ═════════════════════════════════════════════════════════════════

async def run_test(
    query: str,
    wait_seconds: int,
    new_account: bool,
    verbose: bool,
) -> int:
    """Point d'entrée principal — connexion, recherche, attente, rapport.

    Returns:
        Code de sortie (0 = résultats reçus, 1 = timeout, 2 = erreur).
    """
    # Validation de la requête
    if not query or not query.strip():
        logger.error("❌ Requête vide — impossible de lancer la recherche")
        return 2
    query = query.strip()

    # ── 1. Credentials ────────────────────────────────────────
    if new_account:
        username, password = _generate_account()
        logger.info("🔑 Nouveau compte généré : %s / %s", username, password)
    else:
        username, password = _load_credentials()
        logger.info("🔑 Credentials chargés : %s", username)

    # ── 2. Imports aioslsk (après PYTHONPATH) ────────────────
    from aioslsk.client import SoulSeekClient
    from aioslsk.events import (
        PrivateMessageEvent,
        RoomListEvent,
        RoomMessageEvent,
        SearchResultEvent,
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
        SharedDirectorySettingEntry,
        SharesSettings,
        TransferLimitSettings,
        TransfersSettings,
        UpnpSettings,
        UserInfoSettings,
        UsersSettings,
    )
    from aioslsk.shares.model import DirectoryShareMode

    # ── 3. Construction des Settings ──────────────────────────
    logger.info("⚙️  Construction des paramètres…")

    settings = Settings(
        credentials=CredentialsSettings(
            username=username,
            password=password,
            info=UserInfoSettings(
                description="",
                picture=None,
            ),
        ),
        network=NetworkSettings(
            server=ServerSettings(
                hostname="server.slsknet.org",
                port=2416,
                reconnect=ReconnectSettings(auto=False, timeout=10),
            ),
            listening=ListeningSettings(
                port=60010,    # port alternatif pour éviter conflit avec l'app principale
                obfuscated_port=60011,
            ),
            peer=PeerSettings(
                obfuscate=False,
                connect_mode=PeerConnectMode.RACE,
            ),
            limits=NetworkLimitSettings(
                upload_speed_kbps=0,
                download_speed_kbps=0,
            ),
            upnp=UpnpSettings(enabled=False),
        ),
        shares=SharesSettings(
            scan_on_start=False,
        ),
        searches=SearchSettings(
            receive=SearchReceiveSettings(max_results=100, store_amount=500),
            send=SearchSendSettings(store_results=False),
        ),
        transfers=TransfersSettings(
            limits=TransferLimitSettings(upload_slots=2),
        ),
        debug=DebugSettings(),
    )

    # ── 4. Création du client ─────────────────────────────────
    client = SoulSeekClient(settings)
    stats = SearchStats()

    # ── 5. Enregistrement des écouteurs d'événements ──────────
    logger.info("🔌 Enregistrement des écouteurs…")

    stop_event = asyncio.Event()

    def on_search_result(evt: SearchResultEvent) -> None:
        now = time.monotonic()
        # stats est muté (pas rebind) — pas besoin de nonlocal

        query_text = getattr(evt.query, "query", "?")
        ticket = getattr(evt.query, "ticket", "?")
        username_peer = getattr(evt.result, "username", "?")
        shared = getattr(evt.result, "shared_items", [])
        n_files = len(shared) if shared else 0

        stats.results_received += 1
        stats.total_files += n_files
        stats.peers_responded.add(username_peer)

        if stats.first_result_time is None:
            stats.first_result_time = now

        stats.last_result_time = now

        has_free = getattr(evt.result, "has_free_slots", False)
        slots_str = "🟢" if has_free else "🔴"
        queue_length = getattr(evt.result, "queue_length", "?")
        avg_speed = getattr(evt.result, "avg_speed", 0)
        speed_str = f"{avg_speed / 1000:.0f} KB/s" if avg_speed else "?"

        # Aperçu des fichiers
        preview = ""
        if shared and n_files > 0:
            exts: dict[str, int] = {}
            sample_files: list[str] = []
            for f in shared[:3]:
                name = getattr(f, "filename", "?").split("\\")[-1].split("/")[-1]
                ext = getattr(f, "extension", "").lower()
                exts[ext] = exts.get(ext, 0) + 1
                sample_files.append(name)
            if len(shared) > 3:
                sample_files.append("…")
            preview = f"  ex: {', '.join(sample_files)}"
            ext_summary = ", ".join(f".{e} ({c})" for e, c in sorted(exts.items()))
            if ext_summary:
                preview += f"  [{ext_summary}]"

        logger.info(
            "📥 [RÉSULTAT #%d] ticket=%s | %s | %d fichier(s) | slots=%s | file=%s | %s\n%s",
            stats.results_received,
            ticket,
            username_peer,
            n_files,
            slots_str,
            queue_length,
            speed_str,
            preview,
        )

        # Si on a assez de résultats, on arrête
        if stats.results_received >= 20:
            logger.info("🛑 20 lots reçus — arrêt du test")
            stop_event.set()

    client.events.register(SearchResultEvent, on_search_result)

    def on_server_message(evt) -> None:
        logger.debug("📡 Message serveur reçu (%s)", type(evt).__name__)

    client.events.register(RoomListEvent, on_server_message)

    def on_private_message(evt: PrivateMessageEvent) -> None:
        logger.info("💬 Message privé de %s: %s", evt.username, evt.message[:80])

    client.events.register(PrivateMessageEvent, on_private_message)

    def on_room_message(evt: RoomMessageEvent) -> None:
        logger.debug("💬 [#%s] %s: %s", evt.room, evt.username, evt.message[:60])

    client.events.register(RoomMessageEvent, on_room_message)

    # ── 6. Connexion ──────────────────────────────────────────
    logger.info("🔗 Connexion au serveur %s:%s…",
                settings.network.server.hostname,
                settings.network.server.port)

    try:
        t0 = time.monotonic()
        await asyncio.wait_for(client.start(), timeout=30.0)
        logger.info("✅ client.start() OK en %.1fs", time.monotonic() - t0)

        t0 = time.monotonic()
        await asyncio.wait_for(client.login(), timeout=30.0)
        logger.info("✅ client.login() OK en %.1fs — connecté en tant que %s",
                    time.monotonic() - t0, username)

    except asyncio.TimeoutError:
        logger.error("⏱️  TIMEOUT connexion (30s) — serveur injoignable")
        await client.stop()
        return 2
    except Exception as e:
        logger.error("❌ Échec de connexion : %s", e, exc_info=verbose)
        await client.stop()
        return 2

    # ── 7. Petite pause pour laisser le réseau s'installer ────
    logger.info("⏳ Attente 3s pour stabilisation réseau…")
    await asyncio.sleep(3)

    # ── 8. Vérification de l'état du réseau ───────────────────
    try:
        parent = getattr(client, "distributed_parent", None)
        logger.info("🌐 Parent distribué : %s", parent)
    except Exception:
        pass

    # ── 9. Recherche ──────────────────────────────────────────
    logger.info("🔍 Lancement de la recherche « %s »…", query)
    stats.search_started = time.monotonic()

    try:
        request = await client.searches.search(query)
        logger.info("✅ Recherche lancée — ticket=%s | %d requête(s) active(s)",
                    request.ticket,
                    len(client.searches.requests))
    except Exception as e:
        logger.error("❌ Échec du lancement de la recherche : %s", e, exc_info=verbose)
        await client.stop()
        return 2

    # ── 10. Attente des résultats ─────────────────────────────
    logger.info("⏳ Attente des résultats (max %ds)…", wait_seconds)

    # Timer de progression
    async def _progress_ticker() -> None:
        for i in range(1, wait_seconds // 5 + 1):
            await asyncio.sleep(5)
            if stop_event.is_set():
                break
            elapsed = time.monotonic() - stats.search_started
            n_requests = len(client.searches.requests)
            logger.info(
                "⏳ … %ds écoulées | %d lot(s) reçu(s) | %d fichier(s) | %d pair(s) | %d requête(s)",
                int(elapsed),
                stats.results_received,
                stats.total_files,
                len(stats.peers_responded),
                n_requests,
            )

    ticker_task = asyncio.create_task(_progress_ticker())

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
    except asyncio.TimeoutError:
        logger.info("⏱️  Timeout d'attente atteint (%ds)", wait_seconds)
    finally:
        ticker_task.cancel()
        try:
            await ticker_task
        except asyncio.CancelledError:
            pass

    # ── 11. Rapport ───────────────────────────────────────────
    logger.info("\n%s", stats.report(query))

    # ── 12. Nettoyage ─────────────────────────────────────────
    logger.info("🧹 Nettoyage…")
    try:
        await client.stop()
        logger.info("✅ Client arrêté proprement")
    except Exception as e:
        logger.warning("⚠️  Erreur lors de l'arrêt : %s", e)

    if stats.results_received > 0:
        logger.info("✅ SUCCÈS — %d lots reçus en %.1fs",
                    stats.results_received,
                    stats.elapsed_total or 0)
        return 0
    else:
        logger.warning("⚠️  AUCUN RÉSULTAT reçu en %ds", wait_seconds)
        return 1


# ═════════════════════════════════════════════════════════════════
#  Point d'entrée CLI
# ═════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test de recherche Soulseek — diagnostic sans interface Qt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--query", default="trance",
                        help="Terme de recherche (défaut: trance)")
    parser.add_argument("--wait", type=int, default=60,
                        help="Durée max d'attente en secondes (défaut: 60)")
    parser.add_argument("--new", action="store_true",
                        help="Générer un nouveau compte au lieu d'utiliser les credentials stockés")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Logs DEBUG (inclut les traces réseau)")
    parser.add_argument("--list-events", action="store_true",
                        help="Affiche la liste des événements enregistrables du client")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.list_events:
        from aioslsk.events import SearchResultEvent, RoomListEvent, PrivateMessageEvent, RoomMessageEvent
        print("\nÉvénements utilisés :")
        print("  SearchResultEvent  → résultats de recherche")
        print("  RoomListEvent      → liste des salons")
        print("  PrivateMessageEvent → messages privés")
        print("  RoomMessageEvent   → messages de salon")
        print()
        return 0

    return asyncio.run(run_test(
        query=args.query,
        wait_seconds=args.wait,
        new_account=args.new,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    sys.exit(main())
