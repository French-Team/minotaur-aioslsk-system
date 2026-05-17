"""Tests d'intégration OrdonnanceurService avec de vrais fichiers audio.

Utilise les fichiers MP3 réels dans J:/Music-trier/partager/
pour valider l'extraction des métadonnées via mutagen.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from src.services.ordonnanceur_service import (
    TEMPLATE_CLASSEMENT_DEFAUT,
    TEMPLATE_RENOMMAGE_DEFAUT,
    OrdonnanceurService,
)

# ── Chemins ────────────────────────────────────────────────────────

DOSSIER_PARTAGE = Path("J:/Music-trier/partager")

# Skip tout le fichier si le dossier partagé n'est pas accessible
if not DOSSIER_PARTAGE.is_dir():
    pytest.skip(
        f"Dossier partagé introuvable : {DOSSIER_PARTAGE}\n"
        "Ces tests nécessitent des fichiers audio réels pour valider mutagen.",
        allow_module_level=True,
    )

MP3_ALEX_PEACE = DOSSIER_PARTAGE / "01 - Alex Peace - From inside the speaker (Original Mix).mp3"
MP3_ANDREA_DORIA = DOSSIER_PARTAGE / "01 - Andrea Doria - Bucci bag (Original).mp3"

# Skip si l'un des fichiers de référence est absent
_REQUIRED_FILES = [MP3_ALEX_PEACE, MP3_ANDREA_DORIA]
for _f in _REQUIRED_FILES:
    if not _f.is_file():
        pytest.skip(
            f"Fichier requis introuvable : {_f}",
            allow_module_level=True,
        )

# Tags attendus — vérifiés expérimentalement via mutagen
ALEX_PEACE_TAGS = {
    "artist": "Alex Peace",
    "album": "Lagoa 13",
    "title": "From Inside The Speaker (Original Mix)",
    "track": 1,
    "year": 2003,
    "genre": "Techno",
}

ANDREA_DORIA_TAGS = {
    "artist": "Andrea Doria",
    "album": "Lagoa 12",
    "title": "Bucci Bag (original)",
    "track": 1,
    "year": 2003,
    "genre": "Euro-Techno",
}


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def svc() -> OrdonnanceurService:
    """Instance partagée pour tous les tests de la session."""
    return OrdonnanceurService()


@pytest.fixture(scope="session")
def alex_peace(svc: OrdonnanceurService) -> tuple[OrdonnanceurService, object]:
    """Analyse le fichier Alex Peace et retourne (svc, info)."""
    info = svc.analyser_fichier(MP3_ALEX_PEACE)
    return svc, info


@pytest.fixture(scope="session")
def andrea_doria(svc: OrdonnanceurService) -> tuple[OrdonnanceurService, object]:
    """Analyse le fichier Andrea Doria et retourne (svc, info)."""
    info = svc.analyser_fichier(MP3_ANDREA_DORIA)
    return svc, info


# ── Tests extraction métadonnées ───────────────────────────────────


class TestExtractionTags:
    """Valide l'extraction des tags audio via mutagen (EasyID3)."""

    def test_alex_peace_artist(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.artist == ALEX_PEACE_TAGS["artist"], (
            f"artiste: attendu {ALEX_PEACE_TAGS['artist']!r}, obtenu {info.artist!r}"
        )

    def test_alex_peace_album(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.album == ALEX_PEACE_TAGS["album"]

    def test_alex_peace_title(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.title == ALEX_PEACE_TAGS["title"]

    def test_alex_peace_track(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.track == ALEX_PEACE_TAGS["track"]

    def test_alex_peace_year(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.year == ALEX_PEACE_TAGS["year"]

    def test_alex_peace_genre(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.genre == ALEX_PEACE_TAGS["genre"]

    def test_alex_peace_source(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.source_metadata == "tag"

    def test_andrea_doria_artist(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.artist == ANDREA_DORIA_TAGS["artist"]

    def test_andrea_doria_album(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.album == ANDREA_DORIA_TAGS["album"]

    def test_andrea_doria_title(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.title == ANDREA_DORIA_TAGS["title"]

    def test_andrea_doria_track(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.track == ANDREA_DORIA_TAGS["track"]

    def test_andrea_doria_year(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.year == ANDREA_DORIA_TAGS["year"]

    def test_andrea_doria_genre(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.genre == ANDREA_DORIA_TAGS["genre"]

    def test_andrea_doria_source(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.source_metadata == "tag"


class TestExtractionTech:
    """Valide l'extraction des infos techniques (bitrate, sample_rate, durée, codec)."""

    def test_alex_peace_bitrate(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.bitrate is not None
        assert info.bitrate > 0
        # MP3 192 kbps CBR
        assert info.bitrate == 192000, f"bitrate: {info.bitrate}"

    def test_alex_peace_sample_rate(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.sample_rate is not None
        assert info.sample_rate == 44100, f"sample_rate: {info.sample_rate}"

    def test_alex_peace_duration(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.duration is not None
        assert info.duration > 0
        # ~5 min
        assert 250 < info.duration < 350, f"duration: {info.duration}"

    def test_alex_peace_codec(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.codec == "mp3", f"codec: {info.codec}"

    def test_alex_peace_extension(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.extension == ".mp3"

    def test_andrea_doria_bitrate(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.bitrate is not None
        assert info.bitrate > 0
        # MP3 VBR ~192 kbps
        assert info.bitrate > 100000, f"bitrate: {info.bitrate}"

    def test_andrea_doria_sample_rate(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.sample_rate == 44100, f"sample_rate: {info.sample_rate}"

    def test_andrea_doria_duration(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.duration is not None
        assert info.duration > 0
        assert 250 < info.duration < 350, f"duration: {info.duration}"

    def test_andrea_doria_codec(self, andrea_doria) -> None:
        _, info = andrea_doria
        assert info.codec == "mp3", f"codec: {info.codec}"


# ── Tests champs de base ───────────────────────────────────────────


class TestChampsDeBase:
    """Valide les champs basiques (filename, size, path)."""

    def test_alex_peace_filename(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.filename == MP3_ALEX_PEACE.name

    def test_alex_peace_size(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.size > 100 * 1024  # > taille minimale valide
        assert info.size < 50 * 1024 * 1024  # < 50 Mo (raisonnable)

    def test_alex_peace_path(self, alex_peace) -> None:
        _, info = alex_peace
        assert info.path == MP3_ALEX_PEACE


# ── Tests scanner_dossier ──────────────────────────────────────────


class TestScannerDossier:
    """Valide le scan de dossier avec de vrais fichiers."""

    def test_scan_partage(self, svc: OrdonnanceurService) -> None:
        fichiers = svc.scanner_dossier(DOSSIER_PARTAGE, recursive=False)
        assert len(fichiers) >= 2  # au moins nos 2 MP3
        assert MP3_ALEX_PEACE in fichiers
        assert MP3_ANDREA_DORIA in fichiers

    def test_scan_recursif(self, svc: OrdonnanceurService) -> None:
        # Scan du dossier parent (peut-être d'autres fichiers dans les sous-dossiers)
        fichiers = svc.scanner_dossier(DOSSIER_PARTAGE.parent, recursive=True)
        assert len(fichiers) >= 2

    def test_scan_non_recursif_compte(self, svc: OrdonnanceurService) -> None:
        fichiers = svc.scanner_dossier(DOSSIER_PARTAGE, recursive=False)
        # Vérifie qu'au moins nos 2 MP3 sont trouvés
        mp3_trouves = [f for f in fichiers if f.suffix.lower() == ".mp3"]
        assert len(mp3_trouves) >= 2


# ── Tests analyser_dossier ─────────────────────────────────────────


class TestAnalyserDossier:
    """Valide l'analyse complète d'un dossier réel."""

    def test_analyse_partage(self, svc: OrdonnanceurService) -> None:
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        assert result.total_audio >= 2
        assert result.total_fichiers >= 2
        assert result.total_taille > 0
        assert result.total_taille_lisible != "0 o"

    def test_stats_coherentes(self, svc: OrdonnanceurService) -> None:
        """total_taille devrait correspondre à la somme des tailles individuelles."""
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        somme_individuelle = sum(f.size for f in result.fichiers)
        assert result.total_taille == somme_individuelle, (
            f"total_taille {result.total_taille} != somme {somme_individuelle}"
        )

    def test_aucun_erreur_mutagen(self, svc: OrdonnanceurService) -> None:
        """Les MP3 valides ne devraient pas produire d'erreur mutagen."""
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        for f in result.fichiers:
            assert f.erreur is None, f"Erreur sur {f.filename}: {f.erreur}"

    def test_tous_avec_metadata(self, svc: OrdonnanceurService) -> None:
        """Tous les fichiers devraient avoir leurs métadonnées extraites."""
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        for f in result.fichiers:
            assert f.source_metadata in ("tag", "pattern"), f"{f.filename}: source={f.source_metadata}"


# ── Tests templates avec vraies données ────────────────────────────


class TestTemplatesReels:
    """Valide la génération de templates avec de vraies métadonnées."""

    def test_renommage_alex_peace(self, alex_peace) -> None:
        svc, info = alex_peace
        nom = svc.generer_nom_fichier(info)
        # {artist} - {album} - {track:02d} {title}.{ext}
        # "Alex Peace - Lagoa 13 - 01 From Inside The Speaker (Original Mix).mp3"
        assert "Alex Peace" in nom
        assert "Lagoa 13" in nom
        assert "01" in nom
        assert "From Inside The Speaker" in nom
        assert nom.endswith(".mp3")

    def test_classement_alex_peace(self, alex_peace) -> None:
        svc, info = alex_peace
        chemin = svc.generer_chemin_classement(info, racine="downloads")
        # {artist}/{album}/{track:02d} {title}.{ext}
        # downloads/Alex Peace/Lagoa 13/01 From Inside The Speaker (Original Mix).mp3
        assert "downloads" in str(chemin)
        assert "Alex Peace" in str(chemin)
        assert "Lagoa 13" in str(chemin)
        assert chemin.suffix == ".mp3"

    def test_renommage_andrea_doria(self, andrea_doria) -> None:
        svc, info = andrea_doria
        nom = svc.generer_nom_fichier(info)
        assert "Andrea Doria" in nom
        assert "Lagoa 12" in nom
        assert nom.endswith(".mp3")

    def test_classement_andrea_doria(self, andrea_doria) -> None:
        svc, info = andrea_doria
        chemin = svc.generer_chemin_classement(info, racine="downloads")
        assert "Andrea Doria" in str(chemin)
        assert "Lagoa 12" in str(chemin)
        assert chemin.suffix == ".mp3"


# ── Tests dédoublonnage avec vrais fichiers ────────────────────────


class TestDedupReel:
    """Valide le pipeline de dédoublonnage (rapide → hash → résolution)
    avec de vrais fichiers audio taggés."""

    def test_pas_de_faux_positifs(self, svc: OrdonnanceurService) -> None:
        """Aucun faux positif : des fichiers uniques ne sont pas marqués
        comme doublons potentiels ou confirmés."""
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        assert result.doublons_potentiels == [], (
            f"Faux doublons potentiels : {[(g[0].filename for g in result.doublons_potentiels)]}"
        )
        assert result.doublons_confirmes == [], f"Faux doublons confirmés : {len(result.doublons_confirmes)}"
        assert result.doublons_resolus == []

    def test_doublon_detecte_par_hash(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Copier un vrai MP3 dans 2 sous-dossiers (même nom) crée un
        doublon détecté : passe rapide (nom+taille) → confirmation hash."""
        d = tmp_path / "dedup_hash"
        d.mkdir()
        (d / "sub1").mkdir()
        (d / "sub2").mkdir()
        shutil.copy2(MP3_ALEX_PEACE, d / "sub1" / "track.mp3")
        shutil.copy2(MP3_ALEX_PEACE, d / "sub2" / "track.mp3")

        result = svc.analyser_dossier(d, recursive=True)

        # Un groupe potentiel (même nom + même taille)
        assert len(result.doublons_potentiels) == 1, (
            f"Attendu 1 groupe potentiel, obtenu {len(result.doublons_potentiels)}"
        )
        assert len(result.doublons_potentiels[0]) == 2

        # Confirmé par hash
        assert len(result.doublons_confirmes) == 1, (
            f"Attendu 1 groupe confirmé, obtenu {len(result.doublons_confirmes)}"
        )
        assert len(result.doublons_confirmes[0]) == 2

        # Résolu
        assert len(result.doublons_resolus) == 1
        resol = result.doublons_resolus[0]
        assert "garde" in resol
        assert "supprimables" in resol
        assert len(resol["supprimables"]) == 1
        assert resol["taille_economisee"] == MP3_ALEX_PEACE.stat().st_size

    def test_trois_copies_meme_tag(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """3 copies d'un même MP3 dans 3 sous-dossiers : 1 gardée,
        2 supprimables, tags complets conservés."""
        d = tmp_path / "dedup_trois"
        d.mkdir()
        for i in range(3):
            (d / f"sub{i}").mkdir()
            shutil.copy2(MP3_ALEX_PEACE, d / f"sub{i}" / "track.mp3")

        result = svc.analyser_dossier(d, recursive=True)

        assert len(result.doublons_confirmes) == 1
        assert len(result.doublons_confirmes[0]) == 3

        assert len(result.doublons_resolus) == 1
        resol = result.doublons_resolus[0]
        assert len(resol["supprimables"]) == 2
        assert resol["taille_economisee"] == 2 * MP3_ALEX_PEACE.stat().st_size

        # Le fichier gardé conserve ses tags
        garde = resol["garde"]
        assert garde.artist == ALEX_PEACE_TAGS["artist"]
        assert garde.album == ALEX_PEACE_TAGS["album"]
        assert garde.title == ALEX_PEACE_TAGS["title"]
        assert garde.track == ALEX_PEACE_TAGS["track"]
        assert garde.year == ALEX_PEACE_TAGS["year"]
        assert garde.genre == ALEX_PEACE_TAGS["genre"]
        assert garde.source_metadata == "tag"

    def test_fichiers_differents_pas_de_doublon(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """2 MP3 différents dans 2 sous-dossiers (même nom mais taille
        différente) → pas de doublon."""
        d = tmp_path / "dedup_diff"
        d.mkdir()
        (d / "sub1").mkdir()
        (d / "sub2").mkdir()
        shutil.copy2(MP3_ALEX_PEACE, d / "sub1" / "track.mp3")
        shutil.copy2(MP3_ANDREA_DORIA, d / "sub2" / "track.mp3")

        result = svc.analyser_dossier(d, recursive=True)

        # Même nom mais tailles différentes → pas groupé par passe rapide
        assert result.doublons_potentiels == [], f"Faux potentiels : {len(result.doublons_potentiels)}"
        assert result.doublons_confirmes == []
        assert result.doublons_resolus == []

    def test_doublon_reel_tags_andrea_doria(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Idem avec le MP3 Andrea Doria : tags complets après résolution."""
        d = tmp_path / "dedup_andrea"
        d.mkdir()
        (d / "sub1").mkdir()
        (d / "sub2").mkdir()
        shutil.copy2(MP3_ANDREA_DORIA, d / "sub1" / "song.mp3")
        shutil.copy2(MP3_ANDREA_DORIA, d / "sub2" / "song.mp3")

        result = svc.analyser_dossier(d, recursive=True)

        assert len(result.doublons_confirmes) == 1
        assert len(result.doublons_resolus) == 1
        resol = result.doublons_resolus[0]
        garde = resol["garde"]
        assert garde.artist == ANDREA_DORIA_TAGS["artist"]
        assert garde.album == ANDREA_DORIA_TAGS["album"]
        assert garde.title == ANDREA_DORIA_TAGS["title"]
        assert garde.track == ANDREA_DORIA_TAGS["track"]
        assert garde.year == ANDREA_DORIA_TAGS["year"]
        assert garde.genre == ANDREA_DORIA_TAGS["genre"]
        assert garde.source_metadata == "tag"


# ── Tests de performance avec fichiers réels ───────────────────────


class TestPerformanceReel:
    """Mesure les temps d'exécution du pipeline complet
    avec de vrais fichiers audio (MP3 + FLAC) et valide
    qu'ils restent sous des seuils acceptables."""

    def test_scan_rapide(self, svc: OrdonnanceurService) -> None:
        """Le scan du dossier doit être quasi-instantané (< 50 ms)."""

        t0 = time.perf_counter()
        fichiers = svc.scanner_dossier(DOSSIER_PARTAGE, recursive=False)
        dt = time.perf_counter() - t0
        seuil = 0.05  # 50 ms

        assert dt < seuil, f"scan trop lent : {dt * 1000:.1f} ms (seuil {seuil * 1000:.0f} ms)"
        assert len(fichiers) >= 7, f"attendus >= 7 fichiers, trouvés {len(fichiers)}"

    def test_analyse_complete_rapide(self, svc: OrdonnanceurService) -> None:
        """L'analyse complète (scan + mutagen + stats + dedup) avec
        tous les fichiers réels doit être rapide (< 500 ms)."""

        t0 = time.perf_counter()
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        dt = time.perf_counter() - t0
        seuil = 0.5  # 500 ms

        assert dt < seuil, f"analyser_dossier trop lent : {dt * 1000:.1f} ms (seuil {seuil * 1000:.0f} ms)"
        assert result.total_audio >= 2
        assert result.total_taille > 0
        assert result.doublons_potentiels == []  # fichiers uniques
        assert result.doublons_confirmes == []

    def test_dedup_performance(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Le pipeline de dédoublonnage (10 copies d'un vrai MP3)
        doit être rapide (< 1000 ms)."""

        d = tmp_path / "perf_dedup"
        d.mkdir()
        for i in range(10):
            sub = d / f"sub{i}"
            sub.mkdir()
            shutil.copy2(MP3_ALEX_PEACE, sub / "track.mp3")

        t0 = time.perf_counter()
        result = svc.analyser_dossier(d, recursive=True)
        dt = time.perf_counter() - t0
        seuil = 1.0  # 1000 ms

        assert dt < seuil, f"dedup 10 copies trop lent : {dt * 1000:.1f} ms (seuil {seuil * 1000:.0f} ms)"
        # Vérifie que le dédoublonnage a bien fonctionné
        assert len(result.doublons_confirmes) == 1
        assert len(result.doublons_confirmes[0]) == 10
        assert len(result.doublons_resolus) == 1
        assert len(result.doublons_resolus[0]["supprimables"]) == 9

    def test_vitesse_extraction_mutagen(self) -> None:
        """L'extraction des tags mutagen doit prendre < 25 ms par
        fichier en moyenne sur les vrais MP3."""

        svc = OrdonnanceurService()
        fichiers = [MP3_ALEX_PEACE, MP3_ANDREA_DORIA]

        temps: list[float] = []
        for f in fichiers:
            t0 = time.perf_counter()
            info = svc.analyser_fichier(f)
            dt = time.perf_counter() - t0
            temps.append(dt)
            assert info.artist is not None  # extraction réussie

        moyenne = sum(temps) / len(temps)
        seuil = 0.025  # 25 ms (marge 6.5× sur le baseline 3.8 ms)

        assert moyenne < seuil, (
            f"extraction mutagen trop lente : moyenne {moyenne * 1000:.1f} ms (seuil {seuil * 1000:.0f} ms)"
        )

    def test_7_fichiers_moins_100ms(self) -> None:
        """L'analyse complète des 7 fichiers réels (MP3 + FLAC)
        doit prendre moins de 100 ms (pipeline complet).
        Ce test crée une instance fraîche pour mesurer le cas réel."""

        svc = OrdonnanceurService()
        t0 = time.perf_counter()
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        dt = time.perf_counter() - t0
        seuil = 0.1  # 100 ms

        assert dt < seuil, f"7 fichiers en {dt * 1000:.1f} ms (seuil {seuil * 1000:.0f} ms)"
        assert result.total_audio >= 7, f"attendus >= 7 fichiers audio, trouvés {result.total_audio}"


# ── Tests de régression (seuils stricts) ──────────────────────────


class TestRegressionPerformance:
    """Vérifie que les performances ne se dégradent pas entre les
    versions. Seuils 3-15× plus serrés que TestPerformanceReel.

    Baselines mesurées :
      scan      0.20 ms  (×15 → < 3 ms)
      analyse   5.64 ms  (×25 → < 150 ms)
      dedup     13.13 ms (×15 → < 200 ms)
      extract   0.90 ms  (×5  → < 5 ms)

    Note : les seuils tiennent compte du parallélisme pytest (8 workers)
    qui peut ajouter de la variance. Ils restent 3-5× plus stricts que
    les seuils de TestPerformanceReel.
    """

    def test_regression_scan(self) -> None:
        """Le scan des 7 fichiers réels doit rester < 3 ms.
        TestPerformanceReel a un seuil de 50 ms (×17 plus strict)."""
        svc = OrdonnanceurService()
        t0 = time.perf_counter()
        fichiers = svc.scanner_dossier(DOSSIER_PARTAGE, recursive=False)
        dt = time.perf_counter() - t0
        seuil = 0.003  # 3 ms
        assert dt < seuil, f"RÉGRESSION scan : {dt * 1000:.2f} ms (seuil {seuil * 1000:.0f} ms, baseline 0.20 ms)"
        assert len(fichiers) >= 7

    def test_regression_analyse(self) -> None:
        """L'analyse complète (scan + mutagen + stats + dedup) des
        7 fichiers réels doit rester < 150 ms.
        TestPerformanceReel a un seuil de 500 ms (×3.3 plus strict)."""
        svc = OrdonnanceurService()
        t0 = time.perf_counter()
        result = svc.analyser_dossier(DOSSIER_PARTAGE, recursive=False)
        dt = time.perf_counter() - t0
        seuil = 0.150  # 150 ms
        assert dt < seuil, f"RÉGRESSION analyse : {dt * 1000:.2f} ms (seuil {seuil * 1000:.0f} ms, baseline 5.64 ms)"
        assert result.total_audio >= 7
        assert result.doublons_confirmes == []

    def test_regression_dedup(self, svc: OrdonnanceurService, tmp_path: Path) -> None:
        """Le pipeline de dédoublonnage (10 copies d'un vrai MP3)
        doit rester < 200 ms.
        TestPerformanceReel a un seuil de 1000 ms (×5 plus strict)."""

        d = tmp_path / "reg_dedup"
        d.mkdir()
        for i in range(10):
            (d / f"sub{i}").mkdir()
            shutil.copy2(MP3_ALEX_PEACE, d / f"sub{i}" / "track.mp3")

        t0 = time.perf_counter()
        result = svc.analyser_dossier(d, recursive=True)
        dt = time.perf_counter() - t0
        seuil = 0.200  # 200 ms

        assert dt < seuil, f"RÉGRESSION dedup : {dt * 1000:.2f} ms (seuil {seuil * 1000:.0f} ms, baseline 13.13 ms)"
        assert len(result.doublons_confirmes) == 1
        assert len(result.doublons_resolus[0]["supprimables"]) == 9

    def test_regression_extraction(self) -> None:
        """L'extraction mutagen d'un MP3 taggé doit rester < 5 ms.
        TestPerformanceReel a un seuil de 25 ms (×5 plus strict)."""
        svc = OrdonnanceurService()
        temps: list[float] = []
        for _ in range(3):
            t0 = time.perf_counter()
            info = svc.analyser_fichier(MP3_ALEX_PEACE)
            dt = time.perf_counter() - t0
            temps.append(dt)
            assert info.artist is not None

        # 2e run (warm) pour ignorer le cold-start du 1er appel
        # qui inclut l'initialisation des modules mutagen
        warm = temps[1]
        seuil = 0.005  # 5 ms
        assert warm < seuil, (
            f"RÉGRESSION extraction : warm {warm * 1000:.2f} ms (seuil {seuil * 1000:.0f} ms, baseline 0.90 ms)"
        )
