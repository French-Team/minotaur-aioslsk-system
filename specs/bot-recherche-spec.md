# Spec — Bot Recherche

> **Mission :** Interface de recherche puissante et ciblée pour Soulseek.
> Dédiée aux tracks électroniques (1995-2005) en mp3, flac, ogg.
> Offre la recherche globale, la recherche par utilisateur, et la recherche par salon.

---

## 1. Principes fondamentaux

| Principe | Valeur |
|----------|--------|
| **Nature** | Page outil spécialisée dans la recherche |
| **Cible** | Tracks électroniques 1995-2005 — filtre à la réception (mp3, flac, ogg) |
| **Rôle** | Lancer des recherches, afficher, trier, filtrer, et télécharger |
| **Visibilité** | UNIQUEMENT quand l'utilisateur est connecté à Soulseek |
| **Canal d'entrée** | Footer → `page_changed("Recherche")` ou navigation depuis Bot Accueil |
| **Interaction** | Barre de recherche + tableau de résultats + modal de filtres |

---

## 2. Architecture des fichiers

| Fichier | Rôle |
|---------|------|
| `src/gui/widgets/bots/bot_recherche.py` | Classe `BotRecherche(QFrame)` — page complète de recherche |
| `src/gui/widgets/bots/__init__.py` | Export de `BotRecherche` |
| `src/gui/layout/center.py` | Construction de la page `_build_recherche_page()` |
| `src/services/connexion_manager.py` | Relais des signaux `search_result_received` |
| `src/services/soulseek_client.py` | Moteur aioslsk sous-jacent |
| `data/bot_recherche_history.json` | Persistance historique des recherches (20 dernières) |

---

## 3. Interface

### 3.1 Structure visuelle

```
┌─────────────────────────────────────────────────┐
│  🔍 Recherche Soulseek                          │
│                                                  │
│  ┌─────────────────────────────────────[Filtres] │
│  │ Rechercher des fichiers…    [Rechercher] [⏹] │
│  └────────────────────────────────────────────── │
│                                                  │
│  ℹ️ 200 résultats — recherche « daft punk »      │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Fichier          │ Taille │ Bitrate │ Utilis. ││  ← lignes triables
│  │───────────────────────────────────────────────││
│  │ [MP3] Daft...    │ 8.2 Mo │ 192kbps │ DJ_...  ││  ← clic droit → menu
│  │ [FLAC] Daft...   │ 32 Mo  │ 1090kpbs│ User42  ││
│  │ [OGG] Around...  │ 6.1 Mo │ 160kbps │ Electro.││
│  │ ...              │ ...    │ ...     │ ...     ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│  [📥 Téléchargement rapide] [🔴 Mode dispo]      │
└─────────────────────────────────────────────────┘
```

### 3.2 Éléments de l'interface (ordre du layout)

1. **Titre** `🔍 Recherche Soulseek`
2. **Barre de recherche** — `QLineEdit` + bouton `Rechercher` + bouton `⏹ Stop` (visible pendant recherche)
3. **Bouton Filtres** — ouvre une modal centrée de filtrage avancé
4. **Barre d'état** — compteur de résultats + statut de la recherche
5. **Tableau de résultats** — `QTableWidget` triable, lignes cliquables
6. **Barre d'actions** — bouton "📥 Téléchargement rapide" + toggle "🔴 Mode dispo"

### 3.3 Tableau de résultats

#### 3.3.1 Colonnes

| Colonne | Type | Triable | Description |
|---------|------|---------|-------------|
| Extension | Icône/texte | Oui | `[MP3]`, `[FLAC]`, `[OGG]` — badge coloré |
| Fichier | Texte | Oui | Nom du fichier (sans chemin), tronqué si trop long |
| Taille | Texte formaté | Oui | 8.2 Mo, 32 Mo, etc. |
| Bitrate | Texte formaté | Oui **(défaut ↓)** | 192 kbps, 1090 kbps, VBR, etc. |
| Durée | Texte formaté | Oui | 5m32s, 1h02m15s |
| Utilisateur | Texte | Oui | Pseudo Soulseek |
| Slots | Icône | Oui | 🟢 slots libres / 🔴 en file d'attente |
| Vitesse | Texte | Oui | 128 K/s, 512 K/s |
| DL | Bouton | Non | ⬇ télécharger (redirection Bot Téléchargement) |

#### 3.3.2 Tri par défaut

