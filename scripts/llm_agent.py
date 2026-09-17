# ============================================================
# AGENT DE CONVERSATION (LLM via Ollama)
#
# Remplace l'ancien fallback ELIZA : quand aucune commande ne
# matche dans handle_command, c'est ici que la réponse en chat
# est générée. Une conversation par joueur (sender), par bot.
# ============================================================

from config import OLLAMA_HOST, OLLAMA_MODEL

try:
    import ollama
    _client = ollama.Client(host=OLLAMA_HOST)
except ImportError:
    _client = None

SYSTEM_PROMPT = (
    "Tu es {name}, un bot sur un serveur Minecraft communautaire. "
    "Tu discutes dans le chat du jeu comme un joueur normal : réponses "
    "courtes (une phrase ou deux), naturelles, sans emojis ni markdown. "
    "Tu n'es pas un assistant IA et tu ne dois jamais le mentionner. "
    "Tu ne peux pas exécuter d'actions en discutant : si on te demande "
    "d'aller quelque part ou de patrouiller, réponds qu'il faut utiliser "
    "les commandes directement (ex: go, patrouille, chemin)."
)

HISTORY_LIMIT = 12


class ConversationAgent:

    def __init__(self, bot_name):
        self.bot_name = bot_name
        self._histories = {}

    def _history_for(self, sender):
        key = sender or "console"
        return self._histories.setdefault(key, [])

    def _chat(self, messages):
        response = _client.chat(model=OLLAMA_MODEL, messages=messages)
        return response["message"]["content"].strip()

    def greeting(self):
        if _client is None:
            return "Salut !"

        try:
            return self._chat([
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(name=self.bot_name),
                },
                {
                    "role": "user",
                    "content": (
                        "Tu viens de te connecter au serveur. "
                        "Dis bonjour en une phrase courte."
                    ),
                },
            ])
        except Exception:
            return "Salut !"

    def respond(self, sender, message):
        if _client is None:
            return None

        history = self._history_for(sender)
        history.append({"role": "user", "content": message})
        del history[:-HISTORY_LIMIT]

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(name=self.bot_name),
            },
        ] + history

        reply = self._chat(messages)

        history.append({"role": "assistant", "content": reply})
        del history[:-HISTORY_LIMIT]

        return reply
