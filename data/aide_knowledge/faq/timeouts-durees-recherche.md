---
title: "Timeouts et durées dans le bot Recherche"
category: "faq"
icon: "⏱️"
keywords:
  - timeout recherche soulseek
  - duree recherche soulseek
  - durée recherche soulseek
  - timer 30 secondes recherche
  - 30 secondes timeout recherche
  - MAX_RESULTS 200
  - FIFO recherche soulseek
  - limite 200 resultats recherche
  - arret automatique recherche
  - arrêt automatique recherche
  - recherche arriere plan soulseek
  - temps limite recherche soulseek
  - duree maximale recherche
  - recherche continue timeout
  - arreter recherche automatique
  - resultats limites 200
  - résultats limites 200
  - anciens resultats supprimes
  - anciens résultats supprimés
  - FIFO file d attente resultats
  - premier entre premier sorti recherche
  - saturation memoire recherche
  - saturation mémoire recherche
  - performance MAX_RESULTS
  - timer 30000ms
  - QTimer singleShot recherche
  - bouton stop recherche
  - recherche arretée utilisateur
  - arriere plan soulseek recherche
  - timer 30 secondes
  - timeout 30s
  - 30 secondes
  - limite resultats
  - 200 resultats
  - fifo
  - duree recherche
  - temps recherche
  - arret timer
  - recherche timeout
---


# ⏱️ Timeouts et durées dans le bot Recherche

Cette FAQ détaille les mécanismes de **limitation temporelle** et de **gestion du volume** de résultats dans le bot Recherche : le timer de 30 secondes, la limite de 200 résultats (FIFO), et l'arrêt manuel.

---

## ⏲️ Y a-t-il un timeout sur la recherche ?

**Oui.** Une recherche déclenche un timer interne de **30 secondes** (30 000 ms).

### Fonctionnement

1. Au lancement de la recherche (`_on_search`), un `QTimer` est créé :
   - `setSingleShot(True)` — il ne se déclenche qu'une seule fois
   - `timeout.connect(self._on_search_timeout)` — relié à la méthode de timeout
   - `start(30000)` — 30 secondes
2. Pendant ces 30 secondes, les résultats sont collectés et affichés en temps réel
3. Passé ce délai, la méthode `_on_search_timeout()` est appelée

### Que se passe-t-il après le timeout ?

Le timeout **n'arrête pas la recherche réseau**. Le message suivant s'affiche :

```
⏱️ La recherche continue en arrière-plan…
```

L'interface se réinitialise partiellement :
- Le bouton **⏹ Arrêter** est masqué
- Le bouton **🔍 Rechercher** redevient visible et actif
- Le statut passe en mode « arrière-plan »

**Ce que ça signifie :** Le bot continue d'écouter les résultats provenant du serveur Soulseek, mais le timer de 30s était là pour garantir qu'une nouvelle recherche puisse être lancée sans attendre la fin de la précédente. Les résultats reçus après le timeout continuent de s'afficher dans le tableau (dans la limite de `MAX_RESULTS`).

### Puis-je modifier la durée du timeout ?

Oui, dans le code source (`src/gui/widgets/bots/bot_recherche.py`) :
```python
self._search_timer.start(30000)  # 30 000 ms = 30 secondes
```
Modifiez la valeur (en millisecondes) et redémarrez le bot. Une valeur plus courte libère l'interface plus vite, une valeur plus longue collecte plus de résultats avant le timeout.

---

## 📊 Quelle est la limite de résultats affichés ?

Le bot Recherche est limité à **200 résultats maximum** affichés simultanément dans le tableau.

```python
MAX_RESULTS = 200
# « Nombre maximum de lignes affichées simultanément (FIFO). »
```

### Pourquoi 200 ?

- **Performance Qt :** Au-delà de 200 lignes, le `QTableWidget` commence à ralentir l'interface (scroll, rafraîchissement, tri)
- **Lisibilité :** L'utilisateur peut difficilement parcourir plus de 200 résultats efficacement
- **Mémoire :** Chaque ligne contient des données structurées (nom, taille, bitrate, durée, utilisateur, etc.)

### Puis-je augmenter cette limite ?

