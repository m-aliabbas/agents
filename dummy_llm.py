# dummy_llm.py
from livekit.agents import llm
from livekit.agents.llm.chat_context import ChatContext
from livekit.agents.llm.tool_context import FunctionTool
from livekit.agents.types import APIConnectOptions
from livekit.agents.llm import ChatChunk, ChoiceDelta, CompletionUsage


class DummyLLM(llm.LLM):
    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool] | None = None,
        conn_options: APIConnectOptions = APIConnectOptions(),
        **kwargs,
    ) -> llm.LLMStream:
        return DummyLLMStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


class DummyLLMStream(llm.LLMStream):
    async def _run(self) -> None:
        last_user_msg = next((msg for msg in reversed(self._chat_ctx.messages) if msg.role == "user"), None)
        content = last_user_msg.content if last_user_msg else "No user message found."

        chunk = ChatChunk(
            id="dummy-id",
            delta=ChoiceDelta(role="assistant", content=content),
            usage=CompletionUsage(
                prompt_tokens=1,
                completion_tokens=1,
                prompt_cached_tokens=0,
                total_tokens=2,
            ),
        )

        self._event_ch.send_nowait(chunk)
