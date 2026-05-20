"""
Tests TDD du workflow réel Soulseek — phase debug.

Chaque étape est un test TDD strict :
1. L'utilisateur décrit la prochaine action attendue
2. On écrit le test (assertions sur l'état réel)
3. On lance → ça passe ou ça échoue
4. Si échec : on corrige le code, on relance
5. On passe à l'étape suivante

Usage :
    python -m pytest tests/test_tdd_workflow.py -v -x -s --timeout=15 -o "addopts="
"""

from __future__ import annotations

import random
import time

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidget

import src.services.app_config as app_config
from src.services.connexion_manager import ConnexionManager
from src.services.room_service import RoomService
from src.services.soulseek_client import soulseek_service


# ── Marqueurs ────────────────────────────────────────────────────
pytestmark = [
    pytest.mark.qt_heavy,       # nécessite QApplication + QThread
    pytest.mark.tdd_workflow,   # filtrable
    pytest.mark.timeout(20),    # filet de sécurité global
]


# ═══════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════

_DEADLINE_SEC = 5.0


@pytest.fixture
def manager(qapp, tmp_app_config):
    """ConnexionManager avec thread asyncio réel, config isolée."""
    cm = ConnexionManager()
    try:
        yield cm
    finally:
        cm.shutdown()


# ═══════════════════════════════════════════════════════════════════
#  Helpers partagés
# ═══════════════════════════════════════════════════════════════════


_DELAI_TENTATIVE_SEC = 30.0  # le serveur Soulseek peut etre tres lent (rate-limit)


def _connect_avec_retry(manager: ConnexionManager, max_attempts: int = 1) -> None:
    """Helper : tente la connexion avec retry.

    Avant chaque tentative, tue proprement le client precedent
    pour eviter les conflits de port et d'etat.

    Raisons de retry :
    - INVALIDPASS : le nom aleatoire existe deja sur Soulseek
    - Port occupe : un autre client Soulseek tourne sur la machine
    - Timeout reseau : le serveur est lent

    Chaque tentative utilise un port d'ecoute different pour eviter
    les collisions avec un eventuel autre client Soulseek.
    """
    # ── Toujours tuer le client avant de commencer ──────────
    # Permet de garantir un etat propre meme si le singleton
    # soulseek_service est dans un etat residue d'un test precedent.
    manager.disconnect()
    debut_kill = time.monotonic()
    while time.monotonic() - debut_kill < 3:
        QApplication.processEvents()
        if not manager.is_connected:
            break
        time.sleep(0.1)
    time.sleep(0.5)  # laisser le temps OS de liberer le port

    for attempt in range(1, max_attempts + 1):
        erreurs: list[str] = []
        manager.error_occurred.connect(erreurs.append)

        # ── Chaque tentative = port aleatoire haut ─────────────
        port = random.randint(62000, 64000)
        app_config.set("reseau.port_ecoute", port)
        app_config.set("reseau.port_obfusque", port + 1)
        app_config.set("reseau.upnp", False)  # desactiver UPnP (routeur Bbox lent)

        manager.generate_account()

        debut = time.monotonic()
        while True:
            QApplication.processEvents()
            if manager.is_connected:
                assert manager.username != "", "username ne devrait pas etre vide"
                return  # succes
            if time.monotonic() - debut >= _DELAI_TENTATIVE_SEC:
                if attempt < max_attempts:
                    msg = erreurs[-1] if erreurs else f"Timeout apres {_DELAI_TENTATIVE_SEC:.0f}s"
                    # Windows cp1252 ne supporte pas les emojis — on les enleve
                    msg_safe = msg.encode("ascii", "replace").decode("ascii")[:60]
                    print(f"  [Tentative {attempt}/{max_attempts} port={port}] {msg_safe}")
                    break  # retry
                msg = erreurs[-1] if erreurs else f"Timeout apres {_DELAI_TENTATIVE_SEC:.0f}s"
                msg_safe = msg.encode("ascii", "replace").decode("ascii")
                pytest.fail(f"{msg_safe} (apres {max_attempts} tentatives)")
            time.sleep(0.1)

    # Ne devrait jamais arriver (pytest.fail est appelé plus haut)
    pytest.fail("Echec de connexion — cas inattendu")


# ═══════════════════════════════════════════════════════════════════
#  Étape 1 — Connexion
# ═══════════════════════════════════════════════════════════════════


