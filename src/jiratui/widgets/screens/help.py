import inspect
import os

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Input, MarkdownViewer
from textual.widgets._markdown import (
    MarkdownBlock,
    MarkdownFence,
    MarkdownTable,
    MarkdownTableCellContents,
)


class HelpScreen(ModalScreen):
    """The screen that displays help."""

    BINDINGS = [
        ('escape', 'close', 'Close Help'),
        ('/', 'open_search', 'Search Help'),
    ]
    TITLE = 'JiraTUI Help'
    HELP = 'This is the in-app help system. If what you are looking for is not here then please refer to the official help at https://jiratui.readthedocs.io/en/latest/index.html'
    SEARCH_MATCH_CLASS = '-search-match'

    def __init__(self, anchor: str | None = None):
        super().__init__()
        self._anchor = anchor
        self._content = None
        self._search_matches: list[list[Widget]] = []
        self._search_match_index: int = 0
        try:
            in_app_help_filename = self._get_in_app_help_filename()
            with open(in_app_help_filename, 'r') as file:
                self._content = file.read()
        except FileNotFoundError:
            self._content = 'Unable to load the contents of the help. Please refer to https://jiratui.readthedocs.io/en/latest/index.html'

    @property
    def viewer(self) -> MarkdownViewer:
        return self.query_one(MarkdownViewer)

    @property
    def search_input(self) -> Input:
        return self.query_one('#help-search', Input)

    def compose(self) -> ComposeResult:
        yield MarkdownViewer(self._content, show_table_of_contents=True)
        search_input = Input(placeholder='Search the help', id='help-search')
        search_input.border_title = 'Search'
        search_input.display = False
        yield search_input

    @staticmethod
    def _get_in_app_help_filename() -> str:
        filename = inspect.getfile(HelpScreen)
        directory = os.path.dirname(filename)
        directories = directory.rsplit('jiratui', 1)[0].rstrip('/')
        return '/'.join([directories, 'jiratui/utils/in_app_help.md'])

    async def on_mount(self):
        viewer = self.viewer
        viewer.border_title = self.TITLE
        if self._anchor:
            await viewer.go(self._anchor.strip())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # let the search input receive the "/" character while the user is typing in it
        if action == 'open_search' and self.search_input.has_focus:
            return False
        return True

    def action_open_search(self) -> None:
        self.add_class('-searching')
        self.search_input.display = True
        self.search_input.focus()

    def action_close(self) -> None:
        if self.search_input.display:
            self._close_search()
        else:
            self.app.pop_screen()

    def _close_search(self) -> None:
        self._clear_search_matches()
        self.search_input.value = ''
        self.search_input.border_subtitle = ''
        self.search_input.display = False
        self.remove_class('-searching')
        self.viewer.document.focus()

    @on(Input.Changed, '#help-search')
    def _search(self, event: Input.Changed) -> None:
        self._clear_search_matches()
        term = event.value.strip().lower()
        if not term:
            self.search_input.border_subtitle = ''
            return
        self._search_matches = [
            widgets
            for widgets in self._get_searchable_units()
            if any(term in self._get_text(widget).lower() for widget in widgets)
        ]
        self._search_match_index = 0
        self._show_current_match()

    @on(Input.Submitted, '#help-search')
    def _go_to_next_match(self) -> None:
        if not self._search_matches:
            return
        self._set_match_highlight(False)
        self._search_match_index = (self._search_match_index + 1) % len(self._search_matches)
        self._show_current_match()

    def _show_current_match(self) -> None:
        if not self._search_matches:
            self.search_input.border_subtitle = 'No matches'
            return
        self.search_input.border_subtitle = (
            f'{self._search_match_index + 1}/{len(self._search_matches)}'
        )
        self._set_match_highlight(True)
        self.viewer.scroll_to_center(
            self._search_matches[self._search_match_index][0], animate=False
        )

    def _set_match_highlight(self, highlight: bool) -> None:
        for widget in self._search_matches[self._search_match_index]:
            widget.set_class(highlight, self.SEARCH_MATCH_CLASS)

    def _clear_search_matches(self) -> None:
        for widget in self.query(f'.{self.SEARCH_MATCH_CLASS}'):
            widget.remove_class(self.SEARCH_MATCH_CLASS)
        self._search_matches = []
        self._search_match_index = 0

    def _get_searchable_units(self) -> list[list[Widget]]:
        """Splits the help document into the units that a search can land on, in document order.

        Each unit is a list of widgets that are highlighted together: a heading, a paragraph and a code block are
        single-widget units while a table contributes one unit per row, made of the cells in that row.
        """
        units: list[list[Widget]] = []
        for block in self.viewer.document.query(MarkdownBlock):
            if isinstance(block, MarkdownTable):
                rows: dict[str, list[Widget]] = {}
                for cell in block.query(MarkdownTableCellContents):
                    row = next((name for name in cell.classes if name.startswith('row')), 'header')
                    rows.setdefault(row, []).append(cell)
                units.extend(rows.values())
            elif not block.query(MarkdownBlock):
                units.append([block])
        return units

    @staticmethod
    def _get_text(widget: Widget) -> str:
        if isinstance(widget, MarkdownFence):
            return widget.code
        return str(getattr(widget, 'content', ''))
