from collections import defaultdict, deque


class ShortTermMemory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._conversations: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_turns)
        )

    def add_turn(self, conversation_id: str, role: str, content: str):
        self._conversations[conversation_id].append({"role": role, "content": content})

    def get_history(self, conversation_id: str) -> list[dict[str, str]]:
        return list(self._conversations.get(conversation_id, []))

    def format_context(self, conversation_id: str, max_turns: int = 5) -> str:
        history = self.get_history(conversation_id)
        recent = history[-max_turns:] if len(history) > max_turns else history
        lines = []
        for turn in recent:
            lines.append(f"{turn['role'].upper()}: {turn['content']}")
        return "\n".join(lines)

    def clear(self, conversation_id: str):
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]


short_term_memory = ShortTermMemory()
