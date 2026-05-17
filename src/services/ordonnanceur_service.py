"""
Service Ordonnanceur — Analyse et organisation des fichiers audio.

Responsabilités :
- Scan des dossiers pour trouver les fichiers audio
- Extraction des métadonnées via mutagen (artiste, album, titre, piste, année)
- Parsing des noms de fichiers par regex (fallback si tags absents)
- Détection des doublons (nom+taille → hash SHA256)
- Génération de motifs de renommage et de classement
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3

from src.config import settings

logger = logging.getLogger(__name__)


# ── Corbeille dédiée ──────────────────────────────────────────────────


def deplacer_vers_corbeille(chemin: Path) -> Path:
    """Déplace un fichier vers la corbeille dédiée au lieu de le supprimer définitivement.

    La corbeille est un dossier configurable (``corbeille_dir`` dans les settings).
    Pour éviter les collisions de noms, un horodatage est préfixé au nom du fichier.

    Args:
        chemin: Chemin du fichier à déplacer.

    Returns:
        Le chemin de destination dans la corbeille.

    Raises:
        FileNotFoundError: Si le fichier source n'existe pas.
        OSError: Si le déplacement échoue (permissions, disque, etc.).
    """
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    corbeille = settings.corbeille_dir
    corbeille.mkdir(parents=True, exist_ok=True)

    # Préfixe horodaté pour éviter les collisions
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dest = corbeille / f"{timestamp}_{chemin.name}"

    # Si le nom existe déjà, ajouter un suffixe incrémental
    compteur = 1
    while dest.exists():
        dest = corbeille / f"{timestamp}_{chemin.stem}_{compteur}{chemin.suffix}"
        compteur += 1

    shutil.move(str(chemin), str(dest))
    logger.info("Déplacé vers corbeille : %s → %s", chemin, dest)
    return dest


# ── Constantes ──────────────────────────────────────────────────────

# Extensions audio supportées par mutagen
AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".ogg",
    ".opus",
    ".m4a",
    ".m4b",
    ".mp4",
    ".aac",
    ".wav",
    ".wv",
    ".ape",
    ".wma",
    ".aiff",
    ".dsf",
    ".dff",
}

# Taille minimale pour considérer un fichier comme valide (100 Ko)
TAILLE_MIN_VALIDE = 100 * 1024

# Pattern regex par défaut pour parser les noms de fichiers    # Groupes nommés: artist, album, track, title
PATTERN_CLASSIQUE = re.compile(
    r"(?:\[(?P<source>[^\]]+)\]\s*)?"
    r"(?:(?P<artist>.+?)\s*[-–—]\s*)?"
    r"(?:(?P<album>.+?)\s*[-–—]\s*)?"
    r"(?:(?P<track>\d{1,3})[. ]\s*)?"
    r"(?P<title>.+?)"
    r"(?:\s*\((?P<year>\d{4})\))?"
    r"(?:\s*[-–—]\s*(?P<year2>\d{4}))?"
    r"(?:\s*\[(?P<quality>[^\]]+)\])?"
    r"$",
    re.IGNORECASE,
)

# Pattern plus simple: juste "Artiste - Titre"
PATTERN_SIMPLE = re.compile(
    r"(?:(?P<artist>.+?)\s*[-–—]\s*)?"
    r"(?P<title>.+?)"
    r"(?:\s*[-–—]\s*(?P<year>\d{4}))?"
    r"$",
    re.IGNORECASE,
)

# Tous les patterns, du plus spécifique au plus général
_FILENAME_PATTERNS = [PATTERN_CLASSIQUE, PATTERN_SIMPLE]

# Template de renommage par défaut
TEMPLATE_RENOMMAGE_DEFAUT = "{artist} - {album} - {track:02d} {title}.{ext}"
TEMPLATE_CLASSEMENT_DEFAUT = "{artist}/{album}/{track:02d} {title}.{ext}"

# Presets de classement
CLASSEMENT_PRESETS: dict[str, str] = {
    "artiste-album": "{artist}/{album}/{track:02d} {title}.{ext}",
    "artiste": "{artist}/{track:02d} {title}.{ext}",
    "genre-artiste": "{genre}/{artist}/{album}/{track:02d} {title}.{ext}",
    "annee-artiste": "{year}/{artist}/{album}/{track:02d} {title}.{ext}",
    "aucun": "{filename}",
}

# Presets de renommage
RENOMMAGE_PRESETS: dict[str, str] = {
    "standard": "{artist} - {album} - {track:02d} {title}.{ext}",
    "artiste-titre": "{artist} - {title}.{ext}",
    "piste-titre": "{track:02d} {title}.{ext}",
    "album-piste": "{album} - {track:02d} {title}.{ext}",
}


# ── Types ───────────────────────────────────────────────────────────


@dataclass
class FichierInfo:
    """Informations extraites d'un fichier audio."""

    path: Path
    filename: str
    extension: str
    size: int  # octets
    modified: float  # timestamp mtime

    # Métadonnées extraites
    artist: str | None = None
    album: str | None = None
    title: str | None = None
    track: int | None = None
    year: int | None = None
    genre: str | None = None
    quality: str | None = None  # bitrate / profondeur

    # Infos techniques
    bitrate: int | None = None  # bps
    sample_rate: int | None = None  # Hz
    duration: float | None = None  # secondes
    codec: str | None = None  # mp3, flac, etc.

    # Dédoublonnage
    hash_sha256: str | None = None  # SHA256 (64 premiers Ko)

    # Résultats d'analyse
    source_metadata: str = "inconnu"  # "tag", "pattern", "dossier", "inconnu"
    erreur: str | None = None


@dataclass
class AnalyseResultat:
    """Résultat complet d'une analyse de dossier."""

    dossier_source: Path
    fichiers: list[FichierInfo]
    total_fichiers: int
    total_audio: int
    total_taille: int  # octets
    doublons_potentiels: list[list[FichierInfo]] = field(default_factory=list)
    doublons_confirmes: list[list[FichierInfo]] = field(default_factory=list)
    doublons_resolus: list[dict[str, Any]] = field(default_factory=list)
    fichiers_sans_metadata: list[FichierInfo] = field(default_factory=list)

    @property
    def total_taille_lisible(self) -> str:
        """Taille totale formatée lisiblement."""
        return _taille_lisible(self.total_taille)


# ── Helpers ─────────────────────────────────────────────────────────


def _taille_lisible(octets: int) -> str:
    """Formate une taille en octets en chaîne lisible."""
    if octets < 1024:
        return f"{octets} o"
    elif octets < 1024**2:
        return f"{octets / 1024:.1f} Ko"
    elif octets < 1024**3:
        return f"{octets / 1024**2:.1f} Mo"
    else:
        return f"{octets / 1024**3:.2f} Go"


def _est_fichier_audio(path: Path) -> bool:
    """Vérifie si le fichier est un fichier audio supporté."""
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS and path.stat().st_size >= TAILLE_MIN_VALIDE


