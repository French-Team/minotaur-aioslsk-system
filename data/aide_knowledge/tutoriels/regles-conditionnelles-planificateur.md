---
title: "Automatiser avec des règles conditionnelles — Planificateur avancé"
category: tutoriels
keywords: ["planificateur", "regle", "règle", "condition", "automatisation", "declencheur", "déclencheur", "action", "trigger", "evenement", "événement", "programmation", "tache", "tâche", "alerte", "notif", "notification", "conditionnel"]
---

# Automatiser avec des règles conditionnelles

> **Niveau :** Avancé  
> **Temps de lecture :** 12 min  
> **Bots concernés :** 📅 Planificateur, 🔧 Ordonnanceur, 👁️ Surveillance, 🔧 Optimiseur

---

## Objectif

Le **Planificateur** permet de créer des **règles conditionnelles** : exécuter des actions automatiquement quand des événements spécifiques se produisent. Ce tutoriel vous guide de la règle simple au scénario complexe multi-bots.

---

## 1. Anatomie d'une règle

Une règle se compose de 3 éléments :

```
┌─ Nouvelle règle ─────────────────────────────────────┐
│                                                       │
│  SI [déclencheur] → [condition] → ALORS [action]     │
│                                                       │
│  Exemple :                                            │
│  SI [Téléchargement terminé] → [taille > 100 Mo]      │
│  → ALORS [Notifier + Archiver]                        │
│                                                       │
└───────────────────────────────────────────────────────┘
```

| Élément | Description | Exemples |
|---------|-------------|----------|
| **Déclencheur** | Quand vérifier la règle | Horaire fixe, événement, état |
| **Condition** | Filtre optionnel pour affiner | Taille > X, source spécifique |
| **Action** | Que faire si la condition est vraie | Notifier, exécuter, exporter |

---

## 2. Les déclencheurs disponibles

### Déclencheurs temporels

| Déclencheur | Configuration | Usage typique |
|-------------|---------------|---------------|
| **À heure fixe** | `Tous les jours à 22h00` | Changer de profil le soir |
| **Répétition** | `Toutes les 30 minutes` | Vérifier la file d'attente |
| **Plage horaire** | `Lundi-vendredi, 09h00-18h00` | Appliquer un profil « travail » |
| **Période** | `1er du mois à 08h00` | Générer le rapport mensuel |

### Déclencheurs événementiels

| Déclencheur | Quand ? | Usage typique |
|-------------|---------|---------------|
| **Téléchargement terminé** | Un fichier finit de télécharger | Archiver, notifier, lancer le scan |
| **Téléchargement échoué** | Un fichier échoue | Notifier, tenter autre source |
| **Connexion établie** | Connexion à Soulseek réussie | Lancer la synchronisation wishlist |
| **Connexion perdue** | Déconnexion du serveur | Désactiver les téléchargements |

### Déclencheurs d'état

| Déclencheur | Quand ? | Usage typique |
|-------------|---------|---------------|
| **File vide** | Aucun téléchargement actif | Passer en mode Économie |
| **File pleine** | Nombre max d'actifs atteint | Suspendre les nouveaux |
| **Erreur répétée** | 3+ échecs consécutifs sur un fichier | Marquer la source comme défaillante |

---

## 3. Configurer une règle simple

### Exemple : Notifier quand un téléchargement rare se termine

1. Allez dans **Planificateur → Règles → Nouvelle règle**
2. Déclencheur : **« Téléchargement terminé »**
3. Condition : (laisser vide, pas de condition supplémentaire)
4. Action : **« Notification »**
5. Message : `Téléchargement terminé : {fichier} ({taille})`

> 💡 Les variables `{fichier}`, `{taille}`, `{source}` sont automatiquement remplacées par les valeurs réelles.

---

## 4. Configurer une règle avancée

### Exemple : Appliquer un profil économique la nuit

**Objectif :** De 23h à 7h, passer en mode Économie pour ne pas saturer la bande passante.

**Règle 1 — Activation :**
```
Déclencheur : Tous les jours à 23h00
Condition  : Aucun téléchargement actif OU file d'attente < 5
Action     : Changer profil Optimiseur → Économie
```

**Règle 2 — Désactivation :**
```
Déclencheur : Tous les jours à 07h00
Condition  : (aucune)
Action     : Changer profil Optimiseur → Race
```

### Exemple : Sauvegarde automatique des statistiques

