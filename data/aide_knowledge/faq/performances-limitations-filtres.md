---
title: Performances et limitations des filtres de recherche
category: faq
keywords:
  - performance filtre
  - limite resultat
  - 200 resultats
  - max results
  - filtre combine
  - filtre combiné
  - AND filtre
  - fifo
  - limite
  - limite fichier
  - timeout
  - trop de resultat
  - résultats cachés
  - cache
  - lenteur
  - lent
  - ralenti
  - setRowHidden
  - removeRow
  - result_count
  - visible_count
  - performance
  - filtrage
---

❓ **Pourquoi y a-t-il une limite de 200 résultats ?**

➡️ La limite de 200 résultats (`MAX_RESULTS = 200`) est une protection contre la saturation mémoire et le ralentissement de l'interface. Sans cette limite, une recherche large (ex : "radiohead" ou "*") pourrait retourner des milliers de fichiers, ce qui ferait ramer l'application à chaque mise à jour du tableau (tri, filtrage, défilement).

| Sans limite | Avec limite 200 |
|---|---|
| 5 000+ lignes en mémoire | Maximum 200 lignes |
| Tri lent sur toutes les lignes | Tri rapide |
| `setRowHidden` parcourt 5 000 lignes | `setRowHidden` parcourt 200 lignes |
| Défilement saccadé | Défilement fluide |
| Consommation mémoire élevée | Consommation maîtrisée |

➡️ Si vous atteignez cette limite, **affinez votre recherche** : utilisez des mots-clés plus précis, activez le filtre audio, ou ajoutez des critères avancés (bitrate minimum, taille, nom d'utilisateur).

---

❓ **Que se passe-t-il quand j'atteins 200 résultats ?**

➡️ Un message d'avertissement s'affiche dans le statut :
`⚠️ 200 résultats max — affinez votre recherche`

Le comportement est **FIFO (First-In, First-Out)** : chaque nouveau résultat supprime le plus ancien pour rester à 200 lignes.

```
État initial :   [R1] [R2] [R3] ... [R200]  ← 200 résultats
Nouveau résultat : [R201] arrive
                   ↓ removeRow(0)
État final :     [R2] [R3] [R4] ... [R201]  ← toujours 200
```

✅ Les **résultats visibles sont mis à jour** immédiatement : les nouveaux résultats correspondent à la recherche en cours, pas aux anciens.

✅ Les **filtres sont réappliqués** après chaque ajout batch — le tri et le filtrage tiennent compte des toutes dernières données.

> **💡 Conseil :** Si vous voyez souvent ce message, c'est que votre recherche est trop large. Ajoutez un filtre bitrate (> 192 kbps), un nom d'utilisateur, ou utilisez le toggle **🔊 Audio seulement**.

---

❓ **Puis-je augmenter la limite de 200 résultats ?**

➡️ **Oui, dans le code** — mais ce n'est pas recommandé. La constante `MAX_RESULTS = 200` est définie à la ligne 54 de `src/gui/widgets/bots/bot_recherche.py`.

```python
MAX_RESULTS = 200  # ← vous pouvez augmenter cette valeur
```

**Risques si vous augmentez la limite :**

| Nouvelle limite | Risque |
|---|---|
| 500 | Ralentissement notable sur les tris |
| 1 000 | Interface peut devenir peu réactive |
| 5 000 | Risque de freeze sur les recherches larges |
| 10 000+ | Crash probable par saturation mémoire |

> **⚠️ À savoir :** Même avec 200 résultats, les données sont stockées **dans le tableau Qt** (widget mémoire). Chaque résultat peut peser ~1-2 Ko (nom, extension, bitrate, durée, etc.). 200 résultats = ~400 Ko, ce qui est négligeable. À 5 000 résultats, on monte à ~10 Mo juste pour le tableau.

Si vous avez besoin de plus de résultats, **préférez la fonctionnalité de téléchargement** : téléchargez plusieurs fichiers depuis différentes sources plutôt que d'augmenter la limite.

---

❓ **Comment les filtres sont-ils combinés entre eux ?**

➡️ Les filtres sont combinés en **logique AND** : tous les critères actifs doivent être satisfaits pour qu'un résultat soit affiché.

```
Filtres actifs :
  [🔊 Audio seulement]  ET  [🟢 Dispo]  ET  [Bitrate ≥ 192]

Un résultat est visible UNIQUEMENT si :
  ✓ Extension dans {.mp3, .flac, .ogg}
  ✓ ET slots libres disponibles
  ✓ ET bitrate ≥ 192 kbps
```

**Ordre d'évaluation** (short-circuit — s'arrête au premier échec) :

