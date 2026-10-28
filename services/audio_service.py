import os
from pydub import AudioSegment


def configure_ffmpeg():
    """Configure ffmpeg path for pydub"""
    try:
        import imageio_ffmpeg as ffmpeg
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
        print(f"Configured ffmpeg from imageio-ffmpeg: {ffmpeg_path}")
        return True
    except ImportError:
        print("imageio-ffmpeg not available")
        return False
    except Exception as e:
        print(f"Error configuring ffmpeg: {e}")
        return False


# Attempt initial configuration on module load
configure_ffmpeg()


def convert_wav_to_compatible_format(wav_filename):
    """Try multiple methods to convert WAV to WhatsApp-compatible format (MP3/OGG)"""
    # First, ensure ffmpeg is configured
    ffmpeg_configured = configure_ffmpeg()

    # Method 1: Try pydub with configured ffmpeg
    if ffmpeg_configured:
        try:
            print("Attempting conversion with pydub and imageio-ffmpeg...")
            audio = AudioSegment.from_wav(wav_filename)
            mp3_filename = wav_filename.replace('.wav', '.mp3')
            audio.export(mp3_filename, format="mp3", bitrate="128k")

            if os.path.exists(mp3_filename):
                print(f"Successfully converted to MP3: {mp3_filename}")
                return mp3_filename, "audio/mpeg"
        except Exception as e:
            print(f"Pydub with imageio-ffmpeg conversion failed: {e}")

    # Method 2: Try pydub without specific ffmpeg configuration (fallback)
    try:
        print("Attempting conversion with default pydub...")
        audio = AudioSegment.from_wav(wav_filename)
        mp3_filename = wav_filename.replace('.wav', '.mp3')
        audio.export(mp3_filename, format="mp3", bitrate="128k")

        if os.path.exists(mp3_filename):
            return mp3_filename, "audio/mpeg"
    except Exception as e:
        print(f"Default pydub conversion failed: {e}")

    # Method 3: Try converting to OGG using pydub (simpler conversion)
    try:
        print("Attempting conversion to OGG...")
        audio = AudioSegment.from_wav(wav_filename)
        ogg_filename = wav_filename.replace('.wav', '.ogg')
        audio.export(ogg_filename, format="ogg")

        if os.path.exists(ogg_filename):
            return ogg_filename, "audio/ogg"
    except Exception as e:
        print(f"OGG conversion failed: {e}")

    # If all conversions fail, return None to indicate failure
    print("All conversion methods failed")
    return None, None


def is_low_quality_transcription(transcription):
    """Check if transcription appears to be low quality/noise"""
    if not transcription or len(transcription.strip()) == 0:
        return True

    words = transcription.split()

    # Too few words (likely noise)
    if len(words) < 2:
        return True

    # Check for excessive repetition
    unique_words = set(words)
    repetition_ratio = len(words) / len(unique_words) if len(unique_words) > 0 else 0

    # If more than 70% of the words are repetitive, it's likely noise
    if repetition_ratio > 5:
        print(f"High repetition detected: {repetition_ratio:.1f}x average")
        return True

    # Check for very long transcriptions with repetitive patterns
    if len(words) > 50:
        word_frequency = {}
        for word in words:
            word_frequency[word] = word_frequency.get(word, 0) + 1

        # If any single word appears more than 30% of the time in a long text, it's likely noise
        max_frequency = max(word_frequency.values()) if word_frequency else 0
        if max_frequency > len(words) * 0.3:
            print(f"Single word dominance detected: {max_frequency}/{len(words)} words")
            return True

    # Check for very short repetitive words that are likely artifacts
    short_repetitive_words = [word for word in words if len(word) <= 3]
    if len(short_repetitive_words) > len(words) * 0.7:  # More than 70% very short words
        print(f"Too many short words: {len(short_repetitive_words)}/{len(words)}")
        return True

    return False
