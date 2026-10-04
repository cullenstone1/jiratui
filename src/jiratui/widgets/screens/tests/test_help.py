import pytest

from jiratui.widgets.screens.help import HelpScreen


@pytest.mark.asyncio
async def test_open_search(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        assert not screen.search_input.display
        # WHEN
        await pilot.press('/')
        # THEN
        assert screen.search_input.display
        assert screen.search_input.has_focus


@pytest.mark.asyncio
async def test_search_highlights_first_match(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        await pilot.press('/')
        # WHEN
        await pilot.press(*'git branch')
        # THEN
        total = len(screen._search_matches)
        assert total > 1
        assert screen.search_input.border_subtitle == f'1/{total}'
        highlighted = list(screen.query(f'.{HelpScreen.SEARCH_MATCH_CLASS}'))
        assert highlighted == screen._search_matches[0]


@pytest.mark.asyncio
async def test_search_matches_table_rows(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        await pilot.press('/')
        # WHEN
        await pilot.press(*'creates a git branch for a work item')
        # THEN
        assert screen._search_matches
        # every cell in the matching row is highlighted
        first_match = screen._search_matches[0]
        assert len(first_match) == 3
        assert all(cell.has_class(HelpScreen.SEARCH_MATCH_CLASS) for cell in first_match)


@pytest.mark.asyncio
async def test_search_enter_goes_to_next_match_and_wraps(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        await pilot.press('/')
        await pilot.press(*'git branch')
        total = len(screen._search_matches)
        # WHEN
        await pilot.press('enter')
        # THEN
        assert screen.search_input.border_subtitle == f'2/{total}'
        highlighted = list(screen.query(f'.{HelpScreen.SEARCH_MATCH_CLASS}'))
        assert highlighted == screen._search_matches[1]
        # WHEN
        for _ in range(total - 1):
            await pilot.press('enter')
        # THEN
        assert screen.search_input.border_subtitle == f'1/{total}'


@pytest.mark.asyncio
async def test_search_without_matches(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        await pilot.press('/')
        # WHEN
        await pilot.press(*'zzzqqq')
        await pilot.press('enter')
        # THEN
        assert screen._search_matches == []
        assert screen.search_input.border_subtitle == 'No matches'
        assert not list(screen.query(f'.{HelpScreen.SEARCH_MATCH_CLASS}'))


@pytest.mark.asyncio
async def test_search_input_accepts_slash(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        await pilot.press('/')
        # WHEN
        await pilot.press('a', '/', 'b')
        # THEN
        assert screen.search_input.value == 'a/b'


@pytest.mark.asyncio
async def test_escape_closes_search_then_help(app):
    async with app.run_test() as pilot:
        # GIVEN
        screen = HelpScreen()
        await app.push_screen(screen)
        await pilot.press('/')
        await pilot.press(*'git')
        # WHEN
        await pilot.press('escape')
        # THEN
        assert app.screen is screen
        assert not screen.search_input.display
        assert screen.search_input.value == ''
        assert not list(screen.query(f'.{HelpScreen.SEARCH_MATCH_CLASS}'))
        # WHEN
        await pilot.press('escape')
        # THEN
        assert app.screen is not screen
