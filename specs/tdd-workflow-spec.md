# Spec TDD — Workflow Debug

> **Phase :** Debug / TDD strict  
> **Fichier test :** `tests/test_tdd_workflow.py`  
> **Driver :** L'utilisateur pilote le workflow pas à pas — il dit quoi tester ensuite, nous ajoutons au test, lançons, corrigeons le code, relançons.

---

## 1. Objectif

Valider **en conditions réelles** (connexion réelle à Soulseek) le workflow
complet de l'application, étape par étape. Chaque étape est un test TDD :

1. Écrire le test (assertions sur l'état attendu)
2. Lancer le test → il échoue ou plante
3. Corriger le code source
4. Relancer → test passe
5. Passer à l'étape suivante

---

## 2. Architecture du test (validée)

### 2.1 Fichier de test

**`tests/test_tdd_workflow.py`** — classes par étape, exécution séquentielle via `pytest -x`.

```python
class TestEtape01Connexion:
    """Première étape : connexion réussie à Soulseek."""
```

### 2.2 Autonome

Le test **ne dépend d'aucun processus externe**. Il importe directement
les services Python :

```python
from src.services.connexion_manager import ConnexionManager
```

### 2.3 Connexion réelle — `generate_account()`

Le test utilise `ConnexionManager.generate_account()` qui :
1. Génère username/password aléatoires via `_generer_identifiants()`
2. Planifie `_do_generate()` sur le thread asyncio
3. `_do_generate()` appelle `SoulseekService.connect(u, p)` → `client.start()` → `client.login()`
4. Soulseek crée automatiquement le compte si le nom n'existe pas

**Découverte :** `generate_account()` est **fire-and-forget** (retourne `None`).  
Le résultat arrive via les signaux Qt `connected`, `error_occurred`, `generating`.

### 2.4 Timeout — 5 secondes max

```python
_DEADLINE_SEC = 5.0

# Boucle de polling avec processEvents()
debut = time.monotonic()
while True:
    QApplication.processEvents()  # OBLIGATOIRE — voir §2.6
    if manager.is_connected:
        break
    if time.monotonic() - debut >= _DEADLINE_SEC:
        msg = erreurs[0] if erreurs else "Connexion non établie après 5s"
        pytest.fail(msg)
    time.sleep(0.1)
```

### 2.6 ⚠️ Découverte critique — `QApplication.processEvents()`

Les signaux Qt sont émis **depuis le thread asyncio** (où tourne `_do_generate()`)
vers le récepteur dans le **thread principal** (le test pytest).

Qt utilise automatiquement `Qt.QueuedConnection` pour les signaux cross-thread.
Ces signaux en file d'attente **ne sont jamais délivrés** sans boucle d'événements Qt.

→ **Solution :** `QApplication.processEvents()` dans chaque itération de la boucle
de polling. C'est la méthode standard pour « flush » les signaux Qt en file d'attente
dans un contexte sans boucle d'événements (tests, scripts).

### 2.7 Fixtures

```python
@pytest.fixture
def manager(qapp, tmp_app_config):
    """ConnexionManager avec thread asyncio réel, config isolée."""
    cm = ConnexionManager()
    try:
        yield cm
    finally:
        cm.shutdown()  # toujours appelé, même en cas d'échec
```

| Fixture | Scope | Rôle |
|---------|-------|------|
| `qapp` | `session` (conftest) | `QApplication` unique pour toute la session de test |
| `tmp_app_config` | `function` (conftest) | Config temporaire isolée — évite de polluer la vraie config |
| `manager` | `function` | `ConnexionManager` frais à chaque test |

**Pourquoi `scope="function"` et pas `"class"` ?**  
`tmp_app_config` utilise `monkeypatch` (toujours function-scoped).  
Une fixture class-scoped qui dépend d'une fixture function-scoped est un
piège pytest — la fixture function est évaluée à chaque test, pas une fois
pour la classe. On garde `function` pour tout.

### 2.8 Singleton `SoulseekService` — sans risque

`ConnexionManager` utilise l'instance globale `soulseek_service` (singleton).
Avec `pytest -x` (stop au premier échec, exécution séquentielle), **zéro conflit** :
- Chaque test crée un `ConnexionManager` + `_AsyncEventLoopThread` frais
- `cm.shutdown()` déconnecte le singleton (`_client=None`, `_running=False`)
- Le test suivant crée une nouvelle connexion via `generate_account()`

---

## 3. Étapes du workflow

### Étape 1 — Connexion ✅ (TESTÉ — 2/2 PASSENT)

| Aspect | Valeur |
|--------|--------|
| Test | `TestEtape01Connexion.test_generate_account_se_connecte_en_moins_de_5s` |
| Action | `manager.generate_account()` |
| Assertions | `is_connected == True`, `username != ""`, `connected` signal émis 1×, aucune erreur |
| Temps réel | **~1.7s** (compte généré : `House_Wave`, `MaxTechno`, etc.) |
| Découverte | `QApplication.processEvents()` obligatoire pour délivrer les signaux Qt |

**Mécanisme validé :**
```
generate_account()
  → génère identifiants (fast)
  → planifie _do_generate() sur le thread asyncio (fire-and-forget)
  → _do_generate() appelle SoulseekService.connect()
    → SoulSeekClient.start()
    → SoulSeekClient.login()
    → self._running = True
  → connected.emit(username)
  → generation.emit(False)
```

**Captage d'erreurs :**
```python
erreurs: list[str] = []
manager.error_occurred.connect(erreurs.append)
# Si connexion échoue : erreurs[0] contient le message d'erreur
```

**Exemple d'échec réel** (corrigé) : sans `processEvents()`, même avec connexion
réussie, les signaux ne sont jamais délivrés → `connected` reçu 0× → test rouge.

### Étape 2 — Rooms (à définir)

| Aspect | Valeur |
|--------|--------|
| Test | À écrire |
| But | Le panneau latéral droit (`RightZone`) doit afficher les salons publics/privés |
| Contexte | Actuellement, `RightZone` a deux onglets vides (placeholders) |
| Assertions attendues | `len(rooms_publiques) > 0` |

**Pistes techniques :**
- aioslsk expose `client.rooms.rooms` (liste des salons) et `client.rooms.private_rooms`
- Événements : `RoomJoinedEvent`, `RoomLeftEvent`, `RoomMessageEvent`
- Le service `SoulseekService` relaye déjà `room_message_received` via un signal Qt
- Config `salons.auto_join = True` (par défaut) → le client rejoint les salons peu après login

### Étape 3 — Clients actifs (à définir)

| Aspect | Valeur |
|--------|--------|
| Test | À écrire |
| But | `ClientsActifsService` doit maintenir la liste des clients actifs/joignables |
| Contexte | `src/services/clients_actifs_service.py` existe (spec fichier `specs/bot-clients-actifs-spec.md`) |
| Assertions attendues | `service.nombre_actifs() > 0` après un temps d'écoute |

### Étapes suivantes

Définies par l'utilisateur au fil du projet.

---

## 4. Conventions de code

### 4.1 Nommage

| Élément | Convention | Exemple |
|---------|-----------|---------|
| Classe | `TestEtapeNN_Nom` | `TestEtape01Connexion` |
| Méthodes | `test_NOM_descriptif` | `test_generate_account_se_connecte_en_moins_de_5s` |
| Fixtures | `scope="function"` | `manager` |
| Assertions | `assert` natif (pas d'`unittest.TestCase`) | `assert manager.is_connected` |
| Logs | `caplog.set_level("DEBUG", logger="src.services")` | Limité à nos services |

### 4.2 Gestion du temps

```python
import time
from PySide6.QtWidgets import QApplication

_DEADLINE_SEC = 5.0

def _attendre_connexion(manager, timeout=_DEADLINE_SEC):
    """Attend la connexion en traitant les signaux Qt. Plante si timeout."""
    debut = time.monotonic()
    while time.monotonic() - debut < timeout:
        QApplication.processEvents()
        if manager.is_connected:
            return
        time.sleep(0.1)
    raise TimeoutError("Connexion non établie")
```

### 4.3 Marqueurs pytest

```python
# (À enregistrer dans pytest.ini ou pyproject.toml)
pytestmark = [
    pytest.mark.qt_heavy,       # QApplication + QThread
    pytest.mark.tdd_workflow,   # filtrable avec -m
    pytest.mark.timeout(15),    # filet de sécurité global
]
```

---

## 5. Règles pour l'assistant IA

1. **L'utilisateur décide de l'étape suivante** — ne pas avancer sans son accord
2. **TDD strict** : écrire le test d'abord, le lancer (ça échoue ou plante),
   corriger le code, relancer
3. **Ne pas anticiper** les étapes non demandées
4. **Si un test échoue**, analyser l'erreur, proposer une correction ciblée,
   appliquer, relancer
5. **Documenter** chaque étape dans ce fichier de spec

---

## 6. Dépendances et prérequis

- Python 3.12+
- `aioslsk` installé
- Connexion Internet (serveur Soulseek `server.slsknet.org:2416`)
- Aucun compte pré-existant requis (génération automatique)

```bash
pip install pytest pytest-timeout
```

---

## 7. Lancement

```bash
# Étape 1 uniquement
python -m pytest tests/test_tdd_workflow.py -v -x -s --timeout=15 -o "addopts="

# Notes:
# -x           = stop on first failure
# -s           = stdout visible (logs de connexion, DEBUG)
# -o "addopts="= ignore les options pytest globales
```

---

## 8. Historique des étapes

| Étape | Test | Statut | Date | Temps réel |
|-------|------|--------|------|-----------|
| 1 | Connexion réussie | ✅ Testé (2/2) | 2026-05-18 | ~1.7s |
| 2 | Rooms | 📅 À faire | — | — |
| 3 | Clients actifs | 📅 À faire | — | — |

---

## 9. Questions résolues

- [x] **Fixture scope `class` vs `function` ?** → `function` impératif car
      `tmp_app_config` utilise `monkeypatch` (function-scoped). Pas de scope mixte.
- [x] **Singleton `SoulseekService` ?** → Sans risque avec `pytest -x`
      (exécution séquentielle). `cm.shutdown()` nettoie entre les tests.
- [x] **Attendre le signal ou la propriété ?** → Polling de `is_connected` + signaux.
      `processEvents()` obligatoire pour délivrer les signaux cross-thread.
- [x] **generate_account() ou connect() direct ?** → `generate_account()` car
      l'utilisateur veut la génération auto. Le test capture `error_occurred`
      si la connexion échoue.

---

*Généré le 2026-05-18 — à mettre à jour après chaque étape.*
