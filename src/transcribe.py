import os
import subprocess

from faster_whisper import WhisperModel
from pydantic import BaseModel
from typing import List

class TextSegment(BaseModel):
    start_time:str
    end_time: str
    segment:str

def _run_ffmpeg_extract_wav(input_path: str, wav_path: str) -> None:
    """Extract audio from video/audio file and normalize to mono 16kHz PCM WAV."""
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_path,
            "-vn",  # no video
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            wav_path,
            "-y",  # overwrite
        ],
        check=True,
    )


def transcribe_file(input_path: str, model_size: str = "medium") -> tuple[str, List[TextSegment]]:
    """
    Transcribe a video/audio file using faster-whisper.
    
    Args:
        input_path: Path to the target video/audio file
        model_size: Whisper model size (default: "medium")
    
    Returns:
        Tuple of (transcript_text, detected_language)
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        subprocess.CalledProcessError: If ffmpeg fails
    """
    input_path = os.path.abspath(os.path.expanduser(input_path))
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    
    input_dir = os.path.dirname(input_path)
    base_name = os.path.basename(os.path.splitext(input_path)[0])
    audio_path = os.path.join(input_dir, base_name + "_temp_audio.wav")
    
    print(f"Loading Whisper model ({model_size})...", flush=True)
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    print("Model loaded.", flush=True)
    
    try:
        print("Extracting audio from video/audio file...", flush=True)
        _run_ffmpeg_extract_wav(input_path, audio_path)
        print("Audio extracted. Starting transcription...", flush=True)
        
        segments, info = model.transcribe(audio_path, beam_size=5)
        print(f"Transcription complete. Processing {info.language} audio...", flush=True)
        
        transcript_lines: list[str] = []
        time_stamp_lines: list[TextSegment]=[]
        for segment in segments:
            print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text), flush=True)
            
            segment_obj:TextSegment = {
                TextSegment.start_time:segment.start,
                TextSegment.end_time:segment.end, 
                TextSegment.segment_text: segment.text
                }

            transcript_lines.append(segment.text.strip())
            time_stamp_lines.append(segment_obj)

        transcript_text = "\n".join([line for line in transcript_lines if line])
        return transcript_text, time_stamp_lines
    
    finally:
        # Clean up temporary audio file
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except OSError:
            pass
