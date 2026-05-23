"""Crash Reporter — Capture & Sauvegarde Immédiate des Tracebacks.

S'intègre dans le flux général du projet :
1. Remplace ``sys.excepthook`` pour intercepter toute exception Python non gérée
2. Survelile ``sys.stderr`` via un wrapper pour détecter les Traceback imprimés
   (exceptions Qt/C, callbacks, threads qui échappent à ``excepthook``)
3. Dès qu'un Traceback est détecté → sauvegarde dans ``security/crash_*.log``
   → arrêt immédiat du processus

Usage
-----
Dans `run.py`, tout en haut AVANT les autres imports :

    from security.crash_reporter import activate
    activate()
"""

from __future__ import annotations

import os
import platform
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from collections.abc import Callable
from typing import ClassVar

_CRASH_DIR = Path(__file__).parent.resolve()
_SAVED: bool = False
_LOCK = threading.Lock()
_CRASH_HOOKS: list[Callable[[], None]] = []

# Erreurs réseau non-fatales à ne pas transformer en crash
_NONFATAL_CLASSES = {"ConnectionResetError", "ConnectionAbortedError", "ConnectionRefusedError"}
_NONFATAL_WINERRORS = {"10054", "10053", "10061"}


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_system_context() -> str:
    """Retourne une chaîne formatée avec le contexte système (OS, Python, mémoire)."""
    lines = [
        f"# OS            : {platform.platform()}",
        f"# Python        : {sys.version.split()[0]}",
        f"# CPU           : {os.cpu_count()} cœurs",
    ]
    # Mémoire vive — tentatives avec psutil, fallback silencieux
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        avail_gb = mem.available / (1024 ** 3)
        lines.append(f"# Mémoire RAM   : {total_gb:.1f} Go total — {avail_gb:.1f} Go disponible")
    except ImportError:
        lines.append("# Mémoire RAM   : psutil non installé — info indisponible")
    return "\n".join(lines)


def _save_tb(text: str) -> Path:
    """Sauvegarde le texte du traceback dans un fichier horodaté.

    Returns
    -------
    Path
        Chemin absolu vers le fichier créé.
    """
    global _SAVED
    _SAVED = True
    _CRASH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _CRASH_DIR / f"crash_{ts}.log"
    try:
        with open(path, "w", encoding="utf-8") as f:
            ts = datetime.now()
            ctx = _get_system_context()
            f.write(f"# ================================================================================\n")
            f.write(f"#  CRASH REPORT — Arrêt brutal de l'application\n")
            f.write(f"# ================================================================================\n")
            f.write(f"#\n")
            f.write(f"# ❌ JE VIENS DE PLANTER !\n")
            f.write(f"#    Vérifier les logs dans 'data/logs/' et lancer un 'code-review'\n")
            f.write(f"#    sur le code pour identifier la cause racine.\n")
            f.write(f"#\n")
            f.write(f"# QUI SUIS-JE ?\n")
            f.write(f"#   Rapport d'incident critique généré automatiquement par le Crash Reporter\n")
            f.write(f"#   de l'application aioslsk (Soulseek).\n")
            f.write(f"#\n")
            f.write(f"# À QUOI JE SERS ?\n")
            f.write(f"#   Capturer immédiatement une exception non gérée (Traceback) qui a provoqué\n")
            f.write(f"#   l'arrêt brutal du processus. Permet de diagnostiquer l'origine du crash\n")
            f.write(f"#   sans perte d'information, même en cas d'arrêt forcé.\n")
            f.write(f"#\n")
            f.write(f"# QUE FAIRE AVEC CE FICHIER ?\n")
            f.write(f"#   1. Transmettre ce fichier au développeur en charge du module défaillant.\n")
            f.write(f"#   2. Analyser le Traceback ci-dessous pour identifier le fichier, la ligne\n")
            f.write(f"#      et le type d'exception (ImportError, AttributeError, RuntimeError…).\n")
            f.write(f"#   3. Le fichier est horodaté — conserver l'ordre chronologique des crashs\n")
            f.write(f"#      pour corréler avec les logs de session (data/logs/inspector_*.log).\n")
            f.write(f"#\n")
            f.write(f"# ================================================================================\n")
            f.write(f"# --- Métadonnées de la session ---\n")
            f.write(f"# Généré le  : {ts.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Commande   : {' '.join(sys.argv)}\n")
            f.write(f"# Répertoire : {Path.cwd()}\n")
            f.write(f"#\n")
            f.write(f"# --- Contexte système ---\n")
            f.write(ctx + "\n")
            f.write(f"# ================================================================================\n\n")
            f.write(text)
    except Exception:
        pass  # on ne peut plus rien faire si la sauvegarde échoue
    return path


