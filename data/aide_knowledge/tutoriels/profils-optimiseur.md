---
title: "Créer et gérer des profils de performance — Optimiseur avancé"
category: tutoriels
keywords: ["profil", "profile", "optimiseur", "performance", "economie", "recherche", "reglage", "réglage", "preset", "personnalisation", "race", "cautious", "aggressive", "peer", "connexion", "upload", "download"]
---

# Créer et gérer des profils de performance avec l'Optimiseur

> **Niveau :** Avancé  
> **Temps de lecture :** 10 min  
> **Bots concernés :** 🔧 Optimiseur, ⚙️ Configuration réseau

---

## Objectif

L'Optimiseur permet de basculer instantanément entre **plusieurs profils de performance** prédéfinis, chacun adapté à un usage spécifique : téléchargement rapide, économie de bande passante, ou réactivité de recherche.

Ce tutoriel vous apprend à :
- Comprendre les 3 profils intégrés (Race, Économie, Recherche)
- Créer et sauvegarder vos propres profils personnalisés
- Basculer entre profils selon votre activité
- Automatiser le changement de profil

---

## 1. Les 3 profils intégrés

### Profil « Race » (rapide)
| Paramètre | Valeur | Effet |
|-----------|--------|-------|
| Mode connexion peer | `race` | Tente toutes les connexions simultanément |
| Limite upload | 0 (illimité) | Partage maximal — peut ralentir le download |
| UPnP | Activé | Détection automatique des ports |

**Usage :** Quand vous téléchargez activement et voulez maximiser la vitesse.

### Profil « Économie » (prudent)
| Paramètre | Valeur | Effet |
|-----------|--------|-------|
| Mode connexion peer | `cautious` | Connexions progressives, une par une |
| Limite upload | 50 KB/s | Préserve la bande passante |
| UPnP | Désactivé | Pas de modification du routeur |

**Usage :** En arrière-plan, ou quand vous utilisez Internet pour autre chose.

### Profil « Recherche » (réactif)
| Paramètre | Valeur | Effet |
|-----------|--------|-------|
| Mode connexion peer | `aggressive` | Connexions très rapides aux peers |
| Timeout requête | 15s | Résultats de recherche rapides |
| Stockage résultats | Illimité | Conservation de tous les résultats |

**Usage :** Quand vous explorez activement le réseau pour trouver des fichiers rares.

---

## 2. Créer un profil personnalisé

Dans l'interface de l'**Optimiseur** :

1. Cliquez sur **« Nouveau profil »**
2. Donnez-lui un nom explicite (ex: « Téléchargement nocturne »)
3. Réglez chaque paramètre selon vos besoins :

```
┌─ Paramètres recommandés pour un profil ─────────────────┐
│ Mode peer :        [race] [cautious] [aggressive]        │
│ Upload max (KB/s) : [____0____] (0 = illimité)           │
│ Download max (KB/s) : [____0____]                        │
│ UPnP :              [Oui] [Non]                          │
│ Reconnexion auto :  [Oui] [Non]                          │
│ ──────────────────────────────────────────────────────  │
│          [Sauvegarder]      [Appliquer]      [Annuler]   │
└──────────────────────────────────────────────────────────┘
```

4. Cliquez sur **« Sauvegarder »** pour le retrouver plus tard

---

## 3. Basculer entre profils

Vous pouvez changer de profil instantanément :

- **Depuis l'Optimiseur** : double-cliquez sur le nom du profil
- **Depuis le bouton rapide** (footer) : le badge de l'Optimiseur affiche le profil actif
- **Via la configuration réseau** : modifiez les paramètres individuels dans `Paramètres > Réseau`

> 💡 **Astuce :** Le profil actif est indiqué par une icône dans le footer à côté du nom du bot Optimiseur. Un survol affiche le détail des réglages appliqués.

---

## 4. Profils recommandés selon votre usage

| Vous êtes plutôt… | Profil recommandé | Pourquoi |
|-------------------|-------------------|----------|
| **Téléchargeur actif** | Race (personnalisé) | Limite upload à 200 KB/s max |
| **Collectionneur** | Recherche | Agrressive peer + timeout court |
| **Utilisateur passif** | Économie | Préserve votre connexion |
| **Mixte (soir + jour)** | 2 profils programmés | Automatisation (voir section 5) |

---

## 5. Automatisation avancée : changer de profil selon l'horaire

L'**Ordonnanceur** peut être couplé à l'Optimiseur pour changer automatiquement de profil :

1. Allez dans **Ordonnanceur → Planifier une tâche**
2. Types de déclencheur disponibles :

| Déclencheur | Exemple |
|-------------|---------|
| Plage horaire | `23h00 → 07h00` → profil « Race » (téléchargement nocturne) |
| Connexion réseau | `WiFi maison détecté` → profil « Recherche » |
| Inactivité | `15 min sans activité` → profil « Économie » |
| Téléchargement terminé | `File d'attente vide` → profil « Économie » |

3. Associez l'action **« Changer profil Optimiseur »** au déclencheur
4. Sélectionnez le profil cible dans la liste déroulante

---

## 6. Sauvegarder et partager ses profils

L'Optimiseur permet d'exporter vos profils au format JSON :

1. Cliquez sur **« Exporter »** dans la barre d'outils
2. Choisissez un emplacement de sauvegarde
3. Le fichier généré contient tous vos profils :

```json
{
  "profils": [
    {
      "nom": "Race personnalisé",
      "mode_peer": "race",
      "limite_upload": 200,
      "limite_download": 0,
      "upnp": true,
      "reconnexion_auto": true
    }
  ]
}
```

Pour **importer** : cliquez sur **« Importer »** et sélectionnez un fichier `.json` valide.

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Le profil ne s'applique pas | Vérifiez la connexion Soulseek — la modification réseau nécessite d'être connecté |
| Perte du profil après mise à jour | Exportez vos profils régulièrement, ou activez la sauvegarde automatique dans les paramètres de l'Optimiseur |
| Conflit entre profils | Si deux tâches programmées changent de profil simultanément, la plus récente prioritaire |

---

**Voir aussi :** [Configuration réseau →](/technique/configuration-reseau) | [Planifier une tâche programmée →](/tutoriels/planifier-tache-programmee) | [FAQ paramètres recommandés →](/faq/parametres-recommandes)
