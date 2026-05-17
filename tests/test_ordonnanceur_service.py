"""Tests unitaires pour OrdonnanceurService.

Teste : scan, analyse métadonnées, parsing filename, templates,
détection de doublons, estimations d'opérations, et corbeille dédiée.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from src.services.ordonnanceur_service import (
    AUDIO_EXTENSIONS,
    CLASSEMENT_PRESETS,
    RENOMMAGE_PRESETS,
    TEMPLATE_CLASSEMENT_DEFAUT,
    TEMPLATE_RENOMMAGE_DEFAUT,
    AnalyseResultat,
    FichierInfo,
    OrdonnanceurService,
    _est_fichier_audio,
    _identifier_codec,
    _parser_annee,
    _parser_piste,
    _taille_lisible,
    deplacer_vers_corbeille,
    settings,
)

# ── Helpers ────────────────────────────────────────────────────────


class TestTailleLisible:
    def test_zero(self) -> None:
        assert _taille_lisible(0) == "0 o"

    def test_octets(self) -> None:
        assert _taille_lisible(500) == "500 o"

    def test_kilo(self) -> None:
        assert _taille_lisible(2048) == "2.0 Ko"

    def test_mega(self) -> None:
        assert _taille_lisible(5_242_880) == "5.0 Mo"

    def test_giga(self) -> None:
        assert _taille_lisible(3_221_225_472) == "3.00 Go"


class TestParserPiste:
    def test_simple(self) -> None:
        assert _parser_piste("5") == 5

    def test_zero_padded(self) -> None:
        assert _parser_piste("05") == 5

    def test_avec_total(self) -> None:
        assert _parser_piste("5/12") == 5

    def test_zero_padded_avec_total(self) -> None:
        assert _parser_piste("01/12") == 1

    def test_vide(self) -> None:
        assert _parser_piste("") is None

    def test_none(self) -> None:
        assert _parser_piste(None) is None

    def test_invalide(self) -> None:
        assert _parser_piste("ABC") is None

    def test_avec_espaces(self) -> None:
        assert _parser_piste("  03  ") == 3


class TestParserAnnee:
    def test_annee_seule(self) -> None:
        assert _parser_annee("2024") == 2024

    def test_date_iso(self) -> None:
        assert _parser_annee("2024-01-15") == 2024

    def test_date_slash(self) -> None:
        assert _parser_annee("2024/03/21") == 2024

    def test_annee_dans_chaine(self) -> None:
        assert _parser_annee("2024-01") == 2024

    def test_vide(self) -> None:
        assert _parser_annee("") is None

    def test_none(self) -> None:
        assert _parser_annee(None) is None

    def test_invalide(self) -> None:
        assert _parser_annee("pas une année") is None

    def test_troncature_4_premiers(self) -> None:
        # "2024-01-15T00:00:00"
        assert _parser_annee("2024-01-15T00:00:00") == 2024


# ── EstFichierAudio (tests sans fichiers réels) ────────────────────


class TestEstFichierAudio:
    def test_extension_supportee(self, tmp_path: Path) -> None:
        f = tmp_path / "test.mp3"
        f.write_text("x" * (100 * 1024 + 1))
        assert _est_fichier_audio(f) is True

    def test_extension_non_supportee(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("x" * (100 * 1024 + 1))
        assert _est_fichier_audio(f) is False

    def test_fichier_trop_petit(self, tmp_path: Path) -> None:
        f = tmp_path / "test.mp3"
        f.write_text("small")
        assert _est_fichier_audio(f) is False

    def test_dossier(self, tmp_path: Path) -> None:
        d = tmp_path / "test.mp3"
        d.mkdir()
        assert _est_fichier_audio(d) is False

    def test_extensions_valides(self) -> None:
        for ext in [".mp3", ".flac", ".ogg", ".m4a", ".wav", ".aac"]:
            assert ext in AUDIO_EXTENSIONS, f"{ext} devrait être supporté"


class TestIdentifierCodec:
    """Teste le mapping nom_classe → codec."""

    def test_mp3(self) -> None:
        class FakeMP3:
            __name__ = "MP3"

        assert _identifier_codec(Path("f.mp3"), FakeMP3()) == "mp3"

    def test_flac(self) -> None:
        class FakeFLAC:
            __name__ = "FLAC"

        assert _identifier_codec(Path("f.flac"), FakeFLAC()) == "flac"

    def test_inconnu(self) -> None:
        class FakeUnknown:
            __name__ = "UnknownFormat"

        assert _identifier_codec(Path("f.wma"), FakeUnknown()) == "wma"


# ── Filename Parsing ───────────────────────────────────────────────


class TestParserNomFichier:
    """Teste _parser_nom_fichier avec différents formats de noms."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    def test_classique_complet(self, svc: OrdonnanceurService) -> None:
        """Artiste - Album - 01 Titre"""
        r = svc._parser_nom_fichier("Artist - Album - 01 Title")
        assert r is not None
        assert r["artist"] == "Artist"
        assert r["album"] == "Album"
        assert r["track"] == 1
        assert r["title"] == "Title"

    def test_artiste_titre(self, svc: OrdonnanceurService) -> None:
        """Artiste - Titre (sans album ni piste)"""
        r = svc._parser_nom_fichier("Artist - Title")
        assert r is not None
        assert r["artist"] == "Artist"
        assert r["title"] == "Title"
        assert "album" not in r
        assert "track" not in r

    def test_piste_titre(self, svc: OrdonnanceurService) -> None:
        """01 Titre (sans artiste)"""
        r = svc._parser_nom_fichier("01 Title")
        assert r is not None
        assert r["track"] == 1
        assert r["title"] == "Title"
        assert "artist" not in r

    def test_titre_seul(self, svc: OrdonnanceurService) -> None:
        """Juste un titre, sans structuration"""
        r = svc._parser_nom_fichier("Track without artist")
        assert r is not None
        assert r["title"] == "Track without artist"

    def test_avec_source(self, svc: OrdonnanceurService) -> None:
        """[VIP] Artiste - Album - 01 Titre"""
        r = svc._parser_nom_fichier("[VIP] Artist - Album - 01 Title")
        assert r is not None
        assert r["artist"] == "Artist"
        assert r["album"] == "Album"
        assert r["track"] == 1
        assert r["title"] == "Title"

    def test_avec_annee_parentheses(self, svc: OrdonnanceurService) -> None:
        """Titre (2024)"""
        r = svc._parser_nom_fichier("Artist - Album - 01 Title (2024)")
        assert r is not None
        assert r["year"] == 2024
        assert r["title"] == "Title"

    def test_avec_annee_tiret_apres_album(self, svc: OrdonnanceurService) -> None:
        """Artist - Album - 01 Title - 2024 (année après tiret après un titre complet)"""
        r = svc._parser_nom_fichier("Artist - Album - 01 Title - 2024")
        assert r is not None
        assert r["artist"] == "Artist"
        assert r["album"] == "Album"
        assert r["track"] == 1
        assert r["title"] == "Title"
        # L'année extraite via year2 est gérée dans analyser_fichier, pas dans _parser_nom_fichier
        # On vérifie juste que le titre est correct
        assert r.get("year") is None or r["year"] == 2024

    def test_avec_qualite(self, svc: OrdonnanceurService) -> None:
        """Titre [320kbps]"""
        r = svc._parser_nom_fichier("Artist - Album - 01 Title [320kbps]")
        assert r is not None
        assert r["title"] == "Title"

    def test_tiret_em_dash(self, svc: OrdonnanceurService) -> None:
        """Artiste — Titre (em dash)"""
        r = svc._parser_nom_fichier("Artist — Title")
        assert r is not None
        assert r["artist"] == "Artist"
        assert r["title"] == "Title"

    def test_triplet_artiste_album_titre(self, svc: OrdonnanceurService) -> None:
        """Triplet artiste - album - titre parsé par PATTERN_CLASSIQUE"""
        r = svc._parser_nom_fichier("Just - Artist - Name")
        assert r is not None
        assert r["artist"] == "Just"
        assert r["album"] == "Artist"
        assert r["title"] == "Name"


# ── Analyse fichier (mocked) ───────────────────────────────────────


