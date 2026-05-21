"""Sysinternals Suite Launcher — outils système pour le diagnostic.

Intègre les outils Sysinternals (Mark Russinovich) directement depuis
le dossier ``src/gui/devtool/Sysinternals-suite/``.

Permet de :
- Lancer les outils GUI (Process Explorer, Process Monitor, TCPView…)
- Exécuter les outils CLI et capturer leur sortie (Handle, PsList, TCPVCon…)
- Lancer une \"Analyse rapide\" qui capture handles + threads + connexions
  de notre propre processus Python en un clic
- Copier les résultats dans le presse-papier
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QClipboard, QColor, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# ── Chemins ──────────────────────────────────────────────────────────────

SYSINTERNALS_DIR = Path(__file__).resolve().parent.parent / "Sysinternals-suite"

# ── Définition des outils ───────────────────────────────────────────────

@dataclass
class SysinternalsTool:
    """Description d'un outil Sysinternals."""

    name: str
    """Nom d'affichage."""
    exe: str
    """Nom du fichier exécutable (64 bits)."""
    exe32: str = ""
    """Nom du fichier exécutable 32 bits (fallback si 64 bits absent)."""
    category: str = "Divers"
    """Catégorie d'affichage."""
    description: str = ""
    """Description courte."""
    is_gui: bool = False
    """True si outil avec interface graphique, False si CLI."""
    cli_args: list[str] = field(default_factory=list)
    """Arguments CLI par défaut (optionnel)."""
    needs_pid: bool = False
    """True si l'outil a besoin d'un PID pour être utile."""


TOOLS: list[SysinternalsTool] = [
    # ── Réseau & Connexions ──
    SysinternalsTool("TCPView", "tcpview64.exe", "tcpview.exe",
                     "Réseau", "Visualisation en temps réel des connexions TCP/UDP", True),
    SysinternalsTool("TCPVCon", "tcpvcon64.exe", "tcpvcon.exe",
                     "Réseau", "Liste les connexions TCP par PID (CLI)", False,
                     ["-a"]),
    SysinternalsTool("PsPing", "psping64.exe", "psping.exe",
                     "Réseau", "Test de latence réseau (ping, port, latency)", False,
                     ["server.slsknet.org", "2242", "-n", "3"]),
    SysinternalsTool("WhoIs", "whois64.exe", "whois.exe",
                     "Réseau", "Recherche WHOIS pour un nom de domaine", False,
                     ["server.slsknet.org"]),

    # ── Processus & Threads ──
    SysinternalsTool("Process Explorer", "procexp64.exe", "procexp.exe",
                     "Processus", "Gestionnaire de processus complet (threads, handles, stacks)", True),
    SysinternalsTool("Process Monitor", "procmon64.exe", "Procmon.exe",
                     "Processus", "Monitoring en temps réel (fichier, registre, processus)", True),
    SysinternalsTool("PsList", "pslist64.exe", "pslist.exe",
                     "Processus", "Liste les processus et threads avec état détaillé", False,
                     ["-t", "-x"], needs_pid=True),
    SysinternalsTool("ProcDump", "procdump64.exe", "procdump.exe",
                     "Processus", "Capture un dump mémoire (dump complet par défaut)", False,
                     ["-ma"], needs_pid=True),
    SysinternalsTool("PsKill", "pskill64.exe", "pskill.exe",
                     "Processus", "Force l'arrêt d'un processus", False,
                     [], needs_pid=True),
    SysinternalsTool("PsSuspend", "pssuspend64.exe", "pssuspend.exe",
                     "Processus", "Suspend ou reprendre un processus", False,
                     [], needs_pid=True),

    # ── Handles & Mémoire ──
    SysinternalsTool("Handle", "handle64.exe", "handle.exe",
                     "Handles", "Affiche les handles ouverts par processus", False,
                     [], needs_pid=True),
    SysinternalsTool("ListDLLs", "listdlls64.exe", "Listdlls.exe",
                     "Handles", "Liste les DLL chargées par processus", False,
                     [], needs_pid=True),
    SysinternalsTool("VMMap", "vmmap64.exe", "vmmap.exe",
                     "Handles", "Analyse détaillée de la mémoire virtuelle d'un processus", True),
    SysinternalsTool("RAMMap", "RAMMap64.exe", "RAMMap.exe",
                     "Handles", "Analyse de l'utilisation de la RAM physique", True),

    # ── Monitoring ──
    SysinternalsTool("DebugView", "dbgview64.exe", "Dbgview.exe",
                     "Monitoring", "Capture les messages OutputDebugString en temps réel", True),
    SysinternalsTool("DiskMon", "Diskmon64.exe", "Diskmon.exe",
                     "Monitoring", "Surveillance des accès disque en temps réel", True),
    SysinternalsTool("DiskView", "DiskView64.exe", "DiskView.exe",
                     "Monitoring", "Analyse détaillée de l'occupation disque", True),
    SysinternalsTool("ClockRes", "Clockres64.exe", "Clockres.exe",
                     "Monitoring", "Affiche la résolution de l'horloge système", False),

    # ── Système ──
    SysinternalsTool("Autoruns", "autoruns64.exe", "Autoruns.exe",
                     "Système", "Gestionnaire des programmes au démarrage", True),
    SysinternalsTool("CoreInfo", "coreinfo64.exe", "coreinfo.exe",
                     "Système", "Affiche les infos CPU, cache et topology", False,
                     ["-c"]),
    SysinternalsTool("PsInfo", "psinfo64.exe", "psinfo.exe",
                     "Système", "Informations détaillées du système", False,
                     ["-d", "-s"]),
    SysinternalsTool("LogonSessions", "logonsessions64.exe", "logonsessions.exe",
                     "Système", "Liste les sessions utilisateur actives", False),
    SysinternalsTool("PipeList", "pipelist64.exe", "pipelist.exe",
                     "Système", "Liste les canaux nommés (named pipes)", False),
    SysinternalsTool("ShellRunAs", "ShellRunas.exe", "",
                     "Système", "Lance une application en tant qu'autre utilisateur", True),
]


