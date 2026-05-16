# Instructions — Projet Ordonnanceur

**Agent, lis et exécute les tâches ci-dessous immédiatement.**

---

## Objectif Principal

Développer **l'Ordonnanceur**, un outil d'organisation de fichiers audio
accessible en CLI et GUI. L'utilisateur s'appelle **Ordonnanceur**.

L'Ordonnanceur analyse, renomme, classe, dédoublonne et nettoie
les fichiers audio téléchargés.

---

## Ce qui est déjà construit

### Backend — `src/services/ordonnanceur_service.py` ✅
- Analyse de dossier (scan récursif, tags mutagen, pattern filename)
- Renommage intelligent (template personnalisable, presets)
- Classement artiste/album (structure configurable, presets)
- Dédoublonnage (nom+taille → SHA256, règle de conservation)
- Nettoyage temporaire (âge + extension)
- Résolution automatique des conflits de noms
- Exécution réelle des opérations sur le disque
- **128 tests unitaires — ✅ verts**

### CLI — `src/cli_ordonnanceur.py` ✅
- Preview console formatée (renommage, classement, déduplication, nettoyage)
- `--executer` pour appliquer les opérations
- `--dry-run` pour forcer la simulation
- **16 tests — ✅ verts**

### GUI — `src/gui/widgets/bots/bot_ordonnanceur.py` 🏗️
- Structure 4 étapes : Choix → Aperçu → Exécution → Rapport
- UI construite mais service backend **non branché**
- **553 lignes** — à connecter à `ordonnanceur_service`

---

## Prochaines actions

1. **Brancher le service dans le GUI** — connecter `ordonnanceur_service`
   aux méthodes du `BotOrdonnanceur` (analyse, preview, execution)
2. **Tests d'intégration GUI** — tests avec `pytest-qt`
3. **Intégration Planificateur** — exposer les actions individuelles
4. **Auto au démarrage** — hook optionnel
5. **Améliorations** — corbeille, barre de progression, i18n

---

## Conventions

- Service : `src/services/ordonnanceur_service.py`
- CLI : `src/cli_ordonnanceur.py` (argparse, `python -m src.cli_ordonnanceur`)
- GUI : `src/gui/widgets/bots/bot_ordonnanceur.py` (PySide6)
- Tests : `tests/test_ordonnanceur_service.py` + `test_cli_ordonnanceur.py`
- Documentation : `.aioslsk-logbook.md` + `specs/bot-ordonnanceur-spec.md`

## Mise à jour du Logbook

Tout progrès doit être consigné dans `.aioslsk-logbook.md` avec :
- **Date & Heure**
- **Tâche**
- **Résultat**
- **Problèmes rencontrés**
- **Solution / prochaine étape**
