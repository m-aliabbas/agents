# client.py
import asyncio
import aiohttp
import logging
import struct
import numpy as np
from dataclasses import dataclass
from livekit.agents import tts
from livekit import rtc

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
SERVER_URL = "http://127.0.0.1:8000/tts"        # adjust for remote host
CHUNK_SIZE  = 4096                              # must match server stream


@dataclass
class SimpleTTSConfig:
    sample_rate: int = 44100
    num_channels: int = 1
    chunk_size: int = CHUNK_SIZE
    logging_enabled: bool = True
    log_level: int = logging.INFO


# ---------------------------------------------------------------------
# Helper – parse RIFF header robustly (handles >44‑byte headers)
# ---------------------------------------------------------------------
def parse_riff_header(buf: bytes):
    """
    Return (num_channels, sample_rate, bits_per_sample, header_len).
    Raises ValueError until we have the full header (through 'data' chunk).
    """
    if buf[:4] != b"RIFF" or buf[8:12] != b"WAVE":
        raise ValueError("Not a RIFF/WAVE file")

    offset = 12
    num_ch = rate = bps = None
    while offset + 8 <= len(buf):
        chunk_id   = buf[offset:offset + 4]
        chunk_size = int.from_bytes(buf[offset + 4:offset + 8], "little")
        offset += 8

        # Wait until the WHOLE chunk body is in the buffer
        if offset + chunk_size > len(buf):
            raise ValueError("Header incomplete")

        if chunk_id == b"fmt ":
            fmt = buf[offset : offset + 16]            # first 16 bytes
            # ---------  FIX: keep the right order  -------------------
            audio_fmt, num_ch, rate, byte_rate, blk_al, bps = struct.unpack(
                "<HHIIHH", fmt
            )
            # ----------------------------------------------------------
        elif chunk_id == b"data":
            header_len = offset                        # PCM starts here
            return num_ch, rate, bps, header_len

        offset += chunk_size

    raise ValueError("No 'data' chunk yet")


# ---------------------------------------------------------------------
# LiveKit‑style TTS implementation
# ---------------------------------------------------------------------
class SimpleTTS(tts.TTS):
    def __init__(self, cfg: SimpleTTSConfig = SimpleTTSConfig()):
        if cfg.logging_enabled:
            logging.basicConfig(level=cfg.log_level,
                                format="%(asctime)s %(levelname)s: %(message)s")
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=cfg.sample_rate,
            num_channels=cfg.num_channels,
        )
        self.cfg = cfg

    def synthesize(self, file_name: str) -> tts.ChunkedStream:
        return _ChunkedStream(parent=self, file_name=file_name)


# ---------------------------------------------------------------------
# LiveKit‑style chunked stream (fixed)
# ---------------------------------------------------------------------
class _ChunkedStream(tts.ChunkedStream):
    def __init__(self, *, parent: SimpleTTS, file_name: str):
        super().__init__(tts=parent, input_text=file_name)
        self._file_name = file_name

    async def _run(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(SERVER_URL,
                                   params={"file_name": self._file_name}) as resp:
                resp.raise_for_status()

                header_parsed = False
                buf = b""
                last_frame = None  # ← remember the most recent frame

                async for raw in resp.content.iter_chunked(self._tts.cfg.chunk_size):
                    if not raw:
                        continue
                    buf += raw

                    # -- 1. Parse / skip RIFF header once ----------------
                    if not header_parsed:
                        try:
                            ch, rate, bps, hdr_len = parse_riff_header(buf)
                        except ValueError:
                            continue  # header still incomplete
                        logging.info("Header → %d ch | %d Hz | %d bits", ch, rate, bps)
                        assert ch == self._tts.num_channels
                        assert rate == self._tts.sample_rate
                        buf = buf[hdr_len:]          # keep only PCM
                        header_parsed = True
                        if not buf:
                            continue

                    # -- 2. PCM → AudioFrame(s) --------------------------
                    pcm16 = np.frombuffer(buf, dtype=np.int16)
                    buf = b""                       # consumed this chunk

                    for i in range(0, len(pcm16), self._tts.cfg.chunk_size):
                        chunk = pcm16[i:i + self._tts.cfg.chunk_size]
                        if not chunk.size:
                            continue
                        samples = len(chunk) // self._tts.num_channels

                        frame = rtc.AudioFrame(
                            data=chunk.tobytes(),
                            sample_rate=self._tts.sample_rate,
                            num_channels=self._tts.num_channels,
                            samples_per_channel=samples,
                        )

                        # Send *non‑final* frame
                        await self._event_ch.send(
                            tts.SynthesizedAudio(
                                request_id="file-demo",
                                segment_id="0",
                                frame=frame,
                                delta_text=self._input_text,
                                is_final=False,
                            )
                        )
                        last_frame = frame           # remember latest

                # -- 3. Close the stream with the last real frame -------
                if last_frame:
                    await self._event_ch.send(
                        tts.SynthesizedAudio(
                            request_id="file-demo",
                            segment_id="0",
                            frame=last_frame,        # frame **not** None
                            delta_text=self._input_text,
                            is_final=True,
                        )
                    )


# ---------------------------------------------------------------------
# Demo / test harness
# ---------------------------------------------------------------------
async def main():
    tts_engine = SimpleTTS()
    stream = tts_engine.synthesize("abc.wav")

    async for evt in stream:
        if isinstance(evt, tts.SynthesizedAudio) and evt.frame:
            logging.info("Received %d samples", evt.frame.samples_per_channel)


if __name__ == "__main__":
    asyncio.run(main())
