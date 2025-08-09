from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    JobProcess
)
from livekit.plugins import deepgram, openai, silero,elevenlabs
from utils.email_utils import send_email
from utils.utils import *


GLOBAL_CONFIG = load_yaml("truck_config.yaml")

dot_env_file = GLOBAL_CONFIG.get("dot_env_file",".env")
voice = GLOBAL_CONFIG.get("voice","alloy")
turn_detector_flag = GLOBAL_CONFIG.get("turn_detector_flag", False)
agent_id = GLOBAL_CONFIG.get("agent_id", "")

from dotenv import load_dotenv

load_dotenv(dotenv_path=dot_env_file)




@function_tool
async def lookup_weather(
    context: RunContext,
    location: str,
):
    """Used to look up weather information."""

    return {"weather": "sunny", "temperature": 70}

# print(f"Using system prompt: {instruction_file}")


# def prewarm(proc: JobProcess):
#     proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent_details = get_agent_from_web("ccc1065d-89bd-4b33-b486-ee21af3912f5")

    instructions = agent_details.get("prompt", "You are a friendly assistant. You can ask me anything.")
    initial_message = agent_details.get("init_message", "Hello, I am Alex, your trucking assistant. How can I help you today?")
    print(f"Using initial message: {initial_message}")
    agent = Agent(
        instructions=instructions,
        tools=[lookup_weather],
    )
    session = AgentSession(
        vad=silero.VAD.load(),
        # any combination of STT, LLM, TTS, or realtime API can be used
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
        preemptive_generation=True,
    )

    await session.start(agent=agent, room=ctx.room)
    # await session.generate_reply(instructions="Say Hello to user. You are Alex trucking assistant.")
    await session.say(initial_message)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))