# Instructions pour l'Agent (à exécuter)

**Agent, lis et exécute les tâches ci‑dessous immédiatement.**

## Objectif Principal
Développer une interface utilisateur conviviale pour Soulseek, accessible via 12 bots, sans que l'utilisateur n'ait besoin de connaître les rouages de Soulseek.

## Priorités Actuelles (Phase 2 – Bots essentiels)
1. **Bot Accueil** – Reprendre et finaliser le travail sur `home.py`.
2. **Bot Recherche** – Développer l'interface et la logique de recherche Soulseek.
3. **Bot Téléchargement** – Mettre en place la gestion des téléchargements.
4. **Bot Assistant** – Créer une interface de configuration guidée.

## État de la Connexion Backend
La connexion au serveur Soulseek a déjà été vérifiée avec succès (`ConnexionManager`). **Ne pas refaire la vérification**.

## Tâches à exécuter immédiatement
- **Bot Recherche** : finaliser l’UI, afficher les résultats de recherche (utiliser le signal `search_result_received`).
- **Bot Téléchargement** : implémenter la file d’attente, le suivi et l’état des téléchargements.
- **Bot Assistant** : créer l’interface de configuration guidée.
- **Documentation** : à chaque étape, ajouter une entrée détaillée dans `.aioslsk-logbook.md` (progrès, obstacles, solutions).

## Mise à jour du Logbook
- Tout progrès doit être consigné dans `.aioslsk-logbook.md`.
- Utiliser le format suivant pour chaque entrée :
  - **Date & Heure**
  - **Tâche**
  - **Résultat**
  - **Problèmes rencontrés**
  - **Solution / prochaine étape**

---
**Agent, prends ces instructions comme directives à exécuter et mets à jour le logbook dès que chaque tâche est complétée.**

## Objectif Principal
Développer une interface utilisateur conviviale pour Soulseek, accessible via 12 bots, sans que l'utilisateur n'ait besoin de connaître les rouages de Soulseek.

## Priorités Actuelles (Phase 2 - Bots essentiels)

1.  **Bot Accueil :** Reprendre et finaliser le travail sur `home.py`.
2.  **Bot Recherche :** Développer l'interface et la logique pour les fonctionnalités de recherche de Soulseek.
3.  **Bot Téléchargement :** Mettre en place la gestion des téléchargements.
4.  **Bot Assistant :** Créer une interface pour une configuration guidée.

## Connexion au Backend déjà Vérifiée

Le logbook indique que la connexion au serveur Soulseek a été testée avec succès (voir section "✅ Vérification de la connexion Soulseek (backend)"), et que le `ConnexionManager` fonctionne correctement. Aucun besoin de répéter cette vérification.

**Prochaines actions attendues**

1. **Bot Recherche** – Finaliser l'interface utilisateur et afficher les résultats de recherche (utiliser le signal `search_result_received`).
2. **Bot Téléchargement** – Implémenter la gestion des téléchargements (queue, suivi, état).
3. **Bot Assistant** – Créer l'interface de configuration guidée.
4. **Documentation** – Continuer à consigner chaque étape et tout obstacle dans `.aioslsk-logbook.md`.

## Mise à Jour du Logbook
Veuillez maintenir le fichier `.aioslsk-logbook.md` à jour avec votre progression, les défis rencontrés et les solutions apportées. C'est notre point de communication principal pour suivre l'avancement.