def _call_hooks() -> None:
    """Appelle tous les hooks enregistrés (ex: sauvegarde logs inspector).

    Chaque hook est appelé dans un bloc try/except pour qu'un échec
    n'empêche pas les autres hooks de s'exécuter. Les hooks sont appelés
    avant l'arrêt brutal du processus (os._exit).
    """
    for hook in _CRASH_HOOKS:
        try:
            hook()
        except Exception:
            pass


def register_crash_hook(hook: Callable[[], None]) -> None:
    """Enregistre une fonction à appeler avant l'arrêt brutal du processus.

    Les hooks sont appelés dans l'ordre d'enregistrement juste avant
    ``os._exit(1)``, après la sauvegarde du traceback.

    Paramètres
    ----------
    hook : Callable[[], None]
        Fonction sans argument, appelée avant l'arrêt.
        Doit être thread-safe (aucune interaction Qt).
    """
    _CRASH_HOOKS.append(hook)


def _halt(path: Path) -> None:
    """Appelle les hooks, affiche un message sur stdout et arrête le processus."""
    msg = (
        f"\n🚨 CRASH DÉTECTÉ — Traceback sauvegardé : {path}\n"
        f"\n"
        f"❌ Je viens de planter !\n"
        f"   Vérifier les logs dans 'data/logs/' et lancer un 'code-review'\n"
        f"   sur le code pour identifier la cause racine.\n"
    )
    try:
        sys.__stdout__.write(msg)
        sys.__stdout__.flush()
    except Exception:
        pass
    os._exit(1)


# ── Mécanisme 1 : sys.excepthook ──────────────────────────────────────────
# Intercepte toute exception Python non gérée (le cas standard). Fonctionne
# aussi pour les exceptions levées dans les threads (Python ≥ 3.8).

_ORIGINAL_EXCEPTHOOK = sys.excepthook


def _excepthook(exc_type: type[BaseException],
                exc_value: BaseException,
                exc_tb: object) -> None:
    """Remplace sys.excepthook : sauvegarde le traceback + arrêt immédiat."""
    global _SAVED
    if not _SAVED:
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        path = _save_tb(tb_text)
        _call_hooks()
        _halt(path)
    else:
        _ORIGINAL_EXCEPTHOOK(exc_type, exc_value, exc_tb)


# ── Mécanisme 2 : sys.stderr wrapper ──────────────────────────────────────
# Détecte les Traceback imprimés sur stderr (ex : exceptions dans les
# callbacks Qt, librairies C, signaux). Utilise un timer pour attendre
# que la totalité du traceback soit écrite avant de sauvegarder.

