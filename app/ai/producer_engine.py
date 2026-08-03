import os
import tempfile
import uuid
import contextlib


class AIProducer:

    def __init__(self):
        self.provider = "internal"
        self.model_name = "procedural"

    def has_module(self, module_name):
        try:
            import importlib.util
            return importlib.util.find_spec(module_name) is not None
        except Exception:
            return False

    def capabilities(self):
        musicgen = self.musicgen_available()
        transformers = self.transformers_musicgen_available()
        return {
            "provider": self.provider,
            "musicgen_available": musicgen,
            "transformers_musicgen_available": transformers,
            "torch_available": self.has_module("torch"),
            "audiocraft_available": self.has_module("audiocraft"),
            "transformers_available": self.has_module("transformers"),
            "fallback_procedural": True,
            "message": (
                "AI Producer sinifi, once MusicGen veya Transformers MusicGen ile uretim deniyor. "
                "Yoksa dahili prosedural ses motorunu kullanarak demo bir DJ parcasi uretir."
            ),
        }

    def musicgen_available(self):
        return self.has_module("audiocraft")

    def transformers_musicgen_available(self):
        if not self.has_module("transformers"):
            return False

        try:
            from transformers import MusicgenForConditionalGeneration  # noqa: F401
            return True
        except Exception:
            return False

    def _build_output_folder(self, output_folder):
        folder = os.path.abspath(output_folder or "DJ_AI_PRODUCER")
        os.makedirs(folder, exist_ok=True)
        return folder

    def generate_from_prompt(self, prompt, style="AFRO HOUSE", duration_seconds=16, output_folder="DJ_AI_PRODUCER"):
        prompt = str(prompt or "").strip()
        if not prompt:
            return {
                "ok": False,
                "reason": "EMPTY_PROMPT",
                "message": "Lutfen bir parcayi veya tarzi aciklayan bir metin girin.",
            }

        if self.musicgen_available():
            try:
                return self._generate_with_musicgen(prompt, duration_seconds, output_folder)
            except Exception as exc:
                fallback_message = f"MusicGen basarisiz oldu: {exc}."
                self.provider = "procedural"
                self.model_name = "procedural"
                return self._generate_procedural(prompt, style, duration_seconds, output_folder, fallback_message)

        if self.transformers_musicgen_available():
            try:
                return self._generate_with_transformers(prompt, duration_seconds, output_folder)
            except Exception as exc:
                fallback_message = f"Transformers MusicGen basarisiz oldu: {exc}."
                self.provider = "procedural"
                self.model_name = "procedural"
                return self._generate_procedural(prompt, style, duration_seconds, output_folder, fallback_message)

        return self._generate_procedural(prompt, style, duration_seconds, output_folder)

    def _generate_with_musicgen(self, prompt, duration_seconds, output_folder):
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write

        model = MusicGen.get_pretrained("facebook/musicgen-small")
        model.set_generation_params(duration=duration_seconds)
        audio = model.generate([prompt])

        folder = self._build_output_folder(output_folder)
        file_name = f"ai_producer_{uuid.uuid4().hex[:8]}.wav"
        wav_path = os.path.join(folder, file_name)

        audio_write(wav_path, audio[0].cpu(), model.sample_rate, strategy="loudness", loudness_compressor=True)

        self.provider = "MusicGen"
        self.model_name = "facebook/musicgen-small"

        return {
            "ok": True,
            "wav_path": wav_path,
            "provider": self.provider,
            "model": self.model_name,
            "prompt": prompt,
        }

    def _generate_with_transformers(self, prompt, duration_seconds, output_folder):
        from transformers import AutoProcessor, MusicgenForConditionalGeneration
        import torch
        import soundfile as sf

        model_name = "facebook/musicgen-small"
        processor = AutoProcessor.from_pretrained(model_name)
        model = MusicgenForConditionalGeneration.from_pretrained(model_name)

        inputs = processor(text=[prompt], return_tensors="pt")
        audio_values = model.generate(**inputs, max_new_tokens=512)

        folder = self._build_output_folder(output_folder)
        file_name = f"ai_producer_{uuid.uuid4().hex[:8]}.wav"
        wav_path = os.path.join(folder, file_name)

        audio_array = audio_values[0].cpu().numpy()
        sample_rate = model.config.audio_encoder.sampling_rate
        sf.write(wav_path, audio_array, sample_rate)

        self.provider = "Transformers MusicGen"
        self.model_name = model_name

        return {
            "ok": True,
            "wav_path": wav_path,
            "provider": self.provider,
            "model": self.model_name,
            "prompt": prompt,
        }

    def _generate_procedural(self, prompt, style, duration_seconds, output_folder, note=""):
        from app.ai.remix_lab import RemixLab

        self.provider = "procedural"
        self.model_name = "procedural-synth"

        fake_track = {
            "id": f"producer-{uuid.uuid4().hex}",
            "name": prompt,
            "path": "",
            "camelot": "8A",
            "bpm": 120,
            "energy": 0.66,
        }

        if duration_seconds < 8:
            duration_seconds = 8

        remix_lab = RemixLab()
        result = remix_lab.render_remix_wav(
            fake_track,
            style,
            output_folder=output_folder,
            duration_seconds=duration_seconds
        )

        result["provider"] = self.provider
        result["prompt"] = prompt
        result["note"] = note or (
            "Music generation model yuku bulunamadi; prosedural AI prod" 
            " motoruyla demo ses olusturuldu."
        )

        return result

    def generate_procedural_beat(self, style="AFRO HOUSE", duration_seconds=16, output_folder="DJ_AI_PRODUCER"):
        return self._generate_procedural("AI beat production", style, duration_seconds, output_folder)

    def remix_track(self, track, target_style="AFRO HOUSE", output_folder="DJ_AI_PRODUCER"):
        if not track:
            return {
                "ok": False,
                "reason": "NO_TRACK",
                "message": "Remix yapmak icin once bir parca secin.",
            }

        if not track.get("path") and track.get("id"):
            track["path"] = track.get("id")

        result = self._generate_procedural(track.get("name", "AI Remix"), target_style, 96, output_folder)
        result["remix_source"] = track.get("name")
        return result
