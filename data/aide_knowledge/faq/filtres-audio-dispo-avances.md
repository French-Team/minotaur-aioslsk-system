---
title: Différence entre les filtres audio, dispo et avancés
category: faq
keywords:
  - difference filtre audio dispo avance
  - difference filtre audio dispo avance
  - difference filtre audio dispo avance
  - filtre audio
  - filtre dispo
  - filtre avance
  - filtre avancé
  - audio seulement
  - mode dispo
  - dispo
  - slots libres
  - disponible
  - filtres avances
  - filtres avancés
  - combinaison filtre
  - combinaison filtre
  - AND filtre
  - AND logique
  - _audio_filter_enabled
  - _mode_dispo_enabled
  - _filter_state
  - _row_matches_filters
  - filtrer disponible
  - trier disponible
  - slot libre
  - slot libre
  - slot
  - queue
  - file attente
---

❓ **Quelle est la différence entre les 3 types de filtres ?**

➡️ Le bot Recherche propose 3 mécanismes de filtrage indépendants qui se combinent en **logique AND** :

| Type | Déclencheur | État par défaut | Icône |
|---|---|---|---|
| 🔊 **Audio seulement** | Bouton toggle dans la barre d'outils | Activé | `🔊 Audio seulement` / `🔊 Tous les fichiers` |
| 🟢 **Mode dispo** | Bouton toggle dans la barre d'outils | Désactivé | `🔴 Mode dispo` |
| 🔍 **Filtres avancés** | Bouton "🔍 Filtres" → Modal dédiée | Aucun filtre | Badge `N` dans le bouton |

> **Règle d'or :** Les 3 filtres sont combinés en **ET (AND)** — un résultat doit satisfaire **tous** les filtres actifs pour être visible.

---

❓ **Comment fonctionne le filtre 🔊 Audio seulement ?**

➡️ C'est un **filtre binaire** (activé/désactivé) qui ne laisse passer que les formats audio courants.

**Fonctionnement technique :**

```python
EXTENSIONS_AUDIO = {".mp3", ".flac", ".ogg"}

def _is_audio(extension: str) -> bool:
    return extension.lower() in EXTENSIONS_AUDIO
```

**Ce qui passe :** `.mp3`, `.flac`, `.ogg`
**Ce qui est masqué :** `.opus`, `.wav`, `.aiff`, `.ape`, `.wma`, `.m4a`, `.dsf`, `.dff`, `.mp4`, `.zip`, `.pdf`, etc.

**Double niveau d'application :**

