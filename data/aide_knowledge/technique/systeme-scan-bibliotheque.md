---
title: "Système de scan de bibliothèque (LibraryScanner)"
category: technique
icon: 📂
keywords:
  - LibraryScanner scan bibliotheque
  - LibraryScanner scan bibliothèque
  - library_scanner.py
  - _ScanWorker thread
  - scan worker qthread
  - scan bibliotheque asynchrone
  - scan bibliothèque asynchrone
  - LibraryScanner start scan
  - LibraryScanner cancel
  - scan progress signal
  - scan completed signal
  - scan error signal
  - _count_files estimation
  - IGNORED_EXTENSIONS scan
  - extension ignoree scan
  - extension ignorée scan
  - library_db scan all
  - scan all callback progression
  - QThread scan worker
  - thread secondaire scan
  - scan annulation propre
  - _on_worker_completed
  - _on_worker_error
  - _on_worker_finished
  - nettoyage thread scan
  - ScanResult scan
  - scan dossier partage
  - scan dossier partagé
  - scan repertoire recursion
  - scan répertoire récursion
  - scan progress callback
  - comptage fichier scan
  - comptage fichiers scan
  - bot bibliotheque scan
  - progression scan pourcentage
  - scan annulation utilisateur
  - scan cancelled flag
  - arret scan propre
  - arrêt scan propre
  - systeme scan fichier
  - système scan fichier
  - scan bibliotheque performance
  - scan bibliothèque performance
  - scan asynchrone
  - analyseur bibliotheque
  - analyseur bibliothèque
---

# 📂 Système de scan de bibliothèque (LibraryScanner)

## Introduction

Le module `src/services/library_scanner.py` (209 lignes) gère le **scan de la bibliothèque de fichiers partagés** dans un thread séparé, permettant à l'interface de rester réactive pendant l'analyse des dossiers.

Il utilise le pattern **QObject + QThread** : un `_ScanWorker` exécute le scan dans un thread secondaire, tandis que `LibraryScanner` (dans le thread principal) gère l'interface avec l'UI via des signaux.

---

## Architecture

```
Thread UI (principal)                    Thread secondaire
      │                                       │
      │  LibraryScanner.start_scan()           │
      │─────► QThread.start() ───────────────► _ScanWorker.run()
      │                                       │
      │  ┌─ signals ──────────────────────┐   │
      │  │ scan_progress(current, total)  │◄──┤  _progress_cb()
      │  │ scan_completed(ScanResult)     │◄──┤  completion
      │  │ scan_error(message)           │◄──┤  exception
      │  └────────────────────────────────┘   │
      │                                       │
      │  LibraryScanner.cancel()               │
      │─────► worker.cancel() ───────────────► _cancelled = True
      │                                       │
      │  _on_worker_finished()                 │
      │  (nettoie _worker, _thread, _running)  │
      │                                       │
```

---

## Classe `_ScanWorker(QObject)`

Classe **interne** exécutée dans le thread secondaire. Elle n'a pas de signaux directement exposés à l'UI — ils passent par `LibraryScanner`.

### `run()`

Point d'entrée du thread :

```python
def run(self) -> None:
    try:
        total = self._count_files()
        if self._cancelled:
            self.finished.emit()
            return

        result = self._db.scan_all(self._progress_cb)
        if self._cancelled:
            self.finished.emit()
            return

        self.completed.emit(result)
    except Exception as e:
        self.error.emit(str(e))
    finally:
        self.finished.emit()
```

Étapes :
1. **Comptage** : estime le nombre total de fichiers via `_count_files()`
2. **Vérification annulation** : si `_cancelled`, arrêt immédiat
3. **Scan effectif** : appelle `self._db.scan_all(callback)` qui parcourt les dossiers et indexe les fichiers
4. **Nouvelle vérification annulation** : après le scan, avant d'émettre le résultat
5. **Émission** : `completed(ScanResult)` ou `error(str)` selon le résultat
6. **Toujours** : `finished` émis dans le `finally`

### `cancel()`

```python
def cancel(self) -> None:
    self._cancelled = True
```

Positionne un drapeau `_cancelled` vérifié régulièrement dans `run()`.

### `_count_files()`

Estimation du nombre total de fichiers à scanner :

```python
def _count_files(self) -> int:
    total = 0
    for dossier in self._db.get_dossiers():
        for chemin in Path(dossier).rglob("*"):
            if chemin.suffix.lower() not in IGNORED_EXTENSIONS:
                total += 1
    return total
```

- Itère sur les dossiers enregistrés dans `LibraryDB`
- Parcourt récursivement avec `Path.rglob("*")`
- Filtre les extensions ignorées (`IGNORED_EXTENSIONS`)
- Utilisé pour la barre de progression

---

## Classe `LibraryScanner(QObject)`

Interface publique qui gère le cycle de vie du thread de scan.

### Signaux exposés

