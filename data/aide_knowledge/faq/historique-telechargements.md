---
title: "Historique des téléchargements (HistoryDialog)"
category: "faq"
icon: "📜"
keywords:
  - historique telechargement soulseek
  - historique téléchargement soulseek
  - historique telechargement bot
  - historique téléchargement bot
  - HistoryDialog telechargement
  - telechargement_history
  - historique transfert soulseek
  - historique download soulseek
  - historique telechargement SQLite
  - historique téléchargement SQLite
  - telechargement termine historique
  - téléchargement terminé historique
  - telechargement echoue historique
  - téléchargement échoué historique
  - voir historique telechargement
  - filtrer historique telechargement
  - effacer historique telechargement
  - vider historique telechargement
  - bouton historique telechargement
  - icone historique telechargement
  - tableau historique telechargement
  - colonnes historique telechargement
  - historique SQLite telechargement
  - add_to_history telechargement
  - get_history telechargement
  - count_history telechargement
  - clear_history telechargement
  - sauvegarder historique telechargement
  - historique termine echoue
  - filtre statut historique
  - pagination historique 500
  - limite 500 historique
  - date fin historique
  - vitesse moyenne historique
  - historique telechargement
  - historique download
  - historique transfert
  - historique SQLite
  - telechargement fini historique
  - téléchargement fini historique
  - telechargement rate historique
  - historique terminee
  - historique echouee
  - historique efface
  - historique supprime
---


# 📜 Historique des téléchargements (HistoryDialog)

Cette FAQ couvre le système d'historique des téléchargements, de sa persistance SQLite à l'interface `HistoryDialog` qui permet de consulter, filtrer et effacer l'historique.

---

## 📖 Qu'est-ce que l'historique des téléchargements ?

L'historique des téléchargements enregistre automatiquement chaque transfert **terminé** ou **échoué** dans une base de données SQLite. Il permet de :
- Consulter la liste de tous les téléchargements passés
- Filtrer par statut (terminé / échoué)
- Voir les détails (fichier, taille, utilisateur, vitesse, date)
- Effacer l'historique partiellement ou totalement

---

## 🗄️ Où sont stockées les données ?

L'historique est persisté dans une base de données SQLite locale via le module `telechargement_history.py`.

### Base de données

- **Fichier :** `data/bot_telechargement_history.db` (emplacement relatif au projet)
- **Mode :** WAL (Write-Ahead Logging) pour de meilleures performances concurrentes
- **Table unique :** `download_history`
- **Index :** `idx_history_date` (sur `date_fin DESC`), `idx_history_statut` (sur `statut`)

### Structure de la table `download_history`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER (PK, auto) | Identifiant unique |
| `identifiant` | TEXT (NOT NULL) | Identifiant technique du transfert |
| `fichier` | TEXT (NOT NULL) | Nom du fichier téléchargé |
| `utilisateur` | TEXT (NOT NULL, défaut '') | Nom de l'utilisateur source |
| `taille` | TEXT (NOT NULL, défaut '') | Taille formatée (ex: « 12.5 MB ») |
| `taille_bytes` | INTEGER (NOT NULL, défaut 0) | Taille en octets |
| `statut` | TEXT (NOT NULL, CHECK 'termine' ou 'echoue') | Statut du transfert |
| `vitesse_moyenne` | TEXT (NOT NULL, défaut '') | Vitesse formatée (ex: « 1.2 MB/s ») |
| `vitesse_bytes` | REAL (NOT NULL, défaut 0.0) | Vitesse en octets/seconde |
| `date_debut` | TEXT (NOT NULL) | Date et heure de démarrage |
| `date_fin` | TEXT (NOT NULL, défaut `datetime('now')`) | Date et heure de fin |
| `created_at` | TEXT (NOT NULL, défaut `datetime('now')`) | Date de création de l'entrée |

---

## 👀 Comment consulter l'historique ?

### Accès via le bouton « 📜 Historique »

Dans le **bot Téléchargement**, un bouton **📜 Historique** est situé dans la barre d'outils, entre le filtre de téléchargements et le bouton d'ouverture de dossier.

Au clic, une fenêtre modale `HistoryDialog` s'ouvre.

### La fenêtre HistoryDialog

- **Taille :** 900 × 500 pixels
- **Type :** Modale (`QDialog`)
- **Titre :** « 📜 Historique des téléchargements »

L'interface se compose de :

1. **Barre d'en-tête** avec :
   - Un titre
   - Un filtre déroulant (`QComboBox`) : **Tous**, **Terminé**, **Échoué**
   - Un bouton **🗑 Vider l'historique**
2. **Compteur** : Affiche le nombre total d'entrées (ex: « 15 élément(s) »)
3. **Tableau** avec 6 colonnes triables

