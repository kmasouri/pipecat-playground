from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.whisper.stt import WhisperSTTService, Model
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.processors.frame_processor import FrameProcessor
from fastapi import WebSocket
import os
import structlog

log = structlog.get_logger()


async def run_bot(
    websocket_client: WebSocket, stream_sid: str, call_sid: str, testing: bool
):
    # This serializer handles converting between Pipecat frames and Twilio’s WebSocket media streams protocol.
    # It supports audio conversion, DTMF events, and automatic call termination.
    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        # account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        # auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    # Provides bidirectional WebSocket communication with frame serialization, session management, and event handling for client connections and timeouts
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
        ),
    )

    # Initialize AI services
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))

    asr = WhisperSTTService(model=Model.TINY, device="auto")

    transcript = TranscriptProcessor()

    # tts = CartesiaTTSService(
    #     api_key=os.getenv("CARTESIA_API_KEY"),
    #     voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
    #     push_silence_after_stop=testing,
    # )

    # Create the initial conversation prompt
    messages = [
        {
            "role": "system",
            "content": "You are an elementary teacher in an audio call. Your output will be converted to audio so don't include special characters in your answers. Respond to what the student said in a short short sentence.",
        },
    ]

    # Setup the context aggregator
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # Create an audio buffer processor to capture conversation audio
    audio_buffer = AudioBufferProcessor()

    # Build the pipeline
    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            asr,  # Speech recognition
            transcript.user(),  # Capture user transcript
            audio_buffer,  # Used to buffer the audio in the pipeline
        ]
    )

    # Create a pipeline task with appropriate parameters
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,  # Twilio uses 8kHz audio
            audio_out_sample_rate=8000,
            allow_interruptions=False,
        ),
    )

    # Setup event handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Start recording
        await audio_buffer.start_recording()
        # Kickstart the conversation
        messages.append(
            {"role": "system", "content": "Please introduce yourself to the user."}
        )
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    @audio_buffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        server_name = f"server_{websocket_client.client.port}"

    @transcript.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        print(frame)

    # Run the pipeline
    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)
