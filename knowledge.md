# Project knowledge

This file gives Freebuff context about your project: goals, commands, conventions, and gotchas.

## What this is
**L'Ordonnanceur** — un outil CLI + GUI pour organiser les fichiers audio : renommer, classer par artiste/album, dédoublonner (hash SHA256), et nettoyer les fichiers temporaires.

## Quickstart
- **Lancer le CLI :** `python -m src.cli_ordonnanceur DOSSIER`
- **Lancer les tests :** `python -m pytest tests/`
- **Preview sans risque :** `python -m src.cli_ordonnanceur DOSSIER` (simulation par défaut)
- **Exécuter pour de vrai :** `python -m src.cli_ordonnanceur DOSSIER --executer`

## Key directories
| Path | Purpose |
|------|---------|
| `src/services/ordonnanceur_service.py` | Backend complet (1652 lignes) — analyse, renommage, classement, déduplication, nettoyage, exécution |
| `src/cli_ordonnanceur.py` | CLI (432 lignes) — preview console + --executer |
| `src/gui/widgets/bots/bot_ordonnanceur.py` | GUI Qt (553 lignes) — assistant 4 étapes (service non branché) |
| `tests/test_ordonnanceur_service.py` | 128 tests backend |
| `tests/test_cli_ordonnanceur.py` | 16 tests CLI |
| `specs/bot-ordonnanceur-spec.md` | Spécification détaillée |
| `.aioslsk-logbook.md` | Carnet de bord du projet |

## Architecture

```python
# Flux principal
analyse = svc.analyser_dossier(dossier)         # scan + tags mutagen
apercu = svc.generer_apercu(analyse, ops)        # preview
resultat = svc.executer_operations(apercu)       # apply (ou simuler)
```

- **4 opérations :** renommage, classement, deduplication, nettoyage
- **Simulation par défaut** — rien n'est modifié sans `--executer`
- **Résolution de conflits** — suffixes _2, _3… automatiques
- **Dédoublonnage** — passe rapide (nom+taille) → passe sûre (SHA256 64Ko)

## Tests
- **783 tests verts** dans tout le projet
- `python -m pytest tests/` pour tout lancer
- `python -m pytest tests/test_ordonnanceur_service.py::TestExecuterOperations -v` pour un sous-ensemble

## CLI commands
| Commande | Description |
|----------|-------------|
| `python -m src.cli_ordonnanceur --help` | Aide complète |
| `python -m src.cli_ordonnanceur DOSSIER` | Preview simulation |
| `python -m src.cli_ordonnanceur DOSSIER --executer` | Exécution réelle |
| `python -m src.cli_ordonnanceur DOSSIER --ops renommage classement` | Opérations filtrées |
| `python -m src.cli_ordonnanceur DOSSIER --template-renommage "{artist} - {title}.{ext}"` | Template personnalisé |

## Conventions
- **Langue des docs :** français (projet francophone)
- **Code :** Python 3.12+, type hints partout
- **Tests :** pytest, fixtures tmp_path pour les fichiers temporaires
- **CLI :** argparse, `python -m src.cli_ordonnanceur`

## Things to avoid
- Ne pas lancer d'opérations destructives sans confirmation utilisateur (toucher au disque)
- Ne pas modifier les fichiers des anciens bots Soulseek sans demande explicite
- Toujours utiliser `simuler=True` par défaut — `--executer` est une action explicite de l'utilisateur