### Les colonnes du tableau

| Colonne | Largeur | Description |
|---------|---------|-------------|
| Fichier | 260px | Nom du fichier téléchargé |
| Taille | 80px | Taille formatée |
| Utilisateur | 140px | Nom de l'utilisateur source |
| Statut | 80px | ✅ Terminé ou ❌ Échoué (avec couleur) |
| Vitesse | 100px | Vitesse moyenne du transfert |
| Date | 160px | Date et heure de fin (dernière colonne extensible) |

---

## 🔍 Comment filtrer l'historique ?

La liste déroulante dans l'en-tête permet trois modes d'affichage :

| Option | Filtre appliqué | Usage |
|--------|----------------|-------|
| **Tous** | Aucun filtre | Voir tout l'historique |
| **Terminé** | `statut = 'termine'` | Voir les téléchargements réussis uniquement |
| **Échoué** | `statut = 'echoue'` | Voir les téléchargements qui ont échoué |

Le changement de filtre recharge automatiquement les données via `_load_data()`.

---

## 🧮 Combien d'entrées sont affichées ?

La requête utilise une **limite de 500 entrées** (`limit=500, offset=0`). Cela signifie que :

- Si vous avez moins de 500 entrées : toutes sont affichées
- Si vous avez plus de 500 entrées : seules les 500 plus récentes sont visibles

Le compteur (`count_history`) indique le nombre total réel d'entrées dans la base, quelle que soit la limite d'affichage.

---

## 🗑️ Comment effacer l'historique ?

### Effacement total

1. Cliquez sur le bouton **🗑 Vider l'historique** dans l'en-tête de la fenêtre
2. Une confirmation `QMessageBox` apparaît : « Voulez-vous vraiment effacer tout l'historique des téléchargements ? »
3. Confirmez pour supprimer **toutes** les entrées de la base de données
4. La fenêtre se rafraîchit automatiquement (tableau vide)

### Effacement individuel

L'effacement individuel n'est **pas disponible** dans l'interface actuelle. Si vous devez supprimer une entrée spécifique, il faut :
- Soit effacer tout l'historique
- Soit modifier directement la base SQLite

---

## 💾 Quand l'historique est-il sauvegardé ?

Chaque téléchargement est automatiquement sauvegardé dans l'historique à la fin de son transfert via la méthode `_save_to_history(identifiant, statut)`.

### Déclencheurs

| Événement | Statut enregistré |
|-----------|-------------------|
| Téléchargement terminé avec succès | `'termine'` |
| Téléchargement échoué / annulé | `'echoue'` |

### Données sauvegardées

```python
telechargement_history.add_to_history(
    identifiant=identifiant,
    fichier=download["fichier"],
    utilisateur=download["user"],
    taille=download["taille"],
    taille_bytes=download["taille_bytes"],
    statut=statut,                     # 'termine' ou 'echoue'
    vitesse_moyenne=download["vitesse"],
    vitesse_bytes=float(download["vitesse_bytes"]),
)
```

---

## 🛠️ Dépannage

### L'historique est vide alors que j'ai téléchargé des fichiers

**Causes possibles :**
- Les téléchargements sont encore en cours (l'historique n'enregistre que les transferts terminés ou échoués)
- La base SQLite a été supprimée manuellement
- Le fichier `data/bot_telechargement_history.db` est corrompu

**Solution :** Terminez un téléchargement et vérifiez son apparition. Si le problème persiste, consultez les logs.

### Le filtre n'affiche aucun résultat

**Causes possibles :**
- Aucun téléchargement ne correspond au statut sélectionné
- La base de données n'est pas accessible

**Solution :** Basculez sur « Tous » pour vérifier la présence d'entrées.

### Je veux réinitialiser complètement l'historique

**Solution :**
1. Ouvrez l'historique via le bouton **📜 Historique**
2. Cliquez sur **🗑 Vider l'historique**
3. Confirmez la suppression

Vous pouvez aussi supprimer manuellement le fichier `data/bot_telechargement_history.db` (le schéma sera recréé automatiquement).

### Le tableau affiche « 500+ » entrées

**Cause :** La limite d'affichage est fixée à 500 entrées pour des raisons de performance Qt (`limit=500`).

**Solution :** Utilisez le filtre pour réduire le nombre d'entrées affichées (Terminé / Échoué), ou effacez les entrées les plus anciennes.

---

## 🔗 Voir aussi

- `/guide_bots/03-bot-telechargement` — Guide principal du bot Téléchargement
- `/faq/telechargement-lent` — Problèmes de vitesse de téléchargement
- `/tutoriels/optimiser-telechargements` — Optimisation des téléchargements
- `/technique/architecture-application` — Architecture générale de l'application
