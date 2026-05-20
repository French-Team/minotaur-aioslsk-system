---
title: "Popup d'historique (HistoryPopup) du bot Recherche"
category: "guide_bots"
icon: "📜"
keywords:
  - history popup historique
  - popup historique recherche
  - HistoryPopup
  - historique recherche soulseek
  - popup historique recherche
  - historique recherches recentes
  - fenetre historique recherche
  - fenêtre historique recherche
  - modal historique recherche
  - bouton historique recherche
  - icone historique recherche
  - supprimer entree historique
  - effacer historique recherche
  - vue historique recherche
  - naviguer historique recherche
  - restaurer recherche historique
  - troncature historique
  - 42 caracteres historique
  - history popup bot recherche
  - popup historique bot
  - HistoryPopup QDialog
  - fenetre modale historique
  - historique efface
  - tout effacer historique
  - HistoryEntryRow
  - horodatage historique
  - date recherche historique
  - icone salon historique
  - icone utilisateur historique
  - icone globale historique
  - bouton fermer historique
  - scroll historique
  - liste historique recherche
  - historique vide
  - historique complet
  - historique supprime
  - popup historique modal
  - selection historique recherche
  - clic historique recherche
  - cliqué historique recherche
  - historique personnalise
  - historique personnalisé
  - historique supprimer
  - historique supprimé
  - historique effacer tout
  - historique restaurer
  - historique navigation
  - historique salon
  - historique utilisateur
  - historique global
---

# 📜 Popup d'historique (HistoryPopup)

La **popup d'historique** est une fenêtre modale qui affiche l'intégralité des recherches précédentes stockées dans `SearchHistory`. Elle permet de consulter, restaurer ou supprimer des entrées de l'historique.

---

## 📖 Description

`HistoryPopup` est une classe dérivée de `QDialog` qui présente une **vue scrollable** de toutes les entrées d'historique enregistrées. Chaque entrée affiche :

