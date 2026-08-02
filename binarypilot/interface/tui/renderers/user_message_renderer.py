from rich.text import Text


class UserMessageRenderer:
    @classmethod
    def render_simple(cls, content: str) -> Text:
        if not content:
            return Text()

        return cls._format_user_message(content)

    @classmethod
    def _format_user_message(cls, content: str) -> Text:
        text = Text()

        text.append("▍", style="#3b82f6")
        text.append(" ")
        text.append("You:", style="bold")
        text.append("\n")

        lines = content.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                text.append("\n")
            text.append("▍", style="#3b82f6")
            text.append(" ")
            text.append(line)

        return text
