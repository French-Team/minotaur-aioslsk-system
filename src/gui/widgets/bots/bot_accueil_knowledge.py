"""
Dictionnaire de connaissances du bot Accueil.

Chaque entrée contient :
- keywords : list[str] — mots-clés déclencheurs (matché insensiblement)
- icon : str — emoji affiché dans la réponse
- response : str — texte de réponse (support RichText)
- actions : list[dict] — actions à exécuter après la réponse (optionnel)
    Types d'actions disponibles :
    {"type": "navigate", "bot": "BotName"} — redirige vers un bot après 1.5s
    {"type": "delay", "ms": 500} — attend N ms
    {"type": "message", "icon": "...", "text": "..."} — message supplémentaire
    {"type": "suggestions", "items": [...]} — suggestions personnalisées
    {"type": "start_loop", "bot": "BotName"} — démarre la boucle d'un bot
    {"type": "stop_loop", "bot": "BotName"} — arrête la boucle d'un bot
    {"type": "start_loop_and_navigate", "bot": "BotName"} — start_loop + navigate combinés
- suggestions : list[dict] — boutons de suggestion affichés après la réponse
    Chaque item : {"label": "...", "action": "..."}
"""

KNOWLEDGE: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════════
    # Navigation vers les bots
    # ═══════════════════════════════════════════════════════════
    "chercher": {
        "keywords": [
            "chercher",
            "recherche",
            "rechercher",
            "trouver",
            "cherche",
            "fichier",
            "fichiers",
            "search",
            "file",
            "files",
            "trouve",
            "recherches",
            "mot clé",
            "mot-clé",
            "mot cle",
            "cherche moi",
            "recherche moi",
        ],
        "icon": "🔍",
        "response": "Bien sûr ! <b>Athéna</b>, la déesse de la sagesse, est spécialisée "
        "dans la recherche de fichiers sur Soulseek. "
        "Je t'envoie vers elle !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Recherche"},
        ],
        "suggestions": [
            {"label": "🔍 Oui, cherche !", "action": "chercher"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "telechargement": {
        "keywords": [
            "téléchargement",
            "telechargement",
            "télécharger",
            "telecharger",
            "dl",
            "download",
            "downloads",
            "télécharge",
            "telecharge",
            "fichier en cours",
            "mes téléchargements",
            "en cours de dl",
            "queued",
            "file d'attente",
            "file attente",
            "progression",
            "avancement dl",
        ],
        "icon": "📥",
        "response": "Pas de souci ! <b>Hadès</b>, le dieu des enfers, s'occupe "
        "de gérer, suivre et prioriser tes téléchargements. "
        "Je te l'envoie !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Téléchargement"},
        ],
        "suggestions": [
            {"label": "📥 Voir mes DL", "action": "telechargement"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "aide": {
        "keywords": [
            "aide",
            "help",
            "assistance",
            "besoin d'aide",
            "comment",
            "guide",
            "explication",
            "explications",
            "aide-moi",
            "help me",
            "problème",
            "probleme",
            "bug",
            "souci",
            "je comprends pas",
            "comprends pas",
            "tuto",
            "tutoriel",
            "manuel",
            "doc",
            "documentation",
        ],
        "icon": "❓",
        "response": "Tu as besoin d'explications ou d'aide ? "
        "<b>Dionysos</b>, le dieu de la libération, connaît tout sur l'application "
        "et ses 12 dieux. Je te redirige vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Aide"},
        ],
        "suggestions": [
            {"label": "❓ Aide-moi !", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "bibliotheque": {
        "keywords": [
            "bibliothèque",
            "bibliotheque",
            "library",
            "biblio",
            "explorer",
            "parcourir",
            "dossier",
            "dossiers",
            "fichier partagé",
            "fichiers partagés",
            "fichier local",
            "fichiers locaux",
            "scanne",
            "scan",
            "scanner",
            "scan bibliothèque",
            "bibliothèque partagée",
            "partage",
            "partagé",
            "shared",
            "dossier partagé",
            "dossiers partagés",
            "arborescence",
            "mes fichiers",
            "contenu local",
            "mon dossier",
        ],
        "icon": "📚",
        "response": "<b>Déméter</b>, la déesse de l'abondance, est ton explorateur "
        "de fichiers partagés !<br><br>"
        "🔹 <b>Scan</b> — analyse tes dossiers partagés "
        "avec progression en direct<br>"
        "🔹 <b>Arborescence</b> — navigue par dossier "
        "dans l'arbre à gauche<br>\n"
        "🔹 <b>Tableau</b> — tous les fichiers avec "
        "nom, taille, durée, débit, dossier<br>"
        "🔹 <b>Recherche</b> — filtre par mot-clé "
        "dans un dossier ou partout<br>"
        "🔹 <b>Tris</b> — clique sur les en-têtes "
        "de colonne pour trier<br>"
        "🔹 <b>Menu contextuel</b> — infos, lecture, "
        "suppression au clic droit<br><br>"
        "Je t'envoie vers elle !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Bibliothèque"},
        ],
        "suggestions": [
            {"label": "📚 Explorer", "action": "bibliotheque"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "utilisateurs": {
        "keywords": [
            "utilisateurs",
            "utilisateur",
            "user",
            "users",
            "amis",
            "ami",
            "contact",
            "contacts",
            "friends",
            "friend",
            "liste d'amis",
            "messagerie",
            "messages",
        ],
        "icon": "👤",
        "response": "Le panneau <b>Utilisateurs</b> gère tes contacts, "
        "ta liste d'amis et la messagerie. "
        "Je t'envoie vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Utilisateurs"},
        ],
        "suggestions": [
            {"label": "👤 Mes contacts", "action": "utilisateurs"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "wishlist": {
        "keywords": [
            "wishlist",
            "souhait",
            "souhaits",
            "liste de souhaits",
            "automatique",
            "recherche auto",
            "souhaiterais",
            "je voudrais",
            "j'aimerais",
            "aimerais trouver",
            "item",
            "items",
            "wish list",
            "désir",
            "desir",
        ],
        "icon": "📋",
        "response": "<b>Aphrodite</b>, la déesse du désir, s'occupe des souhaits "
        "automatiques et des recherches planifiées. "
        "Je te redirige vers elle !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Wishlist"},
        ],
        "suggestions": [
            {"label": "📋 Wishlist", "action": "wishlist"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "surveillance": {
        "keywords": [
            "surveillance",
            "surveiller",
            "monitor",
            "alertes",
            "alerte",
            "notification",
            "notifications",
            "notifier",
            "en direct",
            "live",
            "événement",
            "evenement",
            "évènement",
            "évènements",
            "événements",
            "evenements",
            "watch",
            "guette",
            "surveillance en direct",
            "feed",
            "flux",
            "activité",
            "activite",
            "realtime",
            "temps réel",
        ],
        "icon": "👁️",
        "response": "<b>Artémis</b>, la déesse chasseresse, te tient informé "
        "avec des notifications et alertes en direct. "
        "Je t'envoie vers elle !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Surveillance"},
        ],
        "suggestions": [
            {"label": "👁️ Alertes", "action": "surveillance"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "planificateur": {
        "keywords": [
            "planificateur",
            "planifier",
            "planning",
            "scheduler",
            "programmer",
            "tâche",
            "tâches",
            "actions planifiées",
            "automatisation",
            "rappel",
            "rappels",
            "programme",
            "programmation",
            "ordonnancer",
            "cron",
            "horaires",
            "horaire",
            "récurrent",
            "recurrent",
        ],
        "icon": "📅",
        "response": "<b>Apollon</b>, le dieu de l'ordre, gère les actions "
        "planifiées et automatisées. "
        "Je te redirige vers lui !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Planificateur"},
        ],
        "suggestions": [
            {"label": "📅 Planifier", "action": "planificateur"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "ordonnanceur": {
        "keywords": [
            "ordonnanceur",
            "nettoyage",
            "nettoyer",
            "clean",
            "organiser",
            "organisation",
            "ranger",
            "trier",
            "classer",
            "renommer",
            "dédoublonner",
            "dédoublon",
            "supprimer doublons",
            "doublon",
            "doublons",
            "réorganiser",
            "reorganiser",
            "rename",
            "move",
            "déplacer",
            "deplacer",
        ],
        "icon": "🧹",
        "response": "<b>Poséidon</b>, le dieu des océans, t'aide à organiser, "
        "classer et nettoyer tes fichiers téléchargés. "
        "Je t'envoie vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Ordonnanceur"},
        ],
        "suggestions": [
            {"label": "🧹 Organiser", "action": "ordonnanceur"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "clients-actifs": {
        "keywords": [
            "clients actifs",
            "clients-actifs",
            "client actif",
            "clients",
            "utilisateurs suivis",
            "suivi utilisateur",
            "tracking",
            "en ligne",
            "hors ligne",
            "connecté",
            "déconnecté",
            "qui est en ligne",
            "qui est connecté",
            "qui est la",
            "slot",
            "slots",
            "file d'attente",
            "status",
            "statut",
        ],
        "icon": "👥",
        "response": "<b>Arès</b>, le dieu de la guerre, te permet de suivre "
        "le statut de tes contacts en temps réel : qui est "
        "en ligne, qui est joignable, leurs slots et files "
        "d'attente. Je te redirige vers lui !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Clients Actifs"},
        ],
        "suggestions": [
            {"label": "👥 Voir les clients", "action": "clients-actifs"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "assistant": {
        "keywords": [
            "assistant",
            "config",
            "configuration",
            "paramètre",
            "paramètres",
            "settings",
            "setup",
            "réglages",
            "préférences",
            "preferences",
            "configurer",
            "options",
            "compte",
            "mot de passe",
            "mdp",
            "username",
            "nom d'utilisateur",
            "identifiants",
            "theme",
            "thème",
            "apparence",
        ],
        "icon": "⚙️",
        "response": "<b>Héra</b>, la reine de l'Olympe, t'aide à configurer et paramétrer l'application. Je t'envoie vers elle !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Assistant"},
        ],
        "suggestions": [
            {"label": "⚙️ Configurer", "action": "assistant"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "rafraichir_clients_actifs": {
        "keywords": [
            "rafraîchir clients actifs",
            "rafraichir clients actifs",
            "rafraîchir les clients",
            "rafraichir les clients",
            "refresh clients",
            "actualiser clients",
            "mettre à jour les clients",
            "mettre a jour les clients",
            "re-scanner clients",
            "rescan clients",
            "réactualiser",
            "reactualiser",
            "refresh",
            "rafraîchir",
            "rafraichir",
            "actualiser",
            "mettre à jour",
            "mettre a jour",
            "re-scan",
            "rescan",
        ],
        "icon": "🔄",
        "response": "Je relance la détection des clients actifs et joignables !<br><br>"
        "<b>Arès</b> va re-parcourir les salons publics, "
        "pinger les membres et filtrer ceux qui sont "
        "véritablement actifs (ONLINE).<br><br>"
        "Un instant…",
        "actions": [
            {"type": "start_loop", "bot": "Rooms"},
            {"type": "start_loop", "bot": "Clients Actifs"},
            {"type": "navigate", "bot": "Clients Actifs"},
        ],
        "suggestions": [
            {"label": "👥 Voir les clients", "action": "clients-actifs"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "optimiseur": {
        "keywords": [
            "optimiseur",
            "optimiser",
            "optimisation",
            "performance",
            "performances",
            "vitesse",
            "profils",
            "profil",
            "quick start",
            "extrême",
            "extreme",
            "puissance max",
            "optimize",
            "optimization",
        ],
        "icon": "⚡",
        "response": "<b>Héphaistos</b>, le dieu du feu et des forgerons, t'aide "
        "à optimiser les performances de l'application. "
        "Je t'envoie vers lui !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Optimiseur"},
        ],
        "suggestions": [
            {"label": "⚡ Optimiser", "action": "optimiseur"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "salons": {
        "keywords": [
            "salon",
            "salons",
            "room",
            "rooms",
            "chat",
            "discuter",
            "discussion",
            "conversation",
            "tchat",
            "salon de discussion",
            "chat room",
            "messagerie instantanée",
            "talk",
        ],
        "icon": "💬",
        "response": "<b>Hestia</b>, la déesse du foyer, gère les salons "
        "de discussion Soulseek. Elle met à jour la liste "
        "des membres pour le suivi des clients actifs.<br><br>"
        "Je lance la boucle des salons en arrière-plan !",
        "actions": [
            {"type": "start_loop", "bot": "Rooms"},
        ],
        "suggestions": [
            {"label": "👥 Clients Actifs", "action": "clients-actifs"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "statistiques": {
        "keywords": [
            "statistiques",
            "stats",
            "statistique",
            "dashboard",
            "tableau de bord",
            "panorama",
            "résumé",
            "resume",
            "synthèse",
            "synthese",
            "chiffres",
            "compteur",
            "stat",
            "statistics",
        ],
        "icon": "📊",
        "response": "Les statistiques sont dispersées entre plusieurs dieux :<br><br>"
        "🔹 <b>Déméter</b> — stats de la bibliothèque<br>"
        "🔹 <b>Hadès</b> — progression des téléchargements<br>"
        "🔹 <b>Artémis</b> — événements et alertes<br>"
        "🔹 <b>Arès</b> — clients en ligne<br><br>"
        "Je t'envoie vers la <b>Bibliothèque</b> pour commencer !",
        "actions": [
            {"type": "start_loop_and_navigate", "bot": "Bibliothèque"},
        ],
        "suggestions": [
            {"label": "📊 Voir les stats", "action": "statistiques"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    # ═══════════════════════════════════════════════════════════
    # Commandes de boucles
    # ═══════════════════════════════════════════════════════════
    "arret": {
        "keywords": [
            "arrête",
            "arrete",
            "arrêter",
            "arreter",
            "stop",
            "stoppe",
            "stopper",
            "coupe",
            "couper",
            "désactive",
            "desactive",
            "éteins",
            "eteins",
            "kill",
            "termine",
            "terminer",
            "mets en pause",
        ],
        "icon": "⏹️",
        "response": "Quelle boucle veux-tu arrêter ?<br><br>"
        "Tu peux préciser par exemple :<br>"
        "🔹 <b>arrête la recherche</b><br>"
        "🔹 <b>stop la surveillance</b><br>"
        "🔹 <b>arrête le planificateur</b><br><br>"
        "Pour l'instant, tu peux me préciser la boucle "
        "à arrêter directement dans le chat.<br>"
        "Exemple : <i>arrête la surveillance</i>",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "📥 Téléchargements", "action": "telechargement"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "relance": {
        "keywords": [
            "relance",
            "relancer",
            "redémarre",
            "redemarre",
            "redémarrer",
            "restart",
            "reboot",
            "réactive",
            "reactive",
            "relance la boucle",
            "réinitialise",
            "reinitialise",
            "recommence",
        ],
        "icon": "🔄",
        "response": "Quelle boucle veux-tu relancer ?<br><br>"
        "Tu peux préciser par exemple :<br>"
        "🔹 <b>relance la recherche</b><br>"
        "🔹 <b>relance la surveillance</b><br>"
        "🔹 <b>relance le planificateur</b><br><br>"
        "Pour l'instant, tu peux me préciser la boucle "
        "à relancer directement dans le chat.<br>"
        "Exemple : <i>relance la surveillance</i>",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "📥 Téléchargements", "action": "telechargement"},
            {"label": "📅 Planificateur", "action": "planificateur"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "connexion": {
        "keywords": [
            "connexion",
            "connecter",
            "connexion",
            "connecte",
            "login",
            "log in",
            "sign in",
            "authentification",
            "authentifier",
            "déconnexion",
            "deconnexion",
            "déconnecte",
            "deconnecte",
            "déconnecter",
            "deconnecter",
            "logout",
            "sign out",
            "se connecter",
            "se déconnecter",
            "identifiants",
            "serveur",
            "serveur soulseek",
        ],
        "icon": "🔌",
        "response": "Tu veux gérer ta connexion à Soulseek ?<br><br>"
        "Je peux t'emmener vers la page de connexion. "
        "<b>Héra</b> peut aussi t'aider à configurer "
        "tes identifiants dans les paramètres.",
        "actions": [
            {"type": "navigate", "bot": "connexion"},
        ],
        "suggestions": [
            {"label": "🔌 Page connexion", "action": "connexion"},
            {"label": "⚙️ Configurer", "action": "assistant"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "etat": {
        "keywords": [
            "état",
            "etat",
            "état des boucles",
            "etat des boucles",
            "qu'est-ce qui tourne",
            "qu est ce qui tourne",
            "que tourne",
            "actif",
            "actifs",
            "actives",
            "en cours",
            "ce qui tourne",
            "quels bots",
            "boucle active",
            "boucles actives",
            "statut des bots",
            "status des bots",
            "que faire",
            "que puis-je faire",
            "quoi faire",
        ],
        "icon": "📡",
        "response": "Voici un aperçu de ce qui est disponible :<br><br>"
        "🔍 <b>Athéna</b> — Recherche de fichiers<br>"
        "📥 <b>Hadès</b> — Téléchargements<br>"
        "📚 <b>Déméter</b> — Bibliothèque partagée<br>"
        "📋 <b>Aphrodite</b> — Wishlist<br>"
        "👁️ <b>Artémis</b> — Surveillance / Alertes<br>"
        "📅 <b>Apollon</b> — Planificateur<br>"
        "🧹 <b>Poséidon</b> — Ordonnanceur<br>"
        "👥 <b>Arès</b> — Clients Actifs<br>"
        "⚡ <b>Héphaistos</b> — Optimiseur<br>"
        "⚙️ <b>Héra</b> — Configuration<br>"
        "💬 <b>Hestia</b> — Salons<br><br>"
        "Tous les bots avec une boucle peuvent être démarrés "
        "et arrêtés. Dis-moi ce que tu veux lancer !",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "📥 Téléchargements", "action": "telechargement"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    # ═══════════════════════════════════════════════════════════
    # Dialogues généraux
    # ═══════════════════════════════════════════════════════════
    "bonjour": {
        "keywords": [
            "bonjour",
            "salut",
            "hey",
            "hello",
            "hi",
            "coucou",
            "bonsoir",
            "yo",
            "cc",
        ],
        "icon": "👋",
        "response": "Salut ! Comment vas-tu aujourd'hui ? "
        "N'hésite pas à me dire ce que tu veux faire. "
        "Je suis là pour t'aider ! 😊",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "📥 Téléchargements", "action": "telechargement"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Retour", "action": "welcome"},
        ],
    },
    "merci": {
        "keywords": [
            "merci",
            "thanks",
            "thank you",
            "merci beaucoup",
            "super",
            "génial",
            "genial",
            "parfait",
            "cool",
        ],
        "icon": "🙏",
        "response": "Avec plaisir ! Tu sais où me trouver si tu as besoin d'autre chose. 😊",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "qui_es_tu": {
        "keywords": [
            "qui es-tu",
            "qui es tu",
            "c'est quoi",
            "tu es qui",
            "t'es qui",
            "présente-toi",
            "présentation",
            "explique",
            "armée",
            "armee",
            "12 bots",
            "douze bots",
        ],
        "icon": "🖐️",
        "response": "Je suis <b>Zeus</b>, le roi de l'Olympe, "
        "ton assistant personnel sur Soulseek !<br><br>"
        "Je fais partie du <b>Panthéon des 12 Dieux</b>, "
        "une équipe de divinités conçues pour t'offrir "
        "une expérience complète sur Soulseek.<br><br>"
        "Les autres dieux sont : <b>Athéna</b> (Recherche), "
        "<b>Hadès</b> (Téléchargement), <b>Déméter</b> (Bibliothèque), "
        "<b>Aphrodite</b> (Wishlist), "
        "<b>Artémis</b> (Surveillance), <b>Apollon</b> (Planificateur), "
        "<b>Poséidon</b> (Ordonnanceur), <b>Arès</b> (Clients Actifs), "
        "<b>Héphaistos</b> (Optimiseur), "
        "<b>Hestia</b> (Salons), "
        "<b>Héra</b> (Assistant), et <b>Dionysos</b> (Aide).",
        "suggestions": [
            {"label": "🎯 Voir les 12 bots", "action": "about"},
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "soulseek": {
        "keywords": [
            "soulseek",
            "slsk",
            "c'est quoi soulseek",
            "à quoi ça sert",
            "a quoi ca sert",
            "réseau",
            "p2p",
            "peer to peer",
        ],
        "icon": "💬",
        "response": "Soulseek est un réseau de partage de fichiers "
        "pair-à-pair (P2P) spécialisé dans la musique "
        "indépendante et les fichiers rares.<br><br>"
        "Avec cette appli et l'<b>Aide des 12 Bots</b>, "
        "tu peux chercher des fichiers, télécharger, "
        "discuter avec d'autres utilisateurs, et bien plus "
        "— le tout de façon automatisée et simplifiée !",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "quoi_de_neuf": {
        "keywords": [
            "quoi de neuf",
            "nouveau",
            "nouveauté",
            "nouveautés",
            "news",
            "actu",
            "actualité",
        ],
        "icon": "✨",
        "response": "Tout va bien de mon côté ! 😊<br><br>"
        "Si tu veux voir ce qui se passe en ce moment, "
        "tu peux jeter un œil à "
        "<b>Artémis</b> (alertes en direct) "
        "ou <b>Arès</b> (suivi des clients).",
        "suggestions": [
            {"label": "👁️ Surveillance", "action": "surveillance"},
            {"label": "👥 Clients Actifs", "action": "clients-actifs"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    # ═══════════════════════════════════════════════════════════
    # Messages utilisateur non reconnus → plusieurs fallbacks
    # ═══════════════════════════════════════════════════════════
    "fallback": {
        "keywords": [
            # Ceci est une entrée spéciale qui ne match jamais
            # par mot-clé. Utilisée uniquement comme fallback.
        ],
        "icon": "🤔",
        "response": "Je n'ai pas bien compris ta demande. "
        "Peux-tu reformuler ?<br><br>"
        "Tu peux aussi utiliser les suggestions "
        "ci-dessous pour me guider !",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "📥 Téléchargements", "action": "telechargement"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🎯 À propos", "action": "about"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },
    "fallback_insulte": {
        "keywords": [
            "connard",
            "con",
            "idiot",
            "imbécile",
            "imbecile",
            "nul",
            "naze",
            "m*rde",
            "merde",
            "putain",
            "fuck",
            "salope",
            "enculé",
            "encule",
            "batard",
            "bâtard",
        ],
        "icon": "😅",
        "response": "Woah, doucement ! 😅<br><br>"
        "Je suis là pour t'aider, pas pour me disputer. "
        "Si quelque chose ne va pas, dis-moi ce qui "
        "ne fonctionne pas et je ferai de mon mieux "
        "pour t'aider !",
        "suggestions": [
            {"label": "🫤 Désolé…", "action": "welcome"},
            {"label": "❓ Aide", "action": "aide"},
        ],
    },
}