# ── Worker CLI (thread séparé pour ne pas bloquer l'UI) ─────────────────

class _CliWorker(QThread):
    """Exécute un outil CLI Sysinternals dans un thread séparé."""

    output_ready = Signal(str)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, exe_path: str, args: list[str],
                 timeout: int = 30, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._exe_path = exe_path
        self._args = args
        self._timeout = timeout

    def run(self) -> None:
        try:
            # Vérifier que l'exécutable existe
            if not os.path.isfile(self._exe_path):
                self.error_occurred.emit(
                    f"Fichier introuvable : {self._exe_path}"
                )
                return

            cmd = [self._exe_path, "/accepteula"] + self._args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                errors='replace',
                timeout=self._timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n--- STDERR ---\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n--- Code retour: {result.returncode} ---"
            self.output_ready.emit(output)
        except subprocess.TimeoutExpired:
            self.error_occurred.emit(f"Timeout ({self._timeout}s) : {self._exe_path}")
        except FileNotFoundError:
            self.error_occurred.emit(f"Exécutable introuvable : {self._exe_path}")
        except Exception as e:
            self.error_occurred.emit(f"Erreur : {e}")
        finally:
            self.finished.emit()


# ── Analyse Rapide Worker (exécute plusieurs outils en séquence) ────────

