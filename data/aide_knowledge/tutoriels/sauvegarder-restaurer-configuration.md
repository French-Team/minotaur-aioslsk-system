---
title: "Sauvegarder et restaurer sa configuration"
category: tutoriels
keywords: ["sauvegarde", "backup", "restauration", "restaurer", "export", "import", "config", "configuration", "migration", "transfert", "reinstallation", "réinstallation", "profil", "donnee", "donnée", "perte", "precaution", "précaution"]
---

# Sauvegarder et restaurer sa configuration

> **Niveau :** Intermédiaire → Avancé  
> **Temps de lecture :** 8 min  
> **Bots concernés :** ⚙️ Configuration, 🔧 Optimiseur, 👁️ Surveillance, 📊 Ordonnanceur

---

## Objectif

Après avoir passé du temps à peaufiner vos réglages, profils et filtres, il serait dommage de tout perdre. Ce tutoriel vous montre comment **sauvegarder l'intégralité de votre configuration** et la **restaurer** en cas de besoin (réinstallation, changement de machine, rollback après un test).

---

## 1. Quoi sauvegarder ?

L'application répartit les données à plusieurs endroits :

| Données | Emplacement | Fichiers | Utilité |
|---------|-------------|----------|---------|
| **Paramètres généraux** | `data/app_config.db` | Base SQLite | Tous les réglages des 8 pages de config |
| **Profils Optimiseur** | `data/` | Export JSON possible depuis l'Optimiseur | Profils de performance personnalisés |
| **Statistiques** | `data/stats.db` | Base SQLite (Surveillance + Ordonnanceur) | Historique d'activité |
| **Bibliothèque** | `data/library.db` | Base SQLite | Index des fichiers partagés |
| **Historique téléchargements** | `data/download_history.db` | Base SQLite | Log des téléchargements |
| **Filtres et modèles** | Intégré à `app_config.db` | Base SQLite | Filtres de recherche sauvegardés |
| **Wishlist** | `data/` | Base SQLite | Liste des souhaits actifs |

---

## 2. Sauvegarde rapide (un clic)

L'application propose une **sauvegarde complète en un clic** :

1. Allez dans **Configuration → Général**
2. Cliquez sur **« Sauvegarder la configuration »**
3. Choisissez un dossier de destination

Un dossier `backup_2025-03-15_14h30/` est créé, contenant :

```
backup_2025-03-15_14h30/
├── config/
│   ├── app_config.db
│   └── profiles_optimiseur.json
├── data/
│   ├── stats.db
│   ├── library.db
│   └── download_history.db
└── logs/
    └── error_log.txt
```

> 💡 **Astuce :** Programmez une sauvegarde automatique hebdomadaire via le Planificateur (voir [Règles conditionnelles →](/tutoriels/regles-conditionnelles-planificateur)).

---

## 3. Sauvegarde manuelle (sélective)

Pour sauvegarder seulement certaines parties :

### Via l'interface

| Ce que vous voulez | Où aller | Action |
|--------------------|----------|--------|
| **Paramètres réseau** | Configuration → Réseau | Capture d'écran ou noter les valeurs |
| **Profils personnalisés** | Optimiseur → Profils | Cliquer « Exporter » (format JSON) |
| **Filtres de recherche** | Recherche → Mes filtres | Noter les noms ou exporter |
| **Règles Planificateur** | Planificateur → Règles | **« Exporter toutes les règles »** |
| **Liste noire/blanche** | Configuration → Utilisateurs | Copier les listes ou exporter |

### Via le système de fichiers

Vous pouvez aussi copier manuellement les fichiers :

```bash
# Windows (PowerShell)
Copy-Item -Path "data\*.db" -Destination "D:\backup_aioslsk\" -Recurse

# Windows (cmd)
xcopy /E /I data backup_aioslsk\data
```

> ⚠️ Faites cette copie **application fermée** pour éviter les conflits d'accès aux bases SQLite.

---

## 4. Restaurer une sauvegarde

