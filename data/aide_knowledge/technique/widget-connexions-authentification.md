---
title: "Widget Connexions : formulaire d'authentification Soulseek"
category: technique
tags:
  - connexion
  - authentification
  - formulaire
  - widget
  - interface
keywords:
  - connexion Soulseek formulaire
  - connexion widget interface
  - ConnexionPage widget
  - ConnexionHeaderWidget avatar
  - widget authentification utilisateur
  - widget connexion utilisateur
  - widget formulaire identifiants
  - login page widget
  - login Soulseek interface
  - connexion header avatar
  - connexion page status led
  - widget connexion automatique
  - widget generate compte
  - widget deconnexion
  - widget déconnexion
  - QStackedWidget page connexion
  - evenement clique header
  - événement cliqué header
  - signal login_requested emit
  - signal disconnect_requested emit
  - signal generate_requested emit
  - signal auto_login_changed emit
  - slot on login validation
  - slot on generate compte
  - slot on disconnect deconnexion
  - slot on auto login toggled
  - set connected mode connecte
  - set connected mode connecté
  - set disconnected mode deconnecte
  - set disconnected mode déconnecté
  - set generating desactivation
  - set generating désactivation
  - show error message erreur
  - show success message succes
  - show success message succès
  - prefill remplir champs
  - set message label couleur
  - led off placeholder couleur
  - led green success couleur
  - led red danger couleur
  - layout formulaire centrer card
  - QLineEdit username password
  - QCheckBox connexion automatique
  - QPushButton login generate disconnect
  - QLabel message statut
  - center py build connexion page
  - header py connexion header widget
  - header zone page changed signal
  - integration stack pages
  - evenement click header navigation
  - navigation page changement
  - icone avatar lettre initiale
  - photo avatar circulaire ronde
  - app config set connexion automatique
  - theme_fragments colors led
  - voyant vert rouge etat
  - voyant vert rouge état
  - widget etat connexion
  - widget état connexion
  - validation champ avant login
  - champ vide validation
  - champ mot de passe vide
  - 381 lignes widget complet
  - deux classes connexion header page
---

# Widget Connexions (connexions.py)

## Vue d'ensemble

Le module `src/gui/widgets/connexions.py` (381 lignes) fournit deux widgets complémentaires pour gérer l'authentification à Soulseek :

| Widget | Rôle | Héritage |
|--------|------|----------|
| **ConnexionHeaderWidget** (ligne 39, ~99 lignes) | Avatar + nom d'utilisateur dans le header | `QFrame` |
| **ConnexionPage** (ligne 138, ~243 lignes) | Formulaire complet de connexion/déconnexion | `QFrame` |

