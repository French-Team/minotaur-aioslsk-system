---
title: "Paramètres réseau et ports (ListeningConnectionFailedError)"
category: faq
icon: 🔌
keywords:
  - parametre reseau port
  - paramètre réseau port
  - port ecoute soulseek
  - port écoute soulseek
  - port ecoute 60000
  - port écoute 60000
  - port obfusque 60001
  - port obfusqué 60001
  - port serveur 2416
  - port 2416 soulseek
  - port 60000 p2p
  - port 60001 obfusque
  - port 60001 obfusqué
  - reseau port ecoute defaut
  - réseau port écoute défaut
  - ListeningConnectionFailedError
  - port ecoute bloque
  - port écoute bloqué
  - firewall soulseek
  - parefeu soulseek
  - pare-feu soulseek
  - ouvrir port firewall
  - port bloquee application
  - port bloquée application
  - changer port ecoute
  - changer port écoute
  - configuration reseau soulseek
  - configuration réseau soulseek
  - port p2p
  - port obfuscation soulseek
  - reseau port obfusque
  - réseau port obfusqué
  - port serveur soulseek
  - server slsknet org port
  - connexion ecoute bloquee
  - connexion écoute bloquée
  - impossible ouvrir port ecoute
  - impossible ouvrir port écoute
  - port deja utilise
  - port déjà utilisé
  - conflit port soulseek
  - nicotin port defaut
  - soulseekqt port defaut
  - quel port ouvrir firewall
  - port tcp soulseek
  - parametre reseau recommand
  - paramètre réseau recommandé
  - erreur port configuration
  - port ecoute erreur
  - port écoute erreur
  - ListeningSettings port
  - listening settings
  - NetworkSettings soulseek
  - config reseau port
  - config réseau port
  - port bloque parefeu
  - port bloqué pare-feu
  - diagnostic port reseau
  - diagnostic port réseau
  - verification port ecoute
  - vérification port écoute
  - netstat port ecoute
  - netstat port écoute
  - telnet port soulseek
  - tester port soulseek
  - configuration avancee reseau
  - configuration avancée réseau
---

# 🔌 Paramètres réseau et ports

## Introduction

L'application utilise plusieurs ports réseau pour communiquer sur le réseau Soulseek. Cette FAQ détaille chaque port, son rôle, et comment résoudre les problèmes courants.

---

## Quels ports l'application utilise-t-elle ?

| Port | Rôle | Valeur par défaut |
|------|------|-------------------|
| **Port d'écoute** | Connexions P2P entrantes (partage de fichiers, transferts) | `60000` |
| **Port obfusqué** | Connexions P2P avec obfuscation (contournement des filtres FAI) | `60001` |
| **Port serveur** | Connexion au serveur central Soulseek (`server.slsknet.org`) | `2416` |

### Port d'écoute (P2P) — 60000

Le port d'écoute est le plus important. Il reçoit les connexions entrantes des autres pairs Soulseek. **Si ce port est bloqué, les autres utilisateurs ne pourront pas se connecter à votre bibliothèque.**

- Protocole : **TCP**
- Configuration : `reseau.port_ecoute` dans `app_config.py`
- Erreur associée : `ListeningConnectionFailedError` → "🔌 Impossible d'ouvrir le port d'écoute"

### Port obfusqué — 60001

L'obfuscation du port permet de **masquer le trafic Soulseek** aux yeux des fournisseurs d'accès qui pourraient limiter le trafic P2P.

- Se place généralement juste à côté du port d'écoute (`port_ecoute + 1`)
- Nécessite aussi d'être ouvert dans le firewall
- Configuration : `reseau.port_obfusque`

### Port serveur — 2416

Le port de connexion au **serveur central Soulseek** (`server.slsknet.org:2416`). Ce port **n'a pas besoin d'être ouvert** dans votre firewall — c'est une connexion sortante.

- C'est toujours le port **2416** pour le réseau officiel Soulseek
- Un timeout sur ce port signifie que le serveur central est injoignable

> **Note** : D'autres clients Soulseek utilisent des ports par défaut différents :
> - **Nicotine+** : port d'écoute 2234
> - **SoulseekQt officiel** : port d'écoute 2242
> 
> L'application utilise 60000 pour éviter les conflits avec d'autres logiciels.

---

## Où configurer les ports ?

Dans l'interface, ouvrez **Configuration** → onglet **Réseau** :

