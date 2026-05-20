---
title: "Configuration des téléchargements (Téléchargement) — destination, slots, intervalle et backend"
category: technique
keywords:
  - telechargement
  - téléchargement
  - download
  - upload
  - slots
  - destination
  - dossier
  - rapport
  - intervalle
  - progression
  - ConfigSpin
  - ConfigDirectoryPicker
  - ConfigSection
  - ConfigPage
  - Optimiseur
  - telechargement.slots_upload
  - telechargement.dossier_destination
  - telechargement.intervalle_rapport
  - TransferLimitSettings
  - TransfersSettings
  - SharesSettings
  - slots d'upload
  - slots d'envoi
  - upload_slots
  - report_interval
  - app_config
  - soulseek_client
  - paramètres
  - parametres
  - configuration
  - limites
  - config
  - widget
---

## Résumé

La page **Téléchargement** de l'Optimiseur contrôle les paramètres liés aux transferts de fichiers : slots d'upload simultanés, dossier de destination et intervalle de rapport de progression. Cet article détaille les widgets UI (`ConfigSpin`, `ConfigDirectoryPicker`) et le backend (`soulseek_client.py`, `TransferLimitSettings`, `TransfersSettings`, conversion ms → secondes).

```
┌─────────────────────────────────────────────────────────────────┐
│                   Optimiseur → Téléchargement                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─ Limites ─────────────────────────────────────────────────┐  │
│  │  ConfigSpin  « telechargement.slots_upload » (min=1,      │  │
│  │               max=100, step=1, defaut=2)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Destination ────────────────────────────────────────────┐  │
│  │  ConfigDirectoryPicker « telechargement.dossier_destination »│
│  │  Placeholder: « Dossier par défaut Soulseek… »            │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Rapport ────────────────────────────────────────────────┐  │
│  │  ConfigSpin  « telechargement.intervalle_rapport »         │  │
│  │             (min=50, max=10000, step=50, defaut=250 ms)  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    app_config.json (persistance)
                              │
                              ▼
                 soulseek_client.py (lecture startup)
                              │
                              ├── SharesSettings(download=...)
                              ├── TransferLimitSettings(upload_slots=...)
                              └── TransfersSettings(report_interval=...)
```

---

## 1. Fichiers sources

| Fichier | Rôle |
|---------|------|
| `src/gui/layout/center.py` | Construction de la `ConfigPage("Téléchargement")` (lignes 691-730) |
| `src/services/soulseek_client.py` | Lecture et application des paramètres (lignes 241-243, 345-352) |
| `src/services/app_config.py` | Persistance des clés `telechargement.*` dans `app_config.json` |

---

## 2. Interface utilisateur (widgets)

La page **Téléchargement** est construite dans `center.py` (ligne 691) avec 3 sections. Elle est enregistrée sous la clé `"config-telechargement"` dans `self._pages` (ligne 730).

### 2.1 Section « Limites »

| Propriété | Valeur |
|-----------|--------|
| **Widget** | `ConfigSpin` |
| **Label** | « Slots d'upload simultanés » |
| **Config key** | `telechargement.slots_upload` |
| **Minimum** | 1 |
| **Maximum** | 100 |
| **Pas** | 1 |
| **Description** | « Nombre de fichiers pouvant être uploadés en même temps. 2 = défaut Soulseek. » |

### 2.2 Section « Destination »

| Propriété | Valeur |
|-----------|--------|
| **Widget** | `ConfigDirectoryPicker` |
| **Label** | « Dossier de destination » |
| **Config key** | `telechargement.dossier_destination` |
| **Placeholder** | « Dossier par défaut Soulseek… » |
| **Description** | « Où enregistrer les fichiers téléchargés. Laissez vide pour utiliser le dossier par défaut de Soulseek. » |

### 2.3 Section « Rapport »

| Propriété | Valeur |
|-----------|--------|
| **Widget** | `ConfigSpin` |
| **Label** | « Intervalle de rapport (ms) » |
| **Config key** | `telechargement.intervalle_rapport` |
| **Minimum** | 50 |
| **Maximum** | 10000 |
| **Pas** | 50 |
| **Description** | « Fréquence des mises à jour de progression. 250 ms = défaut Soulseek (0.25 s). » |

---

## 3. Stockage dans `app_config`

```json
{
  "telechargement": {
    "slots_upload": 2,
    "dossier_destination": "Q:/Downloads/Soulseek",
    "intervalle_rapport": 250
  }
}
```

### Clés et valeurs par défaut