```
┌──────────────────────────────────────────────────┐
│                  HeaderZone                      │
│  ┌──────────────────────────────────────────┐    │
│  │  ConnexionHeaderWidget                   │    │
│  │  ┌────┐                                  │    │
│  │  │ A  │  Alice                           │    │
│  │  └────┘                                  │    │
│  └──────────────────────────────────────────┘    │
├──────────────────────────────────────────────────┤
│              CenterZone (QStackedWidget)          │
│  ┌──────────────────────────────────────────┐    │
│  │  ConnexionPage (page "connexion")        │    │
│  │  ┌──────────────────────────────────┐    │    │
│  │  │       Connexion Soulseek         │    │    │
│  │  │           🟢 Connecté            │    │    │
│  │  │                                  │    │    │
│  │  │  Nom d'utilisateur  [Alice    ]  │    │    │
│  │  │  Mot de passe       [••••••••]  │    │    │
│  │  │  ☑ Connexion auto                │    │    │
│  │  │                                  │    │    │
│  │  │  [🔌 Connexion]  [✨ Générer]    │    │    │
│  │  │  [❌ Déconnexion]               │    │    │
│  │  │  ─────────────────────────────  │    │    │
│  │  │  ✓ Connecté avec succès         │    │    │
│  │  └──────────────────────────────────┘    │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

## Constantes : couleurs du voyant lumineux

```python
_LED_OFF    = COLORS["TEXT_PLACEHOLDER"]   # gris — déconnecté
_LED_GREEN  = COLORS["SUCCESS"]            # vert — connecté
_LED_RED    = COLORS["DANGER"]             # rouge — erreur
```

Les couleurs proviennent de `src/gui/theme_fragments/colors` et s'adaptent automatiquement au thème (clair/sombre).

---

## 1. ConnexionHeaderWidget

Widget compact affiché dans la barre de navigation (`HeaderZone`) lorsque l'utilisateur est connecté. Il sert à la fois d'indicateur de connexion et de bouton de navigation vers la page de connexion.

### API publique

| Méthode | Description |
|---------|-------------|
| `set_username(username)` | Définit le nom affiché et l'avatar initiale (première lettre, majuscule) |
| `set_photo(path)` | Charge une image depuis le disque et l'affiche en avatar circulaire |

### Fonctionnement

- **Avatar** : Affiche la première lettre du nom d'utilisateur dans un cercle coloré. Si une photo de profil a été chargée via `set_photo()`, elle remplace l'initiale et est masquée en cercle (`border-radius` en CSS).
- **Nom** : Affiche le nom d'utilisateur à droite de l'avatar.
- **Signal `clicked()`** : Émis lors du clic sur le widget. Connecté dans `HeaderZone` au changement de page vers `"connexion"`.

```python
# header.py (connexion)
self._connexion = ConnexionHeaderWidget()
self._connexion.clicked.connect(lambda: self.page_changed.emit("connexion"))
```

---

## 2. ConnexionPage

Page complète de gestion de l'authentification, affichée dans la zone centrale (`CenterZone` → `QStackedWidget`). Remplace l'écran de connexion par l'interface connectée après authentification.

### Layout et widgets enfants

| Widget | Attribut | Type | Rôle |
|--------|----------|------|------|
| Carte centrale | `connexionCard` | `QFrame` | Conteneur centré du formulaire |
| Titre | — | `QLabel` | "Connexion Soulseek" |
| Voyant | `_page_led` | `QLabel` | Cercle 🟢/🔴/⚪ indiquant l'état |
| Statut | `_page_status` | `QLabel` | Texte "Connecté" / "Déconnecté" |
| Nom d'utilisateur | `_username` | `QLineEdit` | Champ texte avec placeholder |
| Mot de passe | `_password` | `QLineEdit` | Champ mot de passe masqué |
| Connexion auto | `_auto_cb` | `QCheckBox` | "Connexion automatique au démarrage" |
| Bouton Connexion | `_login_btn` | `QPushButton` | 🔌 Connexion |
| Bouton Générer | `_generate_btn` | `QPushButton` | ✨ Générer un compte |
| Bouton Déconnexion | `_disconnect_btn` | `QPushButton` | ❌ Déconnexion (caché par défaut) |
| Message | `_message` | `QLabel` | Texte de retour (succès/erreur) |

### Signaux émis

| Signal | Paramètres | Déclencheur |
|--------|------------|-------------|
| `login_requested` | `(username: str, password: str)` | Clic sur "Connexion" (après validation) |
| `generate_requested` | — | Clic sur "Générer un compte" |
| `disconnect_requested` | — | Clic sur "Déconnexion" |
| `auto_login_changed` | `(checked: bool)` | Changement de la checkbox |

### API publique

| Méthode | Description |
|---------|-------------|
| `set_connected(username)` | Passe en mode connecté : LED verte, masque le formulaire, affiche le bouton Déconnexion |
| `set_disconnected()` | Passe en mode déconnecté : LED éteinte, réaffiche le formulaire |
| `set_generating(bool)` | Désactive/réactive tous les champs pendant la génération d'un compte |
| `show_error(message)` | Affiche un message d'erreur en rouge |
| `show_success(message)` | Affiche un message de succès en vert |
| `prefill(username, password)` | Remplit les champs avec des identifiants préexistants |
| `set_auto_login(bool)` | Définit l'état de la checkbox (sans émettre de signal) |
| `is_auto_login()` → `bool` | Retourne l'état de la checkbox |
| `get_username()` → `str` | Retourne le contenu du champ utilisateur |
| `get_password()` → `str` | Retourne le contenu du champ mot de passe |

### Slots internes

#### `_on_login()`

```python
def _on_login(self):
    username = self._username.text().strip()
    password = self._password.text().strip()
    if not username or not password:
        self._set_message("Veuillez remplir tous les champs", _LED_RED)
        return
    self.login_requested.emit(username, password)