class _AnalyseRapideWorker(QThread):
    """Exécute l'analyse rapide : pslist + handle + tcpvcon sur un PID."""

    output_ready = Signal(str)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, sysinternals_dir: Path, pid: int,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dir = sysinternals_dir
        self._pid = pid

    def run(self) -> None:
        pid = str(self._pid)
        parts: list[str] = []
        erreurs = 0

        try:
            # 1. PsList - threads
            parts.append("=" * 72)
            parts.append(f"PsList — Threads du processus PID {pid}")
            parts.append("=" * 72)
            pslist = self._dir / "pslist64.exe"
            if pslist.is_file():
                try:
                    r = subprocess.run(
                        # -d = threads, sans -t (tree) qui est incompatible
                        [str(pslist), "/accepteula", "-d", pid],
                        capture_output=True, text=True, errors='replace', timeout=15
                    )
                    parts.append(r.stdout or "(pas de sortie)")
                    if r.stderr:
                        parts.append(f"[STDERR] {r.stderr}")
                except Exception as e:
                    parts.append(f"[ERREUR pslist] {e}")
                    erreurs += 1
            else:
                parts.append("[PsList non trouvé]")

            # 2. Handle - handles ouverts
            parts.append("")
            parts.append("=" * 72)
            parts.append(f"Handle — Handles ouverts du PID {pid}")
            parts.append("=" * 72)
            handle = self._dir / "handle64.exe"
            if handle.is_file():
                try:
                    r = subprocess.run(
                        [str(handle), "/accepteula", "-p", pid, "-a"],
                        capture_output=True, text=True, errors='replace', timeout=15
                    )
                    output = r.stdout or "(pas de sortie)"
                    # Limiter la sortie (les handles peuvent être énormes)
                    lines = output.split("\n")
                    if len(lines) > 100:
                        output = "\n".join(lines[:50] + ["...", f"(tronqué: {len(lines)} lignes total)"] + lines[-50:])
                    parts.append(output)
                    if r.stderr:
                        parts.append(f"[STDERR] {r.stderr}")
                except Exception as e:
                    parts.append(f"[ERREUR handle] {e}")
                    erreurs += 1
            else:
                parts.append("[Handle non trouvé]")

            # 3. TCPVCon - connexions TCP
            parts.append("")
            parts.append("=" * 72)
            parts.append(f"TCPVCon — Connexions TCP du PID {pid}")
            parts.append("=" * 72)
            tcpvcon = self._dir / "tcpvcon64.exe"
            if tcpvcon.is_file():
                try:
                    # Sans -a (all) car trop lent sur tout le système
                    # On prend juste les connexions établies + filtrage PID
                    r = subprocess.run(
                        [str(tcpvcon), "/accepteula"],
                        capture_output=True, text=True, errors='replace', timeout=30
                    )
                    # Filtrer pour notre PID
                    output_lines = []
                    for line in (r.stdout or "").split("\n"):
                        if pid in line:
                            output_lines.append(line)
                    parts.append("\n".join(output_lines[:60]) if output_lines else "(pas de connexions)")
                    if r.stderr:
                        parts.append(f"[STDERR] {r.stderr}")
                except Exception as e:
                    parts.append(f"[ERREUR tcpvcon] {e}")
                    erreurs += 1
            else:
                parts.append("[TCPVCon non trouvé]")

            # 4. Tasklist du processus (fallback basique)
            parts.append("")
            parts.append("=" * 72)
            parts.append(f"Tasklist — Informations processus PID {pid}")
            parts.append("=" * 72)
            try:
                r = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True, text=True, errors='replace', timeout=10
                )
                parts.append(r.stdout or "(pas de sortie)")
                if r.stderr:
                    parts.append(f"[STDERR] {r.stderr}")
            except Exception as e:
                parts.append(f"[ERREUR tasklist] {e}")
                erreurs += 1

            # 5. netstat — connexions réseau
            parts.append("")
            parts.append("=" * 72)
            parts.append("netstat — Connexions réseau (filtrées par PID)")
            parts.append("=" * 72)
            try:
                r = subprocess.run(
                    ["netstat", "-n", "-o"],
                    capture_output=True, text=True, errors='replace', timeout=10
                )
                output_lines = []
                for line in (r.stdout or "").split("\n"):
                    if pid in line and ("ESTABLISHED" in line or "TIME_WAIT" in line or "LISTENING" in line):
                        output_lines.append(line)
                parts.append("\n".join(output_lines[:30]) if output_lines else "(pas de connexions actives)")
            except Exception as e:
                parts.append(f"[ERREUR netstat] {e}")
                erreurs += 1

            result = "\n".join(parts)
            if erreurs:
                result += f"\n\n⚠️ {erreurs} outil(s) en erreur (voir détail ci-dessus)"
            self.output_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"Erreur inattendue dans l'analyse rapide : {e}")
        finally:
            self.finished.emit()


# ── Widget de lancement Sysinternals ────────────────────────────────────