| Clé | Défaut | Type | Widget |
|-----|--------|------|--------|
| `telechargement.slots_upload` | `2` | `int` | `ConfigSpin` (1-100) |
| `telechargement.dossier_destination` | `""` | `str` | `ConfigDirectoryPicker` |
| `telechargement.intervalle_rapport` | `250` | `int` (ms) | `ConfigSpin` (50-10000) |

---

## 4. Backend — lecture au démarrage

### 4.1 Lecture des valeurs (`soulseek_client.py`, lignes 241-243)

```python
slots_upload = int(app_config.get("telechargement.slots_upload", 2))
dossier_destination = app_config.get("telechargement.dossier_destination", "")
intervalle_rapport = int(app_config.get("telechargement.intervalle_rapport", 250))
```

**Détails :**
- **Cast `int()`** : `slots_upload` et `intervalle_rapport` sont explicitement castés en `int` pour garantir le type, même si la valeur stockée est un float ou une chaîne numérique.
- `dossier_destination` reste en `str` (chemin de dossier).

### 4.2 Application aux paramètres Soulseek (lignes 343-352)

```python
shares=SharesSettings(
    scan_on_start=scan_on_start,
    download=dossier_destination,               # ← dossier de destination §2.2
    directories=dossiers_partages,
),
...
transfers=TransfersSettings(
    limits=TransferLimitSettings(
        upload_slots=slots_upload,              # ← slots d'upload §2.1
    ),
    report_interval=intervalle_rapport / 1000.0, # ← intervalle en secondes §2.3
),
```

**Détails importants :**

| Paramètre | Source | Destination | Transformation |
|-----------|--------|-------------|---------------|
| `slots_upload` | `telechargement.slots_upload` | `TransferLimitSettings.upload_slots` | Aucune (entier) |
| `dossier_destination` | `telechargement.dossier_destination` | `SharesSettings.download` | Aucune (chemin) |
| `intervalle_rapport` | `telechargement.intervalle_rapport` | `TransfersSettings.report_interval` | **÷ 1000** (ms → secondes) |

---

## 5. Flux complet (démarrage → réseau Soulseek)

```
Démarrage application
        │
        ▼
soulseek_client.py (initialisation)
        │
        ├── lit telechargement.slots_upload (2)
        ├── lit telechargement.dossier_destination ("")
        └── lit telechargement.intervalle_rapport (250)
              │
              ▼
        Settings(
          shares=SharesSettings(
            download="Q:/Downloads/Soulseek",
            ...
          ),
          transfers=TransfersSettings(
            limits=TransferLimitSettings(
              upload_slots=2,
            ),
            report_interval=0.25,    # 250 ms → 0.25 s
          ),
        )
              │
              ▼
        aioslsk client.init()
              │
              ├── upload_slots=2 → max 2 uploads simultanés
              ├── download=... → dossier de sauvegarde des fichiers
              └── report_interval=0.25 → callback progression toutes les 0.25s
```

---

## 6. Notes techniques

- **`slots_upload` minimum à 1** : l'UI bloque à 1 (impossible de mettre 0), évitant un refus total d'upload.
- **Dossier vide = dossier par défaut** : si `dossier_destination` est vide, Soulseek utilise son dossier par défaut (généralement `~/Soulseek Downloads` ou équivalent).
- **Conversion ms → secondes** : `intervalle_rapport` est stocké en millisecondes dans `app_config` (plus lisible pour l'utilisateur) mais converti en secondes (`÷ 1000.0`) pour l'API aioslsk qui attend un `float` en secondes.
- **Intervalle minimum 50 ms** : l'UI bloque à 50 ms pour éviter une surcharge CPU due à des rapports trop fréquents.
- **`dossier_destination` partagé avec les Partages** : le paramètre `dossier_destination` (`SharesSettings.download`) est utilisé à la fois par la page Téléchargement et par la page [Configuration des partages](configuration-partages.md). Les deux pages configurent le même dossier de sauvegarde — une modification dans l'une affecte l'autre.
- **Prise d'effet au démarrage** : comme les autres pages de configuration, les modifications prennent effet au prochain démarrage de l'application.
- **Alias de page** : la page est accessible via l'alias `"Téléchargement"` → `"telechargements"` dans `_PAGE_ALIASES` (ligne 59), redirigeant vers le bot de téléchargement.

---

## Voir aussi

- [Configuration des partages](configuration-partages.md) — `SharesSettings.download` partagé avec les partages
- [Service app_config](service-app-config.md) — mécanisme de persistance atomique
- [Architecture de l'application](architecture-application.md) — vue d'ensemble des couches logicielles
- [Guide navigation interface](../interface/guide-navigation-interface.md) — accès à la page Téléchargement via le footer