**Objectif :** Exporter les stats de l'Ordonnanceur tous les dimanches.

```
Déclencheur : Tous les dimanches à 10h00
Condition  : (aucune)
Action     : Exporter stats Ordonnanceur vers data/backup_stats/
```

---

## 5. Les actions disponibles

| Action | Effet | Paramètres |
|--------|-------|------------|
| **Notification** | Affiche une notification système | Message, priorité |
| **Changer profil** | Change le profil de l'Optimiseur | Nom du profil |
| **Exécuter recherche** | Lance une recherche Wishlist | Texte ou wishlist |
| **Suspendre/Reprendre** | Contrôle la file d'attente | Tout / Source spécifique |
| **Exporter stats** | Sauvegarde les statistiques | Format, destination |
| **Scan bibliothèque** | Relance un scan des partages | Dossier (optionnel) |
| **Action personnalisée** | Exécute un script ou commande | Chemin, arguments (voir section 7) |

---

## 6. Enchaîner plusieurs actions

Une règle peut déclencher **plusieurs actions séquentiellement** :

```
┌─ Règle : « Fermeture » (tous les soirs à 23h) ────┐
│                                                      │
│  1. Notification : « Passage en mode nuit »          │
│  2. Attendre 30 secondes                              │
│  3. Changer profil → Économie                        │
│  4. Exporter stats → data/rapports/jour/             │
│  5. Suspendre les téléchargements non prioritaires    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Pour ajouter plusieurs actions, cliquez sur **« + Ajouter une action »** dans la règle. L'ordre se modifie par glisser-déposer.

---

## 7. Actions personnalisées (script externe)

Pour les utilisateurs avancés, le Planificateur peut exécuter des **scripts externes** :

1. Action : **« Exécuter un script »**
2. Chemin : `C:\scripts\mon_script.bat` (Windows) ou `/home/user/script.sh`
3. Arguments : `{fichier} {taille}` (variables disponibles)

### Exemple : Script de notification Telegram

```bash
#!/bin/bash
# notifier_telegram.sh — envoie une notification Telegram
MESSAGE="Téléchargement terminé : $1 ($2 Mo)"
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d chat_id=<CHAT_ID> \
  -d text="$MESSAGE"
```

> ⚠️ **Sécurité :** Les scripts sont exécutés avec les droits de l'application. Ne chargez pas de scripts non vérifiés.

---

## 8. Exemples de scénarios complets

### Scénario 1 : L'utilisateur nomade

| Règle | Déclencheur | Action |
|-------|-------------|--------|
| Arrivée au bureau | 09h00 | Profil Économie + notifier |
| Pause déjeuner | 12h30 → 13h30 | Profil Race |
| Retour à la maison | 18h00 | Profil Recherche + notifier |
| Nuit | 23h00 | Profil Économie + exporter stats |

### Scénario 2 : Le collectionneur averti

| Règle | Déclencheur | Action |
|-------|-------------|--------|
| Scan wishlist | Tous les jours à 08h00 et 20h00 | Lancer recherche wishlist |
| Fichier rare trouvé | Résultat wishlist correspondant | Notification haute priorité |
| Téléchargement terminé | Événement succès | Archiver dans dossier « Nouveautés » |
| Espace disque faible | Taille téléchargée > 50 Go/semaine | Notification + suspendre download |

### Scénario 3 : Serveur 24/7

| Règle | Déclencheur | Action |
|-------|-------------|--------|
| Surveillance continue | Connexion perdue + 5 min | Redémarrer connexion |
| Rapport quotidien | 23h59 | Exporter stats → dossier rapports |
| Backup config | 1er du mois | Exporter profils + config |
| Alerte échecs | 5 échecs en 1h | Notification critique |

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Une règle ne se déclenche pas | Vérifiez que le Planificateur est actif (voyant vert dans le footer) |
| Action exécutée deux fois | Une règle peut avoir plusieurs déclencheurs. Vérifiez les doublons |
| Script externe non exécuté | Vérifiez les permissions d'exécution et le chemin absolu |
| Condition jamais vraie | Utilisez le mode **« Tester »** de la règle pour voir les valeurs actuelles |

---

**Voir aussi :** [Planifier une tâche programmée →](/tutoriels/planifier-tache-programmee) | [Profils de performance →](/tutoriels/profils-optimiseur) | [Sauvegarder sa configuration →](/tutoriels/sauvegarder-restaurer-configuration)