1. **Port d'écoute** : champ lié à la clé `reseau.port_ecoute`
2. **Port obfusqué** : champ lié à la clé `reseau.port_obfusque`
3. **Port serveur** : champ lié à la clé `reseau.port_serveur` (description : "Port du serveur Soulseek (défaut: 2416).")

Après modification d'un port, **redémarrez l'application** pour que les changements prennent effet.

---

## ListeningConnectionFailedError — Le port d'écoute ne s'ouvre pas

### Causes possibles

| Cause | Symptôme | Solution |
|-------|----------|----------|
| Port déjà utilisé | `ListeningConnectionFailedError` immédiat au démarrage | Changer le port d'écoute (ex: 60002) |
| Bloqué par le firewall | L'application se connecte au serveur mais les pairs ne peuvent pas vous joindre | Ajouter le port à la liste blanche du pare-feu |
| Bloqué par l'antivirus | Même comportement que le firewall | Ajouter une exception dans l'antivirus |
| Permissions insuffisantes (Linux) | Erreur "Permission denied" sur les ports < 1024 | Utiliser un port > 1024 (60000 par défaut) |

### Comment vérifier si le port est ouvert ?

Sur Windows :
```
netstat -an | findstr 60000
```

Sur Linux / macOS :
```bash
netstat -an | grep 60000
```

Si la ligne suivante apparaît, le port est bien à l'écoute :
```
TCP    0.0.0.0:60000     0.0.0.0:0     LISTENING
```

### Tester le port depuis l'extérieur

Utilisez un scanneur de ports en ligne ou la commande suivante depuis une autre machine :
```bash
telnet <votre_ip> 60000
```

Si la connexion est refusée ou timeout, le port est bloqué.

---

## Comment ouvrir un port dans le pare-feu ?

### Windows Defender Firewall

1. Ouvrir **Pare-feu Windows Defender avec sécurité avancée**
2. Cliquer sur **Règles de trafic entrant** → **Nouvelle règle**
3. Type : **Port** → Suivant
4. **TCP** → **Ports locaux spécifiques :** `60000` (et `60001` si besoin)
5. Action : **Autoriser la connexion**
6. Profil : cocher **Privé** (et Domain si applicable)
7. Nommer la règle : `FreeBuff Soulseek - Port d'écoute`

### Linux (UFW)
```bash
sudo ufw allow 60000/tcp
sudo ufw allow 60001/tcp
```

### macOS
1. **Préférences Système** → **Réseau** → **Pare-feu**
2. **Options du pare-feu** → **Ajouter une application**
3. Ajouter l'application à la liste des applications autorisées

> **Attention** : Ajouter l'application elle-même à la liste blanche du pare-feu est parfois **insuffisant** — il faut aussi ouvrir **explicitement le port TCP**.

---

## Questions fréquentes

### Pourquoi le port par défaut est 60000 et pas 2242 ?

Pour éviter les conflits avec d'autres logiciels qui pourraient déjà utiliser les ports classiques (SoulseekQt → 2242, Nicotine+ → 2234). Le port 60000 se situe dans une plage rarement utilisée.

### Dois-je ouvrir le port serveur 2416 ?

**Non.** Le port 2416 est une connexion **sortante** vers le serveur Soulseek. Il n'a pas besoin d'être ouvert dans votre firewall. C'est le port d'écoute (60000) qui doit être ouvert pour les connexions entrantes.

### Est-ce dangereux d'ouvrir un port ?

Un port ouvert en TCP permet uniquement la réception de connexions. La sécurité dépend de l'application qui écoute sur ce port. L'application utilise le protocole Soulseek qui ne sert qu'aux transferts de fichiers. Assurez-vous d'utiliser un **pare-feu** pour contrôler les connexions.

### Que faire si mon FAI bloque le port ?

Certains fournisseurs d'accès limitent le trafic P2P. Solutions :
1. Activer le **port obfusqué** (60001) qui masque le protocole
2. Changer le port d'écoute vers un port couramment ouvert (443, 993, 5222)
3. Utiliser un **VPN** pour contourner les limitations FAI

### Comment savoir si mon port d'écoute fonctionne ?

1. Lancez l'application et connectez-vous à Soulseek
2. Vérifiez dans **Configuration** que le port d'écoute est bien renseigné
3. Si d'autres utilisateurs peuvent télécharger vos fichiers, le port fonctionne
4. En cas de `ListeningConnectionFailedError`, suivez les étapes de diagnostic ci-dessus