def _identifier_codec(path: Path, mutagen_obj: Any) -> str:
    """Identifie le codec à partir de l'objet mutagen."""
    cls_name = type(mutagen_obj).__name__
    mapping = {
        "MP3": "mp3",
        "MP4": "aac",
        "FLAC": "flac",
        "OggVorbis": "vorbis",
        "OggOpus": "opus",
        "OggFLAC": "oggflac",
        "WavPack": "wavpack",
        "MonkeysAudio": "ape",
        "Musepack": "musepack",
        "TrueAudio": "tta",
        "AIFF": "aiff",
        "DSF": "dsd",
        "WAVE": "pcm",
    }
    return mapping.get(cls_name, path.suffix.lower().lstrip("."))


def _extraire_tags(mutagen_obj: Any, path: Path) -> dict[str, str]:
    """Extrait les tags audio depuis un objet mutagen.

    Priorité :
    1. EasyID3 (pour MP3) — API simplifiée avec clés 'artist', 'album', etc.
    2. FLAC / Ogg Vorbis — VorbisComments avec dict-like .get()
    3. MP4 / M4A — accès par clés brutes iTunes

    Retourne un dict avec les clés standardisées:
    artist, album, title, tracknumber, date, genre.
    """
    tags: dict[str, str] = {}

    # ── 1. Essayer EasyID3 (MP3) — importé en haut de fichier ──
    try:
        easy = EasyID3(str(path))
        for key in ("artist", "album", "title", "tracknumber", "date", "genre"):
            val = easy.get(key)
            if val and isinstance(val, list) and len(val) > 0 and val[0].strip():
                tags[key] = val[0].strip()
        if tags:
            return tags
    except Exception:
        pass

    # ── 2. FLAC / Ogg Vorbis (dict-like direct) ──
    cls_name = type(mutagen_obj).__name__
    if cls_name in ("FLAC", "OggVorbis", "OggOpus", "OggFLAC"):
        for key in ("artist", "album", "title", "tracknumber", "date", "genre"):
            try:
                val = mutagen_obj.get(key)
                if val and isinstance(val, list) and len(val) > 0 and val[0].strip():
                    tags[key] = val[0].strip()
            except Exception:
                pass
        if tags:
            return tags

    # ── 3. MP4 / M4A (clés brutes iTunes) ──
    if cls_name == "MP4":
        KEY_MAP = {
            "\xa9ART": "artist",
            "\xa9alb": "album",
            "\xa9nam": "title",
            "\xa9day": "date",
            "\xa9gen": "genre",
            "trkn": "tracknumber",
        }
        for mut_key, our_key in KEY_MAP.items():
            try:
                val = mutagen_obj[mut_key]
                if val:
                    if isinstance(val, list):
                        val = val[0]
                    if isinstance(val, tuple):
                        val = str(val[0])  # tracknumber est (num, total)
                    if val:
                        tags[our_key] = str(val).strip()
            except (KeyError, IndexError, TypeError):
                pass
        return tags

    # ── 4. Fallback : mutagen_obj.tags (ID3 d'un MP3 non-Easy) ──
    if hasattr(mutagen_obj, "tags") and mutagen_obj.tags is not None:
        try:
            # ID3: mappe les noms de frames vers des clés lisibles
            FRAME_MAP = {
                "TPE1": "artist",
                "TALB": "album",
                "TIT2": "title",
                "TRCK": "tracknumber",
                "TDRC": "date",
                "TCON": "genre",
            }
            for frame_key, our_key in FRAME_MAP.items():
                try:
                    frame = mutagen_obj.tags[frame_key]
                    if frame:
                        text = str(frame)
                        if text.strip():
                            tags[our_key] = text.strip()
                except (KeyError, IndexError):
                    pass
        except Exception:
            pass

    return tags


# ── Service ─────────────────────────────────────────────────────────


