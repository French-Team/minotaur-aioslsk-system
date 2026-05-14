"""
Zone Centrale — contenu principal affiché via QStackedWidget.

Affiche la page correspondant à l'élément sélectionné
dans la zone gauche (ou ailleurs).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.clients_actifs import ClientsActifsPage
from src.gui.widgets.config import (
    ConfigCombo,
    ConfigDirectoryPicker,
    ConfigEntry,
    ConfigFilePicker,
    ConfigPage,
    ConfigSection,
    ConfigSpin,
    ConfigToggle,
)
from src.gui.widgets.connexions import ConnexionPage
from src.gui.widgets.telechargements import TelechargementsPage
from src.services.soulseek_client import soulseek_service

import logging

logger = logging.getLogger(__name__)


# ── Helpers de formatage ─────────────────────────────────────────


def _format_taille(bytes_val: int) -> str:
    """Formate une taille en bytes vers une chaîne lisible."""
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val / 1_000_000_000:.1f} Go"
    if bytes_val >= 1_000_000:
        return f"{bytes_val / 1_000_000:.1f} Mo"
    if bytes_val >= 1_000:
        return f"{bytes_val / 1_000:.1f} Ko"
    return f"{bytes_val} o"


def _transfer_state_to_statut(state: object) -> str:
    """Convertit un TransferState.State en label de statut."""
    state_name = state.name if hasattr(state, 'name') else str(state)
    mapping = {
        "VIRGIN": "attente",
        "QUEUED": "attente",
        "INITIALIZING": "attente",
        "INCOMPLETE": "en_cours",
        "DOWNLOADING": "en_cours",
        "UPLOADING": "en_cours",
        "COMPLETE": "termine",
        "FAILED": "echoue",
        "ABORTED": "echoue",
        "PAUSED": "attente",
        "UNSET": "attente",
    }
    return mapping.get(state_name.upper(), "en_cours")


def _transfer_statut_label(transfer: object) -> str:
    """Détermine le statut initial d'un transfert."""
    state = getattr(transfer, 'state', None)
    if state is None:
        return "attente"
    return _transfer_state_to_statut(state)