class TestAnalyserFichierSansMutagen:
    """Teste analyser_fichier avec des fichiers réels sans tags mutagen.

    Comme les fichiers de test n'ont pas de vrais tags audio,
    le fallback sur le parsing du nom de fichier est testé.
    """

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    def test_analyse_fichier_basique(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Analyse un fichier .mp3 minimal — doit tomber en fallback pattern."""
        audio_dir = tmp_path / "Artist - Album"
        audio_dir.mkdir(parents=True)
        f = audio_dir / "01 Song Title.mp3"
        f.write_text("x" * (100 * 1024 + 1))

        info = svc.analyser_fichier(f)
        assert info.filename == "01 Song Title.mp3"
        assert info.extension == ".mp3"
        assert info.size > 0
        # Fallback pattern
        assert info.title == "Song Title"
        assert info.track == 1
        assert info.source_metadata in ("pattern", "tag")

    def test_analyse_dossier(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Analyse complète d'un dossier avec plusieurs fichiers."""
        audio_dir = tmp_path / "Music"
        audio_dir.mkdir(parents=True)

        for name in ["Artist - 01 Song A.mp3", "Artist - 02 Song B.mp3"]:
            (audio_dir / name).write_text("x" * (100 * 1024 + 1))

        result = svc.analyser_dossier(audio_dir, recursive=False)
        assert result.total_audio == 2
        assert result.dossier_source == audio_dir
        assert len(result.fichiers) == 2

    def test_analyse_recursive(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Analyse récursive avec sous-dossiers."""
        root = tmp_path / "Root"
        sub = root / "Subfolder"
        root.mkdir(parents=True)
        sub.mkdir(parents=True)

        (root / "01 Track A.mp3").write_text("x" * (100 * 1024 + 1))
        (sub / "02 Track B.mp3").write_text("x" * (100 * 1024 + 1))

        result = svc.analyser_dossier(root, recursive=True)
        assert result.total_audio == 2

        result_non_rec = svc.analyser_dossier(root, recursive=False)
        assert result_non_rec.total_audio == 1

    def test_dossier_introuvable(self, svc: OrdonnanceurService) -> None:
        """Dossier inexistant → résultat vide."""
        result = svc.analyser_dossier("/inexistant/path")
        assert result.total_audio == 0
        assert result.fichiers == []

    def test_fichier_non_audio_ignore(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Les fichiers non-audio (.txt, .jpg) sont ignorés."""
        d = tmp_path / "test"
        d.mkdir()
        (d / "song.mp3").write_text("x" * (100 * 1024 + 1))
        (d / "cover.jpg").write_text("x" * (100 * 1024 + 1))
        (d / "notes.txt").write_text("hello")

        result = svc.analyser_dossier(d)
        assert result.total_audio == 1

    def test_fichier_trop_petit_ignore(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Les fichiers trop petits (< 100 Ko) sont ignorés."""
        d = tmp_path / "test"
        d.mkdir()
        (d / "real.mp3").write_text("x" * (100 * 1024 + 1))
        (d / "short.mp3").write_text("tiny")

        result = svc.analyser_dossier(d)
        assert result.total_audio == 1

    def test_annee_dans_nom_fichier(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """L'année dans le nom du fichier est extraite via year2 dans analyser_fichier."""
        d = tmp_path / "test"
        d.mkdir()
        # Format non-ambigu : album + track + title + " - 2024" -> year2 match
        f = d / "Artist - Album - 01 Title - 2024.mp3"
        f.write_text("x" * (100 * 1024 + 1))

        info = svc.analyser_fichier(f)
        assert info.title == "Title"
        assert info.year == 2024
        assert info.track == 1


# ── Templates ──────────────────────────────────────────────────────


class TestTemplates:
    """Teste generer_nom_fichier et generer_chemin_classement."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    @pytest.fixture
    def info(self) -> FichierInfo:
        return FichierInfo(
            path=Path("music/Artist - Album - 01 Song.mp3"),
            filename="Artist - Album - 01 Song.mp3",
            extension=".mp3",
            size=5_000_000,
            modified=1_700_000_000.0,
            artist="TestArtist",
            album="TestAlbum",
            title="TestTitle",
            track=3,
            year=2024,
            genre="Rock",
        )

    def test_renommage_default(self, svc: OrdonnanceurService, info: FichierInfo) -> None:
        name = svc.generer_nom_fichier(info)
        # {artist} - {album} - {track:02d} {title}.{ext}
        assert name == "TestArtist - TestAlbum - 03 TestTitle.mp3"

    def test_classement_default(self, svc: OrdonnanceurService, info: FichierInfo) -> None:
        chemin = svc.generer_chemin_classement(info, racine="downloads")
        # {artist}/{album}/{track:02d} {title}.{ext}
        assert chemin == Path("downloads/TestArtist/TestAlbum/03 TestTitle.mp3")

    def test_renommage_sans_album(self, svc: OrdonnanceurService) -> None:
        info = FichierInfo(
            path=Path("song.mp3"),
            filename="song.mp3",
            extension=".mp3",
            size=100_000,
            modified=0.0,
            artist="Artist",
            title="Title",
        )
        name = svc.generer_nom_fichier(info)
        assert "Inconnu" in name  # album fallback

    def test_classement_preset_artiste(self, svc: OrdonnanceurService, info: FichierInfo) -> None:
        template = CLASSEMENT_PRESETS["artiste"]
        chemin = svc.generer_chemin_classement(info, racine="", template=template)
        assert chemin == Path("TestArtist/03 TestTitle.mp3")

    def test_renommage_preset_piste_titre(self, svc: OrdonnanceurService, info: FichierInfo) -> None:
        template = RENOMMAGE_PRESETS["piste-titre"]
        name = svc.generer_nom_fichier(info, template=template)
        assert name == "03 TestTitle.mp3"

    def test_caracteres_invalides_nettoyes(self, svc: OrdonnanceurService) -> None:
        """Les caractères interdits dans les noms de fichiers sont remplacés."""
        info = FichierInfo(
            path=Path("bad.mp3"),
            filename="bad.mp3",
            extension=".mp3",
            size=100_000,
            modified=0.0,
            artist="Artist:Test",
            album="Album|Name",
            title="Title?File*",
        )
        name = svc.generer_nom_fichier(info)
        assert "<" not in name
        assert ">" not in name
        assert ":" not in name or "\\" in name  # : est interdit sur Windows
        assert "?" not in name
        assert "*" not in name

    def test_fallback_filename(self, svc: OrdonnanceurService) -> None:
        """Sans titre, utilise le stem du fichier comme fallback."""
        info = FichierInfo(
            path=Path("mysterious_song.mp3"),
            filename="mysterious_song.mp3",
            extension=".mp3",
            size=100_000,
            modified=0.0,
        )
        name = svc.generer_nom_fichier(info, template="{title}.{ext}")
        assert name == "mysterious_song.mp3"


# ── Doublons ───────────────────────────────────────────────────────


class TestDoublons:
    """Teste la détection de doublons."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    def test_pas_de_doublons(self, svc: OrdonnanceurService) -> None:
        fichiers = [
            FichierInfo(path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0, title="A"),
            FichierInfo(path=Path("b.mp3"), filename="b.mp3", extension=".mp3", size=2000, modified=0.0, title="B"),
        ]
        doublons = svc._detecter_doublons_rapide(fichiers)
        assert doublons == []

    def test_doublons_nom_taille(self, svc: OrdonnanceurService) -> None:
        fichiers = [
            FichierInfo(path=Path("dup.mp3"), filename="dup.mp3", extension=".mp3", size=1000, modified=0.0, title="A"),
            FichierInfo(path=Path("dup.mp3"), filename="dup.mp3", extension=".mp3", size=1000, modified=0.0, title="B"),
            FichierInfo(
                path=Path("unique.mp3"), filename="unique.mp3", extension=".mp3", size=2000, modified=0.0, title="C"
            ),
        ]
        doublons = svc._detecter_doublons_rapide(fichiers)
        assert len(doublons) == 1
        assert len(doublons[0]) == 2

    def test_doublons_insensible_casse(self, svc: OrdonnanceurService) -> None:
        fichiers = [
            FichierInfo(
                path=Path("Song.mp3"), filename="Song.mp3", extension=".mp3", size=1000, modified=0.0, title="A"
            ),
            FichierInfo(
                path=Path("song.mp3"), filename="song.mp3", extension=".mp3", size=1000, modified=0.0, title="B"
            ),
        ]
        doublons = svc._detecter_doublons_rapide(fichiers)
        assert len(doublons) == 1


# ── Estimations ────────────────────────────────────────────────────


class TestEstimations:
    """Teste estimer_operations."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    @pytest.fixture
    def analyse(self) -> AnalyseResultat:
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"),
                filename="a.mp3",
                extension=".mp3",
                size=1_000_000,
                modified=0.0,
                artist="ArtistA",
                title="TitleA",
                album="AlbumA",
            ),
            FichierInfo(
                path=Path("b.mp3"),
                filename="b.mp3",
                extension=".mp3",
                size=2_000_000,
                modified=0.0,
                artist="ArtistA",
                title="TitleB",
                album="AlbumA",
            ),
            FichierInfo(
                path=Path("c.mp3"),
                filename="c.mp3",
                extension=".mp3",
                size=3_000_000,
                modified=0.0,
                artist=None,
                title=None,
            ),  # sans metadata
            FichierInfo(
                path=Path("d.mp3"),
                filename="d.mp3",
                extension=".mp3",
                size=1_000_000,
                modified=0.0,
                artist="ArtistA",
                title="TitleA",
                album="AlbumA",
            ),
            FichierInfo(
                path=Path("e.mp3"),
                filename="e.mp3",
                extension=".mp3",
                size=1_000_000,
                modified=0.0,
                artist="ArtistA",
                title="TitleA",
                album="AlbumA",
            ),
        ]
        doublons = [[fichiers[0], fichiers[3]], [fichiers[0], fichiers[4]]]
        # Note: doublons_potentiels is normally filled by _detecter_doublons_rapide
        return AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=5,
            total_audio=5,
            total_taille=8_000_000,
            doublons_potentiels=doublons,
            fichiers_sans_metadata=[fichiers[2]],
        )

    def test_classement(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        est = svc.estimer_operations(analyse, {"classement"})
        assert "classement" in est
        assert est["classement"]["fichiers"] == 4  # ceux avec artist

    def test_renommage(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        est = svc.estimer_operations(analyse, {"renommage"})
        assert "renommage" in est
        assert est["renommage"]["fichiers"] == 4  # ceux avec artist ou title

    def test_dedoublonnage(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        est = svc.estimer_operations(analyse, {"dedoublonner"})
        assert "dedoublonner" in est
        assert est["dedoublonner"]["groupes"] == 2
        assert est["dedoublonner"]["fichiers_a_supprimer"] == 2  # 1 par groupe

    def test_multiple_operations(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        est = svc.estimer_operations(analyse, {"classement", "renommage"})
        assert "classement" in est
        assert "renommage" in est
        assert "dedoublonner" not in est

    def test_aucune_operation(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        est = svc.estimer_operations(analyse, set())
        assert est == {}


# ── AnalyseResultat properties ─────────────────────────────────────


class TestAnalyseResultat:
    def test_taille_lisible(self) -> None:
        result = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=[],
            total_fichiers=0,
            total_audio=0,
            total_taille=2_048_000,
        )
        assert result.total_taille_lisible == "2.0 Mo"

    def test_zero_taille(self) -> None:
        result = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=[],
            total_fichiers=0,
            total_audio=0,
            total_taille=0,
        )
        assert result.total_taille_lisible == "0 o"


# ── Patterns filename (configurabilité) ────────────────────────────


# ── Preview des opérations ────────────────────────────────────


class TestPreparerRenommage:
    """Teste preparer_renommage : génération des nouveaux noms et conflits."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    @pytest.fixture
    def analyse(self) -> AnalyseResultat:
        fichiers = [
            FichierInfo(
                path=Path("music/Artist - Album - 01 Song.mp3"),
                filename="Artist - Album - 01 Song.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=1_700_000_000.0,
                artist="Artist",
                album="Album",
                title="Song",
                track=1,
                year=2024,
            ),
            FichierInfo(
                path=Path("music/02 Track B.mp3"),
                filename="02 Track B.mp3",
                extension=".mp3",
                size=4_000_000,
                modified=1_700_000_000.0,
                artist="Artist",
                album="Album",
                title="Track B",
                track=2,
            ),
            FichierInfo(
                path=Path("music/no_artist.mp3"),
                filename="no_artist.mp3",
                extension=".mp3",
                size=3_000_000,
                modified=1_700_000_000.0,
            ),
        ]
        return AnalyseResultat(
            dossier_source=Path("/music"),
            fichiers=fichiers,
            total_fichiers=3,
            total_audio=3,
            total_taille=12_000_000,
        )

    def test_renommage_complet(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        """1er fichier déjà bien nommé (template = filename), 2e à renommer."""
        apercu = svc.preparer_renommage(analyse)
        # Le 1er fichier "Artist - Album - 01 Song.mp3" correspond déjà au template
        # Seul le 2e "02 Track B.mp3" sera renommé → "Artist - Album - 02 Track B.mp3"
        assert apercu["total"] == 1
        assert len(apercu["fichiers"]) == 1
        assert apercu["conflits"] == []
        assert "nouveau_nom" in apercu["fichiers"][0]
        assert apercu["fichiers"][0]["nouveau_nom"] == "Artist - Album - 02 Track B.mp3"

    def test_pas_de_renommage_sans_metadata(self, svc: OrdonnanceurService) -> None:
        fichiers = [
            FichierInfo(path=Path("unknown.mp3"), filename="unknown.mp3", extension=".mp3", size=1000, modified=0.0),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=1,
            total_audio=1,
            total_taille=1000,
        )
        apercu = svc.preparer_renommage(analyse)
        assert apercu["total"] == 0

    def test_conflits_detectes(self, svc: OrdonnanceurService) -> None:
        """Deux fichiers avec le même artiste/album/titre génèrent le même nouveau nom."""
        fichiers = [
            FichierInfo(
                path=Path("sub1/song.mp3"),
                filename="song.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                artist="Artist",
                album="Album",
                title="Song",
                track=1,
            ),
            FichierInfo(
                path=Path("sub2/song.mp3"),
                filename="song.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                artist="Artist",
                album="Album",
                title="Song",
                track=1,
            ),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=10_000_000,
        )
        apercu = svc.preparer_renommage(analyse)
        assert len(apercu["conflits"]) == 1
        assert apercu["conflits"][0]["nb"] == 2
        assert apercu["conflits"][0]["nom_conflit"] == "Artist - Album - 01 Song.mp3"


class TestPreparerClassement:
    """Teste preparer_classement : génération des chemins et regroupement."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    @pytest.fixture
    def analyse(self) -> AnalyseResultat:
        fichiers = [
            FichierInfo(
                path=Path("downloads/ArtistA - AlbumA - 01 Song.mp3"),
                filename="ArtistA - AlbumA - 01 Song.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                artist="ArtistA",
                album="AlbumA",
                title="Song",
                track=1,
            ),
            FichierInfo(
                path=Path("downloads/ArtistA - AlbumA - 02 Track.mp3"),
                filename="ArtistA - AlbumA - 02 Track.mp3",
                extension=".mp3",
                size=4_000_000,
                modified=0.0,
                artist="ArtistA",
                album="AlbumA",
                title="Track",
                track=2,
            ),
            FichierInfo(
                path=Path("downloads/ArtistB - Song.mp3"),
                filename="ArtistB - Song.mp3",
                extension=".mp3",
                size=3_000_000,
                modified=0.0,
                artist="ArtistB",
                title="Song",
            ),
            FichierInfo(
                path=Path("downloads/nometadata.mp3"),
                filename="nometadata.mp3",
                extension=".mp3",
                size=2_000_000,
                modified=0.0,
            ),
        ]
        return AnalyseResultat(
            dossier_source=Path("/downloads"),
            fichiers=fichiers,
            total_fichiers=4,
            total_audio=4,
            total_taille=14_000_000,
        )

    def test_classement_artiste(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        apercu = svc.preparer_classement(analyse, racine="organized")
        assert apercu["total"] == 3  # 3 fichiers avec artiste
        assert apercu["nb_artistes"] == 2
        assert apercu["artistes"]["ArtistA"] == 2
        assert apercu["artistes"]["ArtistB"] == 1
        assert apercu["conflits"] == []

    def test_sans_racine(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        apercu = svc.preparer_classement(analyse)
        assert apercu["total"] == 3
        # Chemin relatif sans racine
        chemin_a1 = str(apercu["fichiers"][0]["nouveau_chemin"])
        assert "ArtistA" in chemin_a1
        assert "AlbumA" in chemin_a1

    def test_conflits_classement(self, svc: OrdonnanceurService) -> None:
        """Deux fichiers avec le même artiste/album/titre génèrent le même chemin."""
        fichiers = [
            FichierInfo(
                path=Path("sub1/a.mp3"),
                filename="a.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                artist="Artist",
                album="Album",
                title="Song",
                track=1,
            ),
            FichierInfo(
                path=Path("sub2/b.mp3"),
                filename="b.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                artist="Artist",
                album="Album",
                title="Song",
                track=1,
            ),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=10_000_000,
        )
        apercu = svc.preparer_classement(analyse, racine="music")
        assert len(apercu["conflits"]) == 1
        assert apercu["conflits"][0]["nb"] == 2

    def test_aucun_artiste(self, svc: OrdonnanceurService) -> None:
        fichiers = [
            FichierInfo(path=Path("no.mp3"), filename="no.mp3", extension=".mp3", size=1000, modified=0.0),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=1,
            total_audio=1,
            total_taille=1000,
        )
        apercu = svc.preparer_classement(analyse)
        assert apercu["total"] == 0


class TestPreparerDeduplication:
    """Teste preparer_deduplication : mise en forme des doublons résolus."""

    def test_avec_doublons_confirmes(self) -> None:
        fichiers = [
            FichierInfo(
                path=Path("garde.mp3"),
                filename="garde.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                hash_sha256="abc",
            ),
            FichierInfo(
                path=Path("dup1.mp3"),
                filename="dup1.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                hash_sha256="abc",
            ),
            FichierInfo(
                path=Path("unique.mp3"),
                filename="unique.mp3",
                extension=".mp3",
                size=3_000_000,
                modified=0.0,
                hash_sha256="def",
            ),
        ]
        resol = {
            "groupe": fichiers[:2],
            "garde": fichiers[0],
            "supprimables": [fichiers[1]],
            "exclus": [],
            "taille_economisee": 5_000_000,
        }
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=3,
            total_audio=3,
            total_taille=13_000_000,
            doublons_potentiels=[[fichiers[0], fichiers[1]]],
            doublons_confirmes=[[fichiers[0], fichiers[1]]],
            doublons_resolus=[resol],
        )
        apercu = OrdonnanceurService.preparer_deduplication(analyse)
        assert apercu["nb_groupes"] == 1
        assert apercu["total_doublons"] == 1
        assert apercu["total_economise"] == 5_000_000
        assert "Mo" in apercu["total_lisible"]

    def test_fallback_potentiels(self) -> None:
        """Sans doublons confirmés, utilise les potentiels."""
        fichiers = [
            FichierInfo(path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0),
            FichierInfo(path=Path("b.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=2000,
            doublons_potentiels=[[fichiers[0], fichiers[1]]],
        )
        apercu = OrdonnanceurService.preparer_deduplication(analyse)
        assert apercu["nb_groupes"] == 1
        assert apercu["total_doublons"] == 1

    def test_aucun_doublon(self) -> None:
        fichiers = [
            FichierInfo(path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0),
            FichierInfo(path=Path("b.mp3"), filename="b.mp3", extension=".mp3", size=2000, modified=0.0),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=3000,
        )
        apercu = OrdonnanceurService.preparer_deduplication(analyse)
        assert apercu["nb_groupes"] == 0
        assert apercu["total_doublons"] == 0
        assert apercu["total_economise"] == 0
        assert apercu["conflits"] == []
        assert apercu["conflits_resolus"] == []

    def test_conflit_gardes_meme_nom(self) -> None:
        """2 groupes avec garde même nom → résolu avec _2."""
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"),
                filename="track.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                hash_sha256="abc",
            ),
            FichierInfo(
                path=Path("a_dup.mp3"),
                filename="track.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                hash_sha256="abc",
            ),
            FichierInfo(
                path=Path("b.mp3"),
                filename="track.mp3",
                extension=".mp3",
                size=4_000_000,
                modified=0.0,
                hash_sha256="def",
            ),
            FichierInfo(
                path=Path("b_dup.mp3"),
                filename="track.mp3",
                extension=".mp3",
                size=4_000_000,
                modified=0.0,
                hash_sha256="def",
            ),
        ]
        resol_a = {
            "groupe": fichiers[:2],
            "garde": fichiers[0],
            "supprimables": [fichiers[1]],
            "exclus": [],
            "taille_economisee": 5_000_000,
        }
        resol_b = {
            "groupe": fichiers[2:],
            "garde": fichiers[2],
            "supprimables": [fichiers[3]],
            "exclus": [],
            "taille_economisee": 4_000_000,
        }
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=4,
            total_audio=4,
            total_taille=18_000_000,
            doublons_resolus=[resol_a, resol_b],
        )
        apercu = OrdonnanceurService.preparer_deduplication(analyse)
        assert apercu["conflits"] == []  # vidé après résolution
        assert apercu["conflits_resolus"][0]["nom_conflit"] == "track.mp3"
        assert apercu["conflits_resolus"][0]["resolutions"][0]["nouveau_nom"] == "track.mp3"
        assert apercu["conflits_resolus"][0]["resolutions"][1]["nouveau_nom"] == "track_2.mp3"
        # Résolution : premier garde conserve, second prend _2
        assert len(apercu["conflits_resolus"]) == 1
        assert "garde_nouveau_nom" not in apercu["groupes"][0]
        assert apercu["groupes"][1]["garde_nouveau_nom"] == "track_2.mp3"
        # Stats inchangées
        assert apercu["nb_groupes"] == 2
        assert apercu["total_doublons"] == 2

    def test_conflit_gardes_trois_meme_nom(self) -> None:
        """3 groupes avec garde même nom → _2, _3."""
        fichiers = []
        resol = []
        for i in range(3):
            f1 = FichierInfo(
                path=Path(f"g{i}.mp3"),
                filename="same.mp3",
                extension=".mp3",
                size=1000,
                modified=0.0,
                hash_sha256=f"h{i}",
            )
            f2 = FichierInfo(
                path=Path(f"d{i}.mp3"),
                filename="same.mp3",
                extension=".mp3",
                size=1000,
                modified=0.0,
                hash_sha256=f"h{i}",
            )
            fichiers.extend([f1, f2])
            resol.append(
                {
                    "groupe": [f1, f2],
                    "garde": f1,
                    "supprimables": [f2],
                    "exclus": [],
                    "taille_economisee": 1000,
                }
            )
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=6,
            total_audio=6,
            total_taille=6000,
            doublons_resolus=resol,
        )
        apercu = OrdonnanceurService.preparer_deduplication(analyse)
        assert apercu["conflits"] == []  # vidé après résolution
        assert len(apercu["conflits_resolus"]) == 1
        assert apercu["conflits_resolus"][0]["resolutions"][0]["nouveau_nom"] == "same.mp3"
        assert apercu["conflits_resolus"][0]["resolutions"][1]["nouveau_nom"] == "same_2.mp3"
        assert apercu["conflits_resolus"][0]["resolutions"][2]["nouveau_nom"] == "same_3.mp3"
        # Premier conserve, second _2, troisième _3
        assert "garde_nouveau_nom" not in apercu["groupes"][0]
        assert apercu["groupes"][1]["garde_nouveau_nom"] == "same_2.mp3"
        assert apercu["groupes"][2]["garde_nouveau_nom"] == "same_3.mp3"
        assert apercu["nb_groupes"] == 3

    def test_pas_de_conflit_gardes(self) -> None:
        """Tous les garde ont des noms différents → pas de conflit."""
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"), filename="song_a.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h1"
            ),
            FichierInfo(
                path=Path("ad.mp3"), filename="song_a.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h1"
            ),
            FichierInfo(
                path=Path("b.mp3"), filename="song_b.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h2"
            ),
            FichierInfo(
                path=Path("bd.mp3"), filename="song_b.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h2"
            ),
        ]
        resol_a = {
            "groupe": fichiers[:2],
            "garde": fichiers[0],
            "supprimables": [fichiers[1]],
            "exclus": [],
            "taille_economisee": 1000,
        }
        resol_b = {
            "groupe": fichiers[2:],
            "garde": fichiers[2],
            "supprimables": [fichiers[3]],
            "exclus": [],
            "taille_economisee": 1000,
        }
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=4,
            total_audio=4,
            total_taille=4000,
            doublons_resolus=[resol_a, resol_b],
        )
        apercu = OrdonnanceurService.preparer_deduplication(analyse)
        assert apercu["conflits"] == []
        assert apercu["conflits_resolus"] == []
        # Aucun groupe modifié
        for g in apercu["groupes"]:
            assert "garde_nouveau_nom" not in g


class TestPreparerNettoyage:
    """Teste preparer_nettoyage : scan des fichiers temporaires."""

    def test_dossier_inexistant(self) -> None:
        apercu = OrdonnanceurService.preparer_nettoyage("/inexistant/path")
        assert apercu["total"] == 0
        assert apercu["taille_lisible"] == "0 o"

    def test_fichiers_a_nettoyer(self, tmp_path: Path) -> None:
        """Crée des fichiers temp d'âges différents."""
        temp = tmp_path / "temp"
        temp.mkdir()

        # Fichier .tmp daté d'hier (simulé via modification time)
        hier = temp / "cache.tmp"
        hier.write_text("data")
        # Modifier mtime pour simuler un fichier de 8 jours
        import time as _time

        vieux_mtime = _time.time() - (8 * 86400)
        os.utime(str(hier), (vieux_mtime, vieux_mtime))

        # Fichier .log récent (ne devrait pas être nettoyé)
        recent = temp / "recent.log"
        recent.write_text("recent")
        # mtime actuel

        apercu = OrdonnanceurService.preparer_nettoyage(temp, age_max_jours=7)
        assert apercu["total"] == 1  # seulement le .tmp de 8 jours
        assert apercu["fichiers"][0]["chemin"] == hier

    def test_extensions_personnalisees(self, tmp_path: Path) -> None:
        temp = tmp_path / "custom"
        temp.mkdir()

        test_file = temp / "old.bak"
        test_file.write_text("old backup")
        import time as _time

        vieux = _time.time() - (10 * 86400)
        os.utime(str(test_file), (vieux, vieux))

        (temp / "recent.txt").write_text("recent")  # txt -> ignoré par défaut

        apercu = OrdonnanceurService.preparer_nettoyage(
            temp,
            age_max_jours=7,
            extensions={".bak"},
        )
        assert apercu["total"] == 1


class TestGenererApercu:
    """Teste generer_apercu : méthode unifiée combinant les 4 opérations."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    @pytest.fixture
    def analyse(self) -> AnalyseResultat:
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"),
                filename="a.mp3",
                extension=".mp3",
                size=5_000_000,
                modified=0.0,
                artist="Artist",
                album="Album",
                title="Song",
                track=1,
            ),
            FichierInfo(
                path=Path("b.mp3"),
                filename="b.mp3",
                extension=".mp3",
                size=1_000_000,
                modified=0.0,
                artist="Artist",
                album="Album",
                title="Track",
                track=2,
            ),
            FichierInfo(
                path=Path("c.mp3"), filename="c.mp3", extension=".mp3", size=500_000, modified=0.0, hash_sha256="dup"
            ),
            FichierInfo(
                path=Path("d.mp3"), filename="c.mp3", extension=".mp3", size=500_000, modified=0.0, hash_sha256="dup"
            ),
        ]
        resol = {
            "groupe": [fichiers[2], fichiers[3]],
            "garde": fichiers[2],
            "supprimables": [fichiers[3]],
            "exclus": [],
            "taille_economisee": 500_000,
        }
        return AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=4,
            total_audio=4,
            total_taille=7_000_000,
            doublons_potentiels=[[fichiers[2], fichiers[3]]],
            doublons_confirmes=[[fichiers[2], fichiers[3]]],
            doublons_resolus=[resol],
        )

    def test_renommage_seul(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        apercu = svc.generer_apercu(analyse, {"renommage"})
        assert "renommage" in apercu
        assert "classement" not in apercu
        assert "deduplication" not in apercu
        assert apercu["renommage"]["total"] == 2

    def test_multi_operations(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        apercu = svc.generer_apercu(analyse, {"renommage", "classement", "dedoublonner"})
        assert "renommage" in apercu
        assert "classement" in apercu
        assert "deduplication" in apercu
        # Résumé
        assert apercu["resume"]["total_fichiers_confernes"] == (
            apercu["renommage"]["total"] + apercu["classement"]["total"] + apercu["deduplication"]["total_doublons"]
        )

    def test_aucune_operation(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        apercu = svc.generer_apercu(analyse, set())
        assert apercu == {
            "resume": {
                "total_fichiers_confernes": 0,
                "total_taille_economisee": 0,
                "total_taille_lisible": "0 o",
            }
        }

    def test_options_personnalisees(self, svc: OrdonnanceurService, analyse: AnalyseResultat) -> None:
        apercu = svc.generer_apercu(
            analyse,
            {"renommage"},
            options={
                "template_renommage": "{artist} - {title}.{ext}",
            },
        )
        assert apercu["renommage"]["total"] == 2
        nom_genere = apercu["renommage"]["fichiers"][0]["nouveau_nom"]
        assert nom_genere == "Artist - Song.mp3"  # template simplifié

    def test_conflits_renommage_auto_resolus(
        self,
        svc: OrdonnanceurService,
    ) -> None:
        """Deux fichiers avec mêmes métadonnées → conflit auto-résolu avec _2."""
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"),
                filename="a.mp3",
                extension=".mp3",
                size=1000,
                modified=0.0,
                artist="MemeArtiste",
                album="MemeAlbum",
                title="MemeTitre",
                track=1,
            ),
            FichierInfo(
                path=Path("b.mp3"),
                filename="b.mp3",
                extension=".mp3",
                size=1000,
                modified=0.0,
                artist="MemeArtiste",
                album="MemeAlbum",
                title="MemeTitre",
                track=1,
            ),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=2000,
        )
        apercu = svc.generer_apercu(analyse, {"renommage", "classement"})
        # Renommage : premier conserve, second _2
        assert apercu["renommage"]["total"] == 2
        assert apercu["renommage"]["conflits"] == []  # vidé par résolution
        assert len(apercu["renommage"]["conflits_resolus"]) == 1
        assert apercu["renommage"]["fichiers"][0]["nouveau_nom"] == ("MemeArtiste - MemeAlbum - 01 MemeTitre.mp3")
        prefix_attend = "MemeArtiste - MemeAlbum - 01 MemeTitre"
        assert apercu["renommage"]["fichiers"][1]["nouveau_nom"] == f"{prefix_attend}_2.mp3"
        # Classement : premier conserve, second _2
        assert apercu["classement"]["conflits"] == []
        assert len(apercu["classement"]["conflits_resolus"]) == 1
        assert apercu["classement"]["fichiers"][0]["nouveau_chemin"] == Path("MemeArtiste/MemeAlbum/01 MemeTitre.mp3")
        assert apercu["classement"]["fichiers"][1]["nouveau_chemin"] == Path("MemeArtiste/MemeAlbum/01 MemeTitre_2.mp3")

    def test_conflits_non_resolus_sans_option(
        self,
        svc: OrdonnanceurService,
    ) -> None:
        """resoudre_conflits=False → conflits en l'état, pas de résolution."""
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"),
                filename="a.mp3",
                extension=".mp3",
                size=1000,
                modified=0.0,
                artist="A",
                album="A",
                title="T",
                track=1,
            ),
            FichierInfo(
                path=Path("b.mp3"),
                filename="b.mp3",
                extension=".mp3",
                size=1000,
                modified=0.0,
                artist="A",
                album="A",
                title="T",
                track=1,
            ),
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=2000,
        )
        apercu = svc.generer_apercu(
            analyse,
            {"renommage"},
            options={
                "resoudre_conflits": False,
            },
        )
        assert len(apercu["renommage"]["conflits"]) == 1  # pas vidé
        assert "conflits_resolus" not in apercu["renommage"]
        # Les deux fichiers ont le même nouveau_nom (non résolu)
        nom_commun = apercu["renommage"]["fichiers"][0]["nouveau_nom"]
        assert apercu["renommage"]["fichiers"][1]["nouveau_nom"] == nom_commun

    def test_deduplication_conflits_auto_resolus(
        self,
        svc: OrdonnanceurService,
    ) -> None:
        """Deux groupes avec gardes de même nom → conflits auto-résolus."""
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h1"
            ),
            FichierInfo(
                path=Path("b.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h1"
            ),
            FichierInfo(
                path=Path("c.mp3"), filename="a.mp3", extension=".mp3", size=2000, modified=0.0, hash_sha256="h2"
            ),
            FichierInfo(
                path=Path("d.mp3"), filename="a.mp3", extension=".mp3", size=2000, modified=0.0, hash_sha256="h2"
            ),
        ]
        resol = [
            {
                "groupe": [fichiers[0], fichiers[1]],
                "garde": fichiers[0],
                "supprimables": [fichiers[1]],
                "exclus": [],
                "taille_economisee": 1000,
            },
            {
                "groupe": [fichiers[2], fichiers[3]],
                "garde": fichiers[2],
                "supprimables": [fichiers[3]],
                "exclus": [],
                "taille_economisee": 2000,
            },
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=4,
            total_audio=4,
            total_taille=6000,
            doublons_resolus=resol,
        )
        apercu = svc.generer_apercu(analyse, {"dedoublonner"})
        assert apercu["deduplication"]["conflits"] == []
        assert len(apercu["deduplication"]["conflits_resolus"]) == 1
        assert "garde_nouveau_nom" not in apercu["deduplication"]["groupes"][0]
        assert apercu["deduplication"]["groupes"][1]["garde_nouveau_nom"] == "a_2.mp3"

    def test_deduplication_conflits_non_resolus(
        self,
        svc: OrdonnanceurService,
    ) -> None:
        """resoudre_conflits=False → conflits gardés préservés."""
        fichiers = [
            FichierInfo(
                path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h1"
            ),
            FichierInfo(
                path=Path("b.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0, hash_sha256="h1"
            ),
            FichierInfo(
                path=Path("c.mp3"), filename="a.mp3", extension=".mp3", size=2000, modified=0.0, hash_sha256="h2"
            ),
            FichierInfo(
                path=Path("d.mp3"), filename="a.mp3", extension=".mp3", size=2000, modified=0.0, hash_sha256="h2"
            ),
        ]
        resol = [
            {
                "groupe": [fichiers[0], fichiers[1]],
                "garde": fichiers[0],
                "supprimables": [fichiers[1]],
                "exclus": [],
                "taille_economisee": 1000,
            },
            {
                "groupe": [fichiers[2], fichiers[3]],
                "garde": fichiers[2],
                "supprimables": [fichiers[3]],
                "exclus": [],
                "taille_economisee": 2000,
            },
        ]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=4,
            total_audio=4,
            total_taille=6000,
            doublons_resolus=resol,
        )
        apercu = svc.generer_apercu(
            analyse,
            {"dedoublonner"},
            options={
                "resoudre_conflits": False,
            },
        )
        assert len(apercu["deduplication"]["conflits"]) == 1
        assert apercu["deduplication"]["conflits_resolus"] == []
        assert "garde_nouveau_nom" not in apercu["deduplication"]["groupes"][0]
        assert "garde_nouveau_nom" not in apercu["deduplication"]["groupes"][1]


class TestFilenamePatterns:
    """Teste la configurabilité des patterns de parsing."""

    def test_patterns_default(self) -> None:
        svc = OrdonnanceurService()
        assert len(svc.filename_patterns) >= 2

    def test_set_patterns(self) -> None:
        svc = OrdonnanceurService()
        custom = [re.compile(r"^(?P<title>.+)$")]
        svc.set_filename_patterns(custom)
        assert svc.filename_patterns == custom
        r = svc._parser_nom_fichier("Anything")
        assert r is not None
        assert r["title"] == "Anything"


# ── Templates prédéfinis ───────────────────────────────────────────


class TestClassementPresets:
    def test_presets_exist(self) -> None:
        assert "artiste-album" in CLASSEMENT_PRESETS
        assert "artiste" in CLASSEMENT_PRESETS
        assert "genre-artiste" in CLASSEMENT_PRESETS
        assert "annee-artiste" in CLASSEMENT_PRESETS
        assert "aucun" in CLASSEMENT_PRESETS


class TestRenommagePresets:
    def test_presets_exist(self) -> None:
        assert "standard" in RENOMMAGE_PRESETS
        assert "artiste-titre" in RENOMMAGE_PRESETS
        assert "piste-titre" in RENOMMAGE_PRESETS
        assert "album-piste" in RENOMMAGE_PRESETS


class TestTemplatesDefaults:
    def test_renommage_default_format(self) -> None:
        assert "{artist}" in TEMPLATE_RENOMMAGE_DEFAUT
        assert "{title}" in TEMPLATE_RENOMMAGE_DEFAUT
        assert "{ext}" in TEMPLATE_RENOMMAGE_DEFAUT

    def test_classement_default_format(self) -> None:
        assert "{artist}" in TEMPLATE_CLASSEMENT_DEFAUT
        assert "{album}" in TEMPLATE_CLASSEMENT_DEFAUT
        assert "{ext}" in TEMPLATE_CLASSEMENT_DEFAUT


# ── Dédoublonnage complet (hash + résolution) ──────────────────────


class TestResoudreDoublons:
    """Teste _resoudre_doublons : règles de conservation."""

    def test_groupe_vide(self) -> None:
        resultat = OrdonnanceurService._resoudre_doublons([])
        assert resultat["garde"] is None
        assert resultat["supprimables"] == []
        assert resultat["taille_economisee"] == 0

    def test_fichier_unique(self) -> None:
        f = FichierInfo(
            path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=500_000, modified=1000.0, bitrate=192000
        )
        resultat = OrdonnanceurService._resoudre_doublons([f])
        assert resultat["garde"] is f
        assert resultat["supprimables"] == []

    def test_priorite_bitrate(self) -> None:
        haut = FichierInfo(
            path=Path("high.mp3"),
            filename="high.mp3",
            extension=".mp3",
            size=500_000,
            modified=1000.0,
            bitrate=320000,
            title="High",
        )
        bas = FichierInfo(
            path=Path("low.mp3"),
            filename="low.mp3",
            extension=".mp3",
            size=500_000,
            modified=1000.0,
            bitrate=128000,
            title="Low",
        )
        resultat = OrdonnanceurService._resoudre_doublons([bas, haut])
        assert resultat["garde"] is haut
        assert haut in resultat["groupe"]
        assert bas in resultat["supprimables"]

    def test_priorite_nom_long(self) -> None:
        long = FichierInfo(
            path=Path("long-descriptive-name.mp3"),
            filename="long-descriptive-name.mp3",
            extension=".mp3",
            size=500_000,
            modified=1000.0,
            bitrate=192000,
        )
        court = FichierInfo(
            path=Path("short.mp3"),
            filename="short.mp3",
            extension=".mp3",
            size=500_000,
            modified=1000.0,
            bitrate=192000,
        )
        resultat = OrdonnanceurService._resoudre_doublons([court, long])
        assert resultat["garde"] is long

    def test_priorite_date_recente(self) -> None:
        recent = FichierInfo(
            path=Path("new.mp3"), filename="new.mp3", extension=".mp3", size=500_000, modified=2000.0, bitrate=192000
        )
        ancien = FichierInfo(
            path=Path("old.mp3"), filename="old.mp3", extension=".mp3", size=500_000, modified=1000.0, bitrate=192000
        )
        resultat = OrdonnanceurService._resoudre_doublons([ancien, recent])
        assert resultat["garde"] is recent

    def test_exclusion_moins_100ko(self) -> None:
        valide = FichierInfo(
            path=Path("good.mp3"), filename="good.mp3", extension=".mp3", size=500_000, modified=1000.0, bitrate=192000
        )
        petit = FichierInfo(
            path=Path("small.mp3"),
            filename="small.mp3",
            extension=".mp3",
            size=50 * 1024,
            modified=1000.0,
            bitrate=192000,
        )
        resultat = OrdonnanceurService._resoudre_doublons([petit, valide])
        assert resultat["garde"] is valide
        assert petit in resultat["exclus"]
        assert petit not in resultat["supprimables"]

    def test_exactement_100ko_inclus(self) -> None:
        exact = FichierInfo(
            path=Path("exact.mp3"),
            filename="exact.mp3",
            extension=".mp3",
            size=100 * 1024,
            modified=1000.0,
            bitrate=192000,
        )
        autre = FichierInfo(
            path=Path("other.mp3"),
            filename="other.mp3",
            extension=".mp3",
            size=100 * 1024,
            modified=1000.0,
            bitrate=128000,
        )
        resultat = OrdonnanceurService._resoudre_doublons([autre, exact])
        assert resultat["garde"] is exact
        assert resultat["exclus"] == []

    def test_tous_exclus(self) -> None:
        petit_a = FichierInfo(
            path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=50 * 1024, modified=1000.0, bitrate=192000
        )
        petit_b = FichierInfo(
            path=Path("b.mp3"), filename="b.mp3", extension=".mp3", size=30 * 1024, modified=1000.0, bitrate=128000
        )
        resultat = OrdonnanceurService._resoudre_doublons([petit_a, petit_b])
        assert resultat["garde"] is None
        assert len(resultat["exclus"]) == 2
        assert resultat["taille_economisee"] == 0


class TestDetecterDoublonsHash:
    """Teste _detecter_doublons_hash avec de vrais fichiers."""

    def test_contenu_identique(self, tmp_path: Path) -> None:
        svc = OrdonnanceurService()
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        a.write_bytes(b"contenu identique " * 5000)
        b.write_bytes(b"contenu identique " * 5000)
        fichiers = [
            FichierInfo(path=a, filename="a.mp3", extension=".mp3", size=a.stat().st_size, modified=a.stat().st_mtime),
            FichierInfo(path=b, filename="b.mp3", extension=".mp3", size=b.stat().st_size, modified=b.stat().st_mtime),
        ]
        groupes = svc._detecter_doublons_hash(fichiers)
        assert len(groupes) == 1, f"Attendu 1 groupe, obtenu {len(groupes)}"
        assert len(groupes[0]) == 2
        assert fichiers[0].hash_sha256 == fichiers[1].hash_sha256

    def test_contenu_different(self, tmp_path: Path) -> None:
        svc = OrdonnanceurService()
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        a.write_bytes(b"contenu different A " * 5000)
        b.write_bytes(b"contenu different B " * 5000)
        fichiers = [
            FichierInfo(path=a, filename="a.mp3", extension=".mp3", size=a.stat().st_size, modified=a.stat().st_mtime),
            FichierInfo(path=b, filename="b.mp3", extension=".mp3", size=b.stat().st_size, modified=b.stat().st_mtime),
        ]
        groupes = svc._detecter_doublons_hash(fichiers)
        assert len(groupes) == 0
        assert fichiers[0].hash_sha256 != fichiers[1].hash_sha256

    def test_fichier_introuvable(self, tmp_path: Path) -> None:
        svc = OrdonnanceurService()
        chemin = tmp_path / "inexistant.mp3"
        f = FichierInfo(path=chemin, filename="inexistant.mp3", extension=".mp3", size=1000, modified=0.0)
        groupes = svc._detecter_doublons_hash([f])
        assert len(groupes) == 0
        assert f.hash_sha256 is None


class TestAnalyseDossierAvecHash:
    """Teste le pipeline complet analyser_dossier avec vérification hash."""

    def test_doublons_confirme_par_hash(self, tmp_path: Path) -> None:
        svc = OrdonnanceurService()
        dossier = tmp_path / "musique"
        dossier.mkdir()
        contenu = b"X" * 200_000  # > 100 Ko pour passer _est_fichier_audio
        # Même nom dans des sous-dossiers différents => passe rapide les détecte
        for sub in ["dir1", "dir2", "dir3"]:
            (dossier / sub).mkdir()
            (dossier / sub / "song.mp3").write_bytes(contenu)
        # Fichier unique (nom différent)
        (dossier / "unique.mp3").write_bytes(b"Y" * 200_000)

        resultat = svc.analyser_dossier(dossier, recursive=True)
        assert resultat.total_audio == 4
        assert len(resultat.doublons_confirmes) >= 1
        tous_hash = [f for g in resultat.doublons_confirmes for f in g]
        assert len(tous_hash) >= 2

    def test_pas_de_doublons_apres_hash(self, tmp_path: Path) -> None:
        svc = OrdonnanceurService()
        dossier = tmp_path / "unique"
        dossier.mkdir()
        for sub in ["dir1", "dir2"]:
            (dossier / sub).mkdir()
            # Même nom et même taille => passe rapide détecte
            # Contenu différent => hash ne confirme PAS
            c = f"contenu_{sub}".encode() * 15000
            (dossier / sub / "a.mp3").write_bytes(c)
        resultat = svc.analyser_dossier(dossier, recursive=True)
        assert resultat.total_audio == 2
        assert resultat.doublons_confirmes == []

    def test_doublons_resolus_presents(self, tmp_path: Path) -> None:
        svc = OrdonnanceurService()
        dossier = tmp_path / "resolve"
        dossier.mkdir()
        contenu = b"W" * 200_000  # > 100 Ko
        for sub in ["dir1", "dir2", "dir3"]:
            (dossier / sub).mkdir()
            (dossier / sub / "a.mp3").write_bytes(contenu)
        resultat = svc.analyser_dossier(dossier, recursive=True)
        assert len(resultat.doublons_resolus) >= 1
        resolution = resultat.doublons_resolus[0]
        assert "garde" in resolution
        assert "supprimables" in resolution
        assert "taille_economisee" in resolution
        assert resolution["garde"] is not None
        assert len(resolution["supprimables"]) >= 1


class TestEstimationAvecConfirmes:
    """Teste estimer_operations avec doublons_confirmes."""

    def test_priorite_confirmes_sur_potentiels(self) -> None:
        svc = OrdonnanceurService()
        fichiers = [
            FichierInfo(
                path=Path("dup.mp3"),
                filename="dup.mp3",
                extension=".mp3",
                size=1_000_000,
                modified=0.0,
                hash_sha256="abc",
            ),
            FichierInfo(
                path=Path("dup2.mp3"),
                filename="dup2.mp3",
                extension=".mp3",
                size=1_000_000,
                modified=0.0,
                hash_sha256="abc",
            ),
            FichierInfo(
                path=Path("unique.mp3"),
                filename="unique.mp3",
                extension=".mp3",
                size=2_000_000,
                modified=0.0,
                hash_sha256="def",
            ),
        ]
        confirme = [[fichiers[0], fichiers[1]]]
        potentiel = [[fichiers[0], fichiers[1], fichiers[2]]]  # +1 si potentiel utilisé
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=3,
            total_audio=3,
            total_taille=4_000_000,
            doublons_potentiels=potentiel,
            doublons_confirmes=confirme,
        )
        est = svc.estimer_operations(analyse, {"dedoublonner"})
        # Doit utiliser confirmés (1 groupe, 1 à supprimer) pas potentiels (1 groupe, 2 à supprimer)
        assert est["dedoublonner"]["groupes"] == 1
        assert est["dedoublonner"]["fichiers_a_supprimer"] == 1

    def test_fallback_potentiels_sans_confirmes(self) -> None:
        svc = OrdonnanceurService()
        fichiers = [
            FichierInfo(path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0),
            FichierInfo(path=Path("a.mp3"), filename="a.mp3", extension=".mp3", size=1000, modified=0.0),
        ]
        potentiel = [[fichiers[0], fichiers[1]]]
        analyse = AnalyseResultat(
            dossier_source=Path("/test"),
            fichiers=fichiers,
            total_fichiers=2,
            total_audio=2,
            total_taille=2000,
            doublons_potentiels=potentiel,
            doublons_confirmes=[],
        )
        est = svc.estimer_operations(analyse, {"dedoublonner"})
        assert est["dedoublonner"]["groupes"] == 1
        assert est["dedoublonner"]["fichiers_a_supprimer"] == 1


