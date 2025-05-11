# dummy_llm.py --------------------------------------------------------------
from __future__ import annotations
import asyncio
from livekit.agents import llm
from livekit.agents.llm.chat_context import ChatContext
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS


class DummyLLM(llm.LLM):
    """A no‑op LLM that echoes the most‑recent user message."""

    def __init__(self, model: str = "dummy-echo") -> None:
        super().__init__()
        self._model = model

    # LiveKit will call this for every turn
    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        **kwargs,
    ) -> "DummyStream":
        last_user_text = next(
            (m.content for m in reversed(chat_ctx.messages) if m.role == "user"), ""
        )
        return DummyStream(last_user_text, conn_options)


class DummyStream(llm.LLMStream):
    def __init__(self, reply_text: str, conn_options: APIConnectOptions) -> None:
        super().__init__(llm=None, chat_ctx=None, tools=[], conn_options=conn_options)
        self._reply_text = reply_text

    async def _run(self) -> None:
        chunk = llm.ChatChunk(
            id="dummy‑echo‑0",
            delta=llm.ChoiceDelta(role="assistant", content=self._reply_text),
            usage=llm.CompletionUsage(
                completion_tokens=len(self._reply_text.split()),
                prompt_tokens=0,
                prompt_cached_tokens=0,
                total_tokens=len(self._reply_text.split()),
            ),
        )
        self._event_ch.send_nowait(chunk)
        await asyncio.sleep(0)