1. **À l'insertion** (dans `_on_search_result`) : si le filtre est activé, les fichiers non-audio ne sont même pas ajoutés au tableau — gain de mémoire
2. **Au filtrage** (dans `_apply_filters`) : même si des fichiers non-audio ont été ajoutés (par exemple avant l'activation du filtre), ils sont masqués par `setRowHidden`

**Changement de texte :**
- `🔊 Audio seulement` → quand le filtre est **actif**
- `🔊 Tous les fichiers` → quand le filtre est **désactivé**

> **💡 Important :** Par défaut, le filtre est **activé** (`_audio_filter_enabled = True`). Si vous ne voyez que des `.mp3`, `.flac` et `.ogg`, c'est normal — cliquez sur le bouton pour voir tous les fichiers.

---

❓ **Comment fonctionne le mode 🟢 Dispo ?**

➡️ Le mode dispo (disponibilité) filtre les résultats pour n'afficher que les utilisateurs qui ont des **slots de téléchargement libres**.

**Fonctionnement technique :** Le bouton `🔴 Mode dispo` est un toggle (désactivé par défaut, `_mode_dispo_enabled = False`). Quand il est activé, le code vérifie que l'attribut `has_free_slots` est `True` pour chaque résultat :

```python
if self._mode_dispo_enabled:
    if not data.get("has_free_slots", False):
        matches = False  # Masqué : pas de slot libre
```

**Ce qui passe :** Utilisateurs avec au moins 1 slot libre (indicateur 🟢 dans la colonne Slots)
**Ce qui est masqué :** Utilisateurs en file d'attente (indicateur 🔴 dans la colonne Slots)

**Utilité :**
- Évite de cliquer sur un téléchargement qui finira en file d'attente
- Priorise les sources immédiatement disponibles
- Particulièrement utile quand vous êtes pressé ou que vous cherchez des fichiers populaires

> **💡** Vous pouvez voir l'état des slots de chaque résultat dans la colonne **Slots** : 🟢 = libre, 🔴 = occupé. Le mode dispo est un raccourci pour ne montrer que les 🟢.

---

❓ **Comment fonctionnent les filtres avancés (🔍 Filtres) ?**

➡️ Les filtres avancés sont accessibles via le bouton **🔍 Filtres** qui ouvre une fenêtre modale (`FiltresRechercheModal`) proposant **7 critères** configurables :

| Groupe | Critère | Valeurs | Widget |
|---|---|---|---|
| **Qualité** | Bitrate minimum | 0–1000 kbps | Curseur + SpinBox synchronisés |
| **Durée** | Durée minimale | 0–3600 secondes | SpinBox |
| | Durée maximale | 0–7200 secondes | SpinBox |
| **Taille** | Taille minimale | 0–10 000 Mo | SpinBox |
| | Taille maximale | 0–10 000 Mo | SpinBox |
| **Source** | Nom d'utilisateur | Texte libre | Champ de saisie |
| | Slots libres uniquement | On/Off | Case à cocher |

**Logique d'évaluation :** Tous les critères sont en **AND** (ET). Si vous configurez bitrate ≥ 192 ET durée ≤ 300 s, un résultat doit satisfaire les DEUX conditions pour être visible.

**Ordre d'évaluation** (short-circuit) :
```
1. Bitrate min (int < int)       → le plus rapide
2. Durée min  (int < int)
3. Durée max  (int > int)
4. Taille min (int / division)
5. Taille max (int / division)
6. Utilisateur (contient, insensible à la casse) → le plus lent
7. Slots libres (bool + .get())
```

> **💡** Les critères sont évalués du plus rapide au plus lent. Si le bitrate est trop bas, les critères suivants ne sont même pas vérifiés (short-circuit).

---

❓ **Comment les 3 filtres sont-ils combinés entre eux ?**

➡️ Dans `_apply_filters()`, les 3 filtres sont appliqués en **séquence logique AND** :

```
_apply_filters()
    │
    ├─ has_filters ? → Non → tout afficher → FIN (optimisation : pas de boucle)
    │
    └─ Oui → Pour chaque ligne du tableau :
              │
              ├─ item existe ? → Non → masqué
              │
              ├─ data existe ? → Non → masqué
              │
              ├─ 🔊 Audio seulement activé ?
              │   └─ extension dans EXTENSIONS_AUDIO ? → Non → masqué
              │
              ├─ 🟢 Mode dispo activé ?
              │   └─ has_free_slots ? → Non → masqué
              │
              └─ 🔍 Filtres avancés actifs ?
                  └─ _row_matches_filters(data) ? → Non → masqué
                  │
                  └─ VISIBLE ✓
```

**Code réel :**

```python
matches = True

# 1. Filtre audio
if self._audio_filter_enabled:
    if not _is_audio(data.get("extension", "")):
        matches = False

# 2. Mode dispo
if matches and self._mode_dispo_enabled:
    if not data.get("has_free_slots", False):
        matches = False

# 3. Filtres avancés
if matches:
    matches = self._row_matches_filters(data)

self._table.setRowHidden(row, not matches)
```

> **Règle :** Si un filtre est désactivé, il n'est pas appliqué et laisse passer tous les résultats.

---

❓ **Quel filtre est appliqué en premier ?**

➡️ L'ordre d'application est toujours :

```
1. 🔊 Audio seulement   → le plus rapide (test d'extension)
2. 🟢 Mode dispo         → booléen has_free_slots
3. 🔍 Filtres avancés    → 7 critères ordonnés du plus rapide au plus lent
```

Cet ordre est optimisé pour le **short-circuit** : les filtres les plus rapides (audio, dispo) sont évalués en premier. Si un résultat échoue au filtre audio, les filtres suivants ne sont pas évalués.

---

❓ **Puis-je utiliser les 3 filtres en même temps ?**

➡️ **Oui, jusqu'à 9 critères simultanés** si vous les activez tous :

| Filtre | Critères activables |
|---|---|
| 🔊 Audio seulement | 1 (oui/non) |
| 🟢 Mode dispo | 1 (oui/non) |
| 🔍 Filtres avancés | 7 (bitrate, durée min, durée max, taille min, taille max, utilisateur, slots) |
| **Total** | **9 critères en AND** |

**Exemple concret — Recherche FLAC dispo :**

```
🔊 Audio seulement : ON    → seulement .flac (ou .mp3, .ogg)
🟢 Mode dispo : ON         → slots libres requis
🔍 Filtres : bitrate ≥ 800 → haute qualité uniquement

Résultat visible uniquement si :
  ✓ Extension = .flac (ou .mp3, .ogg)
  ✓ ET slots libres disponibles
  ✓ ET bitrate ≥ 800 kbps
```

> ⚠️ **Attention :** Plus vous ajoutez de critères, plus le risque d'avoir **0 résultat visible** est élevé. Si c'est le cas, désactivez les filtres un par un pour identifier lequel est trop restrictif.

---

❓ **Quel filtre est le plus performant ?**

➡️ Le **filtre audio** est le plus performant car il s'applique à **deux niveaux** :

1. **À l'insertion** : les fichiers non-audio ne sont pas ajoutés au tableau → **moins de lignes = moins de mémoire = filtrage plus rapide**
2. **Au re-filtrage** : simple test d'appartenance à un `set` Python (O(1))

| Filtre | Coût par ligne | Nombre d'opérations |
|---|---|---|
| 🔊 Audio seulement | O(1) — test `in set` | 1 lookup |
| 🟢 Mode dispo | O(1) — test booléen | 1 `.get()` |
| 🔍 Filtres avancés | O(k) — 7 critères max | Jusqu'à 7 tests |

---

❓ **Le badge « Filtres » prend-il en compte les 3 types ?**

➡️ **Oui.** Le badge affiché à côté du bouton 🔍 Filtres est calculé ainsi :

```python
has_filters = (self._filtres_compte > 0       # filtres avancés actifs
               or not self._audio_filter_enabled  # audio DÉSACTIVÉ (état non défaut)
               or self._mode_dispo_enabled)       # dispo activé
```

| Situation | Badge visible ? | Pourquoi |
|---|---|---|
| 🔊 Audio ON, 🟢 Dispo OFF, aucun avancé | ❌ Non | État par défaut |
| 🔊 Audio OFF, 🟢 Dispo OFF, aucun avancé | ✅ Oui (1) | Audio désactivé = état non défaut |
| 🔊 Audio ON, 🟢 Dispo ON, aucun avancé | ✅ Oui (1) | Mode dispo activé |
| 🔊 Audio OFF, 🟢 Dispo ON, aucun avancé | ✅ Oui (2) | Audio OFF + Dispo ON |
| 🔊 Audio ON, 🟢 Dispo OFF, 2 avancés | ✅ Oui (2) | 2 filtres avancés configurés |
| Tous actifs | ✅ Oui (N) | Tous les états non-défaut |

> **💡** Si le badge indique `1` alors que vous n'avez rien configuré dans la modal, vérifiez que le toggle **🔊 Audio seulement** est bien allumé — s'il est éteint, il compte comme 1 filtre actif.

---

❓ **Comment désactiver tous les filtres d'un coup ?**

➡️ Il n'y a pas de bouton "Réinitialiser tout". Pour revenir à l'affichage complet :

1. **🔊 Audio seulement** : Cliquez pour qu'il soit **allumé** (état par défaut = `🔊 Audio seulement`)
2. **🟢 Mode dispo** : Cliquez pour qu'il soit **éteint** (`🔴 Mode dispo`, pas de check)
3. 🔍 **Filtres avancés** : Ouvrez la modal et remettez tous les champs à leurs valeurs par défaut (0, vide, décoché)

Ou plus simple : **relancez une nouvelle recherche** dans un mode différent (cliquez sur une suggestion globale dans l'historique) pour repartir d'un état vierge.

---

❓ **Puis-je sauvegarder mes configurations de filtres ?**

➡️ Les **filtres avancés** sont conservés en mémoire (`_filter_state`) tant que vous ne fermez pas l'application — ils survivent entre les ouvertures de la modal.

Les **toggles** (audio, dispo) ne sont pas persistés entre les sessions. À chaque ouverture :
- 🔊 Audio seulement = **activé** (par défaut)
- 🟢 Mode dispo = **désactivé** (par défaut)
- 🔍 Filtres avancés = **réinitialisés** (pas de persistance dans un fichier)

> **💡** Si vous utilisez souvent la même combinaison de filtres, notez-la quelque part. Il n'y a pas encore de système de profils de filtres sauvegardés.

---

❓ **Guide de choix rapide**

➡️ Quelle combinaison utiliser selon votre objectif :

| Objectif | Audio | Dispo | Avancés | Résultat attendu |
|---|---|---|---|---|
| Explorer tout le réseau | OFF | OFF | Aucun | Maximum de résultats |
| Trouver de la musique rapidement | ON | ON | Aucun | .mp3/.flac/.ogg avec slots libres |
| Télécharger un album en haute qualité | ON | OFF | Bitrate ≥ 256 | Fichiers audio de bonne qualité |
| Trouver un fichier rare précis | ON | ON | Bitrate ≥ 192 + Utilisateur | Ciblé, disponible, bonne qualité |
| Analyser la bibliothèque d'un utilisateur | ON | OFF | Aucun | Tous les fichiers audio d'un user |
| Chasser les FLAC | ON | ON | Bitrate ≥ 900 | FLAC haute qualité, dispo |
| Recherche large sans bruit | OFF | ON | Taille ≤ 100 Mo | Tous types, dispo, légers |

---

**Voir aussi :**
- [/guide_bots/13-filtres-format-recherche](/guide_bots/13-filtres-format-recherche) — Guide des filtres de format (audio seulement)
- [/technique/architecture-filtres](/technique/architecture-filtres) — Architecture détaillée du système de filtres
- [/faq/performances-limitations-filtres](/faq/performances-limitations-filtres) — Performances et limitations des filtres
- [/guide_bots/02-bot-recherche](/guide_bots/02-bot-recherche) — Guide complet du bot Recherche
