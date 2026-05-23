from __future__ import annotations

import asyncio
import json
import logging

from aioslsk.client import SoulSeekClient
from aioslsk.events import (
    PrivateMessageEvent,
    RoomListEvent,
    RoomMessageEvent,
    SearchResultEvent,
    TransferAddedEvent,
    TransferProgressEvent,
    TransferRemovedEvent,
)
from aioslsk.network.network import ListeningConnectionErrorMode
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
    WishlistSettingEntry,
)
from aioslsk.shares.model import DirectoryShareMode
from aioslsk.transfer.model import TransferDirection
from aioslsk.user.model import BlockingFlag
from PySide6.QtCore import QObject, Signal

from src.services import app_config
from src.services.event_bus import EventBus

logger = logging.getLogger("[SOULSEEK]")


def _parse_interests(raw: str) -> set[str]:
    """Convertit une chaîne séparée par des virgules en ensemble d'intérêts.

    Nettoie les espaces et ignore les éléments vides.

    Args:
        raw: Chaîne brute séparée par des virgules (ex: "Rock, Jazz, Soul").

    Returns:
        Ensemble des intérêts nettoyés.
    """
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


# ── Parsing des utilisateurs bloqués ──────────────────────────────


def _parse_blocked(raw: str) -> dict[str, BlockingFlag]:
    """Convertit une chaîne CSV ("user1, user2") en dict[str, BlockingFlag].

    Chaque utilisateur est bloqué complètement (tous les flags).
    """
    if not raw or not raw.strip():
        return {}
    parts = raw.split(",")
    all_flags = (
        BlockingFlag.PRIVATE_MESSAGES
        | BlockingFlag.ROOM_MESSAGES
        | BlockingFlag.SEARCHES
        | BlockingFlag.SHARES
        | BlockingFlag.INFO
        | BlockingFlag.UPLOADS
    )
    return {
        item.strip(): all_flags for item in parts if item.strip()
    }  # ── Parsing de la wishlist ──────────────────────────────────────


