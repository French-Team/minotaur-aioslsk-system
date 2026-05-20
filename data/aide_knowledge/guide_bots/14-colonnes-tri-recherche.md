---
title: "Colonnes et tri personnalisé des résultats de recherche"
category: guide_bots
keywords: ["colonne", "tri", "recherche", "resultat", "tableau", "fichier", "extension", "taille", "bitrate", "duree", "durée", "utilisateur", "slot", "vitesse", "telechargement", "téléchargement", "trier", "ordonner", "classer", "colonne", "en-tête", "header"]
---

# Colonnes et tri personnalisé des résultats de recherche

> **Niveau :** Débutant  
> **Temps de lecture :** 6 min  
> **Catégorie :** Guide — Bot Recherche

---

## 1. Les 9 colonnes du tableau

Le bot Recherche affiche les résultats dans un **tableau à 9 colonnes** :

| # | Colonne | Type de données | Largeur |
|---|---------|-----------------|---------|
| ① | **Extension** | Texte (`.mp3`, `.flac`, etc.) | Fixe (50 px) |
| ② | **Fichier** | Texte (nom du fichier) | **Extensible** (remplit l'espace) |
| ③ | **Taille** | Taille formatée (Ko, Mo, Go) | Fixe (80 px) |
| ④ | **Bitrate** | Débit binaire (kbps) | Fixe (65 px) |
| ⑤ | **Durée** | Temps (mm:ss) | Fixe (55 px) |
| ⑥ | **Utilisateur** | Texte (pseudo Soulseek) | Fixe (120 px) |
| ⑦ | **Slots** | Nombre (ex: `2/10`) | Fixe (40 px) |
| ⑧ | **Vitesse** | Vitesse (kb/s, Mo/s) | Fixe (70 px) |
| ⑨ | **DL** | Bouton de téléchargement | Fixe (40 px) |

> 💡 La colonne **Fichier** est la seule qui s'étend automatiquement pour remplir la largeur disponible. Les autres ont une largeur fixe optimisée pour leur contenu.

---

## 2. Tri des résultats

### Tri par défaut

Par défaut, les résultats sont triés par **bitrate décroissant** — les fichiers de meilleure qualité apparaissent en premier :

```
Colonne "Bitrate" → Tri décroissant (320 > 256 > 192 > 128...)
```

### Tri personnalisé — Cliquer sur un en-tête

Vous pouvez trier par n'importe quelle colonne en **cliquant sur son en-tête** :

| Action | Résultat |
|--------|----------|
| **1 clic** sur un en-tête | Tri croissant ▲ |
| **2 clics** sur le même en-tête | Tri décroissant ▼ |
| **3 clics** | Retour au tri par défaut |

### Tri intelligent — Valeurs numériques

Contrairement à un tri alphabétique standard, le tableau utilise un **tri numérique intelligent** :

| Colonne | Affichage | Tri basé sur |
|---------|-----------|-------------|
| **Taille** | `12.5 Mo` / `850 Ko` | Valeur brute en **octets** |
| **Bitrate** | `320 kbps` | Valeur brute en **kbps** |
| **Durée** | `4:32` / `12:15` | Valeur brute en **secondes** |

Cela signifie que trier par taille classe correctement `1.2 Go` avant `850 Mo`, même si alphabétiquement "1.2 Go" < "850 Mo".

### Tri par Extension

Le tri alphabétique standard s'applique aux colonnes textuelles (Extension, Fichier, Utilisateur). Trier par Extension permet de regrouper tous les `.flac` ensemble, ou de voir les `.opus` à part.

---

## 3. Exemples concrets de tri

### Exemple 1 : Trouver les meilleures qualités

```
Trier par Bitrate ▼  (décroissant)
```
➡️ Les fichiers 320 kbps et FLAC apparaissent en haut de la liste.

### Exemple 2 : Trouver les fichiers les plus volumineux

```
Trier par Taille ▼  (décroissant)
```
➡️ Les albums FLAC 24-bit ou les sets DJ apparaissent en premier.

### Exemple 3 : Trouver les fichiers les plus longs

```
Trier par Durée ▼  (décroissant)
```
➡️ Idéal pour repérer les mixsets, podcasts ou albums complets.

### Exemple 4 : Voir les utilisateurs les plus rapides

```
Trier par Vitesse ▼  (décroissant)
```
➡️ Les sources avec la meilleure bande passante montent en haut.

### Exemple 5 : Trouver des fichiers disponibles

```
Trier par Slots ▲  (croissant)
```
➡️ Les fichiers avec le plus de slots libres apparaissent en premier (les utilisateurs avec `5/10` avant `8/10`).

---

## 4. Comportement détaillé

### Ajout progressif des résultats

Quand une recherche est en cours, les résultats arrivent **par lots** :

1. Le tri est **désactivé** temporairement pendant l'insertion des résultats
2. Les lignes sont ajoutées une par une
3. Le tri est **réactivé** une fois l'insertion terminée

Cela évite un re-tri à chaque ajout, ce qui ralentirait l'interface avec des centaines de résultats.

### Limite de résultats

```
MAX_RESULTS = 200
```

Quand le tableau atteint 200 résultats, les **plus anciens** sont retirés (FIFO — premier entré, premier sorti) pour faire place aux nouveaux. Si vous triez par bitrate décroissant, seuls les 200 meilleurs fichiers sont conservés.

### Colonne DL (Téléchargement)

La colonne DL n'est pas triable — elle contient un **bouton** `⬇️` qui lance le téléchargement du fichier. Cliquer sur l'en-tête de cette colonne n'a aucun effet.

---

## 5. Aspects techniques

### Classe `TableItem`

Le tri personnalisé est implémenté via une sous-classe de `QTableWidgetItem` :

```python
class TableItem(QTableWidgetItem):
    def __init__(self, text: str, sort_value=None):
        super().__init__(text)
        if sort_value is not None:
            self.setData(Qt.UserRole, sort_value)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        # Comparaison numerique si les deux items ont une sort_value
        v1 = self.data(Qt.UserRole)
        v2 = other.data(Qt.UserRole)
        if v1 is not None and v2 is not None:
            return v1 < v2
        return super().__lt__(other)
```

Cette approche permet d'afficher des valeurs formatées (ex: `12.5 Mo`) tout en triant sur les valeurs brutes (ex: `13107200` octets).

### Valeurs stockées pour le tri

| Colonne | Valeur affichée | Valeur de tri (brute) |
|---------|----------------|----------------------|
| Taille | `12.5 Mo` | `13107200` (octets) |
| Bitrate | `320 kbps` | `320` |
| Durée | `4:32` | `272` (secondes) |
| Fichier | `Song Title` | `song title` (minuscules) |
| Utilisateur | `User123` | `user123` (minuscules) |

---

## Voir aussi

- [Filtres de format dans le bot Recherche](/guide_bots/13-filtres-format-recherche)
- [Bot Recherche — Guide complet](/guide_bots/02-bot-recherche)
- [Filtres de recherche avancée — Tutoriel](/tutoriels/filtres-recherche-avancee)
