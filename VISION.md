# Vision — L'Armée des 12 Bots

> *"En 2026, créer une app qui ressemble à une autre n'aura aucun succès."*

---

## Le constat

Aujourd'hui, tout le monde crée des apps avec des IA intégrées. Mais l'approche actuelle a un défaut : dans une app simple, **l'utilisateur doit tout faire lui-même**, alors qu'il ne connaît pas forcément le fonctionnement.

Utiliser Soulseek — rechercher, télécharger, configurer, gérer ses fichiers — peut être **compliqué pour un utilisateur non technique**. C'est le problème à résoudre.

## La solution : une armée de 12 bots

**L'idée intermédiaire :** créer et utiliser des **bots**. Il est très facile *pour nous* de créer des bots. Chaque bot a une **mission définie**, un **domaine d'expertise**.

Ils accueillent l'utilisateur, lui fournissent des informations sur le fonctionnement de l'app, font des recherches pour lui, lancent les téléchargements, surveillent les téléchargements, nettoient et organisent le dossier `downloads`.

> **Principe fondateur :**
> *L'utilisateur n'a pas besoin de connaître Soulseek. Il parle aux bots, et les bots font le travail.*

---

## Interface

Le **menu du footer** est destiné aux 12 bots : **un bot = un bouton du menu**.

### Les 12 bots

| # | Bot | Mission |
|---|-----|---------|
| 1 | **Accueil** | Hub central : présentation, stats générales, bienvenue, description du profil |
| 2 | **Recherche** | Rechercher des fichiers sur le réseau Soulseek, filtrer les résultats, prévisualiser |
| 3 | **Téléchargement** | Gérer les téléchargements : lancer, suivre, mettre en pause, prioriser |
| 4 | **Wishlist** | Liste de souhaits : ajouter des tracks à surveiller, téléchargement automatique dès que dispo |
| 5 | **Bibliothèque** | Explorer et gérer tous les fichiers téléchargés, tri par artiste/album, tags |
| 6 | **Utilisateurs** | Gérer les contacts : amis, bloqués, profil des users Soulseek, historique d'échange |
| 7 | **Surveillance** | Notifications et alertes : résultat trouvé, téléchargement terminé, user connecté, erreurs |
| 8 | **Planificateur** | Programmer des recherches récurrentes, téléchargements différés, actions planifiées |
| 9 | **Nettoyage** | Organiser les téléchargements : trier, renommer, dédoublonner, déplacer par artiste/album |
| 10 | **Statistiques** | Tableau de bord : volume échangé, activité, historique des téléchargements, top users |
| 11 | **Assistant** | Configuration guidée étape par étape (au lieu des menus techniques) |
| 12 | **Aide / Tutos** | Guide interactif, explications du fonctionnement Soulseek, aide pas à pas |

---

## Architecture technique existante (état des lieux)

Cette section décrit l'architecture réelle du projet, sur laquelle les bots vont se greffer.

### 1. Structure des fichiers

```
src/
├── __init__.py
├── config.py                  # Configuration persistée (JSON) + settings
├── main.py                    # Point d'entrée FastAPI (web)
├── models/
│   ├── __init__.py
│   └── schemas.py             # Schémas Pydantic pour l'API REST
├── services/
│   ├── __init__.py
│   └── soulseek_client.py     # Client aioslsk (backend Soulseek)
├── routers/
│   ├── __init__.py
│   └── connection.py          # Routes API REST connexion
├── static/                    # (réservé) Fichiers statiques web
└── gui/
    ├── __init__.py
    ├── main_window.py         # QMainWindow — fenêtre principale
    ├── theme.py               # Assemble DARK_THEME depuis fragments
    ├── theme_fragments/       # CSS décomposé par module
    │   ├── colors.py          # Dictionnaire COLORS (palette)
    │   ├── base.py            # Styles globaux (QMainWindow, QLabel, etc.)
    │   ├── layout.py          # Zones (left, center, right, footer)
    │   ├── clients.py         # Styles de la page clients actifs
    │   ├── config.py          # Styles de la page configuration
    │   ├── connexion.py       # Styles de la page connexion
    │   ├── downloads.py       # Styles de la page téléchargements
    │   ├── misc.py            # Styles divers
    │   ├── progression.py     # Styles barres de progression
    │   └── scrollbars.py      # Styles scrollbars
    ├── layout/                # Zones de l'interface (3x3 grid)
    │   ├── entry.py           # Assemble la grille QGridLayout 3×3
    │   ├── header.py          # HeaderZone — bannière login
    │   ├── footer.py          # FooterZone — navigation (5 boutons)
    │   ├── left.py            # LeftZone — panneau latéral gauche
    │   ├── center.py          # CenterZone — QStackedWidget (pages)
    │   └── right.py           # RightZone — panneau salons
    └── widgets/               # Pages et widgets réutilisables
        ├── home.py            # Page d'accueil (bannière + description + flèches)
        ├── connexions.py      # Page de connexion Soulseek
        ├── config.py          # Composants de configuration réutilisables
        ├── telechargements.py # Page de gestion des téléchargements
        ├── clients_actifs.py  # Page des clients actifs
        ├── progression.py     # Widget barre de progression multi-mode
        └── clock.py           # Widget horloge (signal toutes les 1s)
```

