import os
import subprocess
import time
import gc
from typing import Optional

from faster_whisper import WhisperModel

# Model cache to avoid reloading the same model multiple times
_model_cache: dict[str, WhisperModel] = {}


def run_ffmpeg_extract_wav(input_path: str, wav_path: str) -> None:
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


def run_ffmpeg_crop_wav(input_wav: str, output_wav: str, start_time: float, end_time: float) -> None:
    """Crop WAV file to a specific time range.
    
    Args:
        input_wav: Path to input WAV file
        output_wav: Path to output WAV file
        start_time: Start time in seconds
        end_time: End time in seconds
    
    Raises:
        subprocess.CalledProcessError: If ffmpeg fails
    """
    duration = end_time - start_time
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_wav,
            "-ss",
            str(start_time),
            "-t",
            str(duration),
            "-acodec",
            "copy",
            output_wav,
            "-y",  # overwrite
        ],
        check=True,
    )


def transcribe_file(input_path: str, model_size: str = "medium") -> tuple[str, str]:
    """
    Transcribe a video/audio file using faster-whisper.
    
    Args:
        input_path: Path to the target video/audio file
        model_size: Whisper model size (default: "medium")
    
    Returns:
        Tuple of (transcript_text, timestamp_text)
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        subprocess.CalledProcessError: If ffmpeg fails
    """
    transcription_start = time.perf_counter()
    
    input_path = os.path.abspath(os.path.expanduser(input_path))
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    
    input_dir = os.path.dirname(input_path)
    base_name = os.path.basename(os.path.splitext(input_path)[0])
    audio_path = os.path.join(input_dir, base_name + "_temp_audio.wav")
    
    print(f"Loading Whisper model ({model_size})...", flush=True)
    device = "auto"
    compute_type = "int8"
    print(f"  Device: {device}", flush=True)
    print(f"  Compute type: {compute_type}", flush=True)
    model_load_start = time.perf_counter()
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    model_load_time = time.perf_counter() - model_load_start
    print(f"Model loaded. (Loading time: {model_load_time:.2f} seconds)", flush=True)
    
    try:
        print("Extracting audio from video/audio file...", flush=True)
        run_ffmpeg_extract_wav(input_path, audio_path)
        print("Audio extracted. Starting transcription...", flush=True)
        
        transcribe_start = time.perf_counter()
        segments, info = model.transcribe(audio_path, beam_size=5)
        transcribe_time = time.perf_counter() - transcribe_start
        print(f"Transcription complete. Processing {info.language} audio...", flush=True)
        
        transcript_lines: list[str] = []
        time_stamp_lines: list[str]=[]
        for segment in segments:
            segment_with_timestamp = f"[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text)
            print(segment_with_timestamp, flush=True)
            
            transcript_lines.append(segment.text.strip())
            time_stamp_lines.append(segment_with_timestamp.strip())

        transcript_text = "\n".join([line for line in transcript_lines if line])
        timestamp_text = "\n".join([line for line in time_stamp_lines if line])
        
        total_time = time.perf_counter() - transcription_start
        print(f"Transcription ({model_size} model): {total_time:.2f} seconds (loading: {model_load_time:.2f}s, transcribing: {transcribe_time:.2f}s)", flush=True)
        
        return transcript_text, timestamp_text
    
    finally:
        # Clean up temporary audio file
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except OSError:
            pass


def _get_or_load_model(model_size: str, device: str = "auto", compute_type: str = "float32") -> WhisperModel:
    """
    Get a cached model or load a new one if not in cache.
    
    Args:
        model_size: Whisper model size
        device: Device to use ("auto", "cpu", "cuda", "mps")
        compute_type: Compute type ("float32", "int8", etc.)
    
    Returns:
        WhisperModel instance
    """
    cache_key = f"{model_size}_{device}_{compute_type}"
    
    if cache_key not in _model_cache:
        print(f"Loading Whisper model ({model_size})...", flush=True)
        print(f"  Device: {device}", flush=True)
        print(f"  Compute type: {compute_type}", flush=True)
        model_load_start = time.perf_counter()
        _model_cache[cache_key] = WhisperModel(model_size, device=device, compute_type=compute_type)
        model_load_time = time.perf_counter() - model_load_start
        print(f"Model loaded. (Loading time: {model_load_time:.2f} seconds)", flush=True)
    else:
        print(f"Using cached Whisper model ({model_size})", flush=True)
        print(f"  Device: {device}", flush=True)
        print(f"  Compute type: {compute_type}", flush=True)
    
    return _model_cache[cache_key]


def clear_model_cache(model_size: Optional[str] = None) -> None:
    """
    Clear the model cache to free memory.
    
    Args:
        model_size: If provided, only clear this specific model. If None, clear all models.
    """
    global _model_cache
    
    if model_size is None:
        # Clear all models
        for cache_key in list(_model_cache.keys()):
            model = _model_cache.pop(cache_key)
            del model
        _model_cache.clear()
    else:
        # Clear specific model (need to match cache key pattern)
        keys_to_remove = [key for key in _model_cache.keys() if key.startswith(model_size + "_")]
        for key in keys_to_remove:
            model = _model_cache.pop(key)
            del model
    
    # Force garbage collection to free GPU/accelerator memory
    gc.collect()


def transcribe_wav_file(
    wav_path: str, 
    model_size: str = "medium", 
    language: str = "en",
    clear_model_after: bool = False
) -> tuple[str, str]:
    """
    Transcribe a WAV audio file using faster-whisper.
    
    Args:
        wav_path: Path to the WAV audio file
        model_size: Whisper model size (default: "medium")
        language: Language code (default: "en")
        clear_model_after: If True, clear the model from cache after use (default: False)
    
    Returns:
        Tuple of (transcript_text, timestamp_text)
    
    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    transcription_start = time.perf_counter()
    
    wav_path = os.path.abspath(os.path.expanduser(wav_path))
    
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"File not found: {wav_path}")
    
    device = "auto"
    compute_type = "int8"
    model_load_start = time.perf_counter()
    model = _get_or_load_model(model_size, device=device, compute_type=compute_type)
    model_load_time = time.perf_counter() - model_load_start
    
    try:
        print("Starting transcription...", flush=True)
        transcribe_start = time.perf_counter()
        segments, info = model.transcribe(wav_path, beam_size=5, language=language)
        transcribe_time = time.perf_counter() - transcribe_start
        print(f"Transcription complete. Processing {info.language} audio...", flush=True)
        
        transcript_lines: list[str] = []
        time_stamp_lines: list[str]=[]
        for segment in segments:
            segment_with_timestamp = f"[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text)
            print(segment_with_timestamp, flush=True)
            
            transcript_lines.append(segment.text.strip())
            time_stamp_lines.append(segment_with_timestamp.strip())

        transcript_text = "\n".join([line for line in transcript_lines if line])
        timestamp_text = "\n".join([line for line in time_stamp_lines if line])
        
        total_time = time.perf_counter() - transcription_start
        print(f"Transcription ({model_size} model): {total_time:.2f} seconds (loading: {model_load_time:.2f}s, transcribing: {transcribe_time:.2f}s)", flush=True)
        
        # Print the full unformatted transcript text
        print(f"\n{'='*60}", flush=True)
        print(f"Full Transcript Text ({len(transcript_text)} characters):", flush=True)
        print(f"{'='*60}", flush=True)
        print(transcript_text, flush=True)
        print(f"{'='*60}\n", flush=True)
        
        return transcript_text, timestamp_text
    
    finally:
        if clear_model_after:
            clear_model_cache(model_size)