Techniquement oui — modifiez `MAX_RESULTS` dans `src/gui/widgets/bots/bot_recherche.py`. Cependant, c'est **déconseillé** car :
- L'interface peut devenir lente ou instable
- Le scroll peut devenir saccadé
- Le tri des colonnes peut prendre plusieurs secondes

**Alternative recommandée :** Affinez votre recherche plutôt que d'augmenter la limite. Utilisez les filtres audio (MP3/FLAC/OGG) et les paramètres avancés (bitrate minimum, taille, durée) pour réduire le nombre de résultats.

---

## 🔄 Comment fonctionne le FIFO ?

Quand le tableau atteint **200 lignes**, chaque nouveau résultat provoque la **suppression du résultat le plus ancien** (First-In, First-Out).

### Implémentation

Dans `_add_result_row()` :
```python
if row >= MAX_RESULTS:
    self._table.removeRow(0)  # Supprime la ligne la plus ancienne
# Puis insère la nouvelle ligne à la fin
row = self._table.rowCount()
self._table.insertRow(row)
```

### Conséquences

- Les **résultats les plus récents** remplacent les plus anciens
- Si la recherche produit plus de 200 résultats, seuls les **200 derniers reçus** sont visibles
- Les résultats supprimés sont **perdus** (pas de pagination possible)
- Le compteur du statut continue d'augmenter au-delà de 200, mais le tableau n'en affiche que 200 max

### Exemple

| Étape | Résultats reçus | Lignes affichées | Anciennes supprimées |
|-------|-----------------|-------------------|----------------------|
| Début | 0 | 0 | — |
| +50 | 50 | 50 | 0 |
| +100 | 150 | 150 | 0 |
| +60 | 210 | 200 | 10 les plus vieilles |
| +30 | 240 | 200 | 30 les plus vieilles |

---

## ⏹️ Puis-je arrêter la recherche manuellement ?

**Oui.** Cliquez sur le bouton **⏹ Arrêter** (visible uniquement pendant une recherche active).

### Ce qui se passe

1. `_on_stop()` est appelée
2. Le timer est arrêté (`self._search_timer.stop()`)
3. La requête réseau est annulée via `self._connexion_manager.stop_search()`
4. L'état de recherche est réinitialisé (`_reset_search_state()`)
5. Le statut affiche : `⏹ Recherche arrêtée — {n} résultat(s) affiché(s)`
6. Un événement `EventBus` est émis pour informer le système

### Différence avec le timeout

| Mécanisme | Timer 30s | Arrêt manuel |
|-----------|-----------|--------------|
| **Réseau** | Continue (arrière-plan) | Arrêté |
| **Statut** | ⏱️ Continue en arrière-plan | ⏹ Arrêtée |
| **Timer** | Déclenché automatiquement | Stoppé |
| **Nouveaux résultats** | Encore affichés (dans limite) | Plus aucun |

---

## 🧮 Comment le compteur de résultats est-il mis à jour ?

Le compteur `_result_count` est incrémenté à chaque réception de résultats (`_on_search_result`).

### Messages de statut

| Situation | Message affiché |
|-----------|----------------|
| Résultats normaux | `✅ {n} résultat(s)` |
| Seuil `MAX_RESULTS` atteint | `⚠️ 200 résultats max — affinez votre recherche` (ou `#{salon}` / `@{utilisateur}`) |
| Timeout 30s | `⏱️ La recherche continue en arrière-plan…` |
| Arrêt utilisateur | `⏹ Recherche arrêtée — {n} résultat(s) affiché(s)` |
| Aucun résultat | Dépend du contexte (voir FAQ `recherche-sans-resultat`) |

### Le compteur s'arrête-t-il à 200 ?

**Non.** Le compteur `_result_count` continue d'augmenter au-delà de 200 pour que l'utilisateur sache combien de résultats totaux ont été reçus. Seul le tableau d'affichage est limité à 200 lignes via le FIFO.

---

## 🔗 Voir aussi

- `/faq/performances-limitations-filtres` — Performances et limitations générales
- `/faq/recherche-sans-resultat` — Aucun résultat trouvé
- `/guide_bots/02-bot-recherche` — Guide principal du bot Recherche
- `/technique/mecanismes-threading-recherche` — Architecture threading et QTimer
- `/technique/cache-performance-recherche` — Cache et performance