### 2. Disposition : grille 3×3 (entry.py)

Le `LayoutEntry` utilise un `QGridLayout` :

```
┌───────────── Row 0 ───────────────┐
│          HeaderZone                │  ← fixe (stretch=0)
├────────┬──────────────┬───────────┤
│ Left   │  CenterZone  │  Right    │  ← ligne extensible (stretch=1)
│ Zone   │ (StackedW.)  │  Zone     │
│ (col 0)│   (col 1)    │  (col 2)  │
├────────┴──────────────┴───────────┤
│          FooterZone                │  ← fixe (stretch=0)
└────────────────────────────────────┘
```

- **HeaderZone** : caché par défaut, montre login + avatar quand connecté
- **LeftZone** : panneau de navigation rétractable (catégories config)
- **CenterZone** : `QStackedWidget` avec pages identifiées par nom
- **RightZone** : panneau des salons rétractable (QTabWidget)
- **FooterZone** : 5 boutons de navigation (actuellement `menu_1` à `menu_5`)

### 3. Navigation actuelle

Le **footer** (5 boutons) et la **left zone** (catégories) sont deux systèmes de navigation indépendants qui changent tous les deux la page affichée dans le `CenterZone` via le signal `page_changed(name)`.

Le `CenterZone` gère un `QStackedWidget` avec des pages comme :
- `"connexion"` (page de login)
- `"accueil"` (page d'accueil avec flèches)
- `"clients-actifs"`
- `"telechargements"`
- `"Général"`, `"Réseau"`, `"Recherche"`, etc. (pages de config)

### 4. Thème : système à fragments

Le thème est assemblé dans `theme.py` via un dictionnaire de couleurs (`COLORS`) avec des placeholders `@KEY@` dans le CSS. Chaque fragment de style est dans son propre fichier sous `theme_fragments/`. Exemple : `@BG_MAIN@` → `#141420`.

### 5. Cycle de vie de l'application

1. `run.py` → crée `QApplication`, style Fusion
2. `MainWindow` → applique `DARK_THEME`, assemble `LayoutEntry`
3. `ConnexionManager` (dans `soulseek_client.py`) gère login Soulseek
4. Avant connexion : on voit uniquement `connexion` page
5. Après connexion : header + footer + left apparaissent, page `accueil`

---

## Vision architecturelle : les bots dans cette structure

### Mapping footer → bots

Le **footer** (actuellement 5 boutons `menu_1..5`) va devenir la **barre de navigation des bots** :

```
┌──────────────────────────────────────────────────┐
│  [Accueil] [Recherche] [Téléchargement] [...] ... │  ← 12 bots max
└──────────────────────────────────────────────────┘
```

Chaque bouton du footer = un bot. Un clic change la page du `CenterZone` pour afficher l'interface de ce bot.

### Chaque bot = une page dans le QStackedWidget

Architecture d'un bot typique :

```python
class BotRecherche(QFrame):        # ou QWidget
    def __init__(self):
        super().__init__()
        self.setObjectName("bot-recherche")
        # Layout interne (barre recherche + résultats)
        # Appels à soulseek_client.py via signaux
```

Chaque bot :
- Est une classe séparée dans `src/gui/widgets/bots/` (dossier dédié)
- Hérite de `QFrame`
- Est ajouté au `QStackedWidget` du `CenterZone`
- Peut émettre/recevoir des signaux vers le backend `soulseek_client.py`
- Dispose de son propre fragment de style CSS dans `theme_fragments/`

### Communication bot → backend

```
Bot UI (widget)  ──(signal)──→  MainWindow (pont)  ──(appel)──→  ConnexionManager
                                                                      │
                                                                      ▼
                                                                 aioslsk (Soulseek)
```

Ou plus simplement : chaque bot reçoit une référence au `ConnexionManager` (ou utilise des signaux Qt).

### Navigation proposée

```
Footer[Accueil] ──clic──→ CenterZone.show_page("bot-accueil")
Footer[Recherche] ──clic──→ CenterZone.show_page("bot-recherche")
...
```

Le `FooterZone` actuel a déjà tout le mécanisme : signaux `page_changed`, boutons `checkable`, méthode `set_active(name)`. Il suffit de :
1. Remplacer les noms `menu_1..5` par les noms des bots
2. Étendre à 12 boutons (ou paginer si nécessaire)
3. Connecter au `CenterZone` comme c'est déjà le cas

---

## Prochaines étapes techniques

## Prochaines étapes techniques

1. ✅ Définir les 12 bots — **fait**
2. **Créer le dossier** `src/gui/widgets/bots/`
3. **Transformer le footer** : 5 → 12 boutons, noms des bots
4. **Créer le premier bot** : `BotAccueil` (reprendre `home.py` actuel)
5. **Créer le bot Recherche** : interface de recherche Soulseek
6. **Adapter le `CenterZone`** pour accepter les pages de bots
7. **Supprimer l'ancienne navigation gauche** (ou la réserver à la config)