class OrdonnanceurService:
    """Service d'analyse et d'organisation des fichiers audio.

    Utilise mutagen pour l'extraction des métadonnées et supporte
    le parsing par regex des noms de fichiers en fallback.
    """

    def __init__(self) -> None:
        self._filename_patterns: list[re.Pattern] = list(_FILENAME_PATTERNS)

    # ── Scan / Analyse ────────────────────────────────────────────

    def scanner_dossier(
        self,
        dossier: str | Path,
        recursive: bool = True,
    ) -> list[Path]:
        """Scanne un dossier et retourne la liste des fichiers audio.

        Args:
            dossier: Chemin du dossier à scanner.
            recursive: Si True, scanne récursivement.

        Returns:
            Liste des chemins des fichiers audio trouvés.
        """
        dossier = Path(dossier)
        if not dossier.is_dir():
            logger.warning("Dossier introuvable: %s", dossier)
            return []

        if recursive:
            fichiers = [f for f in dossier.rglob("*") if _est_fichier_audio(f)]
        else:
            fichiers = [f for f in dossier.iterdir() if _est_fichier_audio(f)]

        logger.info(
            "Scan %s: %d fichiers audio trouvés",
            dossier,
            len(fichiers),
        )
        return sorted(fichiers)

    def analyser_fichier(self, path: Path) -> FichierInfo:
        """Analyse un fichier audio et extrait ses métadonnées.

        1. Tente l'extraction via mutagen (tags)
        2. Fallback sur le parsing du nom de fichier (regex)
        3. Fallback ultime sur le nom du dossier parent

        Args:
            path: Chemin du fichier audio.

        Returns:
            FichierInfo avec les métadonnées extraites.
        """
        stat = path.stat()
        info = FichierInfo(
            path=path,
            filename=path.name,
            extension=path.suffix.lower(),
            size=stat.st_size,
            modified=stat.st_mtime,
        )

        # ── 1. Extraction via mutagen ──
        try:
            audio = MutagenFile(str(path))
        except Exception as exc:
            audio = None
            info.erreur = f"mutagen: {exc}"
            logger.debug("Erreur mutagen pour %s: %s", path.name, exc)

        if audio is not None:
            # Infos techniques
            if hasattr(audio, "info") and audio.info is not None:
                info.bitrate = getattr(audio.info, "bitrate", None)
                info.sample_rate = getattr(audio.info, "sample_rate", None)
                info.duration = getattr(audio.info, "length", None)
            info.codec = _identifier_codec(path, audio)

            # Tags — extraction unifiée via EasyID3 / Vorbis / ID3 / MP4
            tags = _extraire_tags(audio, path)

            if tags:
                info.artist = tags.get("artist")
                info.album = tags.get("album")
                info.title = tags.get("title")
                info.year = _parser_annee(tags.get("date"))
                info.genre = tags.get("genre")
                info.source_metadata = "tag"

                # tracknumber peut être "5", "05", "5/12"
                raw_track = tags.get("tracknumber", "")
                info.track = _parser_piste(raw_track)

        # ── 2. Fallback: parsing du nom de fichier ──
        if info.source_metadata == "inconnu" or (info.title is None and info.filename):
            extrait = self._parser_nom_fichier(path.stem)
            if extrait:
                if info.artist is None:
                    info.artist = extrait.get("artist")
                if info.album is None:
                    info.album = extrait.get("album")
                if info.title is None:
                    info.title = extrait.get("title")
                if info.track is None:
                    info.track = extrait.get("track")
                if info.year is None:
                    info.year = extrait.get("year") or extrait.get("year2")
                if info.source_metadata == "inconnu":
                    info.source_metadata = "pattern"

        # ── 3. Fallback ultime: dossier parent comme artiste ──
        if info.artist is None and info.source_metadata == "inconnu":
            parent_dir = path.parent.name
            if parent_dir and parent_dir not in (".", "downloads", "téléchargements"):
                info.artist = parent_dir
                info.source_metadata = "dossier"

        # Titre fallback = nom sans extension
        if info.title is None:
            info.title = path.stem

        return info

    def analyser_dossier(
        self,
        dossier: str | Path,
        recursive: bool = True,
    ) -> AnalyseResultat:
        """Analyse complète d'un dossier : scan + metadata + stats.

        Args:
            dossier: Chemin du dossier à analyser.
            recursive: Si True, scanne récursivement.

        Returns:
            AnalyseResultat avec tous les fichiers analysés.
        """
        dossier = Path(dossier)
        fichiers_paths = self.scanner_dossier(dossier, recursive=recursive)

        fichiers: list[FichierInfo] = []
        for path in fichiers_paths:
            info = self.analyser_fichier(path)
            fichiers.append(info)

        # Stats globales
        total_audio = len(fichiers)
        total_taille = sum(f.size for f in fichiers)

        # Fichiers sans métadonnées fiables
        sans_tags = [f for f in fichiers if f.source_metadata == "inconnu"]

        # Détection rapide des doublons potentiels (nom+taille)
        doublons = self._detecter_doublons_rapide(fichiers)

        # Passe 2 : confirmation par hash SHA256
        doublons_confirme: list[list[FichierInfo]] = []
        doublons_resolus: list[dict[str, Any]] = []
        if doublons:
            fichiers_suspects = [f for g in doublons for f in g]
            doublons_confirme = self._detecter_doublons_hash(fichiers_suspects)
            doublons_resolus = [self._resoudre_doublons(g) for g in doublons_confirme]

        logger.info(
            "Analyse %s: %d fichiers, %s, %d potentiels, %d confirmés",
            dossier,
            total_audio,
            _taille_lisible(total_taille),
            len(doublons),
            len(doublons_confirme),
        )

        return AnalyseResultat(
            dossier_source=dossier,
            fichiers=fichiers,
            total_fichiers=len(fichiers_paths),
            total_audio=total_audio,
            total_taille=total_taille,
            doublons_potentiels=doublons,
            doublons_confirmes=doublons_confirme,
            doublons_resolus=doublons_resolus,
            fichiers_sans_metadata=sans_tags,
        )

    # ── Parsing du nom de fichier ─────────────────────────────────

    def _parser_nom_fichier(self, stem: str) -> dict[str, Any] | None:
        """Parse un nom de fichier (sans extension) avec les patterns configurés.

        Returns:
            Dict avec clés: artist, album, title, track, year, ou None.
        """
        for pattern in self._filename_patterns:
            match = pattern.match(stem)
            if match:
                groups = match.groupdict()
                result: dict[str, Any] = {}

                if groups.get("title"):
                    result["title"] = groups["title"].strip()
                if groups.get("artist"):
                    result["artist"] = groups["artist"].strip()
                if groups.get("album"):
                    result["album"] = groups["album"].strip()
                if groups.get("track"):
                    result["track"] = _parser_piste(groups["track"])
                if groups.get("year"):
                    result["year"] = _parser_annee(groups["year"])
                if groups.get("year2"):
                    result["year"] = _parser_annee(groups["year2"])

                if result.get("title"):
                    return result
        return None

    # ── Détection des doublons ────────────────────────────────────

    def _detecter_doublons_rapide(
        self,
        fichiers: list[FichierInfo],
    ) -> list[list[FichierInfo]]:
        """Passe 1 : détecte les doublons par (nom en minuscules, taille).

        Returns:
            Liste de groupes de fichiers suspects.
        """
        groupes: dict[tuple[str, int], list[FichierInfo]] = defaultdict(list)
        for f in fichiers:
            key = (f.filename.lower(), f.size)
            groupes[key].append(f)

        return [g for g in groupes.values() if len(g) > 1]

    def _detecter_doublons_hash(
        self,
        fichiers: list[FichierInfo],
    ) -> list[list[FichierInfo]]:
        """Passe 2 : confirme les doublons par hash SHA256 (64 premiers Ko).

        Calcule et met à jour le hash de chaque fichier.

        Returns:
            Liste de groupes de doublons confirmés (même hash, >= 2 fichiers).
        """
        groupes: dict[str, list[FichierInfo]] = defaultdict(list)

        for f in fichiers:
            f.hash_sha256 = self._calculer_hash(f.path)
            if f.hash_sha256:
                groupes[f.hash_sha256].append(f)

        return [g for g in groupes.values() if len(g) > 1]

    @staticmethod
    def _calculer_hash(path: Path, taille_max: int = 65536) -> str | None:
        """Calcule le SHA256 d'un fichier (lecture partielle par défaut).

        Args:
            path: Chemin du fichier.
            taille_max: Nombre d'octets à lire (0 = fichier complet).

        Returns:
            Empreinte hexadécimale, ou None si erreur.
        """
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                if taille_max > 0:
                    h.update(f.read(taille_max))
                else:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
            return h.hexdigest()
        except OSError as exc:
            logger.debug("Erreur hash %s: %s", path.name, exc)
            return None

    @staticmethod
    def _resoudre_doublons(
        groupe: list[FichierInfo],
    ) -> dict[str, Any]:
        """Applique les règles de conservation sur un groupe de doublons confirmés.

        Critères (par ordre de priorité) :
        1. Meilleur bitrate (qualité audio)
        2. Nom de fichier le plus long/descriptif
        3. Fichier le plus récent
        4. Premier fichier trouvé (ordre stable)

        Les fichiers < 100 Ko sont exclus de la conservation.

        Returns:
            Dict avec :
            - 'groupe' : groupe trié par priorité (meilleur en premier)
            - 'garde' : fichier recommandé (premier du classement)
            - 'supprimables' : fichiers à supprimer
            - 'exclus' : fichiers exclus (< 100 Ko)
            - 'taille_economisee' : octets économisés
        """
        valides = [f for f in groupe if f.size >= TAILLE_MIN_VALIDE]
        exclus = [f for f in groupe if f.size < TAILLE_MIN_VALIDE]

        if not valides:
            return {
                "groupe": [],
                "garde": None,
                "supprimables": [],
                "exclus": exclus,
                "taille_economisee": 0,
            }

        # Tri stable : bitrate (desc) → longueur nom (desc) → modification (desc)
        tries = sorted(
            valides,
            key=lambda f: (
                -(f.bitrate or 0),
                -(len(f.filename) or 0),
                -(f.modified or 0),
            ),
        )

        garde = tries[0]
        supprimables = tries[1:]

        return {
            "groupe": tries,
            "garde": garde,
            "supprimables": supprimables,
            "exclus": exclus,
            "taille_economisee": sum(f.size for f in supprimables),
        }

    # ── Génération de nom fichier / chemin ────────────────────────

    def generer_nom_fichier(
        self,
        info: FichierInfo,
        template: str = TEMPLATE_RENOMMAGE_DEFAUT,
    ) -> str:
        """Génère un nom de fichier à partir d'un template.

        Variables disponibles:
            {artist}, {album}, {title}, {track}, {track:02d},
            {year}, {genre}, {ext}, {filename}

        Args:
            info: Métadonnées du fichier.
            template: Template de renommage.

        Returns:
            Nouveau nom de fichier (avec extension).
        """
        return self._appliquer_template(template, info)

    def generer_chemin_classement(
        self,
        info: FichierInfo,
        racine: str | Path = "",
        template: str = TEMPLATE_CLASSEMENT_DEFAUT,
    ) -> Path:
        """Génère le chemin de destination pour le classement artiste/album.

        Args:
            info: Métadonnées du fichier.
            racine: Dossier racine de destination.
            template: Template de chemin relatif.

        Returns:
            Chemin complet vers le fichier classé.
        """
        relatif = self._appliquer_template(template, info)
        return Path(racine) / relatif

    def _appliquer_template(self, template: str, info: FichierInfo) -> str:
        """Applique un template avec les variables du fichier."""
        variables = {
            "artist": self._fallback(info.artist, "Inconnu"),
            "album": self._fallback(info.album, "Inconnu"),
            "title": self._fallback(info.title, Path(info.path).stem),
            "track": info.track if info.track is not None else 0,
            "track:02d": f"{info.track:02d}" if info.track is not None else "00",
            "year": self._fallback(str(info.year) if info.year else None, "0000"),
            "genre": self._fallback(info.genre, "Inconnu"),
            "ext": info.extension.lstrip("."),
            "filename": Path(info.path).stem,
        }

        # Supprimer les clés dupliquées (track:02d est un alias)
        result = template
        for key, val in variables.items():
            if key == "track:02d":
                continue  # géré comme alias de {track:02d}
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(val))

        # Gérer le format spécial {track:02d} via regex
        result = re.sub(
            r"\{track:02d\}",
            variables["track:02d"],
            result,
        )

        # Nettoyer les chemins (pas de doubles séparateurs, etc.)
        result = result.replace("//", "/").replace("\\", "/")
        # Remplacer les caractères invalides dans les noms de fichiers
        result = re.sub(r'[<>:"|?*]', "_", result)

        return result

    @staticmethod
    def _fallback(val: str | None, default: str) -> str:
        """Retourne la valeur ou un fallback si None/vide."""
        if val and val.strip():
            return val.strip()
        return default

    # ── Estimation ────────────────────────────────────────────────

    def estimer_operations(
        self,
        analyse: AnalyseResultat,
        selected_ops: set[str],
    ) -> dict[str, dict[str, Any]]:
        """Estime le nombre de fichiers concernés par chaque opération.

        Args:
            analyse: Résultat d'analyse du dossier.
            selected_ops: Opérations sélectionnées (classement, renommage, etc.).

        Returns:
            Dict par opération avec estimation.
        """
        estimations: dict[str, dict[str, Any]] = {}

        if "classement" in selected_ops:
            # Fichiers qui seront déplacés (ceux qui ont artiste)
            a_classer = [f for f in analyse.fichiers if f.artist]
            estimations["classement"] = {
                "fichiers": len(a_classer),
                "dossiers": len({f.artist for f in a_classer if f.artist}),
                "taille": sum(f.size for f in a_classer),
                "taille_lisible": _taille_lisible(sum(f.size for f in a_classer)),
            }

        if "renommage" in selected_ops:
            # Tous les fichiers audio sauf ceux déjà bien nommés
            a_renommer = [
                f
                for f in analyse.fichiers
                if f.artist or f.title  # au moins un champ exploitable
            ]
            estimations["renommage"] = {
                "fichiers": len(a_renommer),
            }

        if "dedoublonner" in selected_ops:
            # Utiliser les doublons confirmés si disponibles, sinon les potentiels
            groupes = analyse.doublons_confirmes if analyse.doublons_confirmes else analyse.doublons_potentiels
            nb_doublons = sum(len(g) - 1 for g in groupes)
            taille_economisee = sum(sum(f.size for f in g[1:]) for g in groupes) if groupes else 0
            estimations["dedoublonner"] = {
                "groupes": len(groupes),
                "fichiers_a_supprimer": nb_doublons,
                "taille_economisee": taille_economisee,
                "taille_lisible": _taille_lisible(taille_economisee),
            }

        if "nettoyage" in selected_ops:
            estimations["nettoyage"] = {
                "fichiers_temp": 0,  # calculé à l'exécution
                "fichiers_cache": 0,
                "logs_anciens": 0,
            }

        return estimations

    # ── Patterns filename ─────────────────────────────────────────

    # ── Preview des opérations ──────────────────────────────────

    def preparer_renommage(
        self,
        analyse: AnalyseResultat,
        template: str = TEMPLATE_RENOMMAGE_DEFAUT,
    ) -> dict[str, Any]:
        """Prépare un aperçu détaillé du renommage.

        Pour chaque fichier avec une métadonnée exploitable, génère
        le nouveau nom et détecte les conflits (deux fichiers vers
        le même nouveau nom).

        Args:
            analyse: Résultat d'analyse du dossier.
            template: Template de renommage.

        Returns:
            Dict avec :
            - 'fichiers' : liste de {info, nom_actuel, nouveau_nom}
            - 'total' : nombre de fichiers à renommer
            - 'conflits' : liste de {nom_conflit, fichiers, nb}
            - 'exemples' : jusqu'à 5 exemples représentatifs
        """
        fichiers: list[dict[str, Any]] = []
        conflits_dict: dict[str, list[FichierInfo]] = defaultdict(list)

        for info in analyse.fichiers:
            if not info.artist and not info.title:
                continue  # aucune métadonnée exploitable

            nouveau_nom = self.generer_nom_fichier(info, template=template)

            if nouveau_nom == info.filename:
                continue  # déjà bien nommé

            fichiers.append(
                {
                    "info": info,
                    "nom_actuel": info.filename,
                    "nouveau_nom": nouveau_nom,
                }
            )
            conflits_dict[nouveau_nom].append(info)

        # Détection des conflits : plusieurs fichiers → même nouveau nom
        conflits = [
            {
                "nom_conflit": nom,
                "fichiers": [f.filename for f in infos],
                "nb": len(infos),
            }
            for nom, infos in conflits_dict.items()
            if len(infos) > 1
        ]

        # Exemples : premiers résultats, variés si possible
        exemples = fichiers[:5]

        return {
            "fichiers": fichiers,
            "total": len(fichiers),
            "conflits": conflits,
            "exemples": exemples,
        }

    def preparer_classement(
        self,
        analyse: AnalyseResultat,
        racine: str | Path = "",
        template: str = TEMPLATE_CLASSEMENT_DEFAUT,
    ) -> dict[str, Any]:
        """Prépare un aperçu détaillé du classement artiste/album.

        Pour chaque fichier avec un artiste connu, génère le chemin
        de destination et regroupe par artiste.

        Args:
            analyse: Résultat d'analyse du dossier.
            racine: Dossier racine de destination.
            template: Template de classement.

        Returns:
            Dict avec :
            - 'fichiers' : liste de {info, chemin_actuel, nouveau_chemin, artiste}
            - 'total' : nombre de fichiers à classer
            - 'artistes' : dict {nom_artiste: nb_fichiers}
            - 'conflits' : liste de conflits de chemin
            - 'exemples' : jusqu'à 5 exemples
        """
        fichiers: list[dict[str, Any]] = []
        artistes: dict[str, int] = defaultdict(int)
        conflits_dict: dict[str, list[FichierInfo]] = defaultdict(list)

        for info in analyse.fichiers:
            if not info.artist:
                continue  # pas d'artiste → pas classable

            nouveau_chemin = self.generer_chemin_classement(
                info,
                racine=racine,
                template=template,
            )

            chemin_str = str(nouveau_chemin)

            if info.path and chemin_str == str(info.path):
                continue  # déjà au bon endroit

            fichiers.append(
                {
                    "info": info,
                    "chemin_actuel": info.path,
                    "nouveau_chemin": nouveau_chemin,
                    "artiste": info.artist,
                }
            )
            artistes[info.artist] += 1
            conflits_dict[chemin_str].append(info)

        conflits = [
            {
                "chemin": chemin,
                "fichiers": [f.filename for f in infos],
                "nb": len(infos),
            }
            for chemin, infos in conflits_dict.items()
            if len(infos) > 1
        ]

        return {
            "fichiers": fichiers,
            "total": len(fichiers),
            "artistes": dict(artistes),
            "nb_artistes": len(artistes),
            "conflits": conflits,
            "exemples": fichiers[:5],
        }

    @staticmethod
    def preparer_deduplication(
        analyse: AnalyseResultat,
        resoudre_conflits: bool = True,
    ) -> dict[str, Any]:
        """Prépare un aperçu du dédoublonnage à partir de l'analyse.

        Utilise les doublons résolus (hash + règles de conservation)
        ou les potentiels (nom+taille) si non confirmés.
        Détecte et résout automatiquement les conflits de noms entre
        fichiers gardés de groupes différents (suffixes _2, _3…).

        Args:
            analyse: Résultat d'analyse du dossier.

        Returns:
            Dict avec :
            - 'groupes' : liste des groupes résolus (avec 'garde_nouveau_nom'
              sur les groupes concernés par un conflit)
            - 'total_doublons' : nombre de fichiers à supprimer
            - 'total_economise' : octets économisés
            - 'total_lisible' : taille formatée
            - 'nb_groupes' : nombre de groupes de doublons
            - 'conflits' : liste des conflits détectés (ou [])
            - 'conflits_resolus' : liste des résolutions appliquées (ou [])
        """
        groupes = analyse.doublons_resolus or [
            {
                "groupe": g,
                "garde": g[0],
                "supprimables": g[1:],
                "exclus": [],
                "taille_economisee": sum(f.size for f in g[1:]),
            }
            for g in analyse.doublons_potentiels
        ]

        total_doublons = sum(len(g["supprimables"]) for g in groupes)
        total_economise = sum(g["taille_economisee"] for g in groupes)

        # ── Détection des conflits de noms entre fichiers gardés ──
        garde_noms: dict[str, list[int]] = {}
        for idx, g in enumerate(groupes):
            garde = g.get("garde")
            if garde and garde.filename:
                garde_noms.setdefault(garde.filename, []).append(idx)

        conflits: list[dict[str, Any]] = []
        for nom, indices in garde_noms.items():
            if len(indices) > 1:
                conflits.append(
                    {
                        "nom_conflit": nom,
                        "fichiers": [groupes[i]["garde"].filename for i in indices],
                        "nb": len(indices),
                    }
                )

        # ── Résolution par suffixes _2, _3… (optionnelle) ──
        conflits_resolus: list[dict[str, Any]] = []
        if resoudre_conflits:
            for conflit in conflits:
                nom_base = conflit["nom_conflit"]
                p = Path(nom_base)
                stem = p.stem
                ext = p.suffix
                indices = garde_noms[nom_base]

                resolutions: list[dict[str, Any]] = []
                for i, idx in enumerate(indices):
                    if i == 0:
                        nouveau = nom_base
                    else:
                        nouveau = f"{stem}_{i + 1}{ext}"
                        groupes[idx]["garde_nouveau_nom"] = nouveau
                    resolutions.append(
                        {
                            "fichier": nom_base,
                            "groupe_idx": idx,
                            "nom_original": nom_base,
                            "nouveau_nom": nouveau,
                        }
                    )

                conflits_resolus.append(
                    {
                        "nom_conflit": nom_base,
                        "fichiers": conflit["fichiers"],
                        "resolutions": resolutions,
                    }
                )
            conflits = []  # vidé après résolution (cohérent avec resoudre_conflits)

        return {
            "groupes": groupes,
            "total_doublons": total_doublons,
            "total_economise": total_economise,
            "total_lisible": _taille_lisible(total_economise),
            "nb_groupes": len(groupes),
            "conflits": conflits,
            "conflits_resolus": conflits_resolus,
        }

    @staticmethod
    def preparer_nettoyage(
        dossier_temp: str | Path,
        age_max_jours: int = 7,
        extensions: set[str] | None = None,
    ) -> dict[str, Any]:
        """Prépare un aperçu du nettoyage des fichiers temporaires.

        Scanne le dossier temp et liste les fichiers à supprimer
        selon leur extension et leur âge.

        Args:
            dossier_temp: Chemin du dossier temporaire.
            age_max_jours: Âge maximum en jours (défaut: 7).
            extensions: Extensions à cibler (None = extensions par défaut).

        Returns:
            Dict avec :
            - 'fichiers' : liste de {chemin, taille, age_jours}
            - 'total' : nombre de fichiers
            - 'taille_totale' : octets total
            - 'taille_lisible' : taille formatée
        """
        if extensions is None:
            extensions = {".part", ".tmp", ".cache", ".log", ".bak", ".swp"}

        dossier = Path(dossier_temp)
        if not dossier.is_dir():
            return {
                "fichiers": [],
                "total": 0,
                "taille_totale": 0,
                "taille_lisible": "0 o",
            }

        maintenant = time.time()
        age_max_secondes = age_max_jours * 86400

        fichiers: list[dict[str, Any]] = []
        taille_totale = 0

        for p in dossier.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in extensions:
                continue

            try:
                stat = p.stat()
                age = maintenant - stat.st_mtime
                if age >= age_max_secondes:
                    fichiers.append(
                        {
                            "chemin": p,
                            "taille": stat.st_size,
                            "age_jours": round(age / 86400, 1),
                        }
                    )
                    taille_totale += stat.st_size
            except OSError:
                continue

        return {
            "fichiers": sorted(fichiers, key=lambda x: -x["taille"]),
            "total": len(fichiers),
            "taille_totale": taille_totale,
            "taille_lisible": _taille_lisible(taille_totale),
        }

    @staticmethod
    def resoudre_conflits(
        apercu: dict[str, Any],
    ) -> dict[str, Any]:
        """Résout les conflits de noms en ajoutant des suffixes _2, _3…

        Prend l'aperçu retourné par preparer_renommage() ou
        preparer_classement() et résout les conflits détectés.
        Le premier fichier conserve le nom original, les suivants
        reçoivent un suffixe numérique (_2, _3…).

        Args:
            apercu: Dict d'aperçu avec une clé 'conflits'.

        Returns:
            Dict modifié avec les conflits résolus :
            - 'fichiers' mise à jour avec les nouveaux noms/chemins
            - 'conflits' vidée (tous résolus)
            - 'conflits_resolus' : liste des résolutions effectuées
        """
        if not apercu.get("conflits"):
            apercu["conflits_resolus"] = []
            return apercu

        conflits = apercu["conflits"]

        # Détecter le type de conflit
        est_renommage = "nom_conflit" in conflits[0]
        conflits_resolus: list[dict[str, Any]] = []

        for conflit in conflits:
            if est_renommage:
                nom_base: str = conflit["nom_conflit"]
                fichiers_noms: list[str] = conflit["fichiers"]

                # Séparer le stem et l'extension sur le dernier suffixe
                p = Path(nom_base)
                stem = p.stem
                ext = p.suffix

                resolutions: list[dict[str, Any]] = []
                for idx, nom_original in enumerate(fichiers_noms):
                    if idx == 0:
                        nouveau = nom_base
                    else:
                        nouveau = f"{stem}_{idx + 1}{ext}"

                    # Mettre à jour l'entrée correspondante dans fichiers
                    for entry in apercu["fichiers"]:
                        if entry.get("nom_actuel") == nom_original:
                            entry["nouveau_nom"] = nouveau
                            break

                    resolutions.append(
                        {
                            "fichier": nom_original,
                            "nom_original": nom_base,
                            "nouveau_nom": nouveau,
                        }
                    )

                conflits_resolus.append(
                    {
                        "nom_conflit": nom_base,
                        "fichiers": fichiers_noms,
                        "resolutions": resolutions,
                    }
                )

            else:
                # Conflit de classement
                chemin_base: str = conflit["chemin"]
                fichiers_noms = conflit["fichiers"]

                base_path = Path(chemin_base)
                parent = base_path.parent
                stem = base_path.stem
                ext = base_path.suffix

                resolutions = []
                for idx, nom_original in enumerate(fichiers_noms):
                    if idx == 0:
                        nouveau_chemin_str = chemin_base
                    else:
                        nouveau_stem = f"{stem}_{idx + 1}"
                        nouveau_chemin_str = str(parent / f"{nouveau_stem}{ext}")

                    # Mettre à jour l'entrée correspondante
                    for entry in apercu["fichiers"]:
                        if entry["info"].filename == nom_original:
                            entry["nouveau_chemin"] = Path(nouveau_chemin_str)
                            break

                    resolutions.append(
                        {
                            "fichier": nom_original,
                            "chemin_original": chemin_base,
                            "nouveau_chemin": nouveau_chemin_str,
                        }
                    )

                conflits_resolus.append(
                    {
                        "chemin": chemin_base,
                        "fichiers": fichiers_noms,
                        "resolutions": resolutions,
                    }
                )

        # Conflits vidés (tous résolus)
        apercu["conflits"] = []
        apercu["conflits_resolus"] = conflits_resolus

        return apercu

    def generer_apercu(
        self,
        analyse: AnalyseResultat,
        selected_ops: set[str],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Génère un aperçu complet des opérations sélectionnées.

        Combine les 4 previews (renommage, classement, dédoublonnage,
        nettoyage) en un seul dict structuré pour l'affichage.
        Les conflits de noms/chemins sont automatiquement résolus
        par suffixes _2, _3… (sauf si `resoudre_conflits=False`).

        Args:
            analyse: Résultat d'analyse du dossier.
            selected_ops: Opérations sélectionnées (classement, renommage,
                         dedoublonner, nettoyage).
            options: Options supplémentaires :
                - 'template_renommage': template de renommage
                - 'template_classement': template de classement
                - 'racine_classement': dossier racine de classement
                - 'dossier_temp': dossier temporaire pour nettoyage
                - 'age_max_jours': âge max pour nettoyage
                - 'resoudre_conflits': bool, True par défaut

        Returns:
            Dict unifié avec les clés des opérations sélectionnées,
            plus un résumé 'resume'.
        """
        if options is None:
            options = {}

        apercu: dict[str, Any] = {}
        total_fichiers_confernes = 0
        total_taille_economisee = 0
        resoudre = options.get("resoudre_conflits", True)

        if "renommage" in selected_ops:
            template = options.get(
                "template_renommage",
                TEMPLATE_RENOMMAGE_DEFAUT,
            )
            apercu["renommage"] = self.preparer_renommage(analyse, template=template)
            if resoudre:
                self.resoudre_conflits(apercu["renommage"])
            total_fichiers_confernes += apercu["renommage"]["total"]

        if "classement" in selected_ops:
            template = options.get(
                "template_classement",
                TEMPLATE_CLASSEMENT_DEFAUT,
            )
            racine = options.get("racine_classement", "")
            apercu["classement"] = self.preparer_classement(
                analyse,
                racine=racine,
                template=template,
            )
            if resoudre:
                self.resoudre_conflits(apercu["classement"])
            total_fichiers_confernes += apercu["classement"]["total"]

        if "dedoublonner" in selected_ops:
            apercu["deduplication"] = self.preparer_deduplication(
                analyse,
                resoudre_conflits=resoudre,
            )
            total_fichiers_confernes += apercu["deduplication"]["total_doublons"]
            total_taille_economisee += apercu["deduplication"]["total_economise"]

        if "nettoyage" in selected_ops:
            dossier_temp = options.get("dossier_temp", "data/tmp")
            age_max = options.get("age_max_jours", 7)
            apercu["nettoyage"] = self.preparer_nettoyage(
                dossier_temp,
                age_max_jours=age_max,
            )
            total_fichiers_confernes += apercu["nettoyage"]["total"]
            total_taille_economisee += apercu["nettoyage"]["taille_totale"]

        apercu["resume"] = {
            "total_fichiers_confernes": total_fichiers_confernes,
            "total_taille_economisee": total_taille_economisee,
            "total_taille_lisible": _taille_lisible(total_taille_economisee),
        }

        return apercu

    # ── Exécution ────────────────────────────────────────────────

    def executer_operations(
        self,
        apercu: dict[str, Any],
        simuler: bool = True,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Exécute les opérations préparées sur le système de fichiers.

        Applique les 4 types d'opérations (renommage, classement,
        dédoublonnage, nettoyage) en séquence, avec gestion des erreurs
        individuelles par fichier.

        Args:
            apercu: Résultat de generer_apercu().
            simuler: Si True (défaut), ne fait que simuler sans toucher
                     au disque. Passer False pour appliquer réellement.
            on_progress: Callable optionnelle (operation, courant, total)
                         appelee a chaque fichier traite.

        Returns:
            Dict avec :
            - 'succes' : booléen global (True si aucune erreur)
            - 'simulation' : True si dry-run
            - 'operations' : dict des compteurs par opération
            - 'erreurs' : liste de dicts {operation, fichier, erreur}
            - 'details' : liste des actions effectuées
        """
        operations: dict[str, Any] = {}
        erreurs: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []

        if "renommage" in apercu:
            ops, errs, dets = self._executer_renommage(
                apercu["renommage"],
                apercu=apercu,
                simuler=simuler,
                on_progress=on_progress,
            )
            operations["renommage"] = ops
            erreurs.extend(errs)
            details.extend(dets)

        if "classement" in apercu:
            ops, errs, dets = self._executer_classement(
                apercu["classement"],
                simuler=simuler,
                on_progress=on_progress,
            )
            operations["classement"] = ops
            erreurs.extend(errs)
            details.extend(dets)

        if "deduplication" in apercu:
            ops, errs, dets = self._executer_deduplication(
                apercu["deduplication"],
                simuler=simuler,
                on_progress=on_progress,
            )
            operations["deduplication"] = ops
            erreurs.extend(errs)
            details.extend(dets)

        if "nettoyage" in apercu:
            ops, errs, dets = self._executer_nettoyage(
                apercu["nettoyage"],
                simuler=simuler,
                on_progress=on_progress,
            )
            operations["nettoyage"] = ops
            erreurs.extend(errs)
            details.extend(dets)

        return {
            "succes": len(erreurs) == 0,
            "simulation": simuler,
            "operations": operations,
            "erreurs": erreurs,
            "details": details,
        }

    def _executer_renommage(
        self,
        apercu_renommage: dict[str, Any],
        simuler: bool = True,
        apercu: dict[str, Any] | None = None,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
        """Exécute le renommage des fichiers.

        Met à jour `info.path` après rename et propage le changement
        aux autres sections de l'aperçu (classement) pour éviter
        les stale paths dans les opérations combinées.
        """
        tente = 0
        reussi = 0
        erreurs: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []

        for idx, entry in enumerate(apercu_renommage.get("fichiers", [])):
            if on_progress:
                on_progress("renommage", idx + 1, len(apercu_renommage.get("fichiers", [])))
            info: FichierInfo = entry["info"]
            ancien = info.path
            nouveau = ancien.parent / entry["nouveau_nom"]
            tente += 1

            if simuler:
                details.append(
                    {
                        "operation": "renommage",
                        "type": "simulation",
                        "ancien": str(ancien),
                        "nouveau": str(nouveau),
                    }
                )
                reussi += 1
                continue

            try:
                if nouveau.exists():
                    raise FileExistsError(f"Le fichier destination existe déjà : {nouveau}")
                ancien.rename(nouveau)
                # Mettre à jour le path dans FichierInfo pour les opérations suivantes
                info.path = nouveau

                # Propager aux autres sections si c'est le même FichierInfo
                if apercu and "classement" in apercu:
                    for ce in apercu["classement"].get("fichiers", []):
                        if ce["info"] is info:
                            ce["chemin_actuel"] = nouveau

                reussi += 1
                details.append(
                    {
                        "operation": "renommage",
                        "type": "reussi",
                        "ancien": str(ancien),
                        "nouveau": str(nouveau),
                    }
                )
            except Exception as e:
                erreurs.append(
                    {
                        "operation": "renommage",
                        "fichier": str(ancien),
                        "erreur": str(e),
                    }
                )
                details.append(
                    {
                        "operation": "renommage",
                        "type": "erreur",
                        "ancien": str(ancien),
                        "erreur": str(e),
                    }
                )

        ops = {"tente": tente, "reussi": reussi, "echoue": tente - reussi}
        return ops, erreurs, details

    def _executer_classement(
        self,
        apercu_classement: dict[str, Any],
        simuler: bool = True,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
        """Exécute le déplacement des fichiers selon le classement."""
        tente = 0
        reussi = 0
        erreurs: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []

        for idx, entry in enumerate(apercu_classement.get("fichiers", [])):
            if on_progress:
                on_progress("classement", idx + 1, len(apercu_classement.get("fichiers", [])))
            source: Path = entry["chemin_actuel"]
            dest: Path = entry["nouveau_chemin"]
            tente += 1

            if simuler:
                details.append(
                    {
                        "operation": "classement",
                        "type": "simulation",
                        "source": str(source),
                        "destination": str(dest),
                    }
                )
                reussi += 1
                continue

            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    raise FileExistsError(f"Le fichier destination existe déjà : {dest}")
                source.rename(dest)
                reussi += 1
                details.append(
                    {
                        "operation": "classement",
                        "type": "reussi",
                        "source": str(source),
                        "destination": str(dest),
                    }
                )
            except Exception as e:
                erreurs.append(
                    {
                        "operation": "classement",
                        "fichier": str(source),
                        "erreur": str(e),
                    }
                )
                details.append(
                    {
                        "operation": "classement",
                        "type": "erreur",
                        "source": str(source),
                        "erreur": str(e),
                    }
                )

        ops = {"tente": tente, "reussi": reussi, "echoue": tente - reussi}
        return ops, erreurs, details

    def _executer_deduplication(
        self,
        apercu_dedup: dict[str, Any],
        simuler: bool = True,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        """Exécute la suppression des doublons et le renommage des gardes."""
        supprime = 0
        renomme_gardes = 0
        tente_suppression = 0
        tente_renommage = 0
        erreurs: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []

        for idx, groupe in enumerate(apercu_dedup.get("groupes", [])):
            if on_progress:
                on_progress("deduplication", idx + 1, len(apercu_dedup.get("groupes", [])))
            garde: FichierInfo | None = groupe.get("garde")
            supprimables: list[FichierInfo] = groupe.get("supprimables", [])

            # ── Renommage du garde si conflit résolu ──
            nouveau_nom = groupe.get("garde_nouveau_nom")
            if garde and nouveau_nom:
                ancien_path = garde.path
                nouveau_path = ancien_path.parent / nouveau_nom
                tente_renommage += 1

                if not simuler:
                    try:
                        if nouveau_path.exists():
                            raise FileExistsError(f"Le fichier garde destination existe déjà : {nouveau_path}")
                        ancien_path.rename(nouveau_path)
                        garde.path = nouveau_path
                        renomme_gardes += 1
                        details.append(
                            {
                                "operation": "deduplication_renommage_garde",
                                "type": "reussi",
                                "ancien": str(ancien_path),
                                "nouveau": str(nouveau_path),
                            }
                        )
                    except Exception as e:
                        erreurs.append(
                            {
                                "operation": "deduplication_renommage_garde",
                                "fichier": str(ancien_path),
                                "erreur": str(e),
                            }
                        )
                        details.append(
                            {
                                "operation": "deduplication_renommage_garde",
                                "type": "erreur",
                                "ancien": str(ancien_path),
                                "erreur": str(e),
                            }
                        )
                else:
                    renomme_gardes += 1
                    details.append(
                        {
                            "operation": "deduplication_renommage_garde",
                            "type": "simulation",
                            "ancien": str(ancien_path),
                            "nouveau": str(nouveau_path),
                        }
                    )

            # ── Suppression des doublons ──
            for f in supprimables:
                tente_suppression += 1

                if simuler:
                    details.append(
                        {
                            "operation": "deduplication_suppression",
                            "type": "simulation",
                            "fichier": str(f.path),
                            "taille": f.size,
                        }
                    )
                    supprime += 1
                    continue

                try:
                    deplacer_vers_corbeille(f.path)
                    supprime += 1
                    details.append(
                        {
                            "operation": "deduplication_suppression",
                            "type": "reussi",
                            "fichier": str(f.path),
                            "taille": f.size,
                        }
                    )
                except Exception as e:
                    erreurs.append(
                        {
                            "operation": "deduplication_suppression",
                            "fichier": str(f.path),
                            "erreur": str(e),
                        }
                    )
                    details.append(
                        {
                            "operation": "deduplication_suppression",
                            "type": "erreur",
                            "fichier": str(f.path),
                            "erreur": str(e),
                        }
                    )

        ops = {
            "supprime": supprime,
            "renomme_gardes": renomme_gardes,
            "tente": tente_suppression + tente_renommage,
            "echoue": len(erreurs),
        }
        return ops, erreurs, details

    def _executer_nettoyage(
        self,
        apercu_nettoyage: dict[str, Any],
        simuler: bool = True,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        """Exécute la suppression des fichiers temporaires."""
        tente = 0
        supprime = 0
        taille_total = 0
        erreurs: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []

        for idx, entry in enumerate(apercu_nettoyage.get("fichiers", [])):
            if on_progress:
                on_progress("nettoyage", idx + 1, len(apercu_nettoyage.get("fichiers", [])))
            chemin: Path = entry["chemin"]
            taille = entry.get("taille", 0)
            tente += 1
            taille_total += taille

            if simuler:
                details.append(
                    {
                        "operation": "nettoyage",
                        "type": "simulation",
                        "fichier": str(chemin),
                        "taille": taille,
                    }
                )
                supprime += 1
                continue

            try:
                deplacer_vers_corbeille(chemin)
                supprime += 1
                details.append(
                    {
                        "operation": "nettoyage",
                        "type": "reussi",
                        "fichier": str(chemin),
                        "taille": taille,
                    }
                )
            except Exception as e:
                erreurs.append(
                    {
                        "operation": "nettoyage",
                        "fichier": str(chemin),
                        "erreur": str(e),
                    }
                )
                details.append(
                    {
                        "operation": "nettoyage",
                        "type": "erreur",
                        "fichier": str(chemin),
                        "erreur": str(e),
                    }
                )

        ops = {
            "tente": tente,
            "supprime": supprime,
            "echoue": tente - supprime,
            "taille_total": taille_total,
            "taille_lisible": _taille_lisible(taille_total),
        }
        return ops, erreurs, details

    # ── Patterns filename ─────────────────────────────────────────

    @property
    def filename_patterns(self) -> list[re.Pattern]:
        """Patterns regex utilisés pour le parsing des noms de fichiers."""
        return list(self._filename_patterns)

    def set_filename_patterns(self, patterns: list[re.Pattern]) -> None:
        """Remplace les patterns de parsing."""
        self._filename_patterns = list(patterns)

    # ── Intégration Planificateur ────────────────────────────────────────

    def executer_action_planificateur(
        self,
        action_type: str,
        params: dict[str, Any],
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Exécute une action individuelle pour le Planificateur.

        Args:
            action_type: 'classement', 'renommage', 'deduplication', 'nettoyage_temp'
            params: Paramètres (dossier, template, age_jours, etc.)
            on_progress: Callback de progression (section, fait, total)

        Returns:
            Dict avec 'succes', 'message', 'details'
        """
        dossier = params.get("dossier", "")

        try:
            if action_type == "renommage":
                template = params.get("template", TEMPLATE_RENOMMAGE_DEFAUT)
                analyse = self.analyser_dossier(dossier)
                apercu = self.preparer_renommage(analyse, template=template)
                ops, erreurs, details = self._executer_renommage(apercu, simuler=False, on_progress=on_progress)
                msg = f"Renommage : {ops.get('reussi', 0)}/{ops.get('total', 0)} fichiers renommés"

            elif action_type == "classement":
                template = params.get("template", TEMPLATE_CLASSEMENT_DEFAUT)
                analyse = self.analyser_dossier(dossier)
                apercu = self.preparer_classement(analyse, template=template)
                ops, erreurs, details = self._executer_classement(apercu, simuler=False, on_progress=on_progress)
                msg = f"Classement : {ops.get('reussi', 0)}/{ops.get('total', 0)} fichiers classés"

            elif action_type == "deduplication":
                analyse = self.analyser_dossier(dossier)
                apercu = self.preparer_deduplication(analyse)
                ops, erreurs, details = self._executer_deduplication(apercu, simuler=False, on_progress=on_progress)
                msg = f"Dédoublonnage : {ops.get('supprime', 0)} doublons supprimés"

            elif action_type == "nettoyage_temp":
                age_jours = params.get("age_jours", 7)
                apercu = self.preparer_nettoyage(dossier, age_max_jours=age_jours)
                ops, erreurs, details = self._executer_nettoyage(apercu, simuler=False, on_progress=on_progress)
                msg = f"Nettoyage : {ops.get('supprime', 0)} fichiers supprimés ({ops.get('taille_lisible', '0 o')})"

            else:
                return {"succes": False, "message": f"Type d'action inconnu : {action_type}", "details": []}

            succes = len(erreurs) == 0
            if not succes:
                msg += f" — {len(erreurs)} erreur(s)"

            return {
                "succes": succes,
                "message": msg,
                "details": details,
                "ops": ops,
                "erreurs": erreurs,
            }

        except Exception as e:
            return {
                "succes": False,
                "message": f"Erreur lors de {action_type} : {e}",
                "details": [],
            }


# ── Helpers utilitaires (module-level) ────────────────────────────────


def _parser_piste(raw: str | None) -> int | None:
    """Parse un numéro de piste depuis une chaîne."""
    if not raw:
        return None
    raw = raw.strip()
    # "5/12" → 5
    if "/" in raw:
        raw = raw.split("/")[0]
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _parser_annee(raw: str | None) -> int | None:
    """Parse une année depuis une chaîne (date, année seule, etc.)."""
    if not raw:
        return None
    raw = raw.strip()
    # "2024-01-15" → 2024
    for sep in ("-", "/", "."):
        if sep in raw:
            raw = raw.split(sep)[0]
    try:
        return int(raw[:4])
    except (ValueError, IndexError, TypeError):
        return None