class CenterZone(QFrame):
    """Zone de contenu principal avec pages empilables."""

    disconnect_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("centerZone")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Stacked widget : chaque page = un contenu ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("centerStack")
        layout.addWidget(self._stack)

        # Pages indexées par nom
        self._pages: dict[str, QWidget] = {}

        # Page de connexion (affichée au démarrage)
        self._build_connexion_page()

        # Page d'accueil (après connexion)
        self._build_home_page()

        # Page clients actifs
        self._build_clients_actifs_page()

        # Page téléchargements
        self._build_telechargements_page()

        # Pages de configuration — remplies avec les vraies options
        self._build_config_pages()

        # Pages du footer (menus)
        for name in ("menu_1", "menu_2", "menu_3", "menu_4", "menu_5"):
            self._build_menu_page(name)

        # Connexion des signaux d'événements Soulseek
        self._connect_event_signals()

        # Affiche la page de connexion au démarrage
        self.show_page("connexion")

    # ── API publique ─────────────────────────────────────────────

    @property
    def stack(self) -> QStackedWidget:
        return self._stack

    @property
    def current_page(self) -> str | None:
        """Retourne le nom de la page affichée ou None."""
        widget = self._stack.currentWidget()
        for name, page in self._pages.items():
            if page is widget:
                return name
        return None

    def show_page(self, name: str) -> None:
        """Affiche la page demandée par son nom."""
        page = self._pages.get(name)
        if page is not None:
            self._stack.setCurrentWidget(page)

    def show_home(self, username: str) -> None:
        """Affiche la page d'accueil avec les infos de l'utilisateur connecté."""
        self._home_greeting.setText(f"Bienvenue, {username} !")
        self._home_subtitle.setText("Vous êtes connecté au réseau Soulseek.")
        # Met à jour les stats
        for row in [self._home_stat_user, self._home_stat_status, self._home_stat_serveur]:
            label = getattr(row, '_value_label', None)
            if label is not None:
                if row is self._home_stat_user:
                    label.setText(username)
                elif row is self._home_stat_status:
                    label.setText("Connecté ✓")
                    label.setStyleSheet("color: #00e676; font-size: 13px; background: transparent;")
                elif row is self._home_stat_serveur:
                    label.setText("Soulseek (slsk:// )")
        self.show_page("accueil")

    def show_connexion(self) -> None:
        """Affiche la page de connexion."""
        # Réinitialise la page d'accueil pour le prochain utilisateur
        self._home_greeting.setText("Bienvenue sur aioslsk")
        self._home_subtitle.setText("Vous êtes connecté au réseau Soulseek.")
        for row in [self._home_stat_user, self._home_stat_status, self._home_stat_serveur]:
            label = getattr(row, '_value_label', None)
            if label is not None:
                label.setText("—")
                label.setStyleSheet("color: #e4e4ec; font-size: 12px; background: transparent;")
        self.show_page("connexion")

    def page(self, name: str) -> QWidget | None:
        """Retourne le widget d'une page par son nom."""
        return self._pages.get(name)

    @property
    def connexion_page(self) -> QWidget | None:
        """Page de connexion Soulseek."""
        return self._pages.get("connexion")

    @property
    def clients_actifs_page(self) -> QWidget | None:
        """Page des clients actifs."""
        return self._pages.get("clients-actifs")

    @property
    def telechargements_page(self) -> QWidget | None:
        """Page des téléchargements."""
        return self._pages.get("telechargements")

    # ── Construction des pages ───────────────────────────────────

    def _build_clients_actifs_page(self) -> None:
        """Page des clients actifs et joignables."""
        page = ClientsActifsPage()
        self._pages["clients-actifs"] = page
        self._stack.addWidget(page)

    def _build_telechargements_page(self) -> None:
        """Page des téléchargements."""
        page = TelechargementsPage()
        self._pages["telechargements"] = page
        self._stack.addWidget(page)

    def _build_connexion_page(self) -> None:
        """Page de connexion Soulseek."""
        page = ConnexionPage()
        self._pages["connexion"] = page
        self._stack.addWidget(page)

    def _build_home_page(self) -> None:
        """Page d'accueil / dashboard (affichée après connexion)."""
        page = QWidget()
        page.setObjectName("pageAccueil")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(0)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # ── Contenu centré avec largeur max ──
        container = QWidget()
        container.setFixedWidth(560)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        # ── Bannière de bienvenue ──
        welcome = QFrame()
        welcome.setObjectName("homeWelcome")
        welcome.setStyleSheet(
            "#homeWelcome {"
            "  background: #1e1e2e; border: 1px solid #2e2e3a;"
            "  border-radius: 12px; padding: 24px;"
            "}"
        )
        wl = QVBoxLayout(welcome)
        wl.setSpacing(4)

        self._home_greeting = QLabel("Bienvenue sur aioslsk")
        self._home_greeting.setStyleSheet(
            "color: #e4e4ec; font-size: 20px; font-weight: 700;"
        )
        self._home_greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(self._home_greeting)

        self._home_subtitle = QLabel(
            "Vous êtes connecté au réseau Soulseek."
        )
        self._home_subtitle.setStyleSheet(
            "color: #8a8a9a; font-size: 13px;"
        )
        self._home_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(self._home_subtitle)

        lay.addWidget(welcome)

        # ── Grille d'actions rapides ──
        actions_title = QLabel("Actions rapides")
        actions_title.setStyleSheet(
            "color: #5a5a6a; font-size: 11px; font-weight: 700;"
            " letter-spacing: 1px;"
        )
        lay.addWidget(actions_title)

        grid = QFrame()
        grid.setStyleSheet(
            "background: transparent; border: none;"
        )
        gl = QHBoxLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(12)

        cards_data = [
            ("🔍", "Rechercher", "Chercher des fichiers\nsur le réseau", "Recherche"),
            ("📥", "Téléchargements", "Voir vos fichiers\nen cours", "Téléchargement"),
            ("👥", "Clients actifs", "Utilisateurs\nconnectés", "clients-actifs"),
            ("⚙️", "Configuration", "Paramètres du\ncompte et réseau", "Général"),
        ]

        for icon, title_text, desc, page_name in cards_data:
            card = self._create_action_card(icon, title_text, desc, page_name)
            gl.addWidget(card)

        lay.addWidget(grid)

        # ── Stats ──
        stats_title = QLabel("Informations")
        stats_title.setStyleSheet(
            "color: #5a5a6a; font-size: 11px; font-weight: 700;"
            " letter-spacing: 1px;"
        )
        lay.addWidget(stats_title)

        stats = QFrame()
        stats.setObjectName("homeStats")
        stats.setStyleSheet(
            "#homeStats {"
            "  background: #1e1e2e; border: 1px solid #2e2e3a;"
            "  border-radius: 12px; padding: 20px;"
            "}"
        )
        sl = QVBoxLayout(stats)
        sl.setSpacing(4)

        self._home_stat_user = self._stat_row("👤", "Utilisateur")
        sl.addWidget(self._home_stat_user)

        self._home_stat_status = self._stat_row("🔌", "Statut")
        sl.addWidget(self._home_stat_status)

        self._home_stat_serveur = self._stat_row("🌐", "Serveur")
        sl.addWidget(self._home_stat_serveur)

        lay.addWidget(stats)

        # ── Bouton déconnexion ──
        self._home_disconnect_btn = QPushButton("Se déconnecter")
        self._home_disconnect_btn.setObjectName("homeDisconnectBtn")
        self._home_disconnect_btn.setStyleSheet(
            "#homeDisconnectBtn {"
            "  background: #2a1a1a; color: #ff5252;"
            "  border: 1px solid #3a2020; border-radius: 8px;"
            "  padding: 10px 20px; font-size: 13px; font-weight: 600;"
            "}"
            "#homeDisconnectBtn:hover {"
            "  background: #3a2020; border-color: #ff5252;"
            "}"
        )
        self._home_disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        lay.addWidget(self._home_disconnect_btn)

        outer.addWidget(container, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._pages["accueil"] = page
        self._stack.addWidget(page)

    def _create_action_card(self, icon: str, title: str, desc: str, page_name: str) -> QWidget:
        """Crée une carte d'action rapide cliquable."""
        card = QFrame()
        card.setObjectName("homeActionCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(
            "#homeActionCard {"
            "  background: #1e1e2e; border: 1px solid #2e2e3a;"
            "  border-radius: 10px; padding: 16px;"
            "}"
            "#homeActionCard:hover {"
            "  background: #252538; border-color: #6c5ce7;"
            "}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(6)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ic = QLabel(icon)
        ic.setStyleSheet("font-size: 24px; background: transparent;")
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(ic)

        t = QLabel(title)
        t.setStyleSheet("color: #c4c4d0; font-size: 12px; font-weight: 700; background: transparent;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet("color: #6a6a7a; font-size: 10px; background: transparent;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setWordWrap(True)
        cl.addWidget(d)

        # Click navigation
        card.mousePressEvent = lambda e, pn=page_name: self.show_page(pn)  # type: ignore[method-assign]

        return card

    def _stat_row(self, icon: str, label: str) -> QFrame:
        """Crée une ligne d'information avec icône et label."""
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 4, 0, 4)
        rl.setSpacing(10)

        ic = QLabel(icon)
        ic.setStyleSheet("font-size: 16px; background: transparent;")
        ic.setFixedWidth(24)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(ic)

        lb = QLabel(label)
        lb.setStyleSheet("color: #8a8a9a; font-size: 12px; font-weight: 600; background: transparent;")
        lb.setFixedWidth(100)
        rl.addWidget(lb)

        val = QLabel("—")
        val.setStyleSheet("color: #e4e4ec; font-size: 12px; background: transparent;")
        rl.addWidget(val)
        rl.addStretch(1)

        # Stocker la référence pour la mettre à jour plus tard
        setattr(row, '_value_label', val)

        return row

    def _build_config_pages(self) -> None:
        """Construit les pages de configuration avec leurs options."""

        # ════════════════════════ Général ════════════════════════
        general = ConfigPage("Général")

        section_demarrage = ConfigSection("Démarrage")
        section_demarrage.add(ConfigToggle(
            "Scanner les partages au démarrage",
            "general.scan_on_start",
            description="Analyse les dossiers partagés au lancement de l'application",
        ))
        general.add(section_demarrage)

        section_profil = ConfigSection("Profil")
        section_profil.add(ConfigEntry(
            "Description",
            "general.description_profil",
            placeholder="Présentez-vous aux autres utilisateurs Soulseek...",
            description="Description affichée sur votre profil public Soulseek. "
                       "Visible par les autres utilisateurs.",
        ))
        section_profil.add(ConfigFilePicker(
            "Photo de profil",
            "general.photo_profil",
            placeholder="Aucune image sélectionnée",
            file_filter="Images (*.png *.jpg *.jpeg *.gif *.bmp)",
            description="Image affichée sur votre profil public. "
                       "Formats supportés : PNG, JPG, GIF, BMP.",
        ))
        general.add(section_profil)

        section_interets = ConfigSection("Centres d'intérêt")
        section_interets.add(ConfigEntry(
            "J'aime",
            "general.interets_aimes",
            placeholder="Ex: Rock, Jazz, Soulseek, Production musicale…",
            description="Centres d'intérêt que vous appréciez. "
                       "Séparez les valeurs par des virgules.",
        ))
        section_interets.add(ConfigEntry(
            "Je n'aime pas",
            "general.interets_detestes",
            placeholder="Ex: Spam, Mauvaise qualité audio…",
            description="Centres d'intérêt que vous n'appréciez pas. "
                       "Séparez les valeurs par des virgules.",
        ))
        general.add(section_interets)

        self._pages["Général"] = general
        self._stack.addWidget(general)

        # ════════════════════════ Réseau ═════════════════════════
        reseau = ConfigPage("Réseau")

        section_connexion = ConfigSection("Connexion")
        section_connexion.add(ConfigToggle(
            "UPnP (Port mapping automatique)",
            "reseau.upnp",
            description="Permet aux autres utilisateurs de vous joindre directement. "
                       "Nécessite une box compatible. Mode passif sinon.",
        ))
        section_connexion.add(ConfigSpin(
            "Port d'écoute",
            "reseau.port_ecoute",
            minimum=1024,
            maximum=65535,
            step=1,
            description="Port TCP pour les connexions entrantes (défaut: 60000). "
                       "Redémarrage nécessaire pour appliquer.",
        ))
        section_connexion.add(ConfigSpin(
            "Port obfusqué",
            "reseau.port_obfusque",
            minimum=1024,
            maximum=65535,
            step=1,
            description="Port secondaire pour connexions obfusquées (défaut: 60001).",
        ))
        section_connexion.add(ConfigToggle(
            "Obfuscation des connexions P2P",
            "reseau.obfuscation_p2p",
            description="Obfusque le trafic entre pairs pour contourner "
                       "certains filtres réseau. Désactivez si vous avez des "
                       "problèmes de connexion.",
        ))
        section_connexion.add(ConfigCombo(
            "Mode de connexion peer",
            "reseau.mode_connexion_peer",
            options=[
                ("Course (RACE) — Tente toutes les méthodes en parallèle", "race"),
                ("Secours (FALLBACK) — Méthodes séquentielles", "fallback"),
            ],
            description="Comment le client établit les connexions avec les autres "
                       "utilisateurs. 'RACE' est plus rapide mais plus agressif.",
        ))
        section_connexion.add(ConfigCombo(
            "Mode d'erreur d'écoute",
            "reseau.mode_erreur_ecoute",
            options=[
                ("Clear — Erreur seulement si connexion non-obfusquée échoue", "clear"),
                ("Any — Erreur si une connexion échoue", "any"),
                ("All — Erreur si toutes les connexions échouent", "all"),
            ],
            description="Quand déclencher une erreur d'écoute. 'Clear' est le comportement par défaut de Soulseek.",
        ))
        reseau.add(section_connexion)

        section_limites = ConfigSection("Limites")
        section_limites.add(ConfigSpin(
            "Limite upload (Kbps)",
            "reseau.limite_upload_kbps",
            minimum=0,
            maximum=100000,
            step=10,
            suffix=" Kbps",
            description="Vitesse maximale d'envoi vers les autres utilisateurs. "
                       "0 = illimité.",
        ))
        section_limites.add(ConfigSpin(
            "Limite download (Kbps)",
            "reseau.limite_download_kbps",
            minimum=0,
            maximum=100000,
            step=10,
            suffix=" Kbps",
            description="Vitesse maximale de réception depuis les autres utilisateurs. "
                       "0 = illimité.",
        ))
        reseau.add(section_limites)

        section_reconnexion = ConfigSection("Reconnexion")
        section_reconnexion.add(ConfigToggle(
            "Reconnexion automatique",
            "reseau.reconnexion_auto",
            description="Tente de se reconnecter automatiquement au serveur "
                       "en cas de déconnexion.",
        ))
        section_reconnexion.add(ConfigSpin(
            "Délai de reconnexion (s)",
            "reseau.reconnexion_timeout",
            minimum=1,
            maximum=300,
            step=5,
            suffix=" s",
            description="Temps d'attente avant de tenter une reconnexion. "
                       "1 = immédiat, 300 = 5 minutes.",
        ))
        reseau.add(section_reconnexion)

        section_serveur = ConfigSection("Serveur")
        section_serveur.add(ConfigEntry(
            "Hôte du serveur",
            "reseau.hote_serveur",
            placeholder="server.slsknet.org",
            description="Adresse du serveur Soulseek auquel se connecter. "
                       "Ne changez que si vous utilisez un serveur alternatif.",
        ))
        section_serveur.add(ConfigSpin(
            "Port du serveur",
            "reseau.port_serveur",
            minimum=1,
            maximum=65535,
            step=1,
            description="Port du serveur Soulseek (défaut: 2416).",
        ))
        reseau.add(section_serveur)

        section_upnp = ConfigSection("UPnP avancé")
        section_upnp.add(ConfigSpin(
            "Durée de bail (s)",
            "reseau.duree_bail_upnp",
            minimum=300,
            maximum=86400,
            step=60,
            suffix=" s",
            description="Durée de validité du mapping de port UPnP (défaut: 21600 = 6h). "
                       "Redemandé automatiquement après expiration.",
        ))
        section_upnp.add(ConfigSpin(
            "Intervalle de vérification (s)",
            "reseau.intervalle_upnp",
            minimum=30,
            maximum=3600,
            step=10,
            suffix=" s",
            description="Fréquence de vérification de l'état UPnP (défaut: 600 = 10 min).",
        ))
        section_upnp.add(ConfigSpin(
            "Timeout de découverte (s)",
            "reseau.timeout_upnp",
            minimum=1,
            maximum=60,
            step=1,
            suffix=" s",
            description="Délai maximum pour découvrir les périphériques UPnP "
                       "sur le réseau local (défaut: 10s).",
        ))
        reseau.add(section_upnp)

        self._pages["Réseau"] = reseau
        self._stack.addWidget(reseau)

        # ════════════════════════ Recherche ══════════════════════
        recherche = ConfigPage("Recherche")

        section_resultats = ConfigSection("Résultats")
        section_resultats.add(ConfigSpin(
            "Nombre max de résultats",
            "recherche.nb_resultats_max",
            minimum=0,
            maximum=10000,
            step=50,
            description="Nombre maximal de résultats à afficher par recherche. "
                       "100 = défaut Soulseek. 0 = illimité.",
        ))
        section_resultats.add(ConfigSpin(
            "Stockage mémoire max",
            "recherche.nb_max_memoire",
            minimum=10,
            maximum=50000,
            step=100,
            description="Nombre maximal de résultats conservés en mémoire. "
                       "500 = défaut Soulseek. Réduire pour économiser la RAM.",
        ))
        recherche.add(section_resultats)

        section_envoi = ConfigSection("Envoi")
        section_envoi.add(ConfigToggle(
            "Stocker les résultats",
            "recherche.stocker_resultats",
            description="Conserve localement les résultats de recherches "
                       "pour consultation ultérieure. Désactiver pour "
                       "économiser de la mémoire.",
        ))
        section_envoi.add(ConfigSpin(
            "Timeout des requêtes (s)",
            "recherche.timeout_requete",
            minimum=0,
            maximum=300,
            step=5,
            suffix=" s",
            description="Délai maximum d'attente d'une réponse de recherche. "
                       "0 = pas de timeout. 30 = valeur recommandée.",
        ))
        section_envoi.add(ConfigSpin(
            "Timeout des souhaits (s)",
            "recherche.timeout_souhaits",
            minimum=-1,
            maximum=3600,
            step=5,
            suffix=" s",
            description="Délai maximum d'attente pour les résultats de souhaits. "
                       "-1 = désactivé. 60 = valeur recommandée.",
        ))
        recherche.add(section_envoi)

        section_souhaits = ConfigSection("Souhaits")
        section_souhaits.add(ConfigEntry(
            "Requêtes de souhaits",
            "recherche.souhaits",
            placeholder="Ex: album vinyl, rare flac, concert bootleg…",
            description="Requêtes de souhaits surveillées en permanence. "
                       "Séparez les requêtes par des virgules.",
        ))
        recherche.add(section_souhaits)

        self._pages["Recherche"] = recherche
        self._stack.addWidget(recherche)

        # ════════════════════════ Téléchargement ═════════════════
        telechargement = ConfigPage("Téléchargement")

        section_limites = ConfigSection("Limites")
        section_limites.add(ConfigSpin(
            "Slots d'upload simultanés",
            "telechargement.slots_upload",
            minimum=1,
            maximum=100,
            step=1,
            description="Nombre de fichiers pouvant être uploadés en même temps. 2 = défaut Soulseek.",
        ))
        telechargement.add(section_limites)

        section_destination = ConfigSection("Destination")
        section_destination.add(ConfigDirectoryPicker(
            "Dossier de destination",
            "telechargement.dossier_destination",
            placeholder="Dossier par défaut Soulseek…",
            description="Où enregistrer les fichiers téléchargés. Laissez vide pour utiliser le dossier par défaut de Soulseek.",
        ))
        telechargement.add(section_destination)

        section_rapport = ConfigSection("Rapport")
        section_rapport.add(ConfigSpin(
            "Intervalle de rapport (ms)",
            "telechargement.intervalle_rapport",
            minimum=50,
            maximum=10000,
            step=50,
            description="Fréquence des mises à jour de progression. 250 ms = défaut Soulseek (0.25 s).",
        ))
        telechargement.add(section_rapport)

        self._pages["Téléchargement"] = telechargement
        self._stack.addWidget(telechargement)

        # ══════════════════════════ Utilisateurs ═══════════════════
        utilisateurs = ConfigPage("Utilisateurs")

        section_amis = ConfigSection("Amis")
        section_amis.add(ConfigEntry(
            "Liste d'amis",
            "utilisateurs.liste_amis",
            placeholder="user1, user2, user3",
            description="Noms d'utilisateur séparés par des virgules. Ces amis seront ajoutés au démarrage.",
        ))
        utilisateurs.add(section_amis)

        section_bloques = ConfigSection("Bloqués")
        section_bloques.add(ConfigEntry(
            "Utilisateurs bloqués",
            "utilisateurs.liste_bloques",
            placeholder="spammer, troll",
            description="Noms d'utilisateur séparés par des virgules. Bloquer = restreindre les messages, recherches, téléchargements, etc.",
        ))
        utilisateurs.add(section_bloques)

        self._pages["Utilisateurs"] = utilisateurs
        self._stack.addWidget(utilisateurs)

        # ════════════════════════════ Partages ═════════════════════
        partages = ConfigPage("Partages")

        section_dossier1 = ConfigSection("Dossier 1")
        section_dossier1.add(ConfigDirectoryPicker(
            "Chemin du dossier",
            "partages.dossier_1_chemin",
            placeholder="Sélectionnez un dossier à partager…",
            description="Dossier à partager avec les autres utilisateurs Soulseek.",
        ))
        section_dossier1.add(ConfigCombo(
            "Mode de partage",
            "partages.dossier_1_mode",
            options=[
                ("Tout le monde — Partagé avec tous les utilisateurs", "everyone"),
                ("Amis uniquement — Partagé seulement avec vos amis", "friends"),
                ("Utilisateurs — Partagé avec une liste spécifique", "users"),
            ],
            description="Qui peut voir et télécharger ce dossier. "
                       "'Tout le monde' est le comportement par défaut.",
        ))
        section_dossier1.add(ConfigEntry(
            "Utilisateurs autorisés",
            "partages.dossier_1_utilisateurs",
            placeholder="user1, user2 (mode 'Utilisateurs' uniquement)",
            description="Noms d'utilisateur autorisés à accéder à ce dossier. "
                       "Séparez les noms par des virgules. "
                       "Applicable uniquement avec le mode 'Utilisateurs'.",
        ))
        partages.add(section_dossier1)

        section_dossier2 = ConfigSection("Dossier 2")
        section_dossier2.add(ConfigDirectoryPicker(
            "Chemin du dossier",
            "partages.dossier_2_chemin",
            placeholder="Sélectionnez un dossier à partager…",
            description="Second dossier à partager avec les autres utilisateurs Soulseek.",
        ))
        section_dossier2.add(ConfigCombo(
            "Mode de partage",
            "partages.dossier_2_mode",
            options=[
                ("Tout le monde — Partagé avec tous les utilisateurs", "everyone"),
                ("Amis uniquement — Partagé seulement avec vos amis", "friends"),
                ("Utilisateurs — Partagé avec une liste spécifique", "users"),
            ],
            description="Qui peut voir et télécharger ce dossier. "
                       "'Tout le monde' est le comportement par défaut.",
        ))
        section_dossier2.add(ConfigEntry(
            "Utilisateurs autorisés",
            "partages.dossier_2_utilisateurs",
            placeholder="user1, user2 (mode 'Utilisateurs' uniquement)",
            description="Noms d'utilisateur autorisés à accéder à ce dossier. "
                       "Séparez les noms par des virgules. "
                       "Applicable uniquement avec le mode 'Utilisateurs'.",
        ))
        partages.add(section_dossier2)

        self._pages["Partages"] = partages
        self._stack.addWidget(partages)

        # ════════════════════════════ Salons ══════════════════════
        salons = ConfigPage("Salons")

        section_general = ConfigSection("Général")
        section_general.add(ConfigToggle(
            "Rejoindre les salons automatiquement",
            "salons.auto_join",
            description="Rejoindre les salons favoris et les salons par défaut dès la connexion.",
        ))
        section_general.add(ConfigToggle(
            "Accepter les invitations aux salons privés",
            "salons.invitations_privees",
            description="Permet aux autres utilisateurs de vous inviter dans des salons privés. "
                       "Désactivez pour ne recevoir aucune invitation.",
        ))
        section_general.add(ConfigEntry(
            "Salons favoris",
            "salons.favoris",
            placeholder="Ex: #musique, #techno, #chat-francais…",
            description="Salons à rejoindre automatiquement au démarrage. "
                       "Séparez les noms par des virgules.",
        ))
        salons.add(section_general)

        self._pages["Salons"] = salons
        self._stack.addWidget(salons)

        # ── Debug ────────────────────────────────────────────────────────
        debug = ConfigPage("Debug")
        section_debug = ConfigSection("Options de débogage")
        section_debug.add(
            ConfigToggle(
                "debug.search_for_parent",
                "Rechercher un parent",
                "Activer la recherche d'un parent lors de la connexion au serveur",
            )
        )
        section_debug.add(
            ConfigEntry(
                "debug.ip_overrides",
                "Surcharges IP (JSON)",
                "Surcharges d'adresses IP au format JSON\nex: {\"username\": \"1.2.3.4\"}",
            )
        )
        section_debug.add(
            ConfigToggle(
                "debug.log_connection_count",
                "Journaliser les connexions",
                "Enregistrer le nombre de connexions dans les logs",
            )
        )
        debug.add(section_debug)
        self._pages["Debug"] = debug
        self._stack.addWidget(debug)

    def _build_menu_page(self, name: str) -> None:
        """Crée une page de menu vide (remplie plus tard)."""
        page = QWidget()
        page.setObjectName(f"page{name}")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        title = QLabel(f"Menu : {name}")
        title.setStyleSheet(
            "color: #6c5ce7; font-size: 16px; font-weight: 700;"
        )
        lay.addWidget(title)

        placeholder = QLabel(
            f"Contenu de la page {name}\n"
            "(à venir)"
        )
        placeholder.setStyleSheet("color: #3a3a4a; font-size: 12px;")
        lay.addWidget(placeholder)

        lay.addStretch(1)
        self._pages[name] = page
        self._stack.addWidget(page)

    # ── Connexion des événements Soulseek ───────────────────────

    def _connect_event_signals(self) -> None:
        """Connecte les signaux d'événements Soulseek aux widgets UI."""

        # ── Transfers → TelechargementsPage ──────────────────────

        soulseek_service.transfer_added.connect(self._on_transfer_added)
        soulseek_service.transfer_removed.connect(self._on_transfer_removed)
        soulseek_service.transfer_progress.connect(self._on_transfer_progress)

        # ── Recherche → log (UI à venir) ─────────────────────────

        soulseek_service.search_result_received.connect(
            lambda evt: logger.debug(
                "Résultat de recherche '%s': %s fichiers de %s",
                evt.query.query,
                len(evt.query.results) if hasattr(evt.query, 'results') else '?',
                evt.result.username if hasattr(evt.result, 'username') else '?',
            )
        )

        # ── Messages → log (UI à venir) ───────────────────────────

        soulseek_service.private_message_received.connect(
            lambda evt: logger.info(
                "Message privé de %s: %s",
                evt.message.username if hasattr(evt.message, 'username') else '?',
                evt.message.content[:80] if hasattr(evt.message, 'content') else '?',
            )
        )
        soulseek_service.room_message_received.connect(
            lambda evt: logger.debug(
                "Salon %s — %s: %s",
                evt.message.room_name if hasattr(evt.message, 'room_name') else '?',
                evt.message.username if hasattr(evt.message, 'username') else '?',
                evt.message.content[:80] if hasattr(evt.message, 'content') else '?',
            )
        )

    # ── Handlers de transfert ───────────────────────────────────

    def _on_transfer_added(self, evt: object) -> None:
        """Handler : un transfert a été ajouté."""
        page = self.telechargements_page
        if page is None:
            return
        transfer = getattr(evt, 'transfer', None)
        if transfer is None:
            return

        identifiant = transfer.remote_path
        fichier = identifiant.split("/")[-1].split("\\")[-1]  # extraire le nom
        fichiersize = getattr(transfer, 'filesize', 0)
        taille = _format_taille(fichiersize)
        statut = _transfer_statut_label(transfer)

        page.add_download(
            identifiant=identifiant,
            fichier=fichier,
            statut=statut,
            progression=0.0,
            vitesse="",
            taille=taille,
        )
        logger.info("Transfert ajouté : %s (%s)", fichier, statut)

    def _on_transfer_removed(self, evt: object) -> None:
        """Handler : un transfert a été supprimé."""
        page = self.telechargements_page
        if page is None:
            return
        transfer = getattr(evt, 'transfer', None)
        if transfer is None:
            return
        page.remove_download(transfer.remote_path)
        logger.debug("Transfert supprimé : %s", transfer.remote_path)

    def _on_transfer_progress(self, evt: object) -> None:
        """Handler : mise à jour de progression."""
        page = self.telechargements_page
        if page is None:
            return
        updates = getattr(evt, 'updates', None)
        if not updates:
            return
        for transfer, prev_snap, cur_snap in updates:
            remote_path = getattr(transfer, 'remote_path', '')
            if not remote_path:
                continue
            fichiersize = getattr(transfer, 'filesize', 0)
            bytes_transfered = getattr(cur_snap, 'bytes_transfered', 0) if cur_snap else 0
            if fichiersize > 0:
                progression = (bytes_transfered / fichiersize) * 100.0
            else:
                progression = 0.0
            page.update_progression(remote_path, progression)

            # Ne changer le statut que si l'état a réellement changé
            cur_state = cur_snap.state if cur_snap else None
            prev_state = prev_snap.state if prev_snap else None
            if cur_state is not None and prev_state != cur_state:
                page.change_statut(remote_path, _transfer_state_to_statut(cur_state))
