"""Tests du traducteur d'erreurs aioslsk (error_translator.py).

Vérifie que chaque exception aioslsk/générique est correctement
traduite en message lisible + sévérité appropriée.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import aioslsk.exceptions as aioslsk_exc
import pytest

from src.services.error_translator import Severite, afficher, emoji_pour, traduire


# ═══════════════════════════════════════════════════════════════════
#  Severite
# ═══════════════════════════════════════════════════════════════════


class TestSeverite:
    def test_valeurs_presences(self):
        assert Severite.INFO.value == "INFO"
        assert Severite.WARNING.value == "WARNING"
        assert Severite.ERROR.value == "ERROR"
        assert Severite.SUCCES.value == "SUCCES"

    def test_tous_membres_distincts(self):
        valeurs = list(Severite)
        assert len(valeurs) == 4
        assert len({v.value for v in valeurs}) == 4


# ═══════════════════════════════════════════════════════════════════
#  emoji_pour
# ═══════════════════════════════════════════════════════════════════


class TestEmojiPour:
    @pytest.mark.parametrize(
        "severite, attendu",
        [
            (Severite.INFO, "ℹ️"),
            (Severite.WARNING, "⚠️"),
            (Severite.ERROR, "🚨"),
            (Severite.SUCCES, "✅"),
        ],
    )
    def test_emoji_correct(self, severite: Severite, attendu: str):
        assert emoji_pour(severite) == attendu


# ═══════════════════════════════════════════════════════════════════
#  traduire
# ═══════════════════════════════════════════════════════════════════


class TestTraduire:
    """Tests de la fonction traduire() — chaque type d'exception."""

    # ── Erreurs asyncio ──────────────────────────────────────────

    @pytest.mark.parametrize(
        "exc_cls, attendu_severite, extraire_msg",
        [
            pytest.param(
                asyncio.TimeoutError,
                Severite.INFO,
                lambda: "⏱ Timeout",
                id="asyncio_timeout",
            ),
            pytest.param(
                asyncio.CancelledError,
                Severite.INFO,
                lambda: "⏹ Tâche annulée",
                id="asyncio_cancelled",
            ),
        ],
    )
    def test_asyncio(
        self,
        exc_cls: type,
        attendu_severite: Severite,
        extraire_msg,
    ):
        msg, sev = traduire(exc_cls())
        assert sev == attendu_severite
        assert extraire_msg() in msg

    # ── Erreurs de connexion P2P ────────────────────────────────

    @pytest.mark.parametrize(
        "exc, debut_msg, attendu_severite",
        [
            pytest.param(
                aioslsk_exc.ConnectionFailedError("192.168.1.1:1234"),
                "🔴 Connexion P2P impossible",
                Severite.INFO,
                id="connection_failed",
            ),
            pytest.param(
                aioslsk_exc.PeerConnectionError("timed out after 30s"),
                "⏱ Connexion indirecte interrompue",
                Severite.INFO,
                id="peer_timeout",
            ),
            pytest.param(
                aioslsk_exc.PeerConnectionError("connection reset"),
                "🔴 Connexion indirecte échouée",
                Severite.INFO,
                id="peer_generic",
            ),
            pytest.param(
                aioslsk_exc.ConnectionReadError("socket closed"),
                "📖 Erreur de lecture",
                Severite.INFO,
                id="connection_read",
            ),
            pytest.param(
                aioslsk_exc.ConnectionWriteError("broken pipe"),
                "✏ Erreur d'écriture",
                Severite.INFO,
                id="connection_write",
            ),
        ],
    )
    def test_connexion_p2p(
        self, exc: Exception, debut_msg: str, attendu_severite: Severite
    ):
        msg, sev = traduire(exc)
        assert sev == attendu_severite
        assert msg.startswith(debut_msg)

    # ── Erreurs d'utilisateur / fichiers ────────────────────────

    @pytest.mark.parametrize(
        "exc, debut_msg, attendu_severite",
        [
            pytest.param(
                aioslsk_exc.NoSuchUserError("unknown_user"),
                "👤 Utilisateur introuvable",
                Severite.WARNING,
                id="no_such_user",
            ),
            pytest.param(
                aioslsk_exc.FileNotFoundError("file.ogg"),
                "📁 Fichier introuvable",
                Severite.INFO,
                id="file_not_found",
            ),
            pytest.param(
                aioslsk_exc.FileNotSharedError("file.ogg"),
                "🚫 Fichier non partagé",
                Severite.INFO,
                id="file_not_shared",
            ),
            pytest.param(
                aioslsk_exc.TransferException("transfer aborted"),
                "⬇ Erreur de transfert",
                Severite.INFO,
                id="transfer",
            ),
        ],
    )
    def test_fichiers_utilisateurs(
        self, exc: Exception, debut_msg: str, attendu_severite: Severite
    ):
        msg, sev = traduire(exc)
        assert sev == attendu_severite
        assert msg.startswith(debut_msg)

    # ── Erreurs d'authentification ──────────────────────────────

    def test_authentication_error(self):
        msg, sev = traduire(MagicMock(spec=aioslsk_exc.AuthenticationError))
        assert sev == Severite.WARNING
        assert "🔑 Échec d'authentification" in msg

    # ── Erreurs d'écoute / réseau ───────────────────────────────

    @pytest.mark.parametrize(
        "exc, debut_msg, attendu_severite",
        [
            pytest.param(
                aioslsk_exc.ListeningConnectionFailedError("port in use"),
                "🔌 Impossible d'ouvrir le port d'écoute",
                Severite.WARNING,
                id="listening_failed",
            ),
            pytest.param(
                aioslsk_exc.NetworkError("dns failure"),
                "🌐 Erreur réseau",
                Severite.WARNING,
                id="network",
            ),
            pytest.param(
                aioslsk_exc.InvalidSessionError("expired"),
                "🔄 Session invalide",
                Severite.WARNING,
                id="invalid_session",
            ),
            pytest.param(
                aioslsk_exc.RequestPlaceFailedError("server busy"),
                "📋 Échec de placement de requête",
                Severite.INFO,
                id="request_place_failed",
            ),
            pytest.param(
                aioslsk_exc.SharedDirectoryError("/music missing"),
                "📂 Erreur de dossier partagé",
                Severite.WARNING,
                id="shared_directory",
            ),
        ],
    )
    def test_reseau_config(
        self, exc: Exception, debut_msg: str, attendu_severite: Severite
    ):
        msg, sev = traduire(exc)
        assert sev == attendu_severite
        assert msg.startswith(debut_msg)

    # ── Erreurs internes / bugs ─────────────────────────────────

    @pytest.mark.parametrize(
        "exc, debut_msg, attendu_severite",
        [
            pytest.param(
                MagicMock(spec=aioslsk_exc.InvalidStateTransition),
                "❌ BUG INTERNE",
                Severite.ERROR,
                id="invalid_state_transition",
            ),
            pytest.param(
                MagicMock(spec=aioslsk_exc.MessageSerializationError),
                "❌ BUG — erreur de sérialisation",
                Severite.ERROR,
                id="serialization",
            ),
            pytest.param(
                MagicMock(spec=aioslsk_exc.MessageDeserializationError),
                "❌ BUG — erreur de désérialisation",
                Severite.ERROR,
                id="deserialization",
            ),
            pytest.param(
                MagicMock(spec=aioslsk_exc.MessageSerializationError),
                "❌ BUG — erreur de sérialisation",
                Severite.ERROR,
                id="serialization",
            ),
            pytest.param(
                MagicMock(spec=aioslsk_exc.MessageDeserializationError),
                "❌ BUG — erreur de désérialisation",
                Severite.ERROR,
                id="deserialization",
            ),
        ],
    )
    def test_bugs_internes(
        self, exc: Exception, debut_msg: str, attendu_severite: Severite
    ):
        msg, sev = traduire(exc)
        assert sev == attendu_severite
        assert msg.startswith(debut_msg)

    # ── UnknownMessage → INFO ───────────────────────────────────

    def test_unknown_message(self):
        msg, sev = traduire(MagicMock(spec=aioslsk_exc.UnknownMessageError))
        assert sev == Severite.INFO
        assert "📡 Message inconnu" in msg

    # ── Fallback ────────────────────────────────────────────────

    def test_fallback_aioslsk_inconnu_leve_error(self):
        """Une exception aioslsk non listée → ERROR + nom de la classe."""

        class _Fictive(aioslsk_exc.AioSlskException):
            pass

        msg, sev = traduire(_Fictive("weird"))
        assert sev == Severite.ERROR
        assert "_Fictive" in msg

    def test_fallback_exception_generique_leve_warning(self):
        """Une exception Python standard non listée → WARNING."""
        msg, sev = traduire(ValueError("something"))
        assert sev == Severite.WARNING
        assert "ValueError" in msg

    def test_fallback_exception_standard_leve_warning(self):
        msg, sev = traduire(RuntimeError("crash"))
        assert sev == Severite.WARNING
        assert "RuntimeError" in msg


# ═══════════════════════════════════════════════════════════════════
#  afficher
# ═══════════════════════════════════════════════════════════════════


class TestAfficher:
    def test_format_contient_severite_et_message(self):
        resultat = afficher(asyncio.TimeoutError())
        assert "[INFO]" in resultat
        assert "⏱ Timeout" in resultat

    def test_format_contient_nom_severite(self):
        resultat = afficher(aioslsk_exc.AuthenticationError("bad pass", "bad pass"))
        assert "[WARNING]" in resultat
        assert "🔑" in resultat

    def test_unknown_aioslsk_inclut_nom_classe(self):
        class _Bogus(aioslsk_exc.AioSlskException):
            pass

        resultat = afficher(_Bogus("xyz"))
        assert "[ERROR]" in resultat
        assert "_Bogus" in resultat