```

Valide que les champs ne sont pas vides, puis émet le signal `login_requested`.

#### `_on_auto_login_toggled(checked)`

```python
def _on_auto_login_toggled(self, checked):
    from src.services.app_config import set as config_set
    config_set("general.connexion_automatique", checked)
    self.auto_login_changed.emit(checked)
```

Importe et utilise directement `app_config.set` pour persister le réglage dans la configuration.

#### `_on_generate()`

Émet simplement le signal `generate_requested`.

#### `_on_disconnect()`

Émet simplement le signal `disconnect_requested`.

### `_set_message(text, color)`

Méthode utilitaire interne qui :
1. Définit le texte du label `_message`
2. Applique la couleur au texte via `setStyleSheet`
3. Affiche ou masque dynamiquement le label selon la présence de texte

---

## 3. Intégration dans l'application

### Dans `center.py` — CentreZone

```python
# center.py
def _build_connexion_page(self):
    page = ConnexionPage()
    self._pages["connexion"] = page
    self._stack.addWidget(page)
    # Les signaux sont connectés par le contrôleur parent
```

La page est ajoutée au `QStackedWidget` sous la clé `"connexion"`, permettant la navigation via `self._stack.setCurrentWidget(self._pages["connexion"])`.

### Dans `header.py` — HeaderZone

```python
# header.py
self._connexion = ConnexionHeaderWidget()
self._connexion.clicked.connect(lambda: self.page_changed.emit("connexion"))
layout.addWidget(self._connexion)
```

Le `ConnexionHeaderWidget` est ajouté au layout de la `HeaderZone`. Son clic déclenche un changement de page vers l'écran de connexion.

### Cycle de vie des états

```
Déconnecté ──[Connexion]──→ Connexion en cours ──[succès]──→ Connecté
    ↑                                                            │
    │                                                   [Déconnexion]
    └────────────────────────────────────────────────────────────┘
                         ↑ Générer ↑
                    Compte en cours → succès/erreur
```

- **Déconnecté** : `set_disconnected()` → formulaire visible, champs éditables, bouton Connexion/Générer
- **Connexion en cours** : `set_generating(True)` → champs désactivés
- **Connecté** : `set_connected(username)` → LED verte, statut "Connecté", bouton Déconnexion
- **Erreur** : `show_error(msg)` → message rouge dans le formulaire
- **Succès** : `show_success(msg)` → message vert

---

## 4. Résumé technique

| Propriété | Valeur |
|-----------|--------|
| **Fichier** | `src/gui/widgets/connexions.py` |
| **Lignes** | 381 |
| **Classes** | 2 : `ConnexionHeaderWidget`, `ConnexionPage` |
| **Héritage** | `QFrame` (les deux) |
| **Signaux** | 5 : `clicked`, `login_requested`, `generate_requested`, `disconnect_requested`, `auto_login_changed` |
| **Slots publics** | 9 : `set_connected`, `set_disconnected`, `set_generating`, `show_error`, `show_success`, `prefill`, `set_auto_login`, `get_username`, `get_password` |
| **Slots internes** | 4 : `_on_login`, `_on_auto_login_toggled`, `_on_generate`, `_on_disconnect` |
| **Dépendances** | `PySide6`, `src.gui.theme_fragments.colors`, `src.services.app_config` |
| **Intégration** | `center.py` (page), `header.py` (header widget) |
