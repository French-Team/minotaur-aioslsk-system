---
title: "Navigation dans l'interface : footer, panneau gauche et zones"
category: "interface"
tags:
  - navigation
  - interface
  - footer
  - panneau config
keywords:
  - navigation interface footer panneau gauche
  - navigation interface footer panneau gauche
  - footer 12 boutons navigation bots
  - footer navigation Accueil Recherche Bibliotheque
  - footer navigation Accueil Recherche Bibliothèque
  - footer navigation Wishlist Telechargement
  - footer navigation Wishlist Téléchargement
  - footer navigation Surveillance Ordonnanceur Planificateur
  - footer navigation Optimiseur Clients actifs Assistant Aide
  - footer badge notification compteur
  - footer badge notification compteur resultats
  - footer set_badge mise a jour compteur
  - footer set_badge mise à jour compteur
  - footer bouton actif checkable
  - footer navigation page_changee
  - footer navigation page_changée
  - panneau gauche configuration gauche retractable
  - panneau gauche configuration gauche rétractable
  - panneau gauche 8 sections General Partages Reseau
  - panneau gauche 8 sections Général Partages Réseau
  - panneau gauche sections Recherche Telechargement
  - panneau gauche sections Recherche Téléchargement
  - panneau gauche sections Utilisateurs Salons Debug
  - panneau gauche deplier 200px
  - panneau gauche déplier 200px
  - panneau gauche replier 20px
  - panneau gauche handle fleche
  - panneau gauche handle flèche
  - panneau gauche click section config
  - panneau rooms droit retractable
  - panneau rooms droit rétractable
  - panneau rooms onglets Public Prive
  - panneau rooms onglets Public Privé
  - panneau rooms QTabWidget
  - panneau rooms deplier 280px
  - panneau rooms déplier 280px
  - header connexion header navigation
  - header connexion header navigation page
  - header connexion header clique navigation
  - zone centrale QStackedWidget pages
  - zone centrale page courante affichee
  - zone centrale page courante affichée
  - navigation connexion page_affichee
  - navigation connexion page_affichée
  - navigation header page_changed
  - navigation footer page_changed
  - navigation panneau gauche page_changed
  - navigation show_page changement page
  - navigation show_page changement page centrale
  - page bot accueil recherche bibliotheque
  - page bot accueil recherche bibliothèque
  - page bot wishlist telechargement surveillance
  - page bot wishlist téléchargement surveillance
  - page bot ordonnanceur planificateur optimiseur
  - page bot clients actifs assistant aide
  - page config general partages reseau
  - page config général partages réseau
  - page config recherche telechargement utilisateurs
  - page config recherche téléchargement utilisateurs
  - page config salons debug
---

# Navigation dans l'interface : footer, panneau gauche et zones

## Introduction

L'interface de l'application est organisée en **3 zones de navigation** qui permettent d'accéder à toutes les fonctionnalités :

| Zone | Position | Accès |
|------|----------|-------|
| **Footer** | Barre inférieure | 12 boutons → pages des bots |
| **Panneau gauche** | Côté gauche (rétractable) | 8 sections → pages de configuration |
| **Header** | Bannière supérieure | Widget de connexion → page connexion |

Ces 3 zones émettent toutes un signal `page_changed(str)` qui est connecté à la zone centrale (`CenterZone.show_page()`), permettant d'afficher la page demandée dans le `QStackedWidget`.

---

## 1. Le Footer — La navigation principale (12 bots)

### Emplacement et accès

Le footer est situé en **bas de l'application**. Il est **masqué avant la connexion** et apparaît automatiquement après une connexion réussie au serveur Soulseek.

### Les 12 boutons de navigation

| # | Bouton | Page cible | Icône/Description |
|---|--------|-----------|-------------------|
| 1 | **Accueil** | `accueil` | Page d'accueil post-connexion, résumé des activités |
| 2 | **Recherche** | `recherche` | Recherche de fichiers sur le réseau Soulseek |
| 3 | **Bibliothèque** | `bibliotheque` | Gestion de la bibliothèque musicale locale |
| 4 | **Wishlist** | `wishlist` | Liste de souhaits et téléchargements automatiques |
| 5 | **Téléchargement** | `telechargements` | Suivi des téléchargements en cours et terminés |
| 6 | **Surveillance** | `surveillance` | Surveillance des événements et alertes |
| 7 | **Ordonnanceur** | `ordonnanceur` | Ordonnancement et files d'attente |
| 8 | **Planificateur** | `planificateur` | Tâches programmées et automatisation |
| 9 | **Optimiseur** | `optimiseur` | Optimisation des téléchargements |
| 10 | **Clients actifs** | `clients-actifs` | Liste des utilisateurs connectés |
| 11 | **Assistant** | `assistant` | Assistant virtuel d'aide |
| 12 | **Aide** | `aide` | Aide intégrée et documentation |

