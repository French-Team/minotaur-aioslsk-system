# TEMPLATE — Carnet de Bord Agent

> **⚠️ FICHIER TEMPLATE — NE PAS MODIFIER**  
> Utilise ce fichier comme référence pour mettre à jour `agent-logbook.md`

---

## 🎯 État du Système

| # | Composant | Statut | Mission |
|---|-----------|--------|---------|
| 1 | **Core Engine** | ⏳ | Gestion des sessions, appels LLM, exécution d'outils asynchrones |
| 2 | **Guardian** | ⏳ | Sécurité et filtrage des commandes shell dangereuses |
| 3 | **Self-Correction** | ⏳ | Boucles de validation et auto-correction des sorties LLM |
| 4 | **Parallel Tools** | ⏳ | Exécution d'outils en parallèle pour la performance |
| 5 | **Scaffold Agent** | ⏳ | Création automatisée d'agents (nom, template, profil) |
| 6 | **Streaming UI** | ⏳ | Affichage progressif des réponses dans le terminal |
| 7 | **Intelligence Amont** | ⏳ | Profils dédiés à la Recherche Web, Code et Planification |
| 8 | **Banque de Profils** | ⏳ | Profils (agents, bots, daemons) — 0 stub |
| 9 | **Orchestration PACO** | ⏳ | Équipe (Orchestrateur, Superviseur) pilotant la certification |
| 10 | **Golden Rules** | ⏳ | Règles de validation : agent, skill, orchestration PACO |
| 11 | **Templates** | ⏳ | standard, fast, daemon, orchestration-team |

---

## ✅ Étapes Terminées

| Phase | Description | Points clés |
|-------|-------------|-------------|
| — | — | — |

---

## 📊 Profils — 0 / 598 complétés

| Type | Quantité | Statut |
|------|----------|--------|
| Agents | 226 | ⏳ En cours |
| Bots | 269 | ⏳ En cours |
| Daemons | 103 | ⏳ En cours |
| **Total** | **598** | **À compléter** |

---

## 🧩 Architecture

```
src/
├── engine.ts             # Cœur du moteur (Sessions, LLM, Tools)
├── cli.ts                # Interface interactive + logique de création
├── agents.ts             # Gestion fichiers agents et profils
├── providers.ts          # Gestion des providers LLM
├── generate-skill.ts     # Génération et validation de skills
├── skills.ts             # Chargement des skills
├── spawn-agent.ts        # Exécution d'agents en arrière-plan
├── validate-agent.ts     # Validation autonome d'un agent
├── notify.ts             # Notifications inter-processus
└── tmux.ts               # Wrapper tmux (Unix only)

data/
├── profiles/             # 598 profils (agents/, bots/, daemons/)
├── protocols/            # PACO : keyword-registry.yaml, paco-protocol.md
├── golden-rules/         # Règles de validation : agent, skill, orchestration
├── templates/            # Templates TS pour scaffolding
└── agent-name/           # Données pour génération de noms

.agents/                  # Agents runtime
├── alice.ts              # Interface utilisateur principale
├── orchestrateur.ts      # Orchestrateur PACO
├── agent-superviseur.ts  # Superviseur PACO
├── DAEMON-superviseur-01.ts # Daemon de supervision
├── agent-hecatonchires.ts # Pisteur de projet
└── agent-reviewer.ts     # Revue de code
```

---

## 📜 Protocole PACO

- **Registre de mots-clés** : Mapping mots-clés → agents spécialisés
- **Orchestrateur** : Zéro production directe, délégation obligatoire
- **Superviseur** : Scrutation toutes les 5 min, 3 violations → suspension
- **Golden rules** : Règles critiques validant l'équipe d'orchestration

---

## 📝 Instruction Actuelle

<!-- L'agent met à jour cette section avec l'instruction en cours -->

**Instruction :** À définir  
**Statut :** ⏳ En attente  
**Progression :** 0%

---

## 🔜 Prochaines Étapes

1. Lire instruction dans `.in_out/user-instructions.md`
2. Analyser les prérequis et contexte
3. Exécuter les étapes demandées
4. Mettre à jour ce carnet de bord
5. Rapporter progression et résultats

---

## 📋 Légende des Statuts

| Symbole | Signification |
|---------|---------------|
| ✅ | Complété / Succès |
| ⏳ | En cours / En attente |
| ❌ | Échoué / Bloqué |
| 🔄 | En révision / À corriger |
| ⚠️ | Attention requise |

---

**Dernière mise à jour :** YYYY-MM-DD  
**Agent :** À définir  
**Instruction ID :** À définir
