---
title: "Exporter et analyser les données de surveillance"
category: tutoriels
keywords: ["surveillance", "export", "csv", "json", "analyse", "statistique", "stat", "rapport", "historique", "filtre", "fichier", "log", "journal", "diagnostic", "depannage", "dépannage"]
---

# Exporter et analyser les données de surveillance

> **Niveau :** Avancé  
> **Temps de lecture :** 8 min  
> **Bots concernés :** 👁️ Surveillance, 📋 Planificateur

---

## Objectif

Le bot **Surveillance** enregistre en continu l'activité de vos téléchargements, connexions et événements réseau. Ce tutoriel vous montre comment exploiter ces données pour **analyser les tendances**, **identifier les goulots d'étranglement** et **exporter des rapports**.

---

## 1. Exporter les données brutes

### Format CSV (tableur)

Idéal pour Excel, LibreOffice ou Google Sheets.

1. Ouvrez le bot **Surveillance**
2. Cliquez sur **« Exporter » → « CSV »**
3. Choisissez la période :
   - 📅 **Aujourd'hui** — activité récente
   - 📅 **7 derniers jours** — tendances hebdomadaires
   - 📅 **30 derniers jours** — vue d'ensemble
   - 📅 **Personnalisé** — sélectionnez deux dates

Le fichier CSV contient les colonnes suivantes :

| Date | Heure | Type | Détail | Statut | Durée (s) | Taille (Ko) |
|------|-------|------|--------|--------|-----------|-------------|
| 2025-03-15 | 14:32 | Upload | fichier.mp3 | Succès | 45 | 8 200 |
| 2025-03-15 | 14:35 | Download | album.zip | En cours | — | 125 000 |

### Format JSON (analyse avancée)

Pour les utilisateurs qui souhaitent traiter les données avec Python, R ou d'autres outils :

1. Cliquez sur **« Exporter » → « JSON »**
2. Le fichier contient une structure exploitable :

```json
{
  "export": {
    "date": "2025-03-15T14:30:00",
    "periode": "7 jours",
    "total_evenements": 1247
  },
  "evenements": [
    {
      "timestamp": "2025-03-15T14:32:00",
      "type": "upload",
      "fichier": "fichier.mp3",
      "taille_octets": 8396800,
      "statut": "succes",
      "duree_secondes": 45
    }
  ]
}
```

---

## 2. Filtrer les données avant export

Avant d'exporter, utilisez les **filtres** du Surveillance pour ne conserver que les données pertinentes :

| Filtre | Utilité |
|--------|---------|
| **Type d'événement** | Upload / Download / Connexion / Erreur |
| **Statut** | Succès / Échec / En cours / Annulé |
| **Nom de fichier** | Recherche textuelle (supporte les motifs partiels) |
| **Période** | Date de début / date de fin |
| **Taille** | Supérieur à / Inférieur à (en Ko) |

> 💡 **Astuce :** Combinez plusieurs filtres pour isoler précisément ce que vous cherchez. Par exemple : tous les **échecs de download** de **plus de 50 Mo** sur les **7 derniers jours**.

---

## 3. Analyser les tendances

### Identifier les heures de pointe

Après export CSV, créez un tableau croisé dynamique dans votre tableur :

1. Colonne : **Heure** (groupée par tranche de 2h)
2. Valeur : **Nombre d'événements**
3. Filtre : **Type = Download**

→ Vous obtiendrez un histogramme de votre activité.

### Détecter les fichiers problématiques

Dans le Surveillance, activez le **mode Statistiques** (`Statistiques → Analyse des échecs`) :

```
┌─ Analyse des échecs ────────────────────────────────┐
│ Taux d'échec global : 12.3%                         │
│                                                      │
│ Top 5 fichiers bloqués :                             │
│   1. fichier_rare.flac  →  8 échecs (timeout)       │
│   2. album_complet.zip  →  5 échecs (refusé)        │
│   3. video_demo.mkv     →  3 échecs (taille)        │
│                                                      │
│ Causes principales :                                 │
│   🔴 Timeout : 45%                                   │
│   🟡 Refusé : 30%                                    │
│   🟢 Taille excessive : 15%                          │
│   ⚪ Autre : 10%                                      │
└──────────────────────────────────────────────────────┘
```

### Visualiser la bande passante

Le Surveillance propose un **graphique d'activité** en temps réel. Pour une analyse historique :

1. Exportez les 30 derniers jours en CSV
2. Dans votre tableur, créez un graphique **« Aire empilée »**
3. Axe X : Date/heure
4. Axe Y : Taille (Ko)
5. Séries : Upload / Download

→ Vous visualiserez la répartition de votre bande passante.

---

## 4. Générer un rapport automatique

Le **Planificateur** peut générer des rapports périodiques :

1. Allez dans **Planificateur → Nouvelle action**
2. Type : **« Générer rapport Surveillance »**
3. Fréquence : **Tous les lundis à 08h00**
4. Format : CSV
5. Période : **7 derniers jours**
6. Périphérique : **Envoyer vers** → `data/rapports/surveillance/`

Le rapport sera automatiquement créé chaque semaine.

---

## 5. Exemple d'analyse avancée avec Python

Pour les utilisateurs familiers avec Python, voici un exemple de script pour analyser un export JSON :

```python
import json
from pathlib import Path

# Charger l'export
data = json.loads(Path("export_surveillance.json").read_text())

# Compter par type
types = {}
for evt in data["evenements"]:
    t = evt["type"]
    types[t] = types.get(t, 0) + 1

print("Répartition par type :")
for t, count in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

# Taux de succès
succes = sum(1 for e in data["evenements"] if e.get("statut") == "succes")
total = len(data["evenements"])
print(f"\nTaux de succès : {succes/total*100:.1f}%")
```

---

## Dépannage

| Problème | Solution |
|----------|----------|
| L'export CSV est vide | Vérifiez les filtres actifs — vous avez peut-être une exclusion trop stricte |
| Fichier JSON corrompu | L'export peut être volumineux (> 50 000 événements). Préférez CSV dans ce cas |
| Graphique d'activité vide | Le Surveillance doit être actif en arrière-plan pour collecter les données |

---

**Voir aussi :** [Configuration debug →](/technique/configuration-debug) | [FAQ outils de diagnostic →](/faq/debug-journaux) | [Planifier une tâche programmée →](/tutoriels/planifier-tache-programmee)