class SysinternalsLauncherWidget(QFrame):
    """Widget principal de lancement des outils Sysinternals.

    Affiche les outils par catégorie dans une arborescence, avec des
    boutons de lancement (GUI) ou d'exécution (CLI), une console de
    sortie, et une analyse rapide.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_worker: Optional[QThread] = None
        self._analyse_worker: Optional[QThread] = None
        self._analyse_done: bool = False
        self._build_ui()

    # ── Construction UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── Bannière titre ──
        titre = QLabel("🛠  SYSMINTERNALS SUITE  —  Diagnostics Système")
        titre.setStyleSheet(
            "font-weight: bold; color: #cba6f7; font-size: 11px; "
            "background: #181825; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(titre)
        lbl_info = QLabel(
            f"Suite Sysinternals ({_count_tools()} outils) — "
            f"Dossier : {SYSINTERNALS_DIR.name}/"
        )
        lbl_info.setStyleSheet("color: #6c7086; font-size: 9px; font-style: italic;")
        layout.addWidget(lbl_info)

        # ── Splitter vertical ──
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: #313244; height: 2px; }")

        # ── Haut : arborescence des outils + Analyse rapide ──
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        # Barre d'actions rapides
        actions_bar = QFrame()
        actions_bar.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #313244; border-radius: 4px; padding: 4px;"
        )
        actions_layout = QHBoxLayout(actions_bar)
        actions_layout.setContentsMargins(4, 2, 4, 2)

        self._btn_analyse = QPushButton("🔍 Analyse rapide (notre processus)")
        self._btn_analyse.setToolTip("Capture handles + threads + connexions TCP de notre processus Python en un clic")
        self._btn_analyse.setStyleSheet("background-color: #6c5ce7; font-weight: bold; color: #ffffff;")
        self._btn_analyse.clicked.connect(self._run_analyse_rapide)
        actions_layout.addWidget(self._btn_analyse)

        actions_layout.addStretch()

        self._btn_copy = QPushButton("📋 Copier les résultats")
        self._btn_copy.setStyleSheet("background-color: #45475a;")
        self._btn_copy.clicked.connect(self._copy_results)
        actions_layout.addWidget(self._btn_copy)

        self._btn_clear = QPushButton("🗑️ Vider")
        self._btn_clear.setStyleSheet("background-color: #45475a;")
        self._btn_clear.clicked.connect(self._clear_output)
        actions_layout.addWidget(self._btn_clear)

        top_layout.addWidget(actions_bar)

        # Arborescence des outils
        self._tools_tree = QTreeWidget()
        self._tools_tree.setHeaderLabels(["Outil", "Description", "Action"])
        self._tools_tree.setAlternatingRowColors(True)
        self._tools_tree.header().setStretchLastSection(False)
        self._tools_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tools_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tools_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tools_tree.setStyleSheet(
            "QTreeWidget {"
            "  background-color: #11111b;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "  font-size: 10px;"
            "}"
        )
        self._populate_tools_tree()
        top_layout.addWidget(self._tools_tree, 1)

        splitter.addWidget(top_widget)

        # ── Bas : console de sortie ──
        self._output_console = QTextEdit()
        self._output_console.setReadOnly(True)
        self._output_console.setStyleSheet(
            "QTextEdit {"
            "  background-color: #11111b;"
            "  color: #cdd6f4;"
            "  font-family: 'Consolas', 'Courier New', monospace;"
            "  font-size: 10px;"
            "  padding: 6px;"
            "  border: 1px solid #313244;"
            "  border-radius: 4px;"
            "}"
        )
        splitter.addWidget(self._output_console)

        splitter.setSizes([400, 200])
        layout.addWidget(splitter, 1)

    def _populate_tools_tree(self) -> None:
        """Remplit l'arborescence avec les outils par catégorie."""
        categories: dict[str, list[SysinternalsTool]] = {}
        for tool in TOOLS:
            categories.setdefault(tool.category, []).append(tool)

        # Ordre des catégories
        ordre = ["Réseau", "Processus", "Handles", "Monitoring", "Système"]

        for cat in ordre:
            outils = categories.get(cat, [])
            if not outils:
                continue

            cat_item = QTreeWidgetItem([f"  {cat}", "", ""])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            cat_item.setForeground(0, QColor("#89b4fa"))
            cat_item.setExpanded(True)
            self._tools_tree.addTopLevelItem(cat_item)

            for tool in outils:
                exe_path = self._find_exe(tool)
                dispo = exe_path is not None

                # Nom avec indicateur de disponibilité
                nom = f"{'🖥️' if tool.is_gui else '🔧'} {tool.name}"
                if not dispo:
                    nom += " (absent)"

                desc = tool.description

                tool_item = QTreeWidgetItem([nom, desc, ""])
                tool_item.setData(0, Qt.ItemDataRole.UserRole, tool)
                tool_item.setData(2, Qt.ItemDataRole.UserRole, exe_path or "")

                if not dispo:
                    tool_item.setForeground(0, QColor("#6c7086"))
                    tool_item.setForeground(1, QColor("#6c7086"))
                else:
                    tool_item.setForeground(0, QColor("#cdd6f4"))
                    tool_item.setForeground(1, QColor("#a6adc8"))

                # Bouton d'action dans la colonne 2
                if tool.is_gui and dispo:
                    btn = QPushButton("🚀 Lancer")
                    btn.setStyleSheet("font-size: 9px; padding: 1px 6px; background-color: #45475a;")
                    btn.clicked.connect(lambda _, t=tool: self._launch_gui(t))
                    self._tools_tree.setItemWidget(tool_item, 2, btn)
                elif not tool.is_gui and dispo:
                    btn = QPushButton("▶ Exécuter")
                    btn.setStyleSheet("font-size: 9px; padding: 1px 6px; background-color: #45475a;")
                    btn.clicked.connect(lambda _, t=tool: self._run_cli(t))
                    self._tools_tree.setItemWidget(tool_item, 2, btn)
                else:
                    lbl = QLabel("Indisponible")
                    lbl.setStyleSheet("color: #6c7086; font-size: 9px;")
                    self._tools_tree.setItemWidget(tool_item, 2, lbl)

                cat_item.addChild(tool_item)

    @staticmethod
    def _find_exe(tool: SysinternalsTool) -> Optional[str]:
        """Cherche l'exécutable (64 bits puis 32 bits)."""
        d = SYSINTERNALS_DIR
        if not d.is_dir():
            return None
        exe = d / tool.exe
        if exe.is_file():
            return str(exe)
        if tool.exe32:
            exe32 = d / tool.exe32
            if exe32.is_file():
                return str(exe32)
        return None

    # ── Lancement GUI ─────────────────────────────────────────────────

    def _launch_gui(self, tool: SysinternalsTool) -> None:
        """Lance un outil GUI (détaché, ne bloque pas)."""
        exe = self._find_exe(tool)
        if not exe:
            self._append_output(f"❌ {tool.name} : exécutable introuvable\n")
            return
        try:
            subprocess.Popen([exe], close_fds=True)
            self._append_output(f"🚀 {tool.name} lancé\n")
            logger.info("Sysinternals GUI lancé: %s", exe)
        except Exception as e:
            self._append_output(f"❌ {tool.name} : {e}\n")

    # ── Exécution CLI ─────────────────────────────────────────────────

    def _run_cli(self, tool: SysinternalsTool) -> None:
        """Exécute un outil CLI avec ses arguments par défaut."""
        exe = self._find_exe(tool)
        if not exe:
            self._append_output(f"❌ {tool.name} : exécutable introuvable\n")
            return

        # Ne pas écraser un worker en cours
        if self._current_worker and self._current_worker.isRunning():
            self._append_output(f"⏳ Un outil CLI est déjà en cours d'exécution — attendez sa fin.\n")
            return

        # Remplacer {pid} par le PID réel si nécessaire
        args = list(tool.cli_args)
        if tool.needs_pid:
            pid = os.getpid()
            args = [str(pid)] + args

        self._append_output(f"⏳ {tool.name} (PID {os.getpid()})...\n")

        self._current_worker = _CliWorker(exe, args)
        self._current_worker.output_ready.connect(lambda out: self._append_output(
            f"\n─── {tool.name} ───\n{out}\n"
        ))
        self._current_worker.error_occurred.connect(lambda err: self._append_output(
            f"❌ {tool.name} : {err}\n"
        ))
        self._current_worker.finished.connect(lambda: self._cleanup_worker())
        self._current_worker.start()

    # ── Analyse Rapide ────────────────────────────────────────────────

    def _run_analyse_rapide(self) -> None:
        """Lance l'analyse rapide du processus Python actuel."""
        pid = os.getpid()
        self._btn_analyse.setEnabled(False)
        self._btn_analyse.setText("⏳ Analyse en cours...")
        self._clear_output()
        self._analyse_done = False

        self._append_output(
            f"{'='*72}\n"
            f"🔍 ANALYSE RAPIDE — Processus Python PID {pid}\n"
            f"{'='*72}\n\n"
        )

        self._analyse_worker = _AnalyseRapideWorker(SYSINTERNALS_DIR, pid)
        self._analyse_worker.output_ready.connect(self._append_output)
        self._analyse_worker.finished.connect(self._on_analyse_done)

        def on_error(msg: str) -> None:
            self._append_output(f"❌ {msg}\n")
            # finished va aussi être émis via finally — ne pas dupliquer
            self._analyse_worker.finished.disconnect(self._on_analyse_done)
            self._on_analyse_done()

        self._analyse_worker.error_occurred.connect(on_error)
        self._analyse_worker.start()

    def _on_analyse_done(self) -> None:
        """Réactive le bouton après l'analyse."""
        if self._analyse_done:
            return
        self._analyse_done = True
        self._btn_analyse.setEnabled(True)
        self._btn_analyse.setText("🔍 Analyse rapide (notre processus)")
        self._analyse_worker = None
        self._append_output(
            "\n✅ Analyse terminée. Utilisez '📋 Copier les résultats' pour exporter.\n"
        )

    def _cleanup_worker(self) -> None:
        """Nettoie la référence au worker CLI terminé."""
        self._current_worker = None

    # ── Utilitaires ───────────────────────────────────────────────────

    def _append_output(self, text: str) -> None:
        """Ajoute du texte dans la console de sortie."""
        self._output_console.append(text.rstrip())
        # pyrefly: ignore [missing-attribute]
        self._output_console.moveCursor(QTextCursor.End)

    def _clear_output(self) -> None:
        """Vide la console de sortie."""
        self._output_console.clear()

    def _copy_results(self) -> None:
        """Copie le contenu de la console dans le presse-papier."""
        text = self._output_console.toPlainText()
        if not text.strip():
            self._append_output("(rien à copier — la console est vide)\n")
            return
        try:
            clipboard = QApplication.clipboard()
            # pyrefly: ignore [missing-attribute]
            clipboard.setText(text)
            QApplication.processEvents()  # force le flush
            self._append_output(f"📋 {len(text)} caractères copiés dans le presse-papier\n")
            logger.info("Résultats Sysinternals copiés (%d car.)", len(text))
        except Exception as e:
            self._append_output(f"❌ Erreur copie presse-papier : {e}\n")
            logger.error("Échec copie presse-papier: %s", e)


def _count_tools() -> str:
    """Retourne le nombre d'outils disponibles / total."""
    total = len(TOOLS)
    dispo = sum(1 for t in TOOLS if SYSINTERNALS_DIR.is_dir() and (SYSINTERNALS_DIR / t.exe).is_file())
    return f"{dispo}/{total}"


# ── Dock Widget détachable ──────────────────────────────────────────────

class SysinternalsDockWidget(QDockWidget):
    """QDockWidget contenant le lanceur Sysinternals.

    À ajouter à la MainWindow avec ``addDockWidget()``.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Sysinternals Suite", parent)
        self.setObjectName("_sysinternals_dock")
        # pyrefly: ignore [missing-attribute]
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.setMinimumWidth(520)
        self.setFeatures(
            QDockWidget.DockWidgetClosable |
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable
        )

        # Widget central
        self._launcher = SysinternalsLauncherWidget()
        self.setWidget(self._launcher)

        # Style
        self.setStyleSheet(
            "QDockWidget { background: #11111b; color: #cdd6f4; border: 1px solid #313244; }"
            "QDockWidget::title { background: #181825; padding: 6px; font-weight: 600; }"
        )