def _parse_wishlist(raw: str) -> list["WishlistSettingEntry"]:
    """Convertit une chaîne JSON ou CSV en liste WishlistSettingEntry.

    Format JSON : ``[{"query": "...", "enabled": true}, ...]``
    Format CSV (fallback) : ``"query1, query2"``

    Chaque entrée est activée par défaut en format CSV.
    """
    if not raw or not raw.strip():
        return []

    # Format JSON structuré
    if raw.strip().startswith("["):
        try:
            items: list[dict] = json.loads(raw)
            return [
                WishlistSettingEntry(query=item["query"], enabled=item.get("enabled", True))
                for item in items
                if item.get("query", "").strip()
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Fallback CSV (backward compatibility)
    parts = raw.split(",")
    return [WishlistSettingEntry(query=item.strip(), enabled=True) for item in parts if item.strip()]


# ── Parsing des dossiers partagés ────────────────────────────────


def _parse_share_directory(
    chemin: str,
    mode_raw: str,
    utilisateurs_raw: str,
) -> SharedDirectorySettingEntry | None:
    """Construit un SharedDirectorySettingEntry à partir des valeurs de config.

    Retourne None si le chemin est vide (dossier non configuré).
    """
    if not chemin:
        return None
    try:
        mode = DirectoryShareMode(mode_raw)
    except ValueError:
        mode = DirectoryShareMode.EVERYONE
    utilisateurs = [u.strip() for u in utilisateurs_raw.split(",") if u.strip()] if utilisateurs_raw else []
    return SharedDirectorySettingEntry(
        path=chemin,
        share_mode=mode,
        users=utilisateurs,
    )


# ── Lecture de la photo de profil ────────────────────────────────


def _read_profile_picture(path: str) -> bytes | None:
    """Lit un fichier image et retourne son contenu en bytes.

    Args:
        path: Chemin du fichier image.

    Returns:
        Les bytes de l'image, ou None si le chemin est vide ou le fichier
        est introuvable.
    """
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.warning("[SOULSEEK] Impossible de lire la photo de profil '%s': %s", path, e)
        return None


class SoulseekService(QObject):
    """
    Service wrapper autour de SoulSeekClient.
    Gère le cycle de vie du client et expose les événements
    via des signaux Qt.
    """

    # Signaux — Recherche
    search_result_received = Signal(object)  # SearchResultEvent

    # Signaux — Transfers
    transfer_added = Signal(object)  # TransferAddedEvent
    transfer_removed = Signal(object)  # TransferRemovedEvent
    transfer_progress = Signal(object)  # TransferProgressEvent

    # Signaux — Messages
    private_message_received = Signal(object)  # PrivateMessageEvent
    room_message_received = Signal(object)  # RoomMessageEvent

    # Signaux — Connexion
    connection_changed = Signal(bool)  # True = connecté, False = déconnecté
    room_list_received = Signal(object)  # RoomListEvent

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._client: SoulSeekClient | None = None
        self._username: str = ""
        self._running: bool = False
        self._transfer_states: set[str] = set()  # IDs de transferts déjà signalés à l'EventBus
        # ⚠️  Références fortes pour les callbacks enregistrés dans l'EventBus aioslsk
        #     L'EventBus utilise weakref.ref() en interne. Les lambdas anonymes
        #     seraient garbage collectées sans ces références fortes !
        self._event_callbacks: list = []

    @property
    def client(self) -> SoulSeekClient | None:
        """Retourne l'instance du client, ou None si pas connecté."""
        return self._client

    @property
    def is_connected(self) -> bool:
        """Le client est-il connecté ?"""
        return self._client is not None and self._running

    @property
    def username(self) -> str:
        return self._username

    # pyrefly: ignore [bad-override]
    async def connect(self, username: str, password: str) -> str:
        """
        Connecte au serveur Soulseek.

        Args:
            username: Nom d'utilisateur Soulseek.
            password: Mot de passe Soulseek.

        Returns:
            Message de statut.

        Raises:
            Exception: Si la connexion échoue.
        """
        if self.is_connected:
            return f"Déjà connecté en tant que {self._username}"

        # Nettoyer l'ancien client s'il existe (après un échec ou une connexion partielle)
        if self._client is not None:
            logger.warning("[SOULSEEK] Nettoyage d'un ancien client avant reconnect")
            try:
                await asyncio.wait_for(self._client.stop(), timeout=5.0)
            except Exception as e:
                logger.warning("[SOULSEEK] Erreur lors du nettoyage du client précédent: %s", e)
            self._client = None

        # Lire la configuration utilisateur
        upnp_enabled = bool(app_config.get("reseau.upnp", False))
        scan_on_start = bool(app_config.get("general.scan_on_start", True))
        description_profil = app_config.get("general.description_profil", "")
        photo_profil_path = app_config.get("general.photo_profil", "")
        interets_aimes = _parse_interests(app_config.get("general.interets_aimes", ""))
        interets_detestes = _parse_interests(app_config.get("general.interets_detestes", ""))
        nb_resultats_max = int(app_config.get("recherche.nb_resultats_max", 100))
        nb_max_memoire = int(app_config.get("recherche.nb_max_memoire", 500))
        stocker_resultats = bool(app_config.get("recherche.stocker_resultats", True))
        timeout_requete = int(app_config.get("recherche.timeout_requete", 0))
        slots_upload = int(app_config.get("telechargement.slots_upload", 2))
        dossier_destination = app_config.get("telechargement.dossier_destination", "")
        intervalle_rapport = int(app_config.get("telechargement.intervalle_rapport", 250))
        liste_amis = app_config.get("utilisateurs.liste_amis", "")
        liste_bloques = app_config.get("utilisateurs.liste_bloques", "")
        auto_join_salons = bool(app_config.get("salons.auto_join", True))
        invitations_privees = bool(app_config.get("salons.invitations_privees", True))
        timeout_souhaits = int(app_config.get("recherche.timeout_souhaits", -1))
        souhaits_raw = app_config.get("recherche.souhaits", "")
        salons_favoris = app_config.get("salons.favoris", "")
        port_ecoute = int(app_config.get("reseau.port_ecoute", 60000))
        port_obfusque = int(app_config.get("reseau.port_obfusque", 60001))
        obfuscation_p2p = bool(app_config.get("reseau.obfuscation_p2p", False))
        mode_connexion_raw = app_config.get("reseau.mode_connexion_peer", "race")
        mode_connexion = PeerConnectMode(mode_connexion_raw)
        limite_upload = int(app_config.get("reseau.limite_upload_kbps", 0))
        limite_download = int(app_config.get("reseau.limite_download_kbps", 0))
        reconnexion_auto = bool(app_config.get("reseau.reconnexion_auto", False))
        reconnexion_timeout = int(app_config.get("reseau.reconnexion_timeout", 10))
        hote_serveur = app_config.get("reseau.hote_serveur", "server.slsknet.org")
        port_serveur = int(app_config.get("reseau.port_serveur", 2416))
        mode_erreur_raw = app_config.get("reseau.mode_erreur_ecoute", "clear")
        mode_erreur = ListeningConnectionErrorMode(mode_erreur_raw)
        duree_bail_upnp = int(app_config.get("reseau.duree_bail_upnp", 21600))
        intervalle_upnp = int(app_config.get("reseau.intervalle_upnp", 600))
        timeout_upnp = int(app_config.get("reseau.timeout_upnp", 10))
        dossier_1_chemin = app_config.get("partages.dossier_1_chemin", "")
        dossier_1_mode = app_config.get("partages.dossier_1_mode", "everyone")
        dossier_1_utilisateurs = app_config.get("partages.dossier_1_utilisateurs", "")
        dossier_2_chemin = app_config.get("partages.dossier_2_chemin", "")
        dossier_2_mode = app_config.get("partages.dossier_2_mode", "everyone")
        dossier_2_utilisateurs = app_config.get("partages.dossier_2_utilisateurs", "")

        dossiers_partages = list(
            filter(
                None,
                [
                    _parse_share_directory(dossier_1_chemin, dossier_1_mode, dossier_1_utilisateurs),
                    _parse_share_directory(dossier_2_chemin, dossier_2_mode, dossier_2_utilisateurs),
                ],
            )
        )

        settings = Settings(
            credentials=CredentialsSettings(
                username=username,
                password=password,
                info=UserInfoSettings(
                    description=description_profil,
                    picture=_read_profile_picture(photo_profil_path),
                ),
            ),
            network=NetworkSettings(
                upnp=UpnpSettings(
                    enabled=upnp_enabled,
                    lease_duration=duree_bail_upnp,
                    check_interval=intervalle_upnp,
                    search_timeout=timeout_upnp,
                ),
                listening=ListeningSettings(
                    port=port_ecoute,
                    obfuscated_port=port_obfusque,
                    error_mode=mode_erreur,
                ),
                peer=PeerSettings(
                    obfuscate=obfuscation_p2p,
                    connect_mode=mode_connexion,
                ),
                limits=NetworkLimitSettings(
                    upload_speed_kbps=limite_upload,
                    download_speed_kbps=limite_download,
                ),
                server=ServerSettings(
                    hostname=hote_serveur,
                    port=port_serveur,
                    reconnect=ReconnectSettings(
                        auto=reconnexion_auto,
                        timeout=reconnexion_timeout,
                    ),
                ),
            ),
            rooms=RoomsSettings(
                auto_join=auto_join_salons,
                private_room_invites=invitations_privees,
                favorites=_parse_interests(salons_favoris),
            ),
            interests=InterestsSettings(
                liked=interets_aimes,
                hated=interets_detestes,
            ),
            searches=SearchSettings(
                receive=SearchReceiveSettings(
                    max_results=nb_resultats_max,
                    store_amount=nb_max_memoire,
                ),
                send=SearchSendSettings(
                    store_results=stocker_resultats,
                    request_timeout=timeout_requete,
                    wishlist_request_timeout=timeout_souhaits,
                ),
                wishlist=_parse_wishlist(souhaits_raw),
            ),
            shares=SharesSettings(
                scan_on_start=scan_on_start,
                download=dossier_destination,
                directories=dossiers_partages,
            ),
            transfers=TransfersSettings(
                limits=TransferLimitSettings(
                    upload_slots=slots_upload,
                ),
                report_interval=intervalle_rapport / 1000.0,
            ),
            debug=DebugSettings(
                search_for_parent=app_config.get("debug.search_for_parent", False),
                ip_overrides=(
                    json.loads(app_config.get("debug.ip_overrides", "{}"))
                    if app_config.get("debug.ip_overrides", "{}")
                    else {}
                ),
                log_connection_count=app_config.get("debug.log_connection_count", False),
            ),
            users=UsersSettings(
                friends=_parse_interests(liste_amis),
                blocked=_parse_blocked(liste_bloques),
            ),
        )

        self._client = SoulSeekClient(settings)
        self._username = username

        # ── Enregistrement des écouteurs d'événements ────────────
        # ⚠️  IMPORTANT : stocker chaque callback dans self._event_callbacks
        #     pour éviter que le GC ne les collecte (l'EventBus aioslsk
        #     utilise weakref.ref en interne !)
        self._event_callbacks.clear()

        _on_search_result = lambda evt: (
            logger.info(
                "[DIAG] SearchResultEvent reçu — query='%s' | ticket=%s | username='%s' | %d fichiers",
                evt.query.query if hasattr(evt.query, 'query') else '?',
                evt.query.ticket if hasattr(evt.query, 'ticket') else '?',
                evt.result.username if hasattr(evt.result, 'username') else '?',
                len(evt.result.shared_items) if hasattr(evt.result, 'shared_items') else 0,
            ),
            self.search_result_received.emit(evt),
        )
        self._client.events.register(SearchResultEvent, _on_search_result)
        self._event_callbacks.append(_on_search_result)

        _on_transfer_added = lambda evt: (
            self.transfer_added.emit(evt),
            EventBus().emit_event(
                severity="INFO",
                category="transfert",
                title="Transfert ajouté",
                message=f"{evt.transfer.direction} {evt.transfer.remote_path} — {evt.transfer.username}",
                source="SoulseekService",
            ),
        )
        self._client.events.register(TransferAddedEvent, _on_transfer_added)
        self._event_callbacks.append(_on_transfer_added)

        _on_transfer_removed = lambda evt: (
            self.transfer_removed.emit(evt),
            EventBus().emit_event(
                severity="INFO",
                category="transfert",
                title="Transfert terminé",
                message=f"{evt.transfer.direction} {evt.transfer.remote_path} — {evt.transfer.username}",
                source="SoulseekService",
            ),
        )
        self._client.events.register(TransferRemovedEvent, _on_transfer_removed)
        self._event_callbacks.append(_on_transfer_removed)

        _on_transfer_progress = lambda evt: self._on_transfer_progress(evt)
        self._client.events.register(TransferProgressEvent, _on_transfer_progress)
        self._event_callbacks.append(_on_transfer_progress)

        _on_private_message = lambda evt: self.private_message_received.emit(evt)
        self._client.events.register(PrivateMessageEvent, _on_private_message)
        self._event_callbacks.append(_on_private_message)

        _on_room_message = lambda evt: self.room_message_received.emit(evt)
        self._client.events.register(RoomMessageEvent, _on_room_message)
        self._event_callbacks.append(_on_room_message)

        _on_room_list = lambda evt: self.room_list_received.emit(evt)
        self._client.events.register(RoomListEvent, _on_room_list)
        self._event_callbacks.append(_on_room_list)

        logger.info("[SOULSEEK] Tous les écouteurs d'événements ont été enregistrés avec succès (%d callbacks).", len(self._event_callbacks))
        try:
            logger.info("[SOULSEEK] Démarrage des sockets et de la boucle réseau du client avec client.start()...")
            await self._client.start()
            logger.info("[SOULSEEK] [SUCCÈS] client.start() complété. Connexions d'écoute et d'envoi ouvertes.")
            
            logger.info("[SOULSEEK] Envoi du paquet d'authentification et attente du handshake avec client.login()...")
            await self._client.login()
            logger.info("[SOULSEEK] [SUCCÈS] client.login() complété, authentification acceptée par le serveur Soulseek !")
            
            self._running = True
            logger.info("[SOULSEEK] Émission du signal connection_changed(True)...")
            self.connection_changed.emit(True)
            logger.info("[SOULSEEK] Connecté à Soulseek en tant que %s", username)
            return f"Connecté à Soulseek en tant que {username}"
        except Exception as e:
            self._running = False
            logger.warning("[SOULSEEK] Échec de connexion rencontré. Émission de connection_changed(False)...")
            self.connection_changed.emit(False)
            logger.info("[SOULSEEK] Nettoyage et arrêt des sockets du client...")
            await self._cleanup_client()
            logger.error("[SOULSEEK] Échec de connexion: %s", e)
            raise

    def _on_transfer_progress(self, evt: "TransferProgressEvent") -> None:
        """Gère la progression d'un transfert — n'émet à l'EventBus que début et fin."""
        self.transfer_progress.emit(evt)
        updates = getattr(evt, "updates", None)
        if not updates:
            return
        for transfer, prev_snap, cur_snap in updates:
            # Construire une clé unique pour ce transfert
            key = f"{transfer.username}:{transfer.remote_path}:{transfer.direction}"
            current_bytes = getattr(cur_snap, "bytes_transfered", 0) if cur_snap else 0
            total_bytes = getattr(transfer, "filesize", 0)
            if current_bytes <= 0 or (total_bytes > 0 and current_bytes >= total_bytes):
                # Début ou fin de transfert
                is_start = current_bytes <= 0
                title = "Transfert démarré" if is_start else "Transfert terminé"
                EventBus().emit_event(
                    severity="INFO",
                    category="transfert",
                    title=title,
                    message=f"{transfer.direction} {transfer.remote_path} — {transfer.username}",
                    source="SoulseekService",
                )
                if not is_start:
                    self._transfer_states.discard(key)
                else:
                    self._transfer_states.add(key)

    # pyrefly: ignore [bad-override]
    async def disconnect(self) -> str:
        """
        Déconnecte du serveur Soulseek.

        Returns:
            Message de statut.
        """
        if not self.is_connected:
            return "Pas de connexion active"

        self._running = False
        self.connection_changed.emit(False)
        await self._cleanup_client()
        logger.info("[SOULSEEK] Déconnecté de Soulseek")
        return "Déconnecté de Soulseek"

    async def _cleanup_client(self) -> None:
        """Nettoie le client."""
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception as e:
                logger.warning("[SOULSEEK] Erreur lors du cleanup du client: %s", e)
            self._client = None

    # ── Contrôle des transferts ────────────────────────────────────────────

    def pause_transfer(self, username: str, remote_path: str) -> None:
        """Met en pause un téléchargement (fire-and-forget)."""
        if not self.is_connected or self._client is None:
            return
        transfer = self._client.transfers.find_transfer(username, remote_path, TransferDirection.DOWNLOAD)
        if transfer:
            asyncio.ensure_future(self._client.transfers.pause(transfer))
            logger.debug("[SOULSEEK] Transfert mis en pause: %s / %s", username, remote_path)

    def resume_transfer(self, username: str, remote_path: str) -> None:
        """Reprend un téléchargement (fire-and-forget).

        Appelle download() qui relance le transfert s'il existe déjà.
        """
        if not self.is_connected or self._client is None:
            return
        asyncio.ensure_future(self._client.transfers.download(username, remote_path, paused=False))
        logger.debug("[SOULSEEK] Transfert relancé: %s / %s", username, remote_path)

    def abort_transfer(self, username: str, remote_path: str) -> None:
        """Annule/abandonne un téléchargement (fire-and-forget)."""
        if not self.is_connected or self._client is None:
            return
        transfer = self._client.transfers.find_transfer(username, remote_path, TransferDirection.DOWNLOAD)
        if transfer:
            asyncio.ensure_future(self._client.transfers.abort(transfer))
            logger.debug("[SOULSEEK] Transfert annulé: %s / %s", username, remote_path)


# Instance globale partagée
soulseek_service = SoulseekService()
