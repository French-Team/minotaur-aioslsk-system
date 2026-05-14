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
- suggestions : list[dict] — boutons de suggestion affichés après la réponse
    Chaque item : {"label": "...", "action": "..."}
"""

KNOWLEDGE: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════════
    # Navigation vers les bots
    # ═══════════════════════════════════════════════════════════

    "chercher": {
        "keywords": [
            "chercher", "recherche", "rechercher", "trouver", "cherche",
            "fichier", "fichiers", "search", "file", "files", "trouve",
            "recherches",
        ],
        "icon": "🔍",
        "response": "Bien sûr ! Le bot <b>Recherche</b> est spécialisé "
                    "dans la recherche de fichiers sur Soulseek. "
                    "Je t'envoie vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Recherche"},
        ],
        "suggestions": [
            {"label": "🔍 Oui, cherche !", "action": "chercher"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "telechargement": {
        "keywords": [
            "téléchargement", "telechargement", "télécharger", "telecharger",
            "dl", "download", "downloads", "télécharge", "telecharge",
            "fichier en cours", "mes téléchargements",
        ],
        "icon": "📥",
        "response": "Pas de souci ! Le bot <b>Téléchargement</b> s'occupe "
                    "de gérer, suivre et prioriser tes téléchargements. "
                    "Je te l'envoie !",
        "actions": [
            {"type": "navigate", "bot": "Téléchargement"},
        ],
        "suggestions": [
            {"label": "📥 Voir mes DL", "action": "telechargement"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "aide": {
        "keywords": [
            "aide", "help", "assistance", "besoin d'aide", "comment",
            "guide", "explication", "explications", "aide-moi",
            "help me", "problème", "probleme", "bug", "souci",
        ],
        "icon": "❓",
        "response": "Tu as besoin d'explications ou d'aide ? "
                    "Le bot <b>Aide</b> connaît tout sur l'application "
                    "et ses 12 bots. Je te redirige vers lui !",
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
            "bibliothèque", "bibliotheque", "library", "biblio",
            "explorer", "parcourir", "dossier", "dossiers",
        ],
        "icon": "📚",
        "response": "Le bot <b>Bibliothèque</b> te permet d'explorer "
                    "et de parcourir les fichiers partagés. "
                    "Je te dirige vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Bibliothèque"},
        ],
        "suggestions": [
            {"label": "📚 Explorer", "action": "bibliotheque"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "utilisateurs": {
        "keywords": [
            "utilisateurs", "utilisateur", "user", "users", "amis",
            "ami", "contact", "contacts", "friends", "friend",
            "liste d'amis", "messagerie", "messages",
        ],
        "icon": "👤",
        "response": "Le bot <b>Utilisateurs</b> gère tes contacts, "
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
            "wishlist", "souhait", "souhaits", "liste de souhaits",
            "automatique", "recherche auto",
        ],
        "icon": "📋",
        "response": "Le bot <b>Wishlist</b> s'occupe des souhaits "
                    "automatiques et des recherches planifiées. "
                    "Je te redirige vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Wishlist"},
        ],
        "suggestions": [
            {"label": "📋 Wishlist", "action": "wishlist"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "surveillance": {
        "keywords": [
            "surveillance", "surveiller", "monitor", "alertes",
            "alerte", "notification", "notifications", "notifier",
            "en direct", "live",
        ],
        "icon": "👁️",
        "response": "Le bot <b>Surveillance</b> te tient informé "
                    "avec des notifications et alertes en direct. "
                    "Je t'envoie vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Surveillance"},
        ],
        "suggestions": [
            {"label": "👁️ Alertes", "action": "surveillance"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "planificateur": {
        "keywords": [
            "planificateur", "planifier", "planning", "scheduler",
            "programmer", "tâche", "tâches", "actions planifiées",
            "automatisation", "rappel", "rappels",
        ],
        "icon": "📅",
        "response": "Le bot <b>Planificateur</b> gère les actions "
                    "planifiées et automatisées. "
                    "Je te redirige vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Planificateur"},
        ],
        "suggestions": [
            {"label": "📅 Planifier", "action": "planificateur"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "nettoyage": {
        "keywords": [
            "nettoyage", "nettoyer", "clean", "nettoyage",
            "organiser", "organisation", "ranger", "trier",
        ],
        "icon": "🧹",
        "response": "Le bot <b>Nettoyage</b> t'aide à organiser "
                    "et nettoyer tes fichiers. "
                    "Je t'envoie vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Nettoyage"},
        ],
        "suggestions": [
            {"label": "🧹 Nettoyer", "action": "nettoyage"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "statistiques": {
        "keywords": [
            "statistiques", "stats", "statistique", "statistiques",
            "tableau de bord", "dashboard", "données", "data",
            "graphique", "analytics",
        ],
        "icon": "📊",
        "response": "Le bot <b>Statistiques</b> te montre les "
                    "données et le tableau de bord de ton activité. "
                    "Je te redirige vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Statistiques"},
        ],
        "suggestions": [
            {"label": "📊 Voir les stats", "action": "statistiques"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "assistant": {
        "keywords": [
            "assistant", "config", "configuration", "paramètre",
            "paramètres", "settings", "setup", "réglages",
            "préférences", "preferences", "configurer",
        ],
        "icon": "⚙️",
        "response": "Le bot <b>Assistant</b> t'aide à configurer "
                    "et paramétrer l'application. "
                    "Je t'envoie vers lui !",
        "actions": [
            {"type": "navigate", "bot": "Assistant"},
        ],
        "suggestions": [
            {"label": "⚙️ Configurer", "action": "assistant"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # Dialogues généraux
    # ═══════════════════════════════════════════════════════════

    "bonjour": {
        "keywords": [
            "bonjour", "salut", "hey", "hello", "hi", "coucou",
            "bonsoir", "yo", "cc",
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
            "merci", "thanks", "thank you", "merci beaucoup",
            "super", "génial", "genial", "parfait", "cool",
        ],
        "icon": "🙏",
        "response": "Avec plaisir ! Tu sais où me trouver si tu as "
                    "besoin d'autre chose. 😊",
        "suggestions": [
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "qui_es_tu": {
        "keywords": [
            "qui es-tu", "qui es tu", "c'est quoi", "tu es qui",
            "t'es qui", "présente-toi", "présentation", "explique",
            "armée", "armee", "12 bots", "douze bots",
        ],
        "icon": "🖐️",
        "response": "Je suis le bot <b>Accueil</b>, ton assistant "
                    "personnel sur Soulseek !<br><br>"
                    "Je fais partie de <b>l'Armée des 12 Bots</b>, "
                    "une équipe de bots conçus pour t'offrir "
                    "une expérience complète sur Soulseek.<br><br>"
                    "Les autres bots sont : <b>Recherche</b>, "
                    "<b>Téléchargement</b>, <b>Bibliothèque</b>, "
                    "<b>Utilisateurs</b>, <b>Wishlist</b>, "
                    "<b>Surveillance</b>, <b>Planificateur</b>, "
                    "<b>Nettoyage</b>, <b>Statistiques</b>, "
                    "<b>Assistant</b>, et <b>Aide</b>.",
        "suggestions": [
            {"label": "🎯 Voir les 12 bots", "action": "about"},
            {"label": "🔍 Chercher", "action": "chercher"},
            {"label": "❓ Aide", "action": "aide"},
            {"label": "🏠 Accueil", "action": "welcome"},
        ],
    },

    "soulseek": {
        "keywords": [
            "soulseek", "slsk", "c'est quoi soulseek",
            "à quoi ça sert", "a quoi ca sert", "réseau",
            "p2p", "peer to peer",
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
            "quoi de neuf", "nouveau", "nouveauté", "nouveautés",
            "news", "actu", "actualité",
        ],
        "icon": "✨",
        "response": "Tout va bien de mon côté ! 😊<br><br>"
                    "Si tu veux voir ce qui se passe en ce moment, "
                    "tu peux jeter un œil aux bots "
                    "<b>Surveillance</b> (alertes en direct) "
                    "ou <b>Statistiques</b> (tableau de bord).",
        "suggestions": [
            {"label": "👁️ Surveillance", "action": "surveillance"},
            {"label": "📊 Statistiques", "action": "statistiques"},
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
            "connard", "con", "idiot", "imbécile", "imbecile",
            "nul", "naze", "m*rde", "merde", "putain", "fuck",
            "salope", "enculé", "encule", "batard", "bâtard",
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
