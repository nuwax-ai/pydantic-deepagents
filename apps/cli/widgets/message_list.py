"""Scrollable message list container."""

from __future__ import annotations

import contextlib

from textual.containers import VerticalScroll

from apps.cli.widgets.assistant_message import AssistantMessage
from apps.cli.widgets.user_message import UserMessage


class MessageList(VerticalScroll):
    """Scrollable container for chat messages. Auto-scrolls to bottom."""

    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        padding: 0 0;
    }
    """

    _current_assistant: AssistantMessage | None = None

    def append_user_message(self, text: str) -> UserMessage:
        """Add a user message and scroll to bottom."""
        msg = UserMessage(text)
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg

    def begin_assistant_message(self) -> AssistantMessage:
        """Start a new assistant message turn."""
        msg = AssistantMessage()
        self._current_assistant = msg
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg

    @property
    def current_assistant(self) -> AssistantMessage | None:
        """The currently active assistant message (during streaming)."""
        return self._current_assistant

    def end_assistant_message(self) -> None:
        """Finalize the current assistant message."""
        if self._current_assistant:
            self._current_assistant.finalize_text()
            self._current_assistant = None
        self.scroll_end(animate=False)

    def remove_last_if_empty(self) -> None:
        """Remove the current assistant message if it has no visible content."""
        msg = self._current_assistant
        if msg is not None and msg.is_empty:
            self._current_assistant = None
            with contextlib.suppress(Exception):
                msg.remove()

    def complete_tool_call_by_id(
        self,
        call_id: str,
        result: str,
        elapsed: float,
        error: bool = False,
    ) -> bool:
        """Complete the tool call ``call_id`` on whichever message holds it.

        Looks the call up by id across all rendered assistant messages rather
        than relying on the current streaming message — so a tool return that
        straddles a poll tick (after the call's message was ended by a trailing
        text part, or rendered under an earlier assistant message) still
        completes the correct tool-call row instead of spinning forever or
        attaching to the wrong message. Returns ``True`` when a match was found.
        """
        for child in self.children:
            if isinstance(child, AssistantMessage) and child.has_tool_call(call_id):
                child.complete_tool_call(call_id, result, elapsed, error)
                return True
        return False

    def clear_messages(self) -> None:
        """Remove all messages."""
        self._current_assistant = None
        for child in list(self.children):
            child.remove()