1. ✅ **Élément valide** (vérification rapide : `COL_FICHIER` non nul, données `UserRole+1` non nulles)
2. 🔊 **Filtre audio** — `_is_audio(extension)` le plus rapide
3. 🟢 **Mode disponibilité** — `has_free_slots` booléen rapide
4. 🔍 **Filtres avancés** — `_row_matches_filters(data)` :
   - Bitrate minimum
   - Durée minimum
   - Durée maximum
   - Taille minimum
   - Taille maximum
   - Nom d'utilisateur (insensible à la casse)
   - Slots libres uniquement

> **💡 Performance :** Le short-circuit fait que les filtres les plus rapides (audio, dispo) sont évalués en premier. Si un fichier n'est pas audio, il est rejeté immédiatement sans vérifier le bitrate, la durée, etc.

---

❓ **Les filtres ralentissent-ils l'interface ?**

➡️ **Non** — l'implémentation est optimisée pour rester fluide même avec 200 lignes filtrées :

| Technique | Impact |
|---|---|
| `setSortingEnabled(False)` pendant l'insertion | Évite de re-trier à chaque ligne insérée (batch) |
| `setSortingEnabled(True)` après l'insertion | Tri unique à la fin du batch |
| `setRowHidden()` au lieu de `removeRow()` | Préserve les indices de ligne, pas de réallocation |
| Short-circuit dans `_row_matches_filters` | S'arrête dès qu'un critère échoue |
| `column_count` mis en cache | Évite d'appeler `columnCount()` à chaque itération |
| `row_data` stocké via `Qt.UserRole + 1` | Pas de parsing additionnel pendant le filtrage |

**Temps mesuré (estimation) :**
- Parcours + filtrage de 200 lignes : **< 1 ms**
- Réaffichage (setRowHidden x200) : **~2-5 ms**
- Tri (après réactivation) : **~1-3 ms**

→ **Total : ~5-10 ms**, imperceptible pour l'utilisateur.

---

❓ **Pourquoi certains résultats sont masqués même si je n'ai pas de filtre ?**

➡️ Vérifiez trois choses :

1. **🔊 Audio seulement** : le toggle est activé par défaut (`_audio_filter_enabled = True`). Seuls les formats `.mp3`, `.flac`, `.ogg` passent. Cliquez pour passer à **🔊 Tous les fichiers**.

2. **🟢 Mode dispo** : si activé, seuls les utilisateurs avec slots libres sont affichés. Désactivez-le pour voir tous les résultats.

3. **Filtres avancés** : le badge « Filtres » en haut à droite indique le nombre de filtres actifs. Si le badge est visible, des critères sont appliqués (bitrate, durée, taille, utilisateur, slots).

```
Cas : Je ne vois que des .mp3, .flac, .ogg
→ Cause : 🔊 Audio seulement est activé (par défaut)
→ Solution : Cliquez sur le bouton pour passer en mode tous fichiers
```

---

❓ **Que signifie le compteur visible_count / total ?**

➡️ Quand des filtres sont actifs, le statut affiche `✅ 15/200 résultats`.

| Nombre | Signification |
|---|---|
| **15** | Lignes visibles après application des filtres (`visible_count`) |
| **200** | Total des lignes dans le tableau (avant filtrage) |

Si aucun filtre n'est actif, le statut affiche uniquement le total : `✅ 200 résultats`.

> **💡 Exemple :** `✅ 3/200 résultats` avec le filtre audio activé → seulement 3 fichiers sur 200 sont au format .mp3, .flac ou .ogg. Les 197 autres (`.wav`, `.ape`, `.dsf`, `.opus`, etc.) sont masqués.

---

❓ **Puis-je avoir des faux positifs avec les filtres combinés ?**

➡️ **Non** — la logique est conservative. Un résultat est affiché **uniquement** si tous les critères sont vérifiés. Il n'y a pas de mode OR entre les filtres.

```
Filtres : [Bitrate ≥ 192] ET [Taille ≤ 50 Mo]

Résultat A : bitrate=256, taille=45 Mo  → ✅ VISIBLE  (les deux OK)
Résultat B : bitrate=128, taille=45 Mo  → ❌ CACHÉ   (bitrate trop bas)
Résultat C : bitrate=320, taille=80 Mo  → ❌ CACHÉ   (trop volumineux)
Résultat D : bitrate=128, taille=80 Mo  → ❌ CACHÉ   (les deux échouent)
```

> **💡** Si vous cherchez des fichiers qui ont **soit** un bitrate élevé **soit** une petite taille, il faudrait lancer deux recherches séparées avec des critères différents.

---

❓ **Combien de filtres puis-je activer en même temps ?**

➡️ **Jusqu'à 7 critères** peuvent être combinés simultanément :

| # | Filtre | Valeurs possibles |
|---|---|---|
| 1 | 🔊 Audio seulement | On/Off |
| 2 | 🟢 Mode disponibilité | On/Off |
| 3 | Bitrate minimum | 0–1000 kbps (curseur + spinbox synchronisés) |
| 4 | Durée min/max | mm:ss à mm:ss |
| 5 | Taille min/max | 0–9999 Mo |
| 6 | Nom d'utilisateur | Texte libre (recherche insensible à la casse) |
| 7 | Slots libres uniquement | On/Off |

