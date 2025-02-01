import logging

from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero


from utils.utils import *

GLOBAL_CONFIG = load_yaml("ride_book.yaml")

instruction_file = GLOBAL_CONFIG.get("system_prompt","system_prompt.txt")
dot_env_file = GLOBAL_CONFIG.get("dot_env_file",".env")
voice = GLOBAL_CONFIG.get("voice","alloy")
turn_detector_flag = GLOBAL_CONFIG.get("turn_detector_flag", False)
initial_message = GLOBAL_CONFIG.get("initial_message","Hi, how can I help you today?")


if turn_detector_flag:
    print("Using turn detector")
    from livekit.plugins import turn_detector

instructions = load_instructions(instruction_file)
# print(instructions)
load_dotenv(dotenv_path=dot_env_file)


logger = logging.getLogger("voice-assistant")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


# This example uses our open-weight turn detection model to detect when the user is
# done speaking. This approach is more accurate than the default VAD model, reducing
# false positive interruptions by the agent.
async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text= instructions
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice=voice),
        chat_ctx=initial_ctx,
        turn_detector=turn_detector.EOUModel() if turn_detector_flag else None,
        interrupt_speech_duration= 1.5,
        interrupt_min_words = 2,
    )

    agent.start(ctx.room, participant)

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)
        usage_collector.collect(mtrcs)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: ${summary}")

    ctx.add_shutdown_callback(log_usage)

    await agent.say(initial_message, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )