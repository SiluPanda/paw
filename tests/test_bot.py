import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Patch env before importing bot
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("ALLOWED_USER_IDS", "")
    monkeypatch.setenv("WORK_DIR", "/tmp")


@pytest.fixture()
def _reload_bot(_env):
    """Import bot fresh with patched env."""
    import importlib
    import bot

    importlib.reload(bot)
    return bot


# --- run_claude tests ---


@pytest.mark.asyncio
async def test_run_claude_returns_stdout(_reload_bot):
    bot = _reload_bot
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"Hello from Claude", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
        result = await bot.run_claude("test prompt")

    assert result == "Hello from Claude"


@pytest.mark.asyncio
async def test_run_claude_falls_back_to_stderr(_reload_bot):
    bot = _reload_bot
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"some error output")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
        result = await bot.run_claude("bad prompt")

    assert result == "some error output"


@pytest.mark.asyncio
async def test_run_claude_empty_response(_reload_bot):
    bot = _reload_bot
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
        result = await bot.run_claude("empty prompt")

    assert result == "(empty response)"


@pytest.mark.asyncio
async def test_run_claude_binary_not_found(_reload_bot):
    bot = _reload_bot

    with patch(
        "asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        side_effect=FileNotFoundError,
    ):
        result = await bot.run_claude("hello")

    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_run_claude_passes_correct_args(_reload_bot):
    bot = _reload_bot
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"ok", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc) as mock_exec:
        await bot.run_claude("my prompt")

    mock_exec.assert_called_once_with(
        "claude",
        "-p",
        "--dangerously-skip-permissions",
        "my prompt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=bot.WORK_DIR,
    )


# --- handle_message tests ---


def _make_update(user_id=12345, text="hello"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_context():
    ctx = MagicMock()
    ctx.bot.send_chat_action = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_handle_message_sends_response(_reload_bot):
    bot = _reload_bot
    update = _make_update()
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", set()), \
         patch.object(bot, "run_claude", new_callable=AsyncMock, return_value="response"):
        await bot.handle_message(update, ctx)

    update.message.reply_text.assert_called_once_with("response")


@pytest.mark.asyncio
async def test_handle_message_blocks_unauthorized(_reload_bot):
    bot = _reload_bot
    update = _make_update(user_id=99999)
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", {12345}):
        await bot.handle_message(update, ctx)

    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_allows_authorized(_reload_bot):
    bot = _reload_bot
    update = _make_update(user_id=12345)
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", {12345}), \
         patch.object(bot, "run_claude", new_callable=AsyncMock, return_value="ok"):
        await bot.handle_message(update, ctx)

    update.message.reply_text.assert_called_once_with("ok")


@pytest.mark.asyncio
async def test_handle_message_open_access_when_no_allowed_users(_reload_bot):
    bot = _reload_bot
    update = _make_update(user_id=99999)
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", set()), \
         patch.object(bot, "run_claude", new_callable=AsyncMock, return_value="open"):
        await bot.handle_message(update, ctx)

    update.message.reply_text.assert_called_once_with("open")


@pytest.mark.asyncio
async def test_handle_message_ignores_empty_text(_reload_bot):
    bot = _reload_bot
    update = _make_update()
    update.message.text = None
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", set()):
        await bot.handle_message(update, ctx)

    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_splits_long_response(_reload_bot):
    bot = _reload_bot
    long_text = "x" * 5000
    update = _make_update()
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", set()), \
         patch.object(bot, "run_claude", new_callable=AsyncMock, return_value=long_text):
        await bot.handle_message(update, ctx)

    assert update.message.reply_text.call_count == 2
    first = update.message.reply_text.call_args_list[0][0][0]
    second = update.message.reply_text.call_args_list[1][0][0]
    assert len(first) == 4096
    assert len(second) == 904
    assert first + second == long_text


@pytest.mark.asyncio
async def test_handle_message_sends_typing_action(_reload_bot):
    bot = _reload_bot
    update = _make_update()
    ctx = _make_context()

    with patch.object(bot, "ALLOWED_USERS", set()), \
         patch.object(bot, "run_claude", new_callable=AsyncMock, return_value="hi"):
        await bot.handle_message(update, ctx)

    ctx.bot.send_chat_action.assert_called_once_with(update.effective_chat.id, "typing")


# --- cmd_start test ---


@pytest.mark.asyncio
async def test_cmd_start(_reload_bot):
    bot = _reload_bot
    update = _make_update()
    ctx = _make_context()

    await bot.cmd_start(update, ctx)

    update.message.reply_text.assert_called_once()
    assert "ready" in update.message.reply_text.call_args[0][0].lower()