class TestResoudreConflits:
    """Tests pour resoudre_conflits — résolution par suffixes _2, _3."""

    @staticmethod
    def _mk_info(filename: str) -> FichierInfo:
        return FichierInfo(
            path=Path(filename),
            filename=filename,
            extension=".mp3",
            size=1000,
            modified=0.0,
        )

    def test_aucun_conflit(self) -> None:
        """Pas de conflits → inchangé."""
        apercu = {
            "fichiers": [{"info": self._mk_info("a.mp3"), "nom_actuel": "a.mp3", "nouveau_nom": "A - T.mp3"}],
            "total": 1,
            "conflits": [],
            "exemples": [],
        }
        resultat = OrdonnanceurService.resoudre_conflits(apercu)
        assert resultat["conflits"] == []
        assert resultat["conflits_resolus"] == []

    def test_renommage_conflit_2_fichiers(self) -> None:
        """2 fichiers vers le même nom → _2 sur le second."""
        apercu = {
            "fichiers": [
                {"info": self._mk_info("song1.mp3"), "nom_actuel": "song1.mp3", "nouveau_nom": "Duplicate Name.mp3"},
                {"info": self._mk_info("song2.mp3"), "nom_actuel": "song2.mp3", "nouveau_nom": "Duplicate Name.mp3"},
            ],
            "total": 2,
            "conflits": [
                {
                    "nom_conflit": "Duplicate Name.mp3",
                    "fichiers": ["song1.mp3", "song2.mp3"],
                    "nb": 2,
                }
            ],
            "exemples": [],
        }
        resultat = OrdonnanceurService.resoudre_conflits(apercu)
        assert resultat["conflits"] == []
        assert len(resultat["conflits_resolus"]) == 1
        # Premier fichier conserve le nom original
        assert resultat["fichiers"][0]["nouveau_nom"] == "Duplicate Name.mp3"
        # Deuxième fichier reçoit _2
        assert resultat["fichiers"][1]["nouveau_nom"] == "Duplicate Name_2.mp3"

    def test_renommage_conflit_3_fichiers(self) -> None:
        """3 fichiers → _2, _3."""
        apercu = {
            "fichiers": [
                {"info": self._mk_info("a.mp3"), "nom_actuel": "a.mp3", "nouveau_nom": "Conflict.mp3"},
                {"info": self._mk_info("b.mp3"), "nom_actuel": "b.mp3", "nouveau_nom": "Conflict.mp3"},
                {"info": self._mk_info("c.mp3"), "nom_actuel": "c.mp3", "nouveau_nom": "Conflict.mp3"},
            ],
            "total": 3,
            "conflits": [
                {
                    "nom_conflit": "Conflict.mp3",
                    "fichiers": ["a.mp3", "b.mp3", "c.mp3"],
                    "nb": 3,
                }
            ],
            "exemples": [],
        }
        resultat = OrdonnanceurService.resoudre_conflits(apercu)
        assert resultat["fichiers"][0]["nouveau_nom"] == "Conflict.mp3"
        assert resultat["fichiers"][1]["nouveau_nom"] == "Conflict_2.mp3"
        assert resultat["fichiers"][2]["nouveau_nom"] == "Conflict_3.mp3"

    def test_classement_conflit_2_fichiers(self) -> None:
        """2 fichiers vers le même chemin → _2 sur le second."""
        apercu = {
            "fichiers": [
                {
                    "info": self._mk_info("track1.mp3"),
                    "chemin_actuel": Path("/src/track1.mp3"),
                    "nouveau_chemin": Path("/music/Artist/01 Title.mp3"),
                    "artiste": "Artist",
                },
                {
                    "info": self._mk_info("track2.mp3"),
                    "chemin_actuel": Path("/src/track2.mp3"),
                    "nouveau_chemin": Path("/music/Artist/01 Title.mp3"),
                    "artiste": "Artist",
                },
            ],
            "total": 2,
            "artistes": {"Artist": 2},
            "nb_artistes": 1,
            "conflits": [
                {
                    "chemin": "/music/Artist/01 Title.mp3",
                    "fichiers": ["track1.mp3", "track2.mp3"],
                    "nb": 2,
                }
            ],
            "exemples": [],
        }
        resultat = OrdonnanceurService.resoudre_conflits(apercu)
        assert resultat["conflits"] == []
        assert len(resultat["conflits_resolus"]) == 1
        # Premier conserve le chemin original
        assert resultat["fichiers"][0]["nouveau_chemin"] == Path("/music/Artist/01 Title.mp3")
        # Second reçoit _2
        assert resultat["fichiers"][1]["nouveau_chemin"] == Path("/music/Artist/01 Title_2.mp3")

    def test_classement_conflit_3_fichiers(self) -> None:
        """3 fichiers vers le même chemin → _2, _3."""
        apercu = {
            "fichiers": [
                {"info": self._mk_info("a.mp3"), "nouveau_chemin": Path("/x/y.mp3")},
                {"info": self._mk_info("b.mp3"), "nouveau_chemin": Path("/x/y.mp3")},
                {"info": self._mk_info("c.mp3"), "nouveau_chemin": Path("/x/y.mp3")},
            ],
            "total": 3,
            "conflits": [
                {
                    "chemin": "/x/y.mp3",
                    "fichiers": ["a.mp3", "b.mp3", "c.mp3"],
                    "nb": 3,
                }
            ],
            "exemples": [],
        }
        resultat = OrdonnanceurService.resoudre_conflits(apercu)
        assert resultat["fichiers"][0]["nouveau_chemin"] == Path("/x/y.mp3")
        assert resultat["fichiers"][1]["nouveau_chemin"] == Path("/x/y_2.mp3")
        assert resultat["fichiers"][2]["nouveau_chemin"] == Path("/x/y_3.mp3")

    def test_conflits_multiples_resolus(self) -> None:
        """Deux conflits indépendants dans le même aperçu."""
        apercu = {
            "fichiers": [
                {"info": self._mk_info("a.mp3"), "nom_actuel": "a.mp3", "nouveau_nom": "Common.mp3"},
                {"info": self._mk_info("b.mp3"), "nom_actuel": "b.mp3", "nouveau_nom": "Common.mp3"},
                {"info": self._mk_info("c.mp3"), "nom_actuel": "c.mp3", "nouveau_nom": "Another.mp3"},
                {"info": self._mk_info("d.mp3"), "nom_actuel": "d.mp3", "nouveau_nom": "Another.mp3"},
            ],
            "total": 4,
            "conflits": [
                {"nom_conflit": "Common.mp3", "fichiers": ["a.mp3", "b.mp3"], "nb": 2},
                {"nom_conflit": "Another.mp3", "fichiers": ["c.mp3", "d.mp3"], "nb": 2},
            ],
            "exemples": [],
        }
        resultat = OrdonnanceurService.resoudre_conflits(apercu)
        assert len(resultat["conflits_resolus"]) == 2
        assert resultat["fichiers"][0]["nouveau_nom"] == "Common.mp3"
        assert resultat["fichiers"][1]["nouveau_nom"] == "Common_2.mp3"
        assert resultat["fichiers"][2]["nouveau_nom"] == "Another.mp3"
        assert resultat["fichiers"][3]["nouveau_nom"] == "Another_2.mp3"


