---
title: "Événements manquants — Pourquoi certains événements ne s'affichent pas dans le Surveillance ?"
category: faq
keywords: ["evenement", "événement", "surveillance", "manquant", "absent", "afficher", "emission", "emitter", "catégorie", "categorie", "filtre", "pause", "purge", "retention", "rétention", "visible"]
---

# Événements manquants — Pourquoi certains événements ne s'affichent pas ?

> **Niveau :** Intermédiaire  
> **Catégorie :** Dépannage — EventBus

---

## Questions fréquentes

### ❓ Je ne vois pas un événement qui devrait être là

Plusieurs raisons possibles :

### 1. L'EventBus est en pause 🔇

Si vous avez mis l'EventBus en pause (via `pause()`), **aucun événement n'est émis ni persisté**. Vérifiez l'état :

```
┌─ Statut EventBus ───────────────────────────────────┐
│  ● Actif   |   ○ En pause                            │
│                                                      │
│  Dernier événement : il y a 3 minutes                │
│  Total aujourd'hui : 247                             │
└──────────────────────────────────────────────────────┘
```

➡️ Si le statut est « En pause », reprenez l'émission dans **Configuration → Debug → EventBus → Reprendre**.

### 2. L'événement a été purgé 🗑️

L'EventBus conserve les événements **7 jours maximum**. Passé ce délai, ils sont automatiquement supprimés par la purge horaire. Un événement de la semaine dernière n'est donc plus visible.

➡️ Si vous avez besoin d'une rétention plus longue, consultez [Base de données des événements →](/faq/bases-donnees-evenements).

### 3. La catégorie est filtrée dans le Surveillance 🎯

Le bot **Surveillance** peut filtrer par catégorie. Si vous avez un filtre actif, certains événements peuvent être cachés :

```
┌─ Filtres Surveillance ──────────────────────────────┐
│  ☑ reseau      ☑ transfert   ☑ recherche             │
│  ☑ bibliotheque  ☑ bot        ☑ wishlist             │
│  ☑ optimiseur  ☑ configuration ☑ aide               │
│                                                      │
│  [Tout]  [Aucun]  [Erreurs seulement]               │
└──────────────────────────────────────────────────────┘
```

➡️ Vérifiez que la catégorie de votre événement est cochée.

### 4. La sévérité est filtrée 🔴🟡🟢

Par défaut, le Surveillance affiche **toutes les sévérités** (INFO, WARN, ERROR). Mais si vous avez activé le mode « Erreurs seulement », les événements INFO seront masqués.

➡️ Basculez sur **« Tout afficher »** pour voir tous les niveaux.

### 5. L'événement a été émis avant la connexion au signal 🕐

Quand un composant se connecte au signal `event_emitted` de l'EventBus, il ne reçoit que les **nouveaux événements**. Les événements émis avant la connexion ne sont pas rejoués. C'est le comportement normal des signaux Qt.

➡️ Pour voir l'historique complet, utilisez la **liste historique** du bot Surveillance qui lit directement la base SQLite.

---

### ❓ Puis-je retrouver des événements supprimés ?

**Non.** Une fois purgés, les événements sont définitivement supprimés de la base SQLite (opération `DELETE` avec `wal_checkpoint`).

➡️ Si vous souhaitez conserver des événements, exportez-les régulièrement au format CSV ou JSON via le Surveillance (voir [Exporter les données →](/tutoriels/exporter-donnees-surveillance)).

---

### ❓ Pourquoi je vois des événements en double ?

Cela peut arriver si :

1. **Deux composants émettent pour le même fait** — Par exemple, `connexion_manager.py` et `event_bus.py` peuvent tous deux émettre un événement en cas de timeout réseau.
2. **Un événement a été ré-émis après une reconnexion** — Certains composants rejouent leur état après une reconnexion au serveur.

➡️ Ce n'est pas un bug : chaque événement a un `id` unique et un `timestamp` précis. Utilisez le tri par timestamp dans le Surveillance pour identifier les émissions redondantes.

---

### ❓ Comment vérifier qu'un événement a bien été émis ?

Si vous suspectez qu'un événement n'est pas émis :

1. Ouvrez le **bot Surveillance**
2. Filtrez par **source** (ex: `connexion_manager`)
3. Filtrez par **période** (ex: dernières 24h)
4. Lancez l'action qui devrait produire l'événement
5. Si rien n'apparaît, le composant peut ne pas émettre l'événement attendu

➡️ Consultez [Flux de données des événements →](/technique/flux-donnees-evenements) pour savoir quels événements chaque composant émet réellement.

---

**Voir aussi :** [Guide technique de l'EventBus →](/technique/guide-eventbus) | [Flux de données des événements →](/technique/flux-donnees-evenements) | [Exporter les données de surveillance →](/tutoriels/exporter-donnees-surveillance) | [FAQ outils de diagnostic →](/faq/debug-journaux)