Avec les 7 activés, les chances de trouver un résultat sont faibles — mais le filtrage reste rapide (< 10 ms) grâce au short-circuit.

> **⚠️ Attention :** Plus vous ajoutez de filtres, plus vous risquez de vous retrouver avec 0 résultat visible. Commencez par 2-3 critères et ajoutez-en progressivement.

---

❓ **Les filtres s'appliquent-ils aux nouveaux résultats qui arrivent ?**

➡️ **Oui** — `_apply_filters()` est appelée automatiquement après chaque insertion batch de résultats. Même si vous changez un filtre en cours de réception des résultats, l'interface se met à jour immédiatement.

**Cycle de vie d'un résultat :**

```
Résultat reçu → _add_result_row() → insertion dans le tableau
                                    ↓
Nouveau batch complet → setSortingEnabled(False)
                      → _apply_filters() → setRowHidden(ligne, True/False)
                      → setSortingEnabled(True)
                      → Mise à jour du statut : ✅ visible_count/total
```

> **💡** Si vous activez le filtre audio pendant que les résultats arrivent, les fichiers déjà affichés qui ne sont pas `.mp3/.flac/.ogg` seront masqués immédiatement. Les nouveaux résultats seront filtrés à leur arrivée.

---

❓ **Pourquoi le badge « Filtres » indique 1 alors que je n'ai rien configuré ?**

➡️ Le badge `has_filters` compte trois sources :

```
has_filters = (filtres_avancés > 0) OU (audio désactivé) OU (mode dispo activé)
```

| Situation | Compteur badge |
|---|---|
| 🔊 Audio seulement activé + rien d'autre | 0 (état par défaut, pas compté) |
| 🔊 Audio seulement **désactivé** | 1 (état non défaut) |
| 🟢 Mode dispo activé | 1 |
| Filtre avancé configuré | 1+ |
| Audio désactivé + mode dispo | 2 |

➡️ Si le badge indique 1 mais que vous n'avez rien touché, vérifiez que le bouton **🔊 Audio seulement** est bien allumé. S'il est éteint (mode "Tous les fichiers"), cela compte comme 1 filtre actif.

---

❓ **Puis-je filtrer par type de fichier au-delà de mp3/flac/ogg ?**

➡️ **Directement via le toggle audio** — non, seuls `.mp3`, `.flac`, `.ogg` sont reconnus par le filtre audio automatique (voir `EXTENSIONS_AUDIO` dans le code). Les formats comme `.opus`, `.wav`, `.ape` ou `.dsf` ne sont pas filtrés par ce toggle.

➡️ **Via les filtres avancés** (bouton « 🔍 Filtres » dans la barre d'outils), vous pouvez filtrer par :

- **Taille** : fichier ≤ X Mo
- **Bitrate** : ≥ X kbps (utile pour éviter les fichiers de basse qualité)
- **Durée** : entre X min et Y min
- **Utilisateur** : résultats d'un utilisateur spécifique
- **Slots libres** : uniquement les sources disponibles

> **💡 Astuce indirecte :** Pour ne voir que les fichiers `.flac`, utilisez le toggle **🔊 Audio seulement** (qui garde `.mp3`, `.flac`, `.ogg`) puis triez par la colonne **Extension** pour regrouper les FLAC en tête. Pour un filtrage strict par une extension spécifique (`.opus`, `.wav`), il faudrait étendre `EXTENSIONS_AUDIO` dans le code.

---

❓ **Que faire si les filtres sont trop lents ?**

➡️ Normalement, les filtres sont instantanés (< 10 ms). Si vous ressentez une lenteur :

1. **Vérifiez que vous n'êtes pas à 200 résultats** — la limite est atteinte, affinez votre recherche
2. **Désactivez le tri** en cliquant sur un en-tête de colonne déjà trié (alterne l'ordre ou désactive)
3. **Évitez d'activer les 7 filtres** en même temps — utilisez 2-3 critères bien choisis
4. **Redémarrez le bot Recherche** — un bug d'affichage peut parfois persister

> **🔧 Diagnostic :** Ouvrez la console de développement (F12 dans l'interface Qt) et vérifiez qu'il n'y a pas d'erreurs Python dans la boucle d'événements.

---

**Voir aussi :**
- [/technique/architecture-filtres](/technique/architecture-filtres) — Architecture détaillée du système de filtres
- [/guide_bots/13-filtres-format-recherche](/guide_bots/13-filtres-format-recherche) — Guide d'utilisation des filtres de format
- [/faq/recherche-sans-resultat](/faq/recherche-sans-resultat) — Causes et solutions quand la recherche ne donne rien
