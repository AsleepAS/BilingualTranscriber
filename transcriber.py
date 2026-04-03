import datetime
import os
import wave

import pyaudio
from openai import OpenAI

TMP_WAV = "recording_tmp.wav"
PERM_PREFIX = "recording_"


def create_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Export your API key before running this script."
        )
    return OpenAI(api_key=api_key)


def list_input_devices(pa):
    """Return a list of dicts for input-capable devices."""
    devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            devices.append(info)
            print(
                f"{i}: {info['name']} "
                f"(channels={info['maxInputChannels']}, "
                f"default SR={info['defaultSampleRate']:.0f})"
            )
    return devices


def format_transcription(client: OpenAI, text: str, output_format: str) -> str:
    if output_format == "md":
        system_prompt = (
            "You format transcribed speech into structured notes.\n\n"
            "Output format:\n"
            "1. Start with a section titled 'Summary' containing 1-4 concise sentences.\n"
            "2. Then include a section titled 'Transcript'.\n"
            "3. Preserve the original wording of the transcript as much as possible.\n"
            "4. Do NOT rewrite, paraphrase, or remove content.\n"
            "5. Only fix minor grammar, punctuation, and obvious transcription errors.\n"
            "6. Organize the text using headings, subheadings, and bullet points where appropriate.\n"
            "7. Do not add new information or interpretations.\n\n"
            "Use Markdown formatting."
        )
    else:  # txt
        system_prompt = (
            "You format transcribed speech into structured plain text notes.\n\n"
            "Output format:\n"
            "1. Start with a section titled 'SUMMARY' containing 1-4 concise sentences.\n"
            "2. Then include a section titled 'TRANSCRIPT (STRUCTURED)'.\n"
            "3. Preserve the original wording of the transcript as much as possible.\n"
            "4. Do NOT rewrite, paraphrase, or remove content.\n"
            "5. Only fix minor grammar, punctuation, and obvious transcription errors.\n"
            "6. Organize the text using headings and indentation where appropriate.\n"
            "7. Do not add new information or interpretations.\n\n"
            "Do not use markdown symbols."
        )

    response = client.responses.create(
        model="o3-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )

    return response.output_text


def save_output(text: str, base_name: str, output_format: str):
    ext = ".md" if output_format == "md" else ".txt"
    filename = base_name + ext

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Formatted output saved as {filename}")


def transcribe_audio(client: OpenAI, name: str):
    with open(name, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    raw_text = transcription.text
    print("\n--- RAW TRANSCRIPTION ---\n")
    print(raw_text)

    choice = input("\nFormat output? [md/txt/N]: ").strip().lower()
    if choice not in ("md", "txt"):
        print("Skipping formatting.")
        return

    print("\nFormatting...\n")
    formatted = format_transcription(client, raw_text, choice)

    base_name = os.path.splitext(name)[0]
    save_output(formatted, base_name, choice)


def main():
    client = create_client()
    pa = pyaudio.PyAudio()
    stream = None
    wavfile = None

    try:
        list_input_devices(pa)
        idx = int(input("Select device index: "))
        info = pa.get_device_info_by_index(idx)

        channels = min(1, int(info["maxInputChannels"]))
        samplerate = int(info["defaultSampleRate"])
        sampwidth = pa.get_sample_size(pyaudio.paInt16)

        print(f"\nOpening stream @ {samplerate} Hz, {channels} ch on '{info['name']}' ...")

        if not pa.is_format_supported(
            samplerate,
            input_device=idx,
            input_channels=channels,
            input_format=pyaudio.paInt16,
        ):
            raise ValueError("Chosen format not supported by this device")

        stream = pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=samplerate,
            input=True,
            frames_per_buffer=1024,
            input_device_index=idx,
        )

        wavfile = wave.open(TMP_WAV, "wb")
        wavfile.setnchannels(channels)
        wavfile.setsampwidth(sampwidth)
        wavfile.setframerate(samplerate)

        print("Recording... Ctrl-C to stop")
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            wavfile.writeframes(data)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except OSError as e:
        print(f"\n⚠ Couldn't open stream: {e}")
        print(
            "   • Check that the device isn't in exclusive use by another program\n"
            "   • Try a different sample-rate or channel count\n"
            "   • Update / re-plug the audio driver"
        )
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        if wavfile is not None:
            wavfile.close()
        pa.terminate()

        if os.path.exists(TMP_WAV):
            ans = input("Transcribe recording? [y/N]: ").strip().lower()
            if ans == "y":
                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                name = f"{PERM_PREFIX}{ts}.wav"
                os.replace(TMP_WAV, name)
                print(f"Saved as {name}")
                print("\nTranscribing...\n")
                transcribe_audio(client, name)
            else:
                os.remove(TMP_WAV)
                print("Recording discarded.")


if __name__ == "__main__":
    main()
