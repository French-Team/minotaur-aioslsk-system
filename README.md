<p align="center">
  <img src="assets/images/MINAUTOR_logo.png" alt="Minautor Logo" width="400">
</p>

# 🏛️ Minautor AIOSLSK System

[![CI](https://github.com/French-Team/minotaur-aioslsk-system/actions/workflows/ci.yml/badge.svg)](https://github.com/French-Team/minotaur-aioslsk-system/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-blue?logo=qt&logoColor=white)](https://www.qt.io/qt-for-python)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Coverage](https://codecov.io/gh/French-Team/minotaur-aioslsk-system/branch/main/graph/badge.svg)](https://codecov.io/gh/French-Team/minotaur-aioslsk-system)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Minautor** est un client Soulseek de nouvelle génération, conçu pour la puissance et l'automatisation. Il combine une interface graphique moderne (PySide6) avec une architecture événementielle robuste et une suite de "bots" intelligents pour gérer votre bibliothèque musicale.

---

## 🚀 Points Forts

- 🤖 **Multi-Bots** : Gestionnaire de téléchargements, bibliothèque, recherche, surveillance, et plus encore.
- ⚡ **Architecture Événementielle** : Communication fluide via un `EventBus` centralisé.
- 💬 **Salons & Social** : Intégration complète des salons de discussion (Rooms) Soulseek.
- 🧹 **Ordonnanceur Intelligent** : Renommage, classement et dédoublonnage automatique (SHA256).
- 🛠️ **DevTools Intégrés** : Suite Sysinternals, inspecteur QSS et monitoring asyncio.

---

## ✨ Fonctionnalités détaillées

### 🔍 Recherche & Téléchargement
- **Moteur de recherche** : Multi-critères, historique des recherches, et filtres avancés.
- **Gestionnaire de file d'attente** : Téléchargements parallèles avec suivi en temps réel.
- **Wishlist** : Surveillance automatique pour trouver les fichiers rares dès qu'ils apparaissent.

### 🏠 Système de Bots
- **Bot Accueil** : Vue d'ensemble et accès rapide aux modules.
- **Bot Bibliothèque** : Gestion et scan de vos fichiers locaux.
- **Bot Clients Actifs** : Monitoring des pairs connectés.
- **Bot Assistant & Aide** : Base de connaissances intégrée pour vous guider.
- **Bot Optimiseur** : Profils de performance (Défaut, Puissance Max, Extrême).

### 🧹 Ordonnanceur & Planificateur
- **Automatisme** : Classement structurel (`{artist}/{album}/...`) et renommage intelligent.
- **Dédoublonnage** : Analyse par hash SHA256 pour éliminer les doublons réels.
- **Planification** : Exécution de tâches de nettoyage ou de scan à intervalles réguliers.

### 🛠️ Outils de Diagnostic (DevMode)
- **Sysinternals Suite** : Process Explorer, TCPView, et Process Monitor intégrés.
- **Inspecteurs** : Analyse des styles (QSS), des services et des workflows en temps réel.

---

## 🏗️ Architecture du Projet

```text
minautor-aioslsk-system/
├── src/
│   ├── main.py                 # Point d'entrée (FastAPI/Uvicorn)
│   ├── gui/                    # Interface PySide6 (44+ fichiers)
│   │   ├── main_window.py      # Fenêtre principale
│   │   ├── widgets/bots/       # Logique des 10+ bots spécialisés
│   │   └── devtool/            # Outils de diagnostic & Sysinternals
│   ├── services/               # Cœur logique (EventBus, Soulseek, DB)
│   │   ├── event_bus.py        # Système de messagerie inter-module
│   │   ├── room_service.py     # Gestion des salons de discussion
│   │   └── ordonnanceur_service.py # Logique de traitement de fichiers
│   └── models/                 # Schémas de données (Pydantic)
├── data/                       # Bases de données SQLite & Knowledge base
├── tests/                      # Suite de tests massive (860+ tests)
└── specs/                      # Spécifications techniques détaillées
```

---

## 🛠️ Installation & Usage

### Prérequis
- Python 3.11 ou supérieur
- Windows (recommandé pour les outils Sysinternals)

### Installation rapide
```powershell
# Cloner le dépôt
git clone https://github.com/French-Team/minotaur-aioslsk-system.git
cd minotaur-aioslsk-system

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python run.py
```

### CLI Ordonnanceur
L'ordonnanceur peut également être utilisé sans interface graphique :
```powershell
python -m src.cli_ordonnanceur "C:/MaMusique" --ops classement,renommage --executer
```

---

## 🧪 Qualité & Tests

Le projet suit des standards de qualité rigoureux :
- **Tests** : `pytest` (Unitaires, Intégration, E2E).
- **Linting** : `ruff` pour un code propre et performant.
- **Typage** : `mypy` pour la sécurité du code.

```powershell
# Lancer tous les tests
pytest
```

---

## 💻 Stack Technique

- **Langage** : Python 3.11+
- **Interface** : PySide6 (Qt) & FastAPI (Backend Web)
- **Traitement Audio** : Mutagen (Tags), Hashlib (SHA256)
- **Base de données** : SQLite (via `aioslsk` et services internes)
- **Qualité** : Pytest, Ruff, Mypy, Codecov

---

## � Licence

Ce projet est sous licence **Apache 2.0**.
