"""
Audio transcription service using OpenAI Whisper
"""
import io
import asyncio
from typing import Optional, AsyncGenerator, Callable
from datetime import datetime
import openai
from config import get_settings
from models import TranscriptSegment, SpeakerType


class TranscriptionService:
    """Handles audio-to-text transcription using OpenAI Whisper"""

    def __init__(self):
        self.settings = get_settings()
        self.client = openai.AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.is_processing = False
        self._callbacks: list[Callable] = []

    def add_callback(self, callback: Callable):
        """Add a callback to be called when new transcription is available"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """Remove a transcription callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify_callbacks(self, segment: TranscriptSegment):
        """Notify all callbacks of new transcription"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(segment)
                else:
                    callback(segment)
            except Exception as e:
                print(f"Callback error: {e}")

    async def transcribe_audio(
        self,
        audio_data: bytes,
        source: str = "microphone",
        language: str = "en"
    ) -> Optional[TranscriptSegment]:
        """
        Transcribe audio data to text using Whisper API.

        Args:
            audio_data: Raw audio bytes (WAV format preferred)
            source: "microphone" or "system" to help with speaker identification
            language: Language code for transcription

        Returns:
            TranscriptSegment with the transcribed text
        """
        if not audio_data or len(audio_data) < 1000:  # Skip very short chunks
            return None

        try:
            # Create a file-like object from audio bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"

            # Call Whisper API
            response = await self.client.audio.transcriptions.create(
                model=self.settings.whisper_model,
                file=audio_file,
                language=language,
                response_format="verbose_json"
            )

            # Skip empty or very short transcriptions
            if not response.text or len(response.text.strip()) < 2:
                return None

            # Determine speaker based on source
            # System audio = interviewer, Microphone = candidate
            speaker = (
                SpeakerType.INTERVIEWER if source == "system"
                else SpeakerType.CANDIDATE if source == "microphone"
                else SpeakerType.UNKNOWN
            )

            segment = TranscriptSegment(
                text=response.text.strip(),
                speaker=speaker,
                duration=getattr(response, 'duration', None),
                confidence=1.0,  # Whisper doesn't return confidence per-segment
                is_final=True
            )

            # Notify callbacks
            await self._notify_callbacks(segment)

            return segment

        except openai.APIError as e:
            print(f"Whisper API error: {e}")
            return None
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        source: str = "microphone",
        chunk_duration: float = 3.0
    ) -> AsyncGenerator[TranscriptSegment, None]:
        """
        Stream transcription from an audio generator.

        Args:
            audio_stream: Async generator yielding audio chunks
            source: Audio source identifier
            chunk_duration: Duration of each chunk in seconds

        Yields:
            TranscriptSegment for each processed chunk
        """
        self.is_processing = True
        buffer = bytearray()
        sample_rate = self.settings.audio_sample_rate
        bytes_per_chunk = int(sample_rate * 2 * chunk_duration)  # 16-bit audio

        try:
            async for chunk in audio_stream:
                buffer.extend(chunk)

                # Process when we have enough audio
                if len(buffer) >= bytes_per_chunk:
                    audio_data = bytes(buffer[:bytes_per_chunk])
                    buffer = buffer[bytes_per_chunk:]

                    segment = await self.transcribe_audio(audio_data, source)
                    if segment:
                        yield segment

            # Process remaining buffer
            if buffer:
                segment = await self.transcribe_audio(bytes(buffer), source)
                if segment:
                    yield segment

        finally:
            self.is_processing = False

    def stop(self):
        """Stop ongoing transcription"""
        self.is_processing = False


class DualStreamTranscriber:
    """
    Handles transcription from two audio sources simultaneously:
    - System audio (interviewer)
    - Microphone (candidate)
    """

    def __init__(self):
        self.system_transcriber = TranscriptionService()
        self.mic_transcriber = TranscriptionService()
        self._combined_callbacks: list[Callable] = []
        self.is_running = False

    def add_callback(self, callback: Callable):
        """Add callback for combined transcript"""
        self._combined_callbacks.append(callback)

        # Also add to individual transcribers
        self.system_transcriber.add_callback(callback)
        self.mic_transcriber.add_callback(callback)

    async def process_dual_stream(
        self,
        system_stream: AsyncGenerator[bytes, None],
        mic_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[TranscriptSegment, None]:
        """
        Process both audio streams concurrently.

        Args:
            system_stream: System audio generator (interviewer)
            mic_stream: Microphone audio generator (candidate)

        Yields:
            TranscriptSegment from either source
        """
        import asyncio

        self.is_running = True

        async def process_system():
            async for segment in self.system_transcriber.transcribe_stream(
                system_stream, source="system"
            ):
                yield segment

        async def process_mic():
            async for segment in self.mic_transcriber.transcribe_stream(
                mic_stream, source="microphone"
            ):
                yield segment

        # Create queues for both streams
        queue = asyncio.Queue()

        async def enqueue_segments(generator, source_name):
            try:
                async for segment in generator:
                    await queue.put(segment)
            except Exception as e:
                print(f"Error in {source_name}: {e}")
            finally:
                await queue.put(None)  # Signal completion

        # Start both tasks
        task1 = asyncio.create_task(
            enqueue_segments(process_system(), "system")
        )
        task2 = asyncio.create_task(
            enqueue_segments(process_mic(), "mic")
        )

        completed = 0
        while self.is_running and completed < 2:
            try:
                segment = await asyncio.wait_for(queue.get(), timeout=0.5)
                if segment is None:
                    completed += 1
                else:
                    yield segment
            except asyncio.TimeoutError:
                continue

        # Clean up
        task1.cancel()
        task2.cancel()

    def stop(self):
        """Stop all transcription"""
        self.is_running = False
        self.system_transcriber.stop()
        self.mic_transcriber.stop()
