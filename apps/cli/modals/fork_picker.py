"""Fork picker modal — opens on ``/fork`` to collect two branch specs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from pydantic_deep.types import BranchSpec


class ForkPickerModal(ModalScreen["list[BranchSpec] | None"]):
    """Collect labels + steer messages for exactly two branches.

    Stage 1's :class:`LiveForkCapability` hard-codes ``max_branches=2``, so
    this modal only ever asks for two branches. Stage 4 lifts the cap and
    can extend this modal (or replace it) to accept a variable count.

    The modal returns:
    - ``[BranchSpec("a", "..."), BranchSpec("b", "...")]`` on submit, or
    - ``None`` on cancel.
    """

    DEFAULT_CSS = """
    ForkPickerModal {
        align: center middle;
    }
    ForkPickerModal > #fork-picker-container {
        width: 76;
        height: auto;
        border: tall $primary;
        background: $surface;
        padding: 1 2;
    }
    ForkPickerModal > #fork-picker-container > .fork-branch-group {
        height: auto;
        margin: 1 0 0 0;
        padding: 1;
        border: round $surface-lighten-2;
    }
    ForkPickerModal > #fork-picker-container > #fork-picker-error {
        height: auto;
        color: $error;
        margin: 1 0 0 0;
        display: none;
    }
    ForkPickerModal > #fork-picker-container > #fork-picker-error.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="fork-picker-container"):
            yield Static("[bold]Fork the run[/bold]")
            yield Static(
                "Spawn two branches that share the parent's history up to this point.\n"
                "Pick a short label per branch (used by `>>{label} <msg>` steering) "
                "and a first message that differentiates each branch."
            )

            with Vertical(classes="fork-branch-group"):
                yield Static("[bold]Branch A[/bold]")
                yield Input(placeholder="label (e.g. 'a')", id="branch-a-label")
                yield Input(placeholder="steer message…", id="branch-a-steer")

            with Vertical(classes="fork-branch-group"):
                yield Static("[bold]Branch B[/bold]")
                yield Input(placeholder="label (e.g. 'b')", id="branch-b-label")
                yield Input(placeholder="steer message…", id="branch-b-steer")

            yield Static("", id="fork-picker-error")
            yield Static(
                "\n[dim]Tab to move between fields  ·  Enter to submit  ·  Esc to cancel[/dim]"
            )

    def on_mount(self) -> None:
        self.query_one("#branch-a-label", Input).focus()

    def _read_inputs(self) -> tuple[str, str, str, str]:
        return (
            self.query_one("#branch-a-label", Input).value.strip(),
            self.query_one("#branch-a-steer", Input).value.strip(),
            self.query_one("#branch-b-label", Input).value.strip(),
            self.query_one("#branch-b-steer", Input).value.strip(),
        )

    def _show_error(self, message: str) -> None:
        error = self.query_one("#fork-picker-error", Static)
        error.update(message)
        error.add_class("visible")

    def _validate(self, a_label: str, a_steer: str, b_label: str, b_steer: str) -> str | None:
        """Return an error message if invalid, ``None`` if OK."""
        if not a_label or not b_label:
            return "Both branch labels are required."
        if not a_steer or not b_steer:
            return "Both steer messages are required."
        if a_label == b_label:
            return "Branch labels must be distinct."
        return None

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Input submitted callback."""
        self.action_submit()

    def action_submit(self) -> None:
        """Submit action."""
        a_label, a_steer, b_label, b_steer = self._read_inputs()
        err = self._validate(a_label, a_steer, b_label, b_steer)
        if err is not None:
            self._show_error(err)
            return
        self.dismiss(
            [
                BranchSpec(label=a_label, steer=a_steer),
                BranchSpec(label=b_label, steer=b_steer),
            ]
        )

    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss(None)
