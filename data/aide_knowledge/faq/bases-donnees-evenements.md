---
title: "Base de données des événements — Taille, purge et nettoyage"
category: faq
keywords: ["base", "donnee", "donnée", "sqlite", "evenement", "événement", "taille", "poids", "grossir", "purge", "nettoyage", "nettoyer", "supprimer", "retention", "rétention", "periode", "période", "disque", "espace", "wal", "checkpoint", "compactage", "compacter"]
---

# Base de données des événements — Taille, purge et nettoyage

> **Niveau :** Intermédiaire  
> **Catégorie :** Maintenance — EventBus

---

## Questions fréquentes

### ❓ La base de données des événements grossit-elle indéfiniment ?

**Non.** L'EventBus intègre un **système de purge automatique** :

- **Rétention par défaut** : 7 jours
- **Fréquence de purge** : toutes les 1 heure
- **Mécanisme** : suppression des événements plus anciens que 7 jours, suivie d'un `WAL checkpoint (TRUNCATE)` pour compacter le fichier

En pratique :
- Une utilisation normale génère **~200 à 500 événements par jour**
- La base pèse généralement **entre 1 Mo et 10 Mo**
- La purge maintient un volume stable : elle ne grossit pas indéfiniment

---

### ❓ Puis-je changer la durée de rétention ?

La rétention de 7 jours est codée en dur dans l'EventBus actuel :

```python
# Dans event_bus.py
seuil = datetime.now() - timedelta(days=7)  # ← 7 jours
```

➡️ Pour l'instant, cette valeur n'est pas modifiable depuis l'interface. Si vous avez besoin d'une rétention plus longue :

1. **Exportez régulièrement** les événements en CSV/JSON via le Surveillance (voir [Exporter les données →](/tutoriels/exporter-donnees-surveillance))
2. **Automatisez l'export** via le Planificateur pour une sauvegarde hebdomadaire (voir [Règles conditionnelles →](/tutoriels/regles-conditionnelles-planificateur))

---

### ❓ Puis-je vider la base manuellement ?

**Oui**, de deux façons :

#### Méthode 1 — Via le Surveillance

1. Ouvrez le bot **Surveillance**
2. Allez dans **Paramètres → Base de données**
3. Cliquez sur **« Nettoyer les événements »**

Vous pouvez choisir :
- **Supprimer les événements de plus de X jours** (personnalisable)
- **Tout supprimer** (réinitialisation complète)

#### Méthode 2 — Directement (dangereux)

Si l'application est fermée, vous pouvez supprimer le fichier de base :

```bash
# Supprimer la base (application fermée !)
rm data/bot_surveillance.db
rm data/bot_surveillance.db-wal
rm data/bot_surveillance.db-shm
```

> ⚠️ **La base sera recréée automatiquement** au prochain lancement, mais vous perdrez tout l'historique.

---

### ❓ Combien d'espace disque cela représente-t-il ?

Volume typique pour 7 jours :

| Activité | Événements/jour | Taille estimée (7 jours) |
|----------|----------------|--------------------------|
| Faible (consultation) | ~50 | ~500 Ko |
| Normale (téléchargements modérés) | ~300 | ~3 Mo |
| Élevée (24/7, nombreux téléchargements) | ~1000+ | ~10-20 Mo |

> 💡 La taille reste négligeable comparée aux fichiers téléchargés (plusieurs Go).

---

### ❓ Qu'est-ce que le WAL (Write-Ahead Logging) ?

Le WAL est un mode d'écriture SQLite qui permet :
- **Meilleures performances** en lecture/écriture simultanées
- **Safety** : si l'application plante, les données ne sont pas perdues
- **Compaction** : le `wal_checkpoint(TRUNCATE)` (déclenché par la purge et la fermeture) réduit la taille du fichier WAL

Trois fichiers sont créés :
| Fichier | Rôle |
|---------|------|
| `bot_surveillance.db` | Base principale |
| `bot_surveillance.db-wal` | Journal des écritures en attente |
| `bot_surveillance.db-shm` | Verrou partagé |

> Les fichiers `.db-wal` et `.db-shm` sont temporaires et disparaissent après un checkpoint complet.

---

### ❓ Y a-t-il un risque de saturation si j'utilise l'application 24/7 ?

**Non.** La purge automatique toutes les heures garantit que le volume reste stable, même en utilisation intensive.

Cependant, si vous remarquez une croissance anormale :

1. Vérifiez qu'il n'y a pas **d'émission excessive** (ex: une boucle qui émet des événements toutes les secondes)
2. Vérifiez la taille du fichier WAL : un `.db-wal` > 50 Mo peut indiquer un checkpoint qui n'a pas eu lieu
3. Lancez manuellement un checkpoint : `PRAGMA wal_checkpoint(TRUNCATE);`

---

### ❓ Puis-je accéder directement à la base SQLite ?

**Oui**, si vous êtes familier avec SQLite :

```bash
# Lire les 10 derniers événements
sqlite3 data/bot_surveillance.db \
  "SELECT timestamp, severity, category, title FROM surveillance_events \
   ORDER BY id DESC LIMIT 10;"

# Compter par catégorie
sqlite3 data/bot_surveillance.db \
  "SELECT category, COUNT(*) FROM surveillance_events \
   GROUP BY category ORDER BY 2 DESC;"
```

> ⚠️ Faites-le **application fermée** ou utilisez une connexion en lecture seule pour éviter les verrous.

---

**Voir aussi :** [Guide technique de l'EventBus →](/technique/guide-eventbus) | [Événements manquants →](/faq/evenements-introuvables) | [Exporter les données de surveillance →](/tutoriels/exporter-donnees-surveillance) | [Sauvegarder la configuration →](/tutoriels/sauvegarder-restaurer-configuration)