- **Bitrate décroissant** (meilleure qualité d'abord)
- L'utilisateur peut cliquer sur n'importe quelle colonne pour re-trier

#### 3.3.3 Limite d'affichage

- **200 résultats max** affichés simultanément
- Un message `⚠️ 200 résultats max — affinez votre recherche` prévient l'utilisateur si le seuil est atteint
- Les résultats arrivent en continu : les nouveaux remplacent les anciens si le seuil est atteint (FIFO — les plus anciens sortent du tableau)

### 3.4 Filtres (modal centré)

#### 3.4.1 Comportement

- Bouton `[Filtres]` dans la barre de recherche → ouvre une fenêtre modale centrée
- Modal : fond semi-transparent sombre, cadre avec titre, fermeture par clic extérieur ou bouton ✕

#### 3.4.2 Contenu de la modal

| Filtre | Type | Valeur par défaut |
|--------|------|-------------------|
| **Extension** | Checkboxes | ✅ mp3 ✅ flac ✅ ogg ❌ wav ❌ wma ❌ aac ❌ ape ❌ autres |
| **Bitrate min** | Slider + champ | 128 kbps |
| **Durée min** | Champ (secondes) | 30 s (filtre les samples trop courts) |
| **Durée max** | Champ (secondes) | 600 s (10 min — filtres les mixes trop longs) |
| **Taille min** | Champ (Ko/Mo) | 1 Mo |
| **Taille max** | Champ (Ko/Mo) | 100 Mo |
| **Utilisateur** | Champ texte | vide (filtre par pseudo) |
| **Slots libres** | Checkbox | ❌ (optionnel) |

#### 3.4.3 Application des filtres

- **Le filtre par extension (mp3/flac/ogg) est automatique** et s'applique côté réception
- Les autres filtres sont optionnels et s'appliquent en temps réel sur les résultats déjà reçus
- Un badge `[3 filtres actifs]` s'affiche à côté du bouton Filtres

### 3.5 Barre de recherche

| Élément | Style |
|---------|-------|
| `QLineEdit` | Fond `#1e1e2e`, bordure `#3a3a4a`, border-radius `6px`, padding 8px |
| Focus | Bordure `#6c5ce7` (violet) |
| `Rechercher` | Fond `#6c5ce7`, hover `#7c6cf7` |
| `⏹ Stop` | Fond rouge `#e74c3c`, visible SEULEMENT quand `_searching == True` |
| Déclencheur | `returnPressed` ou clic sur `Rechercher` |
| Validation | Minimum **2 caractères** avant de pouvoir lancer |

### 3.6 Bouton "📥 Téléchargement rapide"

- Situé dans la barre d'actions sous le tableau
- **Visible uniquement quand au moins un résultat a des slots libres**
- Lance un téléchargement direct sur l'utilisateur avec la meilleure vitesse ET des slots libres
- Redirige vers le **Bot Téléchargement** avec les infos du fichier

### 3.7 Bouton "🔴 Mode dispo"

- Toggle binaire
- **Désactivé** par défaut (affiche tous les résultats)
- **Activé** → ne montre que les utilisateurs avec `has_free_slots == True`
- Icône change : 🔴 (mode off) → 🟢 (mode on)

### 3.8 Menu contextuel (clic droit sur une ligne)

| Option | Action |
|--------|--------|
| ⬇ Télécharger | Redirige vers Bot Téléchargement avec ce fichier |
| 👤 Voir les fichiers de l'utilisateur | Lance `search_user(username)` — remplace les résultats actuels |
| 📋 Copier le nom du fichier | Copie dans le presse-papier |
| 🚫 Bloquer l'utilisateur | Ajoute à la liste noire (via ConnexionManager) |

---

## 4. Modes de recherche

### 4.1 Recherche globale (standard)

```python
client.searches.search(query: str) -> SearchRequest
```

- Barre de recherche principale
- Résultats filtrés automatiquement (mp3/flac/ogg à la réception)
- Tri par bitrate décroissant par défaut

### 4.2 Recherche par utilisateur (browse)

```python
client.searches.search_user(username: str, query: str) -> SearchRequest
```

- **Déclencheur** : clic droit sur un pseudo → "👤 Voir les fichiers de l'utilisateur"
- Ouvre une sous-vue dans le même tableau (ou un onglet séparé)
- Le pseudo de l'utilisateur est affiché en haut comme `📁 Fichiers de : DJ_Electro`
- Bouton `← Retour` pour revenir aux résultats globaux

### 4.3 Recherche par salon

```python
client.searches.search_room(room: str, query: str) -> SearchRequest
```

- **Déclencheur** : le champ `#salon` dans la modal de filtres (ou un champ à côté de la barre de recherche)
- Affiche le nom du salon comme `💬 Salon : #electronic-music`
- Même tableau, même filtres, même comportement

### 4.4 Annulation d'une recherche

```python
client.searches.remove_request(request: SearchRequest | int) -> None
# ou
client.searches.stop() -> list[Task]
```

- Bouton `⏹ Stop` visible à côté du bouton Rechercher quand `_searching == True`
- Appelle `client.searches.remove_request(ticket)` ou `client.searches.stop()`
- Nettoie l'état et remet le bouton `Rechercher` en vert

---

## 5. Persistance de l'historique

### 5.1 Stockage

- **Fichier :** `data/bot_recherche_history.json`
- **Format :**

```json
{
  "searches": [
    {
      "query": "daft punk",
      "type": "global",
      "count": 47,
      "timestamp": "2026-05-14T14:30:00"
    },
    {
      "query": "Aphex Twin",
      "type": "global",
      "count": 23,
      "timestamp": "2026-05-14T13:15:00"
    },
    {
      "query": "Boards of Canada",
      "type": "user",
      "username": "ElectroDJ42",
      "count": 12,
      "timestamp": "2026-05-14T12:00:00"
    }
  ]
}
```

### 5.2 Comportement

- Les **20 dernières** recherches sont conservées
- Une recherche dupliquée met à jour le timestamp (remonte en haut)
- À l'ouverture du bot : les 5 dernières recherches apparaissent sous la barre (suggestions rapides cliquables)
- Bouton `📜 Historique` en fin de liste pour ouvrir une popup listant les 20 entrées
- Persistance : lecture au `__init__`, sauvegarde après chaque recherche

---

## 6. Signalisation

### 6.1 Signaux Qt reçus

| Signal | Émetteur | Quand |
|--------|----------|-------|
| `search_result_received` | `ConnexionManager` | Nouveau lot de résultats |
| `connected` | `ConnexionManager` | Connexion réussie |
| `disconnected` | `ConnexionManager` | Déconnexion |
| `error_occurred` | `ConnexionManager` | Erreur quelconque |

### 6.2 Signaux émis

| Signal | Vers | Quand |
|--------|------|-------|
| `page_changed(bot_name)` | `CenterZone` | Redirection vers Bot Téléchargement ou autre bot |

---

## 7. Gestion d'état

### 7.1 États possibles

| État | Barre recherche | Bouton Rechercher | Bouton Stop | Tableau | Status |
|------|----------------|-------------------|-------------|---------|--------|
| **Déconnecté** | Désactivée | Désactivé | Caché | Vidé | 🔴 Connectez-vous |
| **Connecté — repos** | Active | ✅ Actif | Caché | Existant | ✅ X résultats |
| **Recherche en cours** | Active (mais désactivée) | Désactivé + "Recherche…" | ⏹ Visible | Se remplit | 🔍 Recherche de « X » |
| **Timeout (30s)** | Active | ✅ Réactivé | Caché | Résultats existants | ⏱️ Continue en arrière-plan |
| **Limite atteinte (200)** | Active | ✅ Actif | Caché | Plein | ⚠️ 200 max — affinez |
| **Erreur** | Active | ✅ Actif | Caché | Peut être vide | ❌ Message d'erreur |

### 7.2 Timeout

- **30 secondes** après le lancement de la recherche
- Le timeout réactive le bouton Rechercher et cache le bouton Stop
- Les résultats continuent d'arriver en arrière-plan (on ne stoppe pas la recherche réseau)
- Nouvelle recherche = reset complet du timeout

---

## 8. Intégration dans CenterZone

### 8.1 `center.py`

```python
from src.gui.widgets.bots.bot_recherche import BotRecherche

class CenterZone(QFrame):
    def _build_recherche_page(self) -> None:
        page = BotRecherche()
        self._pages["Recherche"] = page
        self._stack.addWidget(page)

    def set_connexion_manager(self, manager: ConnexionManager) -> None:
        recherche = self._pages.get("Recherche")
        if isinstance(recherche, BotRecherche):
            recherche.set_connexion_manager(manager)
```

### 8.2 Navigation

- `"Recherche"` est construit via sa propre méthode `_build_recherche_page()` — retiré de la boucle générique `_build_menu_page`
- Le bot est accessible depuis le footer et depuis le Bot Accueil (action `navigate → Recherche`)

---

## 9. Contraintes techniques

### 9.1 Dépendances

- **PySide6** (QtCore, QtWidgets)
- **aioslsk** (via ConnexionManager — déjà intégré)
- **json** + **datetime** + **pathlib** (historique)

### 9.2 Architecture

- `BotRecherche(QFrame)` — page autonome
- `SearchResultCard` — supprimé, remplacé par les lignes du `QTableWidget`
- Signaux Qt standards (thread-safe via `AutoConnection`)
- Pas de dépendances externes supplémentaires

### 9.3 Performances

- Limite de 200 lignes dans le tableau (FIFO si dépassement)
- Les résultats arrivent par paquets via `SearchResultEvent`
- Filtrage à la réception : si l'extension n'est pas mp3/flac/ogg, la ligne n'est **pas ajoutée** au tableau

---

## 10. Règles & Comportement

### 10.1 Ce que le bot PEUT faire

- Rechercher des fichiers sur tout le réseau Soulseek
- Filtrer automatiquement pour ne garder que les fichiers audio (mp3, flac, ogg)
- Explorer les fichiers d'un utilisateur spécifique
- Rechercher dans un salon de discussion
- Trier les résultats par n'importe quelle colonne
- Filtrer les résultats (bitrate, taille, durée, etc.) via une modal
- Afficher le statut des slots libres et la vitesse des utilisateurs
- Proposer un bouton "Téléchargement rapide" vers le meilleur pair disponible
- Sauvegarder et restaurer l'historique des 20 dernières recherches
- Annuler une recherche en cours
- Rediriger vers le Bot Téléchargement, le Bot Utilisateurs
- Mode "Disponible immédiatement" (slots libres uniquement)

### 10.2 Ce que le bot NE fait PAS

- Pas de téléchargement direct (délègue au Bot Téléchargement)
- Pas de gestion de compte utilisateur (login/logout)
- Pas d'envoi de fichiers
- Pas de modification des fichiers locaux
- Pas de scan des partages

### 10.3 Ciblage audio

Le filtre d'extension est **automatique et permanent** :

```python
EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg"}

def _is_audio(file_data: FileData) -> bool:
    return file_data.extension.lower() in EXTENSIONS_AUDIO
```

Si l'utilisateur veut désactiver ce filtre : un toggle dans la modal Filtres → `🔊 Audio seulement`.

---

## 11. Messages clés

**État déconnecté :**
```
🔴 Connectez-vous à Soulseek pour lancer une recherche
```

**Recherche lancée :**
```
🔍 Recherche de « Daft Punk » en cours…
```

**Résultats reçus :**
```
✅ 47 résultats — recherche « Daft Punk »
```

**Limite atteinte :**
```
⚠️ 200 résultats max — affinez votre recherche
```

**Timeout (30s) :**
```
⏱️ La recherche continue en arrière-plan…
```

**Erreur :**
```
❌ Erreur : [message d'erreur]
```

**Aucun résultat audio trouvé :**
```
🔇 Aucun fichier audio trouvé pour « Daft Punk »
```

---

## 12. Étapes d'implémentation (feuille de route)

| # | Tâche | Statut |
|---|-------|--------|
| 1 | Remplacer SearchResultCard par QTableWidget (colonnes triables) | ❌ |
| 2 | Filtre automatique mp3/flac/ogg à la réception | ❌ |
| 3 | Modal de filtres avancés (extension, bitrate, durée, taille, slots) | ❌ |
| 4 | Bouton Stop + logique d'annulation de recherche | ❌ |
| 5 | Mode dispo (toggle slots libres) | ❌ |
| 6 | Clic droit → menu contextuel (DL, browse, copier, bloquer) | ❌ |
| 7 | Recherche par utilisateur (search_user via clic droit) | ❌ |
| 8 | Recherche par salon (search_room) | ❌ |
| 9 | Barre d'actions (DL rapide + mode dispo) | ❌ |
| 10 | Bouton DL fonctionnel (redirection Bot Téléchargement) | ❌ |
| 11 | Historique persistant JSON (20 dernières, lecture/écriture) | ❌ |
| 12 | Suggestions rapides (5 dernières sous la barre) | ❌ |
| 13 | Mise à jour de `center.py` + intégration | ❌ |
| 14 | Mise à jour `.aioslsk-logbook.md` | ❌ |

## 13. ❓ Questions résolues

### Interface et UX

- [x] **QTableWidget plutôt que SearchResultCard** : L'ancien système utilisait des cartes individuelles (SearchResultCard). Avantages du tableau unique :
  - Tri natif par colonne (cliquer sur l'en-tête) sans code de tri custom
  - Meilleure densité d'information : 9 colonnes visibles sans scroll, contre 3-4 max avec des cartes
  - Performances supérieures avec 200+ lignes (QTableWidget virtualise le rendu)
  - Navigation clavier native (flèches, PageUp/PageDown) sans code supplémentaire

- [x] **200 résultats max avec FIFO** : Pas de pagination (trop complexe pour un flux de résultats temps réel). Le FIFO évite de saturer la mémoire et permet de voir les résultats les plus récents sans perdre les anciens immédiatement. Un message avertit l'utilisateur quand la limite est atteinte.

- [x] **9 colonnes du tableau** : Extension, Fichier, Taille, Bitrate, Durée, Utilisateur, Slots, Vitesse, DL. Ces colonnes couvrent tout ce dont un utilisateur a besoin pour décider de télécharger : format, qualité, disponibilité du pair. Pas de colonnes superflues (chemin complet, date) pour garder le tableau lisible.

- [x] **Tri par bitrate décroissant par défaut** : La qualité audio est le critère principal de sélection. Alternative envisagée : tri par slots libres — écarté car le statut des slots change trop vite entre la recherche et le clic.

- [x] **Filtres en modal centrée plutôt qu'inline** : Les filtres (extension, bitrate, durée, taille, utilisateur, slots) sont nombreux (8+). La modal économise l'espace vertical, offre une UX plus propre, et un badge [N filtres actifs] rappelle l'état sans rouvrir la modal.

- [x] **Mode dispo (toggle binaire plutôt que filtre)** : Le toggle « slots libres seulement » est séparé des filtres car c'est une action fréquente. L'icône change (rouge → vert) pour un feedback immédiat. Une checkbox dans la modal aurait nécessité 2 clics supplémentaires.

- [x] **Menu contextuel (4 actions)** : Télécharger, browse, copier nom, bloquer. Pas d'actions secondaires (partager, favoris) pour éviter la surcharge. Les actions avancées sont dans le Bot Téléchargement.

### Moteur de recherche

- [x] **3 modes (global, user, room) dans un seul tableau** : Plutôt que 3 onglets séparés, le même QTableWidget est réutilisé. Le mode est indiqué par le titre (recherche normale / « Fichiers de : X » / « Salon : #x »). Bouton « Retour » depuis les modes user/room.

- [x] **Filtre automatique mp3/flac/ogg à la réception** : Évite de polluer le tableau avec .zip/.exe/.nfo. S'applique côté réception avant ajout au QTableWidget. Toggle « Audio seulement » dans la modal pour désactiver.

- [x] **30 secondes de timeout** : Durée empirique adaptée aux latences Soulseek (5-15s pour une recherche broadcast). Assez longue pour laisser les résultats arriver, assez courte pour ne pas bloquer l'UI. Après timeout, le bouton Rechercher est réactivé mais les résultats continuent en arrière-plan.

- [x] **Validation 2 caractères minimum** : Évite les recherches accidentelles (Entrée sur champ vide) et les requêtes trop courtes qui inondent le réseau.

### Architecture technique

- [x] **Service SearchHistory séparé** : Classe dédiée dans src/services/search_history.py plutôt que logique embarquée dans BotRecherche. SRP, testable indépendamment du GUI, réutilisable.

- [x] **Historique JSON plutôt que base de données** : 20 entrées max. JSON plus simple (pas de DB, pas de schéma, lisible, déboguable). SQLite serait du surkill pour 20 lignes.

- [x] **20 entrées max** : 5 affichées sous la barre (suggestions rapides), 20 via bouton Historique complet. Nombre suffisant pour une session de recherche typique.

- [x] **Déduplication automatique** : Même requête + type + utilisateur = timestamp mis à jour + remonte en tête. Évite les doublons dans l'historique.

- [x] **Signaux via ConnexionManager** : BotRecherche ne touche jamais aioslsk directement. Tout passe par ConnexionManager (search_result_received, connected, disconnected, error_occurred). Découplage, thread-safe, testable.

- [x] **Téléchargement rapide automatique** : Sélectionne le meilleur fichier (slots libres + meilleure vitesse). Pas de liste de choix — trop de clics pour une action fréquente.

- [x] **Pas de gestion directe des téléchargements** : Délègue au Bot Téléchargement via page_changed. SRP : chercher, pas télécharger.

### Performance et limites

- [x] **Extension non bloquante** : Filtre appliqué à la réception avant ajout au tableau. Un fichier .exe n'est jamais ajouté — économie mémoire, pas de scintillement.

- [x] **Persistance immédiate** : Chaque modification déclenche une sauvegarde JSON. Pas de perte de données en cas de crash.

- [x] **Pas de QTimer pour le rafraîchissement** : Résultats via signaux (event-driven), pas de polling. Économise CPU, pas d'appels réseau inutiles.

---

*Section ajoutée le 2026-06-23 — documente les décisions de conception prises pendant l'implémentation.*