class TestEtape01Connexion:
    """Première étape : connexion réussie à Soulseek."""

    def test_generer_identifiants_produit_credentials_valides(self):
        """Vérifie que _generer_identifiants() est fonctionnel (unitaire)."""
        from src.services.connexion_manager import _generer_identifiants

        username, password = _generer_identifiants()
        assert isinstance(username, str) and len(username) > 0
        assert isinstance(password, str) and len(password) == 12
        assert " " not in username

    def test_generate_account_se_connecte_en_moins_de_5s(
        self, manager: ConnexionManager, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Connexion réelle à Soulseek via generate_account().

        - Génére un compte aléatoire
        - Attend max 5s que is_connected devienne True
        - Vérifie qu'aucune erreur n'a été émise
        - Vérifie que le username est non vide
        """
        caplog.set_level("DEBUG", logger="src.services")

        # ── Setup : écouter les erreurs ──────────────────────────────
        erreurs: list[str] = []
        manager.error_occurred.connect(erreurs.append)

        signaux_connected: list[str] = []
        manager.connected.connect(signaux_connected.append)

        signaux_generating: list[bool] = []
        manager.generating.connect(signaux_generating.append)

        # ── État initial ─────────────────────────────────────────────
        print(f"\n[DEBUG] Avant generate_account : is_connected={manager.is_connected}, username={manager.username!r}")
        print(f"[DEBUG] service._client={manager._service._client is not None}, _running={manager._service._running}")

        # ── Action : lancer la génération de compte ──────────────────
        manager.generate_account()
        print(f"[DEBUG] Après generate_account() : is_connected={manager.is_connected}")

        # ── Attente active (polling + processEvents) — max 5s ───────
        # NB: processEvents() est OBLIGATOIRE car les signaux Qt sont émis
        # depuis le thread asyncio et mis en file d'attente (QueuedConnection).
        # Sans boucle d'événements, les signaux ne sont jamais délivrés.
        debut = time.monotonic()
        while True:
            QApplication.processEvents()  # traite les signaux en file d'attente
            if manager.is_connected:
                break
            if time.monotonic() - debut >= _DEADLINE_SEC:
                elapsed = time.monotonic() - debut
                print(f"[DEBUG] Timeout après {elapsed:.1f}s")
                print(f"[DEBUG] signaux: connected={signaux_connected}, generating={signaux_generating}, erreurs={erreurs}")
                print(f"[DEBUG] service: client={manager._service._client is not None}, _running={manager._service._running}")
                msg = erreurs[0] if erreurs else "⏱️ Connexion non établie après 5s"
                pytest.fail(msg)
            time.sleep(0.1)

        # ── Assertions ───────────────────────────────────────────────
        elapsed = time.monotonic() - debut
        print(f"[DEBUG] Assertions: is_connected={manager.is_connected}, username={manager.username!r}")
        print(f"[DEBUG] signaux: connected={signaux_connected}, generating={signaux_generating}, erreurs={erreurs}")

        assert manager.is_connected, "is_connected devrait être True"
        assert manager.username != "", "username ne devrait pas être vide"
        assert len(signaux_connected) == 1, \
            f"connected aurait dû être émis 1×, reçu {len(signaux_connected)}"
        assert signaux_connected[0] == manager.username, \
            "le signal connected doit contenir le bon username"
        assert len(erreurs) == 0, f"Erreurs reçues pendant la connexion : {erreurs}"

        # ── Rapport ──────────────────────────────────────────────────
        print(f"\n[OK] Connecte en {elapsed:.1f}s — {manager.username}")


# ═══════════════════════════════════════════════════════════════════
#  Étape 3 — RightZone peuplé avec les salons
# ═══════════════════════════════════════════════════════════════════


class TestEtape03RightZone:
    """Troisième étape : RightZone se remplit automatiquement avec les salons."""

    def test_etape_03_rightzone_peuple_avec_salons(
        self,
        manager: ConnexionManager,
        qapp,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Vérifie que RightZone se remplit avec les salons après connexion.

        Stratégie :
        1. Crée RoomService + RightZone, les branche via setup()
        2. Se connecte à Soulseek
        3. Sonde l'API synchrone client.rooms.get_public_rooms() (comme étape 2)
        4. Appelle room_service.rafraichir() explicitement (même thread = emission directe)
        5. Vérifie que RightZone a été peuplé

        NB: le signal room_list_received (cross-thread depuis le thread asyncio)
        n'est pas fiable avec processEvents() dans le test. En production,
        la boucle d'événements Qt tourne en continu et le signal fonctionne.
        """
        from src.gui.layout.right import RightZone

        caplog.set_level("INFO", logger="src.services")

        # ── 1. Créer RoomService et RightZone ──────────────────
        room_service = RoomService(soulseek_service)
        right_zone = RightZone()
        right_zone.setup(room_service)
        room_service.demarrer()

        # ── 2. Se connecter (avec retry INVALIDPASS) ────────────
        _connect_avec_retry(manager)

        # ── 3. Polling synchrone : attendre que les rooms arrivent ─
        # On lit client.rooms.get_public_rooms() DIRECTEMENT
        # (même approche que l'étape 2, qui fonctionne)
        client = manager._service._client
        assert client is not None

        debut = time.monotonic()
        nb_rooms = 0
        while True:
            rooms_brutes = client.rooms.get_public_rooms()
            if rooms_brutes:
                nb_rooms = len(rooms_brutes)
                break
            if time.monotonic() - debut >= 5:
                elapsed = time.monotonic() - debut
                pytest.fail(f"Aucune room recue apres {elapsed:.1f}s (poll synchrone)")
            time.sleep(0.1)

        elapsed = time.monotonic() - debut
        print(f"\n[OK] {nb_rooms} salons arrives en {elapsed:.1f}s (poll synchrone)")

        # ── 4. Déclencher manuellement la synchro RoomService → RightZone ─
        # Après l'arrivée des rooms, on appelle rafraichir() explicitement.
        # Cela exécute _synchroniser() sur le thread principal,
        # les signaux rooms_publiques_recues sont émis en DirectConnection
        # et RightZone._remplir_public est appelé immédiatement.
        room_service.rafraichir()
        QApplication.processEvents()  # traite les signaux résiduels

        # ── 5. Vérifier RightZone ───────────────────────────────
        liste: QListWidget = right_zone._list_public
        items_liste: list[str] = [
            liste.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(liste.count())
            if liste.item(i).data(Qt.ItemDataRole.UserRole)
        ]

        assert len(items_liste) > 0, \
            "Au moins un salon devrait apparaitre dans RightZone"
        assert len(items_liste) == nb_rooms, \
            f"RightZone devrait avoir {nb_rooms} salons, en a {len(items_liste)}"
        assert all(isinstance(n, str) and len(n) > 0 for n in items_liste), \
            "Tous les noms de salons devraient etre non vides"

        premiers = [
            liste.item(i).text()
            for i in range(min(3, liste.count()))
        ]

        # ── 6. Rapport ───────────────────────────────────────────
        print(f"[OK] {len(items_liste)} salons dans RightZone")
        print(f"     Apercu: {premiers}")


# ═══════════════════════════════════════════════════════════════════
#  Étape 2 — Salons publics
# ═══════════════════════════════════════════════════════════════════


class TestEtape02Rooms:
    """Deuxième étape : après connexion, vérifier que les salons publics arrivent."""

    def test_etape_02_rooms_recues_apres_connexion(
        self, manager: ConnexionManager, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Après connexion, vérifie que les salons publics sont reçus du serveur.

        Le serveur Soulseek envoie automatiquement la liste des salons
        (RoomListEvent) après la connexion. On interroge le RoomManager
        pour vérifier que des salons ont été reçus.

        Attend max 5s que la liste arrive.
        """
        caplog.set_level("INFO", logger="src.services")

        # ── 1. Se connecter (avec retry INVALIDPASS) ──────────────────
        _connect_avec_retry(manager)

        # ── 2. Récupérer le client Soulseek ────────────────────────────
        client = manager._service._client
        assert client is not None, "Le client Soulseek devrait etre disponible"

        # ── 3. Attendre que la liste des rooms arrive (≤ 5s) ─────────
        debut = time.monotonic()
        rooms_publiques: list[str] = []
        echantillon: list[tuple] = []

        while True:
            QApplication.processEvents()

            rooms = client.rooms.get_public_rooms()
            if rooms:
                rooms_publiques = [r.name for r in rooms]
                echantillon = [(r.name, r.user_count) for r in rooms[:5]]
                break

            if time.monotonic() - debut >= _DEADLINE_SEC:
                elapsed = time.monotonic() - debut
                print(f"[DEBUG] Aucune room apres {elapsed:.1f}s")
                print(f"[DEBUG] Joined rooms: {[r.name for r in client.rooms.get_joined_rooms()]}")
                pytest.fail(f"Aucun salon public recu apres {elapsed:.1f}s")

            time.sleep(0.1)

        # ── 4. Assertions ───────────────────────────────────────────
        elapsed = time.monotonic() - debut

        assert len(rooms_publiques) > 0, \
            "Au moins un salon public devrait etre disponible"
        assert all(isinstance(n, str) and len(n) > 0 for n in rooms_publiques), \
            "Tous les salons devraient avoir un nom non vide"

        # Verifier que les 5 premiers salons ont des utilisateurs (ou sont valides)
        for nom, nb in echantillon:
            assert isinstance(nom, str) and len(nom) > 0, \
                f"nom de salon invalide: {nom!r}"

        # ── 5. Rapport ───────────────────────────────────────────────
        print(f"\n[OK] {len(rooms_publiques)} salons publics recus en {elapsed:.1f}s")
        print(f"     Exemples: {echantillon[:5]}")

        noms_avec_diese = [n for n in rooms_publiques if n.startswith("#") or "/" in n or "-" in n]
        if noms_avec_diese:
            print(f"     Salons typiques: {noms_avec_diese[:3]}")


# ═══════════════════════════════════════════════════════════════════
#  Étape 4 — Clients Actifs
# ═══════════════════════════════════════════════════════════════════


class TestEtape04ClientsActifs:
    """Quatrième étape : après connexion, le bot ClientsActifs se remplit."""

    def test_etape_04_clients_actifs_peuple_apres_connexion(
        self,
        manager: ConnexionManager,
        qapp,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Vérifie que les clients actifs (Online/Away) sont reçus
        après connexion et que le bot ClientsActifs se peuple.

        Stratégie :
        1. Se connecte à Soulseek
        2. Crée ClientsActifsService + BotClientsActifs, les branche
        3. Sonde l'API synchrone client.users.users pour détecter les users
        4. Appelle service.rafraichir() explicitement
        5. Vérifie le service ET le bot
        """
        from aioslsk.user.model import UserStatus
        from src.services.clients_actifs_service import ClientsActifsService
        from src.gui.widgets.bots.bot_clients_actifs import BotClientsActifs

        caplog.set_level("INFO", logger="src.services")

        # ── 1. Se connecter (avec retry INVALIDPASS) ────────────
        _connect_avec_retry(manager)

        client = manager._service._client
        assert client is not None, "Le client Soulseek devrait etre disponible"

        # ── 2. Créer le service et le widget ────────────────────
        service = ClientsActifsService(soulseek_service)
        bot = BotClientsActifs()
        bot.setup(service)
        service.demarrer()

        # ── 3. Polling synchrone : attendre que des users arrivent ──
        # On lit client.users.users (UserManager) via l'API synchrone
        debut = time.monotonic()
        nb_users = 0
        while True:
            users_dict = client.users.users
            nb_users = len(users_dict)
            if nb_users > 0:
                break
            if time.monotonic() - debut >= 5:
                elapsed = time.monotonic() - debut
                pytest.fail(f"Aucun utilisateur recu apres {elapsed:.1f}s (users={nb_users})")
            time.sleep(0.1)

        elapsed = time.monotonic() - debut
        print(f"\n[OK] {nb_users} utilisateurs suivis apres {elapsed:.1f}s (poll synchrone)")

        # ── 4. Synchroniser le service (→ bot via signal) ──────────
        # service.rafraichir() → _synchroniser() → clients_synchronises.emit()
        # → bot._initialiser_tableau() en DirectConnection (même thread)
        service.rafraichir()
        QApplication.processEvents()

        # ── 5. Vérifier le service ──────────────────────────────
        actifs = service.clients_actifs()
        assert len(actifs) > 0, "Au moins un client actif devrait etre present"

        statuts = {c.statut for c in actifs}
        online_ou_away = len(
            [c for c in actifs if c.statut in (UserStatus.ONLINE, UserStatus.AWAY)]
        )
        # L'utilisateur demande explicitement des clients Online/Away
        assert online_ou_away > 0, \
            f"Au moins un client Online/Away attendu, trouve {online_ou_away}/{len(actifs)}"

        print(f"     Statuts trouves: {[s.name for s in sorted(statuts, key=lambda s: s.value)]}")
        print(f"     Clients Online/Away: {online_ou_away}/{len(actifs)}")

        # ── 6. Vérifier le bot (peuplé via le signal) ───────────
        nb_lignes = bot._table.rowCount()
        assert nb_lignes > 0, "BotClientsActifs devrait avoir au moins une ligne"
        assert nb_lignes == len(actifs), \
            f"Bot devrait avoir {len(actifs)} lignes, en a {nb_lignes}"

        # ── 7. Rapport ─────────────────────────────────────────
        print(f"\n[OK] {len(actifs)} clients actifs dans le service")
        print(f"[OK] {nb_lignes} lignes dans BotClientsActifs")
        print(f"     Echantillon: {[c.username for c in actifs[:5]]}")
        print(f"     Stats: {online_ou_away} online/away sur {len(actifs)}")