### Fonctionnement des boutons

Chaque bouton est un `_FooterNavButton` (sous-classe de `QPushButton`) avec les caractéristiques suivantes :

- **État checkable** : Le bouton actif reste visuellement enfoncé/sélectionné
- **Badge de notification** : Un compteur rouge peut s'afficher en haut à droite du bouton pour indiquer :
  - Nombre de résultats de recherche (`"99+"`)
  - Nombre d'alertes de surveillance
  - Événements planifiés en attente
  - Téléchargements en cours

### Utilisation

1. **Changer de page** : Cliquez sur un bouton du footer pour afficher la page correspondante dans la zone centrale
2. **Identifier la page active** : Le bouton correspondant à la page affichée reste visuellement actif (enfoncé)
3. **Voir les notifications** : Un badge rouge sur un bouton indique des informations nouvelles (résultats, alertes...)
4. **Mise à jour automatique** : Les badges sont mis à jour automatiquement par la zone centrale (`CenterZone`) via `footer.set_badge(name, count)`

---

## 2. Le Panneau Gauche — La navigation de configuration

### Emplacement et accès

Le panneau gauche (`LeftZone`) est situé sur le **côté gauche de l'application**. Il est toujours visible (contrairement au footer et au header) et permet d'accéder aux **pages de configuration**.

### Caractère rétractable

Le panneau gauche peut être **déplié ou replié** à l'aide de la poignée (`_Handle`) située sur son bord droit :

| État | Largeur | Indicateur |
|------|---------|------------|
| **Déplié** | 200 px | Noms des sections affichés + flèche `◀` |
| **Replié** | 20 px | Flèche `▶` seulement |

Pour basculer entre les deux états : **cliquez sur la poignée** (le bord droit du panneau avec la flèche).

### Les 8 sections de configuration

| Section | Page cible | Description |
|---------|-----------|-------------|
| **Général** | `config-general` | Paramètres généraux (langue, comportement) |
| **Partages** | `config-partages` | Gestion des dossiers partagés |
| **Réseau** | `config-reseau` | Paramètres réseau (ports, UPnP, connexion) |
| **Recherche** | `config-recherche` | Configuration de la recherche |
| **Téléchargement** | `config-telechargement` | Limites et destinations des téléchargements |
| **Utilisateurs** | `config-utilisateurs` | Listes d'amis et d'utilisateurs bloqués |
| **Salons** | `config-salons` | Salons de discussion (auto-join, favoris) |
| **Debug** | `config-debug` | Options de débogage (logs, overrides IP) |

### Utilisation

1. **Ouvrir une page de configuration** : Cliquez sur le nom d'une section dans le panneau gauche
2. **Replier pour gagner de l'espace** : Cliquez sur la flèche `◀` pour replier le panneau
3. **Identifier la section active** : Le bouton de la section affichée reste visuellement actif
4. **Navigation rapide** : Le panneau peut rester replié ; cliquez sur la flèche `▶` pour le déplier quand vous avez besoin de changer de section de configuration

---

## 3. Le Header — La navigation de connexion

### Emplacement et accès

Le header (`HeaderZone`) est situé en **haut de l'application**. Il est **masqué avant la connexion** et apparaît après une connexion réussie.

### Contenu

Le header contient un widget `ConnexionHeaderWidget` qui affiche :
- L'avatar (initiale ou photo de profil) de l'utilisateur connecté
- Le nom d'utilisateur Soulseek

### Utilisation

1. **Retourner à la page de connexion** : Cliquez sur le widget de connexion dans le header pour revenir à la page de connexion (utile pour se déconnecter ou changer de compte)

---

## 4. Le Panneau Droit — Les rooms (salons)

### Emplacement et accès