### Restauration automatique (recommandée)

1. Allez dans **Configuration → Général**
2. Cliquez sur **« Restaurer la configuration »**
3. Sélectionnez le dossier de sauvegarde (le `backup_2025-.../`)
4. Choisissez ce que vous voulez restaurer :

```
┌─ Restauration ──────────────────────────────────────┐
│                                                      │
│  ☑ Paramètres généraux (app_config.db)               │
│  ☑ Profils Optimiseur                                │
│  ☐ Statistiques (écrase l'existant)                  │
│  ☐ Bibliothèque (nécessite un rescannage)             │
│  ☐ Historique téléchargements                        │
│  ☑ Règles Planificateur                              │
│                                                      │
│  ⚠️ Les données existantes seront remplacées          │
│                                                      │
│  [Restaurer]  [Annuler]                              │
└──────────────────────────────────────────────────────┘
```

5. Redémarrez l'application (optionnel — certains paramètres réseau nécessitent un redémarrage)

### Restauration manuelle

1. Fermez l'application
2. Remplacez les fichiers `.db` dans `data/` par ceux de votre sauvegarde
3. Redémarrez l'application

---

## 5. Migration vers une autre machine

Pour transférer votre configuration sur un autre ordinateur :

1. **Machine source** : faites une **sauvegarde complète** (section 2)
2. **Machine cible** : installez l'application, puis **restaurez** (section 4)
3. **Ajustements réseau** : vérifiez les paramètres réseau (ils peuvent différer selon votre connexion)

### Points d'attention

| Élément | Attention |
|---------|-----------|
| **Ports UPnP** | Le routeur de la machine cible peut être différent |
| **Dossiers partagés** | Vérifiez que les chemins existent sur la nouvelle machine |
| **Limites de débit** | Adaptez-les à la connexion de la machine cible |
| **Bibliothèque** | Après restauration, lancez un **scan complet** (`Configuration → Partages → Scanner`) |

> 💡 **Astuce pro :** Exportez vos profils Optimiseur en JSON séparément, c'est le moyen le plus fiable de les transférer.

---

## 6. Planifier des sauvegardes automatiques

Via le **Planificateur**, créez une règle de sauvegarde périodique :

```
Règle : « Backup hebdomadaire »
Déclencheur : Tous les dimanches à 02h00
Condition  : (aucune)
Action : Sauvegarder la configuration → data/backups/
```

L'application conserve les **10 dernières sauvegardes** et supprime automatiquement les plus anciennes.

---

## 7. Que faire en cas de perte ?

### Perte partielle

Si vous perdez seulement quelques paramètres :

1. **Profils Optimiseur** : vérifiez `data/` — les exports JSON manuels persistent
2. **Règles Planificateur** : consultez le fichier `data/rules_backup.json` (sauvegarde automatique)
3. **Filtres de recherche** : malheureusement non sauvegardés automatiquement en dehors de `app_config.db`

### Perte totale

1. Installez l'application
2. Restaurez votre dernière sauvegarde complète
3. Si pas de sauvegarde : reconfigurez manuellement (les pages de configuration sont documentées dans [Configuration générale →](/technique/configuration-generale))
4. Relancez un scan de la bibliothèque

---

## Checklist de sauvegarde

Avant une opération sensible (réinstallation, mise à jour majeure) :

- [ ] Sauvegarde complète effectuée (Configuration → Général)
- [ ] Export des profils Optimiseur (JSON)
- [ ] Export des règles Planificateur
- [ ] Note des paramètres réseau (si personnalisés)
- [ ] Vérification que le fichier de sauvegarde fait au moins 1 Mo
- [ ] Copie sur un support externe (clé USB, cloud, autre disque)

---

**Voir aussi :** [Configuration générale →](/technique/configuration-generale) | [Règles conditionnelles →](/tutoriels/regles-conditionnelles-planificateur) | [FAQ paramètres recommandés →](/faq/parametres-recommandes)