- L'**icône** correspondant au type de recherche
- La **requête** tronquée
- Des **informations supplémentaires** (nom du salon/de l'utilisateur, nombre de résultats, date)
- Un **bouton de suppression** individuelle (`✕`)

Un **bouton « Tout effacer »** permet de vider l'intégralité de l'historique.

---

## 🚀 Accès à la popup

La popup est accessible via le bouton **📜 Historique** situé dans la barre de recherche du bot Recherche.

**Bouton 📜 Historique :**
- Texte : `📜 Historique`
- Style : fond transparent, bordure fine, coins arrondis (`border-radius: 10px`), police 10px gras
- Survol : bordure et texte passent à la couleur principale (`COLORS["PRIMARY"]`)
- Curseur : main (`PointingHandCursor`)

Au clic, la méthode `_open_history_popup()` est appelée.

---

## 🖼️ Interface de la popup

### Titre
```
📜 Historique ({n} recherche(s))
```
Le compteur est **mis à jour dynamiquement** lors de l'ajout ou de la suppression d'entrées.

### Liste scrollable
- **Zone** : `QScrollArea` sans bordure, fond transparent
- **Contenu** : layout vertical (`QVBoxLayout`) contenant les lignes d'entrées
- **Haut** : les entrées les plus récentes

### Chaque entrée (HistoryEntryRow)

Une ligne se compose de deux boutons dans un layout horizontal (`QHBoxLayout`) :

#### Bouton principal (clic → restaurer la recherche)
Format du texte :
```
{icône}  {requête tronquée}{info supplémentaire}
```

| Type      | Icône | Info supplémentaire                     |
|-----------|-------|----------------------------------------|
| `room`    | 💬   | ` #{nom_du_salon}`                     |
| `user`    | 👤   | ` {nom_utilisateur}`                   |
| `global`  | 🌐   | *(aucun)*                              |

Caractéristiques :
- **Requête** : tronquée à **42 caractères** avec `…` si nécessaire
- **Résultats** : si `count > 0`, ajout de ` — {n} résultat(s)`
- **Date** : si un horodatage est présent, affichage de ` ({date})`
- **Style** : fond `BG_SURFACE`, texte `TEXT_PRIMARY`, bordure `BORDER` avec coins `6px`, padding `8px 12px`, aligné à gauche
- **Survol** : fond légèrement teinté, bordure couleur principale
- **Curseur** : main (`PointingHandCursor`)

#### Bouton suppression (`✕`)
- Permet de supprimer **cette entrée uniquement** de l'historique
- Appelle directement `SearchHistory.remove()` et **rafraîchit la popup** sans la fermer

### Bouton « Tout effacer »
- Situé en bas de la popup
- Style distinctif (couleur danger)
- Connecté à `_on_clear()` → émet le signal `clear_requested`
- **Ferme la popup** et vide tout l'historique

### Bouton « Fermer »
- Simple fermeture de la popup sans action (`self.reject()`)

---

## ⚙️ Fonctionnement détaillé

### Ouverture (`_open_history_popup`)

1. **Récupération des données** : `self._search_history.get_all()` renvoie toutes les entrées depuis `SearchHistory`
2. **Création du dialogue** : `HistoryPopup(entries=self._search_history.get_all(), parent=self, history=self._search_history)`
3. **Connexion des signaux** :
   - `dialog.clear_requested` → `self._on_history_clear` (vide l'historique et rafraîchit les suggestions)
   - `dialog.entries_changed` → `self._rebuild_suggestions` (met à jour la barre de suggestions)
4. **Affichage modal** : `dialog.exec()` bloque l'interaction avec le reste du bot
5. **Restauration** : si `dialog.exec()` retourne `True`, `dialog.selected_entry` est passé à `_on_suggestion_clicked()` qui restaure le contexte (salon, utilisateur, ou global)

### Effacement complet (`_on_history_clear`)
```python
self._search_history.clear()
self._rebuild_suggestions()
self._status_label.setText("🗑 Historique effacé")
```

### Suppression individuelle (`_on_remove_entry`)
```python
self._history.remove(entry)       # Supprime de SearchHistory
self._entries.remove(entry)        # Met à jour la liste locale
self.entries_changed.emit()        # Notifie le parent
self._rebuild_entries_ui()         # Rafraîchit la popup
```

### Reconstruction de l'UI (`_rebuild_entries_ui`)
```python
# 1. Supprime tous les widgets du layout
# 2. Met à jour le titre avec le nouveau compteur
# 3. Si liste vide : affiche "Aucune recherche pour l'instant."
# 4. Sinon : appelle _build_entry_rows() + addStretch(1)
```

---

## 🔄 Parcours utilisateur typique

1. L'utilisateur clique sur **📜 Historique**
2. La popup modale s'ouvre avec la liste complète des recherches
3. L'utilisateur peut :
   - **Cliquer sur une entrée** → restaure la recherche (contexte salon, utilisateur ou global) et ferme la popup
   - **Cliquer sur `✕`** sur une entrée → supprime cette entrée, la popup reste ouverte
   - **Cliquer sur « Tout effacer »** → vide tout l'historique, ferme la popup
   - **Cliquer sur « Fermer »** → ferme sans action
4. Si une entrée est restaurée :
   - La recherche est lancée automatiquement
   - Le contexte s'affiche (bannière 💬 salon, 👤 navigation, ou 🌐 global)
   - Les suggestions d'historique se mettent à jour

---

## 🛠️ Dépannage

### La popup ne s'ouvre pas
**Causes possibles :**
- Le bot Recherche n'est pas initialisé (`_search_history` est `None`)
- Problème de connexion du signal du bouton

**Solution :** Vérifiez que la méthode `setup()` du bot a bien été appelée. Redémarrez le bot si nécessaire.

### Une entrée ne s'affiche pas dans la popup
**Causes possibles :**
- `MAX_HISTORY = 20` : les entrées les plus anciennes ont été purgées
- L'entrée n'a jamais été enregistrée (recherche annulée avant réception ?)

**Solution :** La popup affiche tout l'historique via `get_all()`. Si une recherche récente manque, refaites-la pour qu'elle soit enregistrée.

### Le clic sur une entrée ne restaure rien
**Causes possibles :**
- Le fichier `data/bot_recherche_history.json` est corrompu
- La connexion Soulseek n'est pas active
- `_on_suggestion_clicked()` ne parvient pas à charger le contexte

**Solutions :**
1. Vérifiez votre connexion Soulseek
2. Effacez l'historique via « Tout effacer » et réessayez
3. Consultez les logs pour détecter d'éventuelles erreurs

### Le compteur de résultats ne s'affiche pas
**Causes possibles :**
- La recherche n'a retourné aucun résultat (`count = 0`)
- L'entrée a été enregistrée avant l'ajout de la fonctionnalité de comptage

**Solution :** Le compteur s'affiche uniquement si `count > 0`. C'est un comportement normal.

### « Tout effacer » ne fonctionne pas
**Causes possibles :**
- Le signal `clear_requested` n'est pas connecté à `_on_history_clear`
- `SearchHistory.clear()` échoue (fichier verrouillé ?)

**Solution :** Vérifiez les logs pour des erreurs d'écriture. Redémarrez le bot et réessayez.

---

## 🔗 Voir aussi

- `/guide_bots/02-bot-recherche` — Guide principal du bot Recherche
- `/faq/suggestions-historique-recherche` — FAQ sur le système de suggestions d'historique
- `/technique/cache-performance-recherche` — Article technique sur le cache et les performances