class TestExecuterOperations:
    """Teste executer_operations : execution des operations sur le disque."""

    @pytest.fixture
    def svc(self) -> OrdonnanceurService:
        return OrdonnanceurService()

    def _cree_fichier(self, tmp_path: Path, rel_path: str) -> Path:
        """Helper : crée un fichier texte dans tmp_path."""
        p = tmp_path / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("contenu test")
        return p

    def _analyse_avec_fichiers(
        self,
        fichiers: list[FichierInfo],
        source: Path,
    ) -> AnalyseResultat:
        return AnalyseResultat(
            dossier_source=source,
            fichiers=fichiers,
            total_fichiers=len(fichiers),
            total_audio=len(fichiers),
            total_taille=sum(f.size for f in fichiers),
        )

    # ── Simulation (mode par défaut) ──

    def test_simulation_renommage(self, svc: OrdonnanceurService) -> None:
        info = FichierInfo(
            path=Path("music/song.mp3"),
            filename="song.mp3",
            extension=".mp3",
            size=5000,
            modified=0.0,
            artist="Artist",
            title="Song",
        )
        fichiers = [
            {"info": info, "nom_actuel": "song.mp3", "nouveau_nom": "Artist - Song.mp3"},
        ]
        apercu = {"renommage": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=True)
        assert resultat["simulation"] is True
        assert resultat["succes"] is True
        assert resultat["operations"]["renommage"]["tente"] == 1
        assert resultat["operations"]["renommage"]["reussi"] == 1
        assert resultat["operations"]["renommage"]["echoue"] == 0

    def test_simulation_classement(self, svc: OrdonnanceurService) -> None:
        info = FichierInfo(
            path=Path("music/song.mp3"),
            filename="song.mp3",
            extension=".mp3",
            size=5000,
            modified=0.0,
            artist="Artist",
        )
        fichiers = [
            {
                "info": info,
                "chemin_actuel": Path("music/song.mp3"),
                "nouveau_chemin": Path("Artist/Album/Song.mp3"),
                "artiste": "Artist",
            },
        ]
        apercu = {"classement": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=True)
        assert resultat["operations"]["classement"]["tente"] == 1
        assert resultat["operations"]["classement"]["reussi"] == 1

    def test_simulation_deduplication(self, svc: OrdonnanceurService) -> None:
        garde = FichierInfo(
            path=Path("keep.mp3"),
            filename="keep.mp3",
            extension=".mp3",
            size=5000,
            modified=0.0,
        )
        doublon = FichierInfo(
            path=Path("dup.mp3"),
            filename="dup.mp3",
            extension=".mp3",
            size=5000,
            modified=0.0,
        )
        groupes = [
            {"garde": garde, "supprimables": [doublon], "taille_economisee": 5000},
        ]
        apercu = {"deduplication": {"groupes": groupes, "total_doublons": 1}}
        resultat = svc.executer_operations(apercu, simuler=True)
        ops = resultat["operations"]["deduplication"]
        assert ops["supprime"] == 1
        assert ops["renomme_gardes"] == 0

    def test_simulation_nettoyage(self, svc: OrdonnanceurService) -> None:
        fichiers = [
            {"chemin": Path("/tmp/old.tmp"), "taille": 1000, "age_jours": 15.0},
        ]
        apercu = {"nettoyage": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=True)
        assert resultat["operations"]["nettoyage"]["supprime"] == 1
        assert resultat["operations"]["nettoyage"]["tente"] == 1

    # ── Exécution réelle ──

    def test_executer_renommage(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Renomme un fichier réel sur le disque."""
        source = self._cree_fichier(tmp_path, "old_name.mp3")
        info = FichierInfo(
            path=source,
            filename="old_name.mp3",
            extension=".mp3",
            size=source.stat().st_size,
            modified=source.stat().st_mtime,
            artist="Artist",
            title="Song",
        )
        fichiers = [
            {"info": info, "nom_actuel": "old_name.mp3", "nouveau_nom": "Artist - Song.mp3"},
        ]
        apercu = {"renommage": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["simulation"] is False
        assert resultat["succes"] is True
        assert resultat["operations"]["renommage"]["reussi"] == 1
        assert not (tmp_path / "old_name.mp3").exists()
        assert (tmp_path / "Artist - Song.mp3").exists()

    def test_executer_classement(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Déplace un fichier réel selon le classement."""
        source = self._cree_fichier(tmp_path, "music/song.mp3")
        dest = tmp_path / "Artist/Album/Song.mp3"
        info = FichierInfo(
            path=source,
            filename="song.mp3",
            extension=".mp3",
            size=source.stat().st_size,
            modified=source.stat().st_mtime,
            artist="Artist",
        )
        fichiers = [
            {"info": info, "chemin_actuel": source, "nouveau_chemin": dest, "artiste": "Artist"},
        ]
        apercu = {"classement": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is True
        assert resultat["operations"]["classement"]["reussi"] == 1
        assert not source.exists()
        assert dest.exists()

    def test_executer_deduplication(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Supprime les fichiers doublons."""
        garde = self._cree_fichier(tmp_path, "keep.mp3")
        doublon = self._cree_fichier(tmp_path, "dup.mp3")
        info_garde = FichierInfo(
            path=garde,
            filename="keep.mp3",
            extension=".mp3",
            size=garde.stat().st_size,
            modified=garde.stat().st_mtime,
        )
        info_doublon = FichierInfo(
            path=doublon,
            filename="dup.mp3",
            extension=".mp3",
            size=doublon.stat().st_size,
            modified=doublon.stat().st_mtime,
        )
        groupes = [
            {"garde": info_garde, "supprimables": [info_doublon], "taille_economisee": doublon.stat().st_size},
        ]
        apercu = {"deduplication": {"groupes": groupes, "total_doublons": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is True
        assert resultat["operations"]["deduplication"]["supprime"] == 1
        assert garde.exists()  # garde conservé
        assert not doublon.exists()  # doublon supprimé

    def test_executer_deduplication_avec_renommage_garde(
        self,
        svc: OrdonnanceurService,
        tmp_path: Path,
    ) -> None:
        """Renomme le garde puis supprime les doublons."""
        garde = self._cree_fichier(tmp_path, "same.mp3")
        doublon = self._cree_fichier(tmp_path, "dup.mp3")
        info_garde = FichierInfo(
            path=garde,
            filename="same.mp3",
            extension=".mp3",
            size=garde.stat().st_size,
            modified=garde.stat().st_mtime,
        )
        info_doublon = FichierInfo(
            path=doublon,
            filename="dup.mp3",
            extension=".mp3",
            size=doublon.stat().st_size,
            modified=doublon.stat().st_mtime,
        )
        groupes = [
            {
                "garde": info_garde,
                "garde_nouveau_nom": "same_2.mp3",
                "supprimables": [info_doublon],
                "taille_economisee": doublon.stat().st_size,
            },
        ]
        apercu = {"deduplication": {"groupes": groupes, "total_doublons": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is True
        ops = resultat["operations"]["deduplication"]
        assert ops["renomme_gardes"] == 1
        assert ops["supprime"] == 1
        assert (tmp_path / "same_2.mp3").exists()  # garde renommé
        assert not doublon.exists()  # doublon supprimé

    def test_executer_nettoyage(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Supprime les fichiers temporaires."""
        temp = tmp_path / "temp"
        temp.mkdir()
        fichier = temp / "old.tmp"
        fichier.write_text("old data")

        fichiers = [
            {"chemin": fichier, "taille": fichier.stat().st_size, "age_jours": 15.0},
        ]
        apercu = {"nettoyage": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is True
        assert resultat["operations"]["nettoyage"]["supprime"] == 1
        assert not fichier.exists()

    # ── Gestion d'erreurs ──

    def test_erreur_renommage_destination_existe(
        self,
        svc: OrdonnanceurService,
        tmp_path: Path,
    ) -> None:
        """Tente de renommer vers un fichier qui existe déjà → erreur."""
        source = self._cree_fichier(tmp_path, "source.mp3")
        self._cree_fichier(tmp_path, "dest.mp3")  # déjà existant
        info = FichierInfo(
            path=source,
            filename="source.mp3",
            extension=".mp3",
            size=source.stat().st_size,
            modified=source.stat().st_mtime,
        )
        fichiers = [
            {"info": info, "nom_actuel": "source.mp3", "nouveau_nom": "dest.mp3"},
        ]
        apercu = {"renommage": {"fichiers": fichiers, "total": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is False
        ops = resultat["operations"]["renommage"]
        assert ops["echoue"] == 1
        assert len(resultat["erreurs"]) == 1
        assert "dest.mp3" in resultat["erreurs"][0]["erreur"]

    def test_erreur_fichier_introuvable(self, svc: OrdonnanceurService) -> None:
        """Tente de supprimer un fichier qui n'existe pas → erreur."""
        info = FichierInfo(
            path=Path("/inexistant/file.mp3"),
            filename="file.mp3",
            extension=".mp3",
            size=1000,
            modified=0.0,
        )
        groupes = [
            {"garde": info, "supprimables": [info], "taille_economisee": 1000},
        ]
        apercu = {"deduplication": {"groupes": groupes, "total_doublons": 1}}
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is False
        assert len(resultat["erreurs"]) > 0

    # ── Cas aux limites ──

    def test_apercu_vide(self, svc: OrdonnanceurService) -> None:
        """Aperçu sans aucune opération → résultat vide."""
        resultat = svc.executer_operations({}, simuler=True)
        assert resultat["succes"] is True
        assert resultat["operations"] == {}
        assert resultat["erreurs"] == []

    def test_operations_combinees(
        self,
        svc: OrdonnanceurService,
        tmp_path: Path,
    ) -> None:
        """Exécute renommage + classement + nettoyage en un seul appel."""
        # Renommage
        src_renomme = self._cree_fichier(tmp_path, "a.mp3")
        info_r = FichierInfo(path=src_renomme, filename="a.mp3", extension=".mp3", size=100, modified=0.0)
        # Classement
        src_classe = self._cree_fichier(tmp_path, "music/song.mp3")
        dest_classe = tmp_path / "Artist/Album/Song.mp3"
        info_c = FichierInfo(
            path=src_classe, filename="song.mp3", extension=".mp3", size=100, modified=0.0, artist="Artist"
        )
        # Nettoyage
        temp = tmp_path / "temp"
        temp.mkdir()
        a_suppr = temp / "old.tmp"
        a_suppr.write_text("data")

        apercu = {
            "renommage": {
                "fichiers": [{"info": info_r, "nom_actuel": "a.mp3", "nouveau_nom": "b.mp3"}],
                "total": 1,
            },
            "classement": {
                "fichiers": [
                    {"info": info_c, "chemin_actuel": src_classe, "nouveau_chemin": dest_classe, "artiste": "Artist"}
                ],
                "total": 1,
            },
            "nettoyage": {
                "fichiers": [{"chemin": a_suppr, "taille": 100, "age_jours": 15.0}],
                "total": 1,
            },
        }
        resultat = svc.executer_operations(apercu, simuler=False)

        assert resultat["succes"] is True
        assert resultat["operations"]["renommage"]["reussi"] == 1
        assert resultat["operations"]["classement"]["reussi"] == 1
        assert resultat["operations"]["nettoyage"]["supprime"] == 1
        assert (tmp_path / "b.mp3").exists()  # renommé
        assert dest_classe.exists()  # classé
        assert not a_suppr.exists()  # nettoyé


# ── Tests corbeille dédiée ──────────────────────────────────────────────


class TestDeplacerVersCorbeille:
    """Teste deplacer_vers_corbeille : déplacement vers corbeille dédiée."""

    @pytest.fixture(autouse=True)
    def _setup_corbeille(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Redirige la corbeille vers tmp_path/.corbeille pour chaque test."""
        self.corbeille = tmp_path / ".corbeille"
        monkeypatch.setattr(settings, "corbeille_dir", self.corbeille)

    def _cree_fichier(self, tmp_path: Path, nom: str = "test.txt") -> Path:
        """Helper : crée un fichier texte dans tmp_path."""
        p = tmp_path / nom
        p.write_text("contenu test")
        return p

    def test_deplacement_simple(self, tmp_path: Path) -> None:
        """Le fichier est déplacé vers la corbeille avec préfixe horodaté."""
        src = self._cree_fichier(tmp_path)
        assert src.exists()

        dest = deplacer_vers_corbeille(src)

        assert not src.exists()  # source supprimée
        assert dest.exists()  # destination existe dans corbeille
        assert dest.parent == self.corbeille
        assert dest.name.startswith("20")  # commence par timestamp YYYYMMDD_
        assert dest.name.endswith("_test.txt")
        assert dest.read_text() == "contenu test"  # contenu préservé

    def test_fichier_inexistant(self) -> None:
        """Lève FileNotFoundError si le fichier source n'existe pas."""
        inexistant = Path("/chemin/inexistant.txt")
        with pytest.raises(FileNotFoundError, match="Fichier introuvable"):
            deplacer_vers_corbeille(inexistant)

    def test_dossier_corbeille_cree_automatiquement(self, tmp_path: Path) -> None:
        """Le dossier corbeille est créé s'il n'existe pas."""
        assert not self.corbeille.exists()
        src = self._cree_fichier(tmp_path)
        deplacer_vers_corbeille(src)
        assert self.corbeille.exists()
        assert self.corbeille.is_dir()

    def test_collision_nom(self, tmp_path: Path) -> None:
        """En cas de collision, un compteur suffixe le nom."""
        src1 = self._cree_fichier(tmp_path, "fichier.txt")
        dest1 = deplacer_vers_corbeille(src1)
        assert dest1.suffix == ".txt"

        # Deuxième fichier avec le même nom — doit ajouter _1
        src2 = self._cree_fichier(tmp_path, "fichier.txt")
        dest2 = deplacer_vers_corbeille(src2)
        assert dest2.suffix == ".txt"
        assert "_1" in dest2.stem
        assert dest2.exists()

    def test_collision_multiple(self, tmp_path: Path) -> None:
        """Collisions multiples : _1, _2, _3 ..."""
        dossiers = []
        for i in range(3):
            src = self._cree_fichier(tmp_path, f"document.txt")
            dest = deplacer_vers_corbeille(src)
            dossiers.append(dest)
            assert dest.exists()

        # Vérifie que les 3 sont dans la corbeille avec des noms différents
        noms = [d.name for d in dossiers]
        assert len(set(noms)) == 3, f"Noms en double : {noms}"
        assert all(d.parent == self.corbeille for d in dossiers)

    def test_chemin_retourne_correct(self, tmp_path: Path) -> None:
        """Le chemin retourné est le bon chemin de destination."""
        src = self._cree_fichier(tmp_path, "musique.mp3")
        dest = deplacer_vers_corbeille(src)
        assert dest == self.corbeille / dest.name
        assert dest.exists()
        # Vérifie qu'on peut le lire
        assert dest.read_text() == "contenu test"

    def test_contenu_preserve(self, tmp_path: Path) -> None:
        """Le contenu du fichier est intact après déplacement."""
        src = tmp_path / "donnees.bin"
        src.write_bytes(bytes(range(256)))
        dest = deplacer_vers_corbeille(src)
        assert dest.read_bytes() == bytes(range(256))

    def test_dossier_profond_cree(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Le chemin complet vers la corbeille (parents) est créé automatiquement."""
        profond = tmp_path / "a" / "b" / "c" / "corbeille"
        monkeypatch.setattr(settings, "corbeille_dir", profond)
        assert not profond.exists()

        src = self._cree_fichier(tmp_path)
        dest = deplacer_vers_corbeille(src)
        assert dest.exists()
        assert profond.exists()

    def test_fichier_vide(self, tmp_path: Path) -> None:
        """Un fichier vide est déplacé vers la corbeille sans erreur."""
        src = tmp_path / "vide.txt"
        src.touch()
        assert src.exists()
        assert src.stat().st_size == 0

        dest = deplacer_vers_corbeille(src)

        assert not src.exists()
        assert dest.exists()
        assert dest.parent == self.corbeille
        assert dest.stat().st_size == 0

    def test_nom_unicode(self, tmp_path: Path) -> None:
        """Les fichiers avec caractères Unicode dans le nom sont gérés."""
        src = tmp_path / "♫ Música_élève_日本_🎵.mp3"
        src.write_text("unicode test")
        assert src.exists()

        dest = deplacer_vers_corbeille(src)

        assert not src.exists()
        assert dest.exists()
        assert dest.parent == self.corbeille
        # Le nom original est conservé (préfixé par timestamp)
        assert "♫" in dest.name or dest.suffix == ".mp3"
        assert dest.read_text() == "unicode test"
