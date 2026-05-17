# free-buff

[![CI](https://github.com/French-Team/minotaur-aioslsk-system/actions/workflows/ci.yml/badge.svg)](https://github.com/French-Team/minotaur-aioslsk-system/actions/workflows/ci.yml) [![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)](https://python.org) [![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE) [![PySide6](https://img.shields.io/badge/PySide6-6.5+-blue?logo=qt&logoColor=white)]() [![Coverage](https://codecov.io/gh/French-Team/minotaur-aioslsk-system/branch/main/graph/badge.svg)](https://codecov.io/gh/French-Team/minotaur-aioslsk-system)

**Client Soulseek** avec interface graphique (PySide6) et bots de gestion intelligents.

Interface complète pour la recherche, le téléchargement, et l'organisation de fichiers audio via le réseau Soulseek, avec des outils avancés de classement, déduplication, planification, et optimisation.

---

## ✨ Fonctionnalités

### 🔍 Recherche & Téléchargement
- Recherche multi-critères sur le réseau Soulseek
- Téléchargements en parallèle avec file d'attente
- Gestion de la wishlist et surveillance des fichiers rares
- Bibliothèque de fichiers synchronisée

### 🧹 Ordonnanceur
- Analyse complète d'un dossier de fichiers audio
- **Renommage** via template personnalisable (`{artist} - {album} - {track:02d} {title}`)
- **Classement** en structure `{artist}/{album}/...`
- **Dédoublonnage** par hash SHA256 (passe rapide + passe sûre)
- **Nettoyage** des fichiers temporaires
- **Corbeille dédiée** : suppression sécurisée avec horodatage
- Mode simulation (dry-run) par défaut — preview avant exécution
- Interface en 4 étapes : Choix → Aperçu → Exécution → Rapport
- CLI complète pour usage automatisé

### 📅 Planificateur
- Planification d'actions récurrentes
- Intégration avec l'Ordonnanceur pour des nettoyages programmés

### 📊 Surveillance
- Surveillance des téléchargements en cours
- Suivi des performances du réseau

---

## 🏗️ Architecture

```
free-buff/
├── src/
│   ├── main.py                 # Point d'entrée
│   ├── config.py               # Configuration
│   ├── cli_ordonnanceur.py     # CLI Ordonnanceur (432 lignes)
│   ├── services/               # Backend (12 fichiers, 5 568 lignes)
│   │   ├── ordonnanceur_service.py   # 1 789 lignes
│   │   ├── planificateur_service.py  # 712 lignes
│   │   ├── library_db.py             # 715 lignes
│   │   ├── library_scanner.py        # 208 lignes
│   │   ├── soulseek_client.py       # 520 lignes
│   │   └── ...
│   ├── gui/                    # Interface Qt (44 fichiers, 18 028 lignes)
│   │   ├── main_window.py
│   │   ├── layout/             # Center, Left, Right, Footer, Header
│   │   ├── widgets/
│   │   │   ├── bots/           # Tous les bots
│   │   │   │   ├── bot_ordonnanceur.py     # 1 425 lignes
│   │   │   │   ├── bot_planificateur.py    # 1 135 lignes
│   │   │   │   ├── bot_recherche.py        # 2 005 lignes
│   │   │   │   ├── bot_bibliotheque.py     # 1 120 lignes
│   │   │   │   ├── bot_telechargement.py   # 1 224 lignes
│   │   │   │   ├── bot_surveillance.py     # 1 400 lignes
│   │   │   │   ├── bot_accueil.py          # 652 lignes
│   │   │   │   ├── bot_wishlist.py         # 807 lignes
│   │   │   │   └── bot_optimiseur.py       # 889 lignes
│   │   │   └── ...
│   │   └── theme_fragments/    # Thème QSS modulaire
│   └── models/
│       └── schemas.py
├── tests/                      # 21 fichiers, 863 tests
│   ├── test_ordonnanceur_service.py           # 2 060 lignes, 178 tests
│   ├── test_ordonnanceur_service_mutagen.py   # 652 lignes
│   ├── test_cli_ordonnanceur.py               # 237 lignes, 16 tests
│   ├── test_bot_ordonnanceur_integration.py   # 726 lignes, 43 tests
│   ├── test_integration_planificateur_ordonnanceur.py # 733 lignes, 38 tests
│   ├── test_bot_accueil.py                   # 554 lignes
│   ├── test_bot_bibliotheque.py              # 1 426 lignes
│   └── ...
├── specs/                      # Spécifications détaillées
│   ├── bot-ordonnanceur-spec.md
│   ├── bot-planificateur-spec.md
│   └── ...
└── .agents/                    # Agents Codebuff
```

---

## 🚀 Installation

```bash
# Cloner le dépôt
git clone <url>
cd free-buff-aioslsk

# Dépendances
pip install -r requirements.txt

# Lancement GUI
python run.py

# CLI Ordonnanceur
python -m src.cli_ordonnanceur DOSSIER [--ops ...] [--executer]
```

---

## 🧪 Tests

```bash
# Tout lancer
python -m pytest tests/ --tb=short -q

# Ordonnanceur seulement
python -m pytest tests/test_ordonnanceur_service.py -v

# Tests GUI intégration
python -m pytest tests/test_bot_ordonnanceur_integration.py -v
```

**Couverture :** 863 tests (tout vert ✅)

---

## 💻 Stack technique

| Technologie | Usage |
|-------------|-------|
| **Python 3.12+** | Langage principal |
| **PySide6** | Interface graphique Qt |
| **mutagen** | Lecture des tags audio (ID3, Vorbis, FLAC) |
| **pathlib / shutil** | Manipulation fichiers système |
| **hashlib (SHA256)** | Dédoublonnage |
| **pytest** | Tests unitaires et intégration |
| **argparse** | CLI |
| **FastAPI / uvicorn** | Interface web Soulseek |

---

## 📜 License

Apache 2.0
