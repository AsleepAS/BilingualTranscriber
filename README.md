# BilingualTranscriber

Simple local microphone recorder + OpenAI transcription helper.

## What this does

- Lists your available audio input devices.
- Records audio from your selected device until you press `Ctrl-C`.
- Saves the recording as a timestamped `.wav` file.
- Sends audio to `whisper-1` for transcription.
- Optionally formats the transcript using `o3-mini` as either:
  - Markdown notes (`.md`)
  - Plain structured text (`.txt`)

## Requirements

- Python 3.9+
- PortAudio (required by PyAudio)
- Python packages:
  - `openai`
  - `pyaudio`

## Setup

1. Install system dependency (PortAudio) using your OS package manager.
2. Install Python packages:

```bash
pip install openai pyaudio
```

3. Set your API key (recommended: environment variable, **not hardcoded**):

```bash
export OPENAI_API_KEY="your_key_here"
```

## Run

```bash
python transcriber.py
```

## Notes

- The script creates a temporary file `recording_tmp.wav` while recording.
- If you choose to transcribe, the file is renamed to `recording_YYYYMMDD-HHMMSS.wav`.
- If you decline transcription, the temporary recording is deleted.