class _StderrCapture:
    """Wrapper autour de ``sys.stderr`` qui détecte 'Traceback' en temps réel.

    Dès que la chaîne ``'Traceback'`` est détectée dans le flux, on bascule
    en mode capture. Un timer de 500 ms est lancé pour collecter la fin
    du traceback (les lignes ``File "...", line N``) avant de sauvegarder
    et de tuer le processus.
    """

    _instance: ClassVar[_StderrCapture | None] = None

    def __init__(self) -> None:
        self._original = sys.stderr
        self._buffer: list[str] = []
        self._capturing = False
        self._timer: threading.Timer | None = None
        _StderrCapture._instance = self

    # ── Interface file-like ────────────────────────────────────────────

    def write(self, text: str) -> None:
        with _LOCK:
            if not _SAVED and "Traceback (most recent call last)" in text:
                self._capturing = True
                self._buffer = [text]
                self._reset_debounce()
            elif self._capturing and not _SAVED:
                self._buffer.append(text)
                self._reset_debounce()

        self._original.write(text)

    def flush(self) -> None:
        self._original.flush()

    def close(self) -> None:
        pass

    def isatty(self) -> bool:
        return self._original.isatty()

    def fileno(self) -> int:
        return self._original.fileno()

    # ── Interne ────────────────────────────────────────────────────────

    def _reset_debounce(self) -> None:
        """Annule le timer existant et en recrée un.

        Chaque nouveau ``write()`` pendant la capture réinitialise
        le délai à 500ms — on attend ainsi 500ms d'inactivité sur
        stderr avant de considérer le traceback complet.
        """
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(0.5, self._flush)
        self._timer.daemon = True
        self._timer.start()

    @staticmethod
    def _is_nonfatal(tb_text: str) -> bool:
        """Vérifie si le traceback correspond à une erreur réseau non-fatale.

        Sur un réseau P2P comme Soulseek, les connexions entre pairs
        ferment brutalement tout le temps. Ces erreurs Windows Socket
        sont normales et ne doivent PAS crasher l'application :

        - ``ConnectionResetError`` (10054) — pair distant ferme la connexion
        - ``ConnectionAbortedError`` (10053) — connexion annulée par le logiciel
        - ``ConnectionRefusedError`` (10061) — connexion refusée par la cible

        Returns
        -------
        bool
            True si l'erreur est non-fatale (log seulement, pas de crash).
        """
        # Vérification par nom de classe d'exception (plus fiable)
        for cls_name in _NONFATAL_CLASSES:
            if cls_name in tb_text:
                return True
        # Vérification par code WinError (fallback)
        for code in _NONFATAL_WINERRORS:
            if code in tb_text:
                return True
        return False

    def _flush(self) -> None:
        """Sauvegarde le buffer capturé et arrête le processus.

        Les erreurs réseau non-fatales (ConnectionResetError) sont
        simplement loguées et ignorées — l'application continue.
        """
        with _LOCK:
            if _SAVED or not self._buffer:
                return
            tb_text = "".join(self._buffer)

        # ── Vérifier si l'erreur est non-fatale (réseau P2P normal) ──
        if self._is_nonfatal(tb_text):
            try:
                self._original.write(
                    f"[WARN] Erreur réseau non-fatale ignorée (normale en P2P) — "
                    f"l'application continue.\n"
                )
                self._original.flush()
            except Exception:
                pass
            self._capturing = False
            self._buffer.clear()
            return

        try:
            path = _save_tb(tb_text)
        except Exception:
            path = _CRASH_DIR / "crash_unsaved.log"

        # Appeler les hooks (sauvegarde logs inspector) avant l'arrêt
        _call_hooks()

        # Écrire le message sur le stderr original (pas le wrapper)
        msg = (
            f"\n🚨 CRASH DÉTECTÉ (stderr) — Traceback sauvegardé : {path}\n"
            f"\n"
            f"❌ Je viens de planter !\n"
            f"   Vérifier les logs dans 'data/logs/' et lancer un 'code-review'\n"
            f"   sur le code pour identifier la cause racine.\n"
        )
        try:
            self._original.write(msg)
            self._original.flush()
        except Exception:
            pass
        os._exit(1)


# ── Point d'entrée ─────────────────────────────────────────────────────────

def activate() -> None:
    """Active le crash reporter immédiatement.

    Doit être appelée le plus tôt possible dans le point d'entrée principal
    (``run.py``), avant tout import pouvant générer une exception.

    Effets de bord
    --------------
    - Remplace ``sys.excepthook`` par ``_excepthook``
    - Remplace ``sys.stderr`` par une instance de ``_StderrCapture``
    """
    sys.excepthook = _excepthook
    sys.stderr = _StderrCapture()


# ── Désactivation (optionnelle) ────────────────────────────────────────────

def deactivate() -> None:
    """Rétablit les valeurs originales de ``sys.excepthook`` et ``sys.stderr``."""
    sys.excepthook = _ORIGINAL_EXCEPTHOOK
    inst = _StderrCapture._instance
    if inst is not None:
        sys.stderr = inst._original
        _StderrCapture._instance = None
