"""Service asynchrone pour le Mode Genre (Athéna).

Itère sur les clients Arès, récupère les arborescences partagées via
``PeerGetSharesCommand``, filtre par genre musical, et retourne
les dossiers matchés avec leurs fichiers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from src.services.connexion_manager import ConnexionManager

logger = logging.getLogger("[GENRE-SERVICE]")

# ── Chemins ──────────────────────────────────────────────────────
_GENRES_JSON = Path("data/genres.json")


# ── Structure de résultat ────────────────────────────────────────


@dataclass
class GenreResultat:
    """Résultat d'un dossier matché par genre chez un client.

    Attributs
    ---------
    username : str
        Nom du client Soulseek.
    chemin : str
        Chemin complet du dossier matché (ex: ``Music/Techno/``).
    fichiers : list[dict]
        Liste des fichiers dans ce dossier (clés : filename, filesize, extension).
    nb_fichiers_audio : int
        Nombre de fichiers audio (mp3/flac/ogg) dans le dossier.
    """

    username: str
    chemin: str
    fichiers: list[dict[str, Any]] = field(default_factory=list)
    nb_fichiers_audio: int = 0
    statut_client: str = ""


# ── Service ──────────────────────────────────────────────────────


class GenreService(QObject):
    """Service asynchrone pour le Mode Genre.

    Boucle dédiée : itère sur les clients Arès, récupère les
    arborescences via ``PeerGetSharesCommand``, filtre par genre,
    et émet des signaux à chaque dossier matché.

    Signaux
    -------
    resultat_recu(GenreResultat)
        Émis pour chaque dossier matché chez un client.
    termine()
        Émis quand la boucle est terminée (ou arrêtée).
    erreur(str)
        Émis quand une erreur survient.
    progression(str, int, int)
        Émis pour suivre la progression : username, dossiers_matchés, total_dossiers.
    """

    resultat_recu = Signal(object)  # GenreResultat
    termine = Signal()
    erreur = Signal(str)
    progression = Signal(str, int, int)  # username, matchés, total

    # Extensions audio autorisées
    _EXTENSIONS_AUDIO = {"mp3", "flac", "ogg", "wav", "aac", "wma", "m4a", "ape", "opus"}

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._en_cours = False
        self._connexion_manager: ConnexionManager | None = None
        self._timeout_arborescence = 15.0  # secondes
        self._delai_entre_clients = 0.5  # 500ms rate limiting
        self._genres_data: list[dict] = []
        self._aliases: dict[str, str] = {}

        # Charger la liste des genres au démarrage
        self._charger_genres()

    # ── Chargement des genres ────────────────────────────────────

    def _charger_genres(self) -> None:
        """Charge la liste des genres depuis ``data/genres.json``."""
        try:
            if not _GENRES_JSON.exists():
                logger.warning("Fichier genres.json introuvable : %s", _GENRES_JSON)
                return
            data = json.loads(_GENRES_JSON.read_text(encoding="utf-8"))
            self._genres_data = data.get("genres", [])
            self._aliases = data.get("aliases", {})
            logger.info("Genres chargés : %d genres, %d alias", len(self._genres_data), len(self._aliases))
        except Exception as e:
            logger.error("Erreur chargement genres.json : %s", e)
            self._genres_data = []
            self._aliases = {}

    @property
    def genres_disponibles(self) -> list[dict]:
        """Liste des genres disponibles (lecture seule)."""
        return list(self._genres_data)

    def obtenir_genre(self, genre_id: str) -> dict | None:
        """Retourne les infos d'un genre par son ID."""
        for g in self._genres_data:
            if g["id"] == genre_id:
                return dict(g)
        # Chercher dans les alias
        resolved = self._aliases.get(genre_id.lower())
        if resolved:
            for g in self._genres_data:
                if g["id"] == resolved:
                    return dict(g)
        return None

    # ── API publique ─────────────────────────────────────────────

    def set_connexion_manager(self, manager: ConnexionManager) -> None:
        """Injecte le connexion_manager pour l'accès au client Soulseek."""
        self._connexion_manager = manager

    def lancer(self, genre_id: str) -> None:
        """Lance la boucle de recherche Genre sur Arès.

        Paramètres
        ----------
        genre_id : str
            Identifiant du genre (ex: ``"techno"``, ``"house"``).
        """
        if self._en_cours:
            logger.warning("GenreService déjà en cours — ignoré")
            return
        if self._connexion_manager is None:
            self.erreur.emit("❌ Gestionnaire de connexion non initialisé")
            return

        genre_info = self.obtenir_genre(genre_id)
        if not genre_info:
            self.erreur.emit(f"❌ Genre « {genre_id} » inconnu")
            return

        self._en_cours = True
        logger.info("GenreService: lancement pour « %s »", genre_info["name"])

        # Lancer la boucle asynchrone via le thread asyncio de ConnexionManager
        self._connexion_manager.run_coro(
            self._boucle_genre(genre_info)
        )

    def arreter(self) -> None:
        """Arrête la boucle en cours."""
        if not self._en_cours:
            return
        self._en_cours = False
        logger.info("GenreService: arrêt demandé")
        self.termine.emit()

    @property
    def en_cours(self) -> bool:
        return self._en_cours

    # ── Boucle asynchrone ────────────────────────────────────────

    async def _boucle_genre(self, genre_info: dict) -> None:
        """Boucle principale de recherche Genre.

        Itère sur les clients Arès, récupère les arborescences,
        filtre par genre, et émet les résultats.

        Paramètres
        ----------
        genre_info : dict
            Informations du genre (id, name, keywords, exclude).
        """
        keywords = [k.lower() for k in genre_info.get("keywords", [genre_info["id"]])]
        exclude = [e.lower() for e in genre_info.get("exclude", [])]
        genre_name = genre_info["name"]

        logger.info("Boucle Genre « %s » démarrée — mots-clés: %s", genre_name, keywords)

        try:
            # Récupérer le client Soulseek
            client = self._connexion_manager.client if self._connexion_manager else None
            if client is None:
                self.erreur.emit("❌ Client Soulseek non disponible")
                self._en_cours = False
                self.termine.emit()
                return

            # Récupérer les clients Arès (depuis le service clients actifs)
            from aioslsk.commands import PeerGetSharesCommand

            # On utilise les users du client (UserManager) comme source
            # car il contient les clients connectés (rooms, etc.)
            users = getattr(client, "users", None)
            if users is None or not hasattr(users, "users"):
                logger.warning("UserManager non disponible — utilisation des users du client")
                # Fallback: essayer client.user_manager ou autre
                all_users = {}
            else:
                all_users = dict(users.users) if hasattr(users, "users") else {}

            # Filtrer les clients ONLINE
            cibles = [
                username
                for username, user in all_users.items()
                if hasattr(user, "status") and user.status is not None
                and hasattr(user.status, "name") and user.status.name == "ONLINE"
            ]

            if not cibles:
                logger.warning("Aucun client ONLINE trouvé — tentative avec GetUserStatusCommand")
                # Fallback: on essaie de pinger via les commands
                cibles = list(all_users.keys())[:20]

            logger.info("GenreService: %d clients ONLINE ciblés", len(cibles))

            if not cibles:
                self.erreur.emit("👥 Aucun client actif trouvé — rejoignez des salons d'abord")
                self._en_cours = False
                self.termine.emit()
                return

            # Parcourir les clients
            total_match = 0
            for i, username in enumerate(cibles):
                if not self._en_cours:
                    break

                logger.debug("GenreService: traitement de %s (%d/%d)", username, i + 1, len(cibles))

                try:
                    # Étape 1 : Récupérer l'arborescence du client
                    result = await asyncio.wait_for(
                        client.execute(PeerGetSharesCommand(username)),
                        timeout=self._timeout_arborescence,
                    )

                    # Le résultat est (directories, locked_directories)
                    if isinstance(result, tuple) and len(result) >= 1:
                        directories = result[0]
                    elif hasattr(result, "directories"):
                        directories = result.directories
                    else:
                        logger.warning("Format de résultat inattendu pour %s: %s", username, type(result))
                        continue

                    if not directories:
                        continue

                    # Étape 2 : Filtrer les dossiers qui matchent le genre
                    dossiers_match = self._filtrer_par_genre(directories, keywords, exclude)

                    self.progression.emit(username, len(dossiers_match), len(directories))

                    if not dossiers_match:
                        continue

                    # Étape 3 : Pour chaque dossier matché, préparer le résultat
                    for chemin, fichiers in dossiers_match:
                        if not self._en_cours:
                            break

                        fichiers_data = []
                        nb_audio = 0
                        for f in fichiers:
                            fname = getattr(f, "filename", "") or ""
                            fsize = getattr(f, "filesize", 0) or 0
                            ext = self._extraire_extension(fname)
                            is_audio = ext in self._EXTENSIONS_AUDIO
                            if is_audio:
                                nb_audio += 1
                            fichiers_data.append({
                                "filename": fname,
                                "filesize": fsize,
                                "extension": ext,
                            })

                        resultat = GenreResultat(
                            username=username,
                            chemin=chemin,
                            fichiers=fichiers_data,
                            nb_fichiers_audio=nb_audio,
                            statut_client="ONLINE",
                        )
                        self.resultat_recu.emit(resultat)
                        total_match += 1

                except asyncio.TimeoutError:
                    logger.warning("Timeout arborescence pour %s (%.1fs)", username, self._timeout_arborescence)
                    continue
                except Exception as e:
                    logger.warning("Erreur pour %s: %s", username, e)
                    continue

                # Rate limiting
                if i < len(cibles) - 1:
                    await asyncio.sleep(self._delai_entre_clients)

            logger.info("GenreService: boucle terminée — %d dossiers matchés pour « %s »", total_match, genre_name)

        except Exception as e:
            logger.error("Erreur dans la boucle Genre: %s", e, exc_info=True)
            self.erreur.emit(f"❌ Erreur: {str(e)[:100]}")
        finally:
            self._en_cours = False
            self.termine.emit()

    # ── Filtrage ─────────────────────────────────────────────────

    def _filtrer_par_genre(
        self,
        directories: list,
        keywords: list[str],
        exclude: list[str],
    ) -> list[tuple[str, list]]:
        """Filtre une liste de DirectoryData pour ne garder que ceux qui
        matchent les mots-clés du genre.

        Paramètres
        ----------
        directories : list
            Liste d'objets DirectoryData (aioslsk).
        keywords : list[str]
            Mots-clés à rechercher dans les chemins (minuscules).
        exclude : list[str]
            Mots à exclure des chemins.

        Retourne
        --------
        list[tuple[str, list]]
            Liste de (chemin, fichiers) pour les dossiers matchés.
        """
        resultats: list[tuple[str, list]] = []

        for d in directories:
            chemin = getattr(d, "name", "") or ""
            if not chemin:
                continue

            chemin_lower = chemin.lower()

            # Vérifier les mots d'exclusion
            if any(mot in chemin_lower for mot in exclude):
                continue

            # Vérifier les mots-clés
            match = any(keyword in chemin_lower for keyword in keywords)
            if not match:
                continue

            fichiers = getattr(d, "files", []) or []
            resultats.append((chemin, fichiers))

        return resultats

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extraire_extension(filename: str) -> str:
        """Extrait l'extension d'un fichier depuis son chemin complet."""
        if not filename:
            return ""
        basename = filename.replace("\\", "/").rstrip("/").split("/")[-1]
        if "." in basename:
            return basename.rsplit(".", 1)[-1].lower()
        return ""

    @staticmethod
    def _normaliser_chemin(path: str) -> str:
        """Normalise un chemin : bas de casse, sans accents, sans séparateurs doubles."""
        normalized = path.lower().replace("\\", "/")
        # Supprimer les accents de base
        normalized = normalized.replace("é", "e").replace("è", "e").replace("ê", "e")
        normalized = normalized.replace("à", "a").replace("â", "a")
        normalized = normalized.replace("ù", "u").replace("û", "u")
        normalized = normalized.replace("ô", "o").replace("ö", "o")
        normalized = normalized.replace("ï", "i").replace("î", "i")
        normalized = normalized.replace("ç", "c")
        # Nettoyer les séparateurs
        normalized = re.sub(r"/+", "/", normalized)
        return normalized.strip("/")