| Signal | Arguments | Description |
|--------|-----------|-------------|
| `scan_started` | — | Émis quand le scan commence |
| `scan_progress` | `int current, int total` | Mise à jour progression |
| `scan_completed` | `ScanResult result` | Scan terminé avec succès |
| `scan_error` | `str message` | Erreur pendant le scan |

### `start_scan()`

```python
def start_scan(self) -> None:
    if self._running:
        return  # Évite les scans concurrents

    self._running = True
    self._thread = QThread(self)
    self._worker = _ScanWorker(self._db)

    self._worker.moveToThread(self._thread)

    self._thread.started.connect(self._worker.run)
    self._worker.finished.connect(self._thread.quit)
    self._worker.finished.connect(self._worker.deleteLater)
    self._thread.finished.connect(self._thread.deleteLater)
    self._worker.completed.connect(self._on_worker_completed)
    self._worker.error.connect(self._on_worker_error)
    self._worker.finished.connect(self._on_worker_finished)

    self.scan_started.emit()
    self._thread.start()
```

Points clés :
- **Protection** : `if self._running: return` empêche les scans concurrents
- **Connexions** : le worker est déplacé dans le thread via `moveToThread()`
- **Nettoyage** : `deleteLater` sur worker et thread, `quit` sur le thread
- **File d'attente** : tous les signaux sont en `AutoConnection` (deviennent `QueuedConnection` entre threads)

### `cancel()`

```python
def cancel(self) -> None:
    if self._worker:
        self._worker.cancel()
```

Délègue l'annulation au `_ScanWorker` qui positionne `_cancelled`.

### `_on_worker_completed(result)`

```python
def _on_worker_completed(self, result) -> None:
    if self._cancelled:
        return  # Ignore si l'utilisateur a annulé
    self.scan_completed.emit(result)
```

### `_on_worker_error(message)`

```python
def _on_worker_error(self, message: str) -> None:
    if self._cancelled:
        return
    self.scan_error.emit(message)
```

### `_on_worker_finished()`

```python
def _on_worker_finished(self) -> None:
    self._worker = None
    self._thread = None
    self._running = False
```

**Nettoyage systématique** : remet tout à `None`/`False` pour permettre un nouveau scan.

---

## Interaction avec LibraryDB

`LibraryScanner` utilise `LibraryDB` pour :
1. **Lister les dossiers** : `self._db.get_dossiers()` → utilisé dans `_count_files()`
2. **Scanner les fichiers** : `self._db.scan_all(callback)` → le scan effectif

Le scan est donc une opération **synchrone** dans le thread secondaire : `scan_all()` parcourt les fichiers et les indexe dans la base SQLite.

### Callback de progression

```python
def _progress_cb(self, current: int, total: int) -> None:
    self.progress.emit(current, total)
```

La callback reçoit `(current, total)` et émet le signal `progress` qui transmet à `LibraryScanner` → `scan_progress.emit()` vers l'UI.

### ScanResult

```python
@dataclass
class ScanResult:
    total: int           # Nombre total de fichiers traités
    ajoutes: int         # Nouveaux fichiers ajoutés à la base
    supprimes: int       # Fichiers supprimés retirés de la base
    duree: float         # Durée du scan en secondes
```

`ScanResult` est retourné via le signal `scan_completed(ScanResult)` et contient le bilan du scan.

---

## Cycle de vie complet

```
1. start_scan()
      │
2. Vérifie _running (refus si déjà actif)
      │
3. Crée QThread + _ScanWorker
      │
4. moveToThread() + connecte signaux
      │
5. _thread.start()
      │
      ├── _ScanWorker.run()
      │       │
      │       ├── _count_files() → total estimé
      │       │
      │       ├── scan_all(callback) → scan effectif
      │       │       │
      │       │       └── émet scan_progress(current, total)
      │       │
      │       ├── completed(ScanResult)  OU  error(str)
      │       │
      │       └── finished() (toujours)
      │
      ├── _on_worker_completed → scan_completed.emit()
      │   _on_worker_error    → scan_error.emit()
      │
      └── _on_worker_finished → nettoyage (_worker = None, etc.)
```

### Annulation utilisateur

```
cancel()
  │
  └── worker.cancel() → _cancelled = True
                          │
                          ├── run() vérifie _cancelled après comptage
                          ├── run() vérifie _cancelled après scan_all
                          ├── _on_worker_completed ignore si cancelled
                          └── _on_worker_error ignore si cancelled
```

---

## Conclusion

Le système `LibraryScanner` suit le pattern standard Qt pour les opérations longues :

| Aspect | Détail |
|--------|--------|
| **Pattern** | `QObject` worker + `QThread` — standard Qt pour UI réactive |
| **Sécurité** | `_running` flag évite les scans concurrents |
| **Annulation** | `_cancelled` vérifié à 2 endroits dans `run()` + dans les callbacks |
| **Nettoyage** | `deleteLater` + réinitialisation dans `_on_worker_finished` |
| **Progression** | `_count_files()` estime le total avant le scan |
| **Performance** | Le scan lourd s'exécute dans un thread séparé, l'UI reste fluide |
