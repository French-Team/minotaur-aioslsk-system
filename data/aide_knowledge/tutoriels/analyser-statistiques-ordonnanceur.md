---
title: "Analyser les statistiques de téléchargement avec l'Ordonnanceur"
category: tutoriels
keywords: ["ordonnanceur", "telechargement", "téléchargement", "statistique", "analyse", "rapport", "queue", "file attente", "priorite", "priorité", "performance", "vitesse", "debit", "débit", "tendance", "histogramme"]
---

# Analyser les statistiques de téléchargement avec l'Ordonnanceur

> **Niveau :** Avancé  
> **Temps de lecture :** 8 min  
> **Bots concernés :** 📊 Ordonnanceur, 🔧 Téléchargement

---

## Objectif

L'**Ordonnanceur** est le centre névralgique de vos statistiques de téléchargement. Il collecte en temps réel les métriques de votre activité et propose des **analyses détaillées** par fichier, par utilisateur, par période.

Ce tutoriel vous apprend à :
- Lire et interpréter les tableaux de bord de l'Ordonnanceur
- Analyser la file d'attente et prioriser les téléchargements
- Générer des rapports de performance
- Identifier les utilisateurs et sources les plus fiables

---

## 1. Le tableau de bord de l'Ordonnanceur

### Vue d'ensemble

L'onglet principal affiche **4 indicateurs clés** :

```
┌─────────────────────────────────────────────────────┐
│  📊 Tableau de bord Ordonnanceur                     │
│                                                      │
│  Actifs   En attente   Terminés   Échoués            │
│    3         12         1 247       89               │
│                                                      │
│  Débit actuel : 2.4 Mo/s  │  Moyenne : 1.1 Mo/s     │
│  Temps moyen : 4m32s      │  Plus long : 2h15m       │
└──────────────────────────────────────────────────────┘
```

| Indicateur | Description |
|------------|-------------|
| **Actifs** | Téléchargements en cours |
| **En attente** | Dans la file d'attente |
| **Terminés** | Depuis le début de la session (ou depuis la dernière réinitialisation) |
| **Échoués** | Téléchargements qui ont échoué |
| **Débit actuel** | Vitesse de téléchargement instantanée |
| **Temps moyen** | Durée moyenne par fichier |

---

## 2. Analyser la file d'attente

### Prioriser manuellement

Cliquez droit sur un téléchargement dans la file :

- **Priorité haute** → passe en tête de file
- **Priorité normale** → ordre standard (premier arrivé, premier servi)
- **Priorité basse** → repoussé en fin de file
- **Suspendre** → mis en pause sans perdre sa position
- **Reprendre** → réactive un téléchargement suspendu

### Vue détaillée par fichier

L'Ordonnanceur propose un **onglet « Détail fichier »** accessible en double-cliquant sur un élément :

```
┌─ Détail : album_complet.zip (125 Mo) ──────────────┐
│                                                      │
│  Source : user_soulseek (123.45.67.89)               │
│  Débit  : ████████░░░░ 2.1 Mo/s                      │
│  Progrès: ████████████████░░░░ 68% (85/125 Mo)      │
│  ETA    : ~19 secondes                                │
│                                                      │
│  Historique des tentatives :                          │
│    ✓ user_soulseek (2.1 Mo/s) — en cours              │
│    ✗ autre_user (timeout) — abandonné                 │
│    ✓ user_soulseek (1.8 Mo/s) — interrompu            │
│                                                      │
│  [🔄 Changer de source]  [⏸ Suspendre]  [🗑 Annuler]  │
└──────────────────────────────────────────────────────┘
```

---

## 3. Générer des rapports de performance

### Rapport instantané

Dans l'onglet **« Rapports »** :

1. Cliquez sur **« Générer un rapport »**
2. Choisissez le type :

| Type de rapport | Contenu | Usage |
|-----------------|---------|-------|
| **Synthèse** | Métriques globales + top 10 fichiers | Aperçu rapide |
| **Par source** | Statistiques groupées par utilisateur | Identifier les meilleures sources |
| **Par taille** | Répartition par tranche de taille | Comprendre votre profil de téléchargement |
| **Chronologique** | Activité dans le temps (graphique) | Détecter les heures creuses |

### Rapport programmé

Via le **Planificateur**, vous pouvez recevoir un rapport hebdomadaire :

1. Allez dans **Planificateur → Nouvelle action**
2. Type : **« Rapport Ordonnanceur »**
3. Fréquence : **Tous les dimanches à 22h00**
4. Format : CSV ou JSON

---

## 4. Identifier les meilleures sources

L'ordonnanceur classe automatiquement les sources selon plusieurs critères :

### Classement des utilisateurs

Dans l'onglet **« Sources »** :

| Rang | Utilisateur | Fiabilité | Débit moyen | Fichiers fournis |
|------|-------------|-----------|-------------|------------------|
| 🥇 | user_fast | 98% | 5.2 Mo/s | 342 |
| 🥈 | music_library | 95% | 3.1 Mo/s | 1 047 |
| 🥉 | collector_99 | 87% | 1.8 Mo/s | 89 |

La **fiabilité** est calculée ainsi :
- **+1** pour chaque téléchargement réussi
- **-2** pour chaque échec (timeout, refus, déconnexion)
- Score normalisé entre 0% et 100%

### Activer le « mode fiable »

Vous pouvez configurer l'Ordonnanceur pour **privilégier automatiquement** les sources fiables :

1. **Paramètres Ordonnanceur → Sources**
2. Cochez **« Privilégier les sources fiables »**
3. Définissez un seuil (ex: 80%)
4. Option : **« Ignorer les sources sous le seuil »**

> ⚠️ **Attention :** Ignorer les sources peut réduire le nombre de sources disponibles pour les fichiers rares.

---

## 5. Analyse avancée : exports JSON

L'export JSON de l'Ordonnanceur inclut des données structurées pour analyse externe :

```json
{
  "statistiques": {
    "total_telechargements": 1247,
    "volume_total_octets": 53687091200,
    "taux_reussite": 92.8,
    "debit_moyen_octets": 1153433
  },
  "top_sources": [
    {"utilisateur": "user_fast", "fiabilite": 98, "fichiers": 342}
  ],
  "repartition_taille": {
    "petits_<10Mo": 456,
    "moyens_10-100Mo": 623,
    "gros_>100Mo": 168
  }
}
```

Importez ce fichier dans un tableur ou un script Python pour des analyses poussées (voir le tutoriel [Exporter et analyser les données de surveillance →](/tutoriels/exporter-donnees-surveillance)).

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Les stats semblent inexactes | Réinitialisez les compteurs dans **Ordonnanceur → Paramètres → Réinitialiser** |
| Une source fiable devient lente | Les notes sont dynamiques — elle va descendre automatiquement dans le classement |
| Rapport programmé non reçu | Vérifiez que le Planificateur a bien une tâche active pour l'Ordonnanceur |

---

**Voir aussi :** [Configurer les téléchargements →](/technique/configuration-telechargement) | [FAQ téléchargement lent →](/faq/telechargement-lent) | [Optimiser les téléchargements →](/tutoriels/optimiser-telechargements)
