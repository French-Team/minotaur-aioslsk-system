---
title: "UPnP, ports et obfuscation — Configuration réseau"
category: faq
keywords: ["upnp", "port", "ecoute", "écoute", "obfuscation", "routeur", "firewall", "pare-feu", "connexion entrante", "port mapping"]
---

## UPnP, ports et obfuscation — Configuration réseau

### Pourquoi configurer les ports ?

Les ports d'écoute permettent aux autres utilisateurs Soulseek de se connecter à toi pour télécharger tes fichiers. Sans configuration correcte, tu peux uniquement télécharger, mais pas partager efficacement.

### UPnP : automatique ou manuel ?

**UPnP activé** (recommandé) :
- L'application configure automatiquement ton routeur
- Aucune manipulation manuelle nécessaire
- Active UPnP dans les deux : application ET routeur

**UPnP désactivé** :
- Tu dois ouvrir manuellement les ports sur ton routeur
- Plus complexe mais plus de contrôle

### Vérifier si UPnP fonctionne

1. Va dans **Optimiseur** → onglet **Réseau**
2. Active **UPnP** (toggle)
3. Vérifie que le **Port d'écoute** est libre (défaut : `60000`)
4. Redémarre l'application
5. Si les connexions entrantes fonctionnent, c'est bon

### Problèmes fréquents

| Problème | Cause | Solution |
|----------|-------|----------|
| UPnP ne fonctionne pas | UPnP désactivé sur le routeur | Active UPnP dans l'interface de ton routeur |
| Port déjà utilisé | Une autre application utilise le port | Change le port d'écoute (ex: `60002`) |
| Connexions entrantes bloquées | Firewall local | Ajoute l'application à la liste blanche du firewall |
| Obfuscation inefficace | FAI bloque ou ralentit le P2P | Active l'obfuscation P2P dans Réseau |

### Obfuscation P2P — Quand l'utiliser ?

L'obfuscation masque le trafic Soulseek pour qu'il ressemble à du trafic web classique. Active-la si :
- Ton FAI limite ou bloque le trafic peer-to-peer
- Tu es sur un réseau d'entreprise ou scolaire
- Tu remarques que tes connexions sont systématiquement lentes

**Inconvénient** : légère perte de performance (~5-10%).

### Configuration manuelle (sans UPnP)

Si UPnP n'est pas disponible :

1. Trouve l'adresse IP de ton routeur (souvent `192.168.1.1` ou `192.168.0.1`)
2. Connecte-toi à l'interface d'administration
3. Trouve la section **Redirection de ports** ou **Port Forwarding**
4. Ajoute une règle :
   - Port externe : `60000` (ou ton port d'écoute)
   - Port interne : `60000`
   - Protocole : `TCP`
   - IP de destination : l'IP locale de ton PC
5. Sauvegarde et redémarre l'application
