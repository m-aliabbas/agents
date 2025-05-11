import logging
from ttsclient import SimpleTTS
from dotenv import load_dotenv
# from dummy_llm import DummyLLM  # Import our DummyLLM
# from livekit.agents.voice import SpeechEventType
from livekit.agents import ModelSettings, stt, Agent
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    cli,
    metrics,
    AudioConfig,
)
from livekit.plugins import noise_cancellation
from livekit import rtc
from typing import AsyncIterable, Optional
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero
from llmclient import LLM
logger = logging.getLogger("basic-agent")
from livekit.agents.llm.chat_context import ChatContext, ChatMessage
# Configure logging for better debug information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv(dotenv_path='.example.env')


class MyAgent(Agent):
    def __init__(self,room_id='') -> None:
        
        super().__init__(
            instructions="When user says something you reply with the same message.",
            llm=LLM.with_dummy(),
        stt=deepgram.STT(model="nova-3", language="multi"),
        tts=SimpleTTS(),

        )
        self.room_id = room_id
    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        logger.info("Agent entered - generating initial reply")
        self.session.generate_reply()

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active


    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage,
    ) -> None:
        # logger.info(f"Log Transcript: {new_message.content}") 
        logger.info(turn_ctx)
        new_message.content = [new_message.content[0]+";"+self.room_id]
        
    
    # async def stt_node(self, audio, model_settings=None):
    #     keywords = ["Shane", "hello", "thanks"]
    #     # parent_stream = super().stt_node(text, model_settings)
    #     parent_stream = await super().stt_node(audio, model_settings)
    #     if parent_stream is None:
    #         return None

    #     async def process_stream():
    #         async for event in parent_stream:
    #             if hasattr(event, 'type') and str(event.type) == "SpeechEventType.FINAL_TRANSCRIPT" and event.alternatives:
    #                 transcript = event.alternatives[0].text
                    
    #                 for keyword in keywords:
    #                     if keyword.lower() in transcript.lower():
    #                         logger.info(f"Keyword detected: '{keyword}'")
                
    #             yield event

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """

        logger.info(f"Looking up weather for {location}")

        return "sunny with a temperature of 70 degrees."
    


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Prewarm complete - VAD loaded")


async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    logger.info("Connecting to room")
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Initialize our DummyLLM with configuration
   
    logger.info("DummyLLM initialized")

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        # Use our custom DummyLLM
        # use LiveKit's turn detection model
        turn_detection="vad",
        
    )
   
    logger.info("Agent session created")

    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)

    # wait for a participant to join the room
    logger.info("Waiting for participant to join...")
    await ctx.wait_for_participant()
    logger.info("Participant joined")

    logger.info("Starting agent session")
    await session.start(
        agent=MyAgent(room_id=ctx.room.name),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )
    logger.info("Agent session started")

    background_audio = BackgroundAudioPlayer(
        # play office ambience sound looping in the background
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=1.0),
        # play keyboard typing sound when the agent is thinking
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
        ],
    )
    

    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))