Le panneau droit (`RightZone`) est situé sur le **côté droit de l'application**. Il est rétractable et permet d'accéder aux salons de discussion (rooms).

### Caractère rétractable

| État | Largeur | Indicateur |
|------|---------|------------|
| **Déplié** | 280 px | Titre "LES ROOMS" + onglets + flèche `▶` |
| **Replié** | 20 px | Flèche `◀` seulement |

Pour basculer entre les deux états : **cliquez sur la poignée** (le bord gauche du panneau).

### Onglets

Le panneau droit est divisé en deux onglets via un `QTabWidget` :

| Onglet | Contenu |
|--------|---------|
| **Public** | Liste des salons publics disponibles |
| **Privé** | Liste des salons privés / invitations |

---

## 5. Flux de navigation complet

### Avant connexion

```
État initial :
┌────────────────────────────────────────┐
│           (Header masqué)              │
├──────┬──────────────────────┬──────────┤
│      │                      │          │
│Left  │  Page CONNEXION      │ Right    │
│déplié│  (formulaire auth)   │ replié   │
│      │                      │          │
├──────┴──────────────────────┴──────────┤
│           (Footer masqué)              │
└────────────────────────────────────────┘
```

### Après connexion réussie

```
┌────────────────────────────────────────┐
│  Header: [Avatar] Nom d'utilisateur   │  ← visible
├──────┬──────────────────────┬──────────┤
│      │                      │          │
│Left  │  Page ACCUEIL        │ Right    │
│déplié│  (résumé activité)   │ replié   │
│      │                      │          │
├──────┴──────────────────────┴──────────┤
│ [Accueil] [Recherche] [Bibliothèque]...│  ← visible
└────────────────────────────────────────┘
```

### Navigation vers une page bot

```
1. Cliquer sur "Recherche" dans le footer
   └─ FooterZone émet page_changed("recherche")
        └─ CenterZone.show_page("recherche")
             └─ QStackedWidget affiche la page de recherche

2. Le bouton "Recherche" reste actif (checkable)
```

### Navigation vers une page de configuration

```
1. Cliquer sur "Réseau" dans le panneau gauche
   └─ LeftZone émet page_changed("config-reseau")
        └─ CenterZone.show_page("config-reseau")
             └─ QStackedWidget affiche la page config réseau

2. Le bouton "Réseau" reste actif dans le panneau gauche
```

### Navigation vers la page de connexion

```
1. Cliquer sur le widget utilisateur dans le header
   └─ HeaderZone émet page_changed("connexion")
        └─ CenterZone.show_page("connexion")
             └─ QStackedWidget affiche le formulaire de connexion
```

---

## 6. Astuces et bonnes pratiques

| Action | Méthode |
|--------|---------|
| **Basculer rapidement entre deux bots** | Cliquez directement sur leurs boutons dans le footer |
| **Replier le panneau gauche** | Cliquez sur `◀` (bord droit) pour voir plus de contenu central |
| **Déplier le panneau droit** | Cliquez sur `◀` (bord gauche) pour voir les salons |
| **Revenir à l'accueil** | Cliquez sur "Accueil" dans le footer |
| **Voir les notifications** | Repérez les badges rouges sur les boutons du footer |
| **Changer de compte** | Cliquez sur le widget utilisateur dans le header |
| **Configurer l'application** | Utilisez le panneau gauche pour les 8 sections de configuration |
| **Gagner de l'espace** | Repliez les deux panneaux latéraux (gauche et droit) pour maximiser la zone centrale |

---

## 7. Résumé des zones de navigation

| Zone | Visibilité | Contenu | Action |
|------|-----------|---------|--------|
| **Footer** | Après connexion | 12 boutons (Accueil → Aide) | Changer de page bot |
| **Panneau gauche** | Toujours visible | 8 sections config (Général → Debug) | Ouvrir une page de configuration |
| **Header** | Après connexion | Widget utilisateur (avatar + nom) | Revenir à la page connexion |
| **Panneau droit** | Toujours visible (rétractable) | Onglets Public/Privé (rooms) | Gérer les salons de discussion |

Toutes ces zones utilisent le même mécanisme : un signal `page_changed(str)` connecté à `CenterZone.show_page()`, qui active la page correspondante dans le `QStackedWidget` au centre de l'interface.
