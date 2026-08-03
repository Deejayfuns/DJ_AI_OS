try:
    import librosa
    import numpy as np
except Exception:
    librosa = None
    np = None

import math
import os
import shutil
import struct
import subprocess
import wave

from app.ai.mix_master_doctor import MixMasterDoctor


class MixMasterEngine:

    def __init__(self, sample_rate=44100, max_duration=420):

        self.sample_rate = sample_rate
        self.max_duration = max_duration
        self.doctor = MixMasterDoctor()

    def analyze_file(self, path):

        if librosa is None or np is None:
            if str(path or "").lower().endswith(".wav"):
                return self.analyze_wav_without_librosa(path)

            ffmpeg_result = self.analyze_with_ffmpeg_fallback(path)

            if ffmpeg_result.get("ok"):
                return ffmpeg_result

            return self.fallback(
                path,
                ffmpeg_result.get("reason", "LIBROSA_NOT_AVAILABLE"),
                (
                    "MP3/FLAC/M4A waveform icin librosa veya FFmpeg gerekir. "
                    "Kurulum: python -m pip install librosa numpy soundfile audioread "
                    "veya winget install Gyan.FFmpeg. WAV dosyalari paket olmadan analiz edilir."
                )
            )

        try:
            y, sr = librosa.load(
                path,
                sr=self.sample_rate,
                mono=False,
                duration=self.max_duration
            )
        except Exception as exc:
            return self.fallback(path, str(exc))

        if y is None or np.size(y) == 0:
            return self.fallback(path, "EMPTY_AUDIO")

        stereo = self.ensure_stereo(y)
        mono = np.mean(stereo, axis=0)
        duration = len(mono) / float(sr or self.sample_rate)
        spectrum = self.spectral_profile(mono, sr)
        dynamics = self.dynamic_profile(mono)
        stereo_profile = self.stereo_profile(stereo)
        transient = self.transient_profile(mono, sr)

        track = {
            "name": str(path).split("\\")[-1].split("/")[-1],
            "energy": dynamics["energy"],
            "brightness": spectrum["brightness"],
            "roughness": spectrum["harshness"],
            "danceability": transient["groove_confidence"],
            "drop_strength": transient["punch"],
            "vocal_risk": spectrum["mid_presence"],
            "intro_outro_mixability": dynamics["dynamic_range_score"],
            "stereo_width": stereo_profile["width"],
            "phase_correlation": stereo_profile["correlation"],
            "role": "PEAK TIME" if dynamics["energy"] > 0.72 else "GROOVE",
        }
        doctor_report = self.doctor.diagnose(track)

        return {
            "ok": True,
            "engine": "LIBROSA_FULL",
            "path": path,
            "duration": round(duration, 2),
            "sample_rate": sr,
            "spectrum": spectrum,
            "dynamics": dynamics,
            "stereo": stereo_profile,
            "transient": transient,
            "doctor": doctor_report,
            "studio_verdict": self.studio_verdict(
                spectrum,
                dynamics,
                stereo_profile,
                transient
            ),
            "repair_plan": self.repair_plan(spectrum, dynamics, stereo_profile, transient),
            "recreation_dna": self.recreation_dna(spectrum, dynamics, stereo_profile, transient),
            "master_chain": self.master_chain(doctor_report),
            "render_targets": self.render_targets(track),
            "waveform": self.waveform_preview_librosa(mono),
            "phrase_points": self.phrase_points_from_waveform(
                self.waveform_preview_librosa(mono)
            ),
        }

    def analyze_with_ffmpeg_fallback(self, path):

        if not path or not os.path.exists(path):
            return self.fallback(path, "SOURCE_FILE_NOT_FOUND")

        ffmpeg = shutil.which("ffmpeg")

        if not ffmpeg:
            return self.fallback(path, "FFMPEG_NOT_AVAILABLE")

        sr = self.sample_rate
        channels = 2
        max_bytes = int(sr * self.max_duration * channels * 2)
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            path,
            "-t",
            str(self.max_duration),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            str(channels),
            "-ar",
            str(sr),
            "-",
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                timeout=90
            )
        except Exception as exc:
            return self.fallback(path, f"FFMPEG_DECODE_ERROR: {exc}")

        raw = process.stdout[:max_bytes]

        if process.returncode != 0 or not raw:
            reason = process.stderr.decode(errors="ignore")[-500:] or "FFMPEG_EMPTY_AUDIO"
            return self.fallback(path, reason)

        samples = self.decode_pcm(raw, 2)
        left, right = self.split_channels(samples, channels)
        mono = [
            (left[index] + right[index]) * 0.5
            for index in range(min(len(left), len(right)))
        ]

        return self.analyze_plain_pcm(
            path=path,
            mono=mono,
            left=left,
            right=right,
            sr=sr,
            engine="FFMPEG_PCM_FALLBACK",
            note=(
                "Librosa yok; MP3/FLAC/M4A dosyasi FFmpeg ile PCM'e decode edilip "
                "waveform ve mix-master analizi uretildi."
            )
        )

    def analyze_plain_pcm(self, path, mono, left, right, sr, engine, note):

        if not mono:
            return self.fallback(path, "EMPTY_AUDIO")

        duration = len(mono) / float(sr or self.sample_rate)
        dynamics = self.dynamic_profile_plain(mono)
        stereo_profile = self.stereo_profile_plain(left, right)
        transient = self.transient_profile_plain(mono, sr)
        spectrum = self.spectral_profile_plain(mono, sr, dynamics, transient)

        track = {
            "name": os.path.basename(path),
            "energy": dynamics["energy"],
            "brightness": spectrum["brightness"],
            "roughness": spectrum["harshness"],
            "danceability": transient["groove_confidence"],
            "drop_strength": transient["punch"],
            "vocal_risk": spectrum["mid_presence"],
            "intro_outro_mixability": dynamics["dynamic_range_score"],
            "stereo_width": stereo_profile["width"],
            "phase_correlation": stereo_profile["correlation"],
            "role": "PEAK TIME" if dynamics["energy"] > 0.72 else "GROOVE",
        }
        doctor_report = self.doctor.diagnose(track)
        waveform = self.waveform_preview_plain(mono)

        return {
            "ok": True,
            "engine": engine,
            "path": path,
            "duration": round(duration, 2),
            "sample_rate": sr,
            "spectrum": spectrum,
            "dynamics": dynamics,
            "stereo": stereo_profile,
            "transient": transient,
            "doctor": doctor_report,
            "studio_verdict": self.studio_verdict(
                spectrum,
                dynamics,
                stereo_profile,
                transient
            ),
            "repair_plan": self.repair_plan(spectrum, dynamics, stereo_profile, transient),
            "recreation_dna": self.recreation_dna(spectrum, dynamics, stereo_profile, transient),
            "master_chain": self.master_chain(doctor_report),
            "render_targets": self.render_targets(track),
            "waveform": waveform,
            "phrase_points": self.phrase_points_from_waveform(waveform),
            "analysis_note": note,
        }

    def analyze_wav_without_librosa(self, path):

        try:
            with wave.open(path, "rb") as handle:
                channels = handle.getnchannels()
                sample_width = handle.getsampwidth()
                sr = handle.getframerate()
                frames = min(
                    handle.getnframes(),
                    int(sr * self.max_duration)
                )
                raw = handle.readframes(frames)
        except Exception as exc:
            return self.fallback(path, f"WAV_READ_ERROR: {exc}")

        samples = self.decode_pcm(raw, sample_width)

        if not samples:
            return self.fallback(path, "EMPTY_WAV")

        left, right = self.split_channels(samples, channels)
        mono = [
            (left[index] + right[index]) * 0.5
            for index in range(min(len(left), len(right)))
        ]
        return self.analyze_plain_pcm(
            path=path,
            mono=mono,
            left=left,
            right=right,
            sr=sr,
            engine="WAV_STDLIB_FALLBACK",
            note=(
                "Librosa yok; WAV dosyasi Python stdlib fallback motoru ile analiz edildi. "
                "Spektrum degerleri yaklasik, dynamics/stereo degerleri gercek PCM verisinden uretilir."
            ),
        )

    def decode_pcm(self, raw, sample_width):

        if not raw:
            return []

        if sample_width == 1:
            return [
                (byte - 128) / 128.0
                for byte in raw
            ]

        if sample_width == 2:
            count = len(raw) // 2
            values = struct.unpack("<" + "h" * count, raw[:count * 2])
            return [value / 32768.0 for value in values]

        if sample_width == 3:
            values = []

            for index in range(0, len(raw) - 2, 3):
                chunk = raw[index:index + 3]
                value = int.from_bytes(
                    chunk + (b"\xff" if chunk[2] & 0x80 else b"\x00"),
                    byteorder="little",
                    signed=True
                )
                values.append(value / 8388608.0)

            return values

        if sample_width == 4:
            count = len(raw) // 4
            values = struct.unpack("<" + "i" * count, raw[:count * 4])
            return [value / 2147483648.0 for value in values]

        return []

    def split_channels(self, samples, channels):

        channels = max(1, int(channels or 1))

        if channels == 1:
            return samples, list(samples)

        left = samples[0::channels]
        right = samples[1::channels]

        if not right:
            right = list(left)

        return left, right

    def dynamic_profile_plain(self, mono):

        peak = max((abs(value) for value in mono), default=0)
        rms = math.sqrt(sum(value * value for value in mono) / max(len(mono), 1))
        crest = peak / max(rms, 1e-9)
        clipping = sum(1 for value in mono if abs(value) >= 0.98) / max(len(mono), 1)
        energy = max(0, min(1, rms * 8))
        dynamic_range_score = max(0, min(1, (crest - 2.5) / 9))

        return {
            "peak_dbfs": round(self.db_plain(peak), 2),
            "rms_dbfs": round(self.db_plain(rms), 2),
            "lufs_proxy": round(self.db_plain(rms) - 1.5, 2),
            "crest_factor": round(crest, 2),
            "clipping_ratio": round(clipping, 5),
            "energy": round(energy, 3),
            "dynamic_range_score": round(dynamic_range_score, 3),
            "headroom_db": round(max(0, -self.db_plain(peak)), 2),
        }

    def stereo_profile_plain(self, left, right):

        size = min(len(left), len(right))

        if size <= 1:
            return {
                "width": 0,
                "correlation": 1,
                "mono_risk": "LOW",
            }

        left = left[:size]
        right = right[:size]
        mid_power = 0
        side_power = 0
        sum_l = sum(left)
        sum_r = sum(right)
        mean_l = sum_l / size
        mean_r = sum_r / size
        cov = 0
        var_l = 0
        var_r = 0

        for index in range(size):
            mid = (left[index] + right[index]) * 0.5
            side = (left[index] - right[index]) * 0.5
            mid_power += mid * mid
            side_power += side * side
            dl = left[index] - mean_l
            dr = right[index] - mean_r
            cov += dl * dr
            var_l += dl * dl
            var_r += dr * dr

        width = max(0, min(1, side_power / max(mid_power, 1e-9)))
        corr = cov / max(math.sqrt(var_l * var_r), 1e-9)
        corr = max(-1, min(1, corr))

        return {
            "width": round(width, 3),
            "correlation": round(corr, 3),
            "mono_risk": "HIGH" if corr < 0.25 or width > 0.8 else "LOW",
        }

    def transient_profile_plain(self, mono, sr):

        window = max(128, int((sr or self.sample_rate) * 0.02))
        envelopes = []

        for index in range(0, len(mono), window):
            chunk = mono[index:index + window]

            if not chunk:
                continue

            envelopes.append(
                math.sqrt(sum(value * value for value in chunk) / len(chunk))
            )

        if len(envelopes) < 2:
            punch = 0
        else:
            diffs = [
                max(0, envelopes[index] - envelopes[index - 1])
                for index in range(1, len(envelopes))
            ]
            avg = sum(envelopes) / max(len(envelopes), 1)
            punch = (sum(diffs) / max(len(diffs), 1)) / max(avg, 1e-9)

        groove = max(0, min(1, (sum(envelopes) / max(len(envelopes), 1)) * 8))

        return {
            "tempo": 0,
            "punch": round(max(0, min(1, punch)), 3),
            "groove_confidence": round(groove, 3),
        }

    def spectral_profile_plain(self, mono, sr, dynamics, transient):

        zcr = self.zero_crossing_rate(mono)
        brightness = max(0, min(1, zcr * 18))
        harshness = max(0, min(1, (brightness * 0.55) + (dynamics["clipping_ratio"] * 120)))
        mud_risk = max(0, min(1, (1 - brightness) * dynamics["energy"] * 0.55))
        mid_presence = max(0, min(1, dynamics["energy"] * 0.65 + brightness * 0.2))

        return {
            "bands": {
                "sub": 0,
                "bass": round(dynamics["energy"] * 0.18, 4),
                "low_mid": round(mud_risk * 0.18, 4),
                "mid": round(mid_presence * 0.2, 4),
                "presence": round(harshness * 0.12, 4),
                "air": round(brightness * 0.08, 4),
            },
            "brightness": round(brightness, 3),
            "harshness": round(harshness, 3),
            "mud_risk": round(mud_risk, 3),
            "mid_presence": round(mid_presence, 3),
            "spectral_centroid_hz": round(brightness * (sr or self.sample_rate) / 2, 2),
            "rolloff_hz": round(min((sr or self.sample_rate) / 2, brightness * (sr or self.sample_rate)), 2),
        }

    def zero_crossing_rate(self, mono):

        if len(mono) < 2:
            return 0

        crossings = 0
        last = mono[0]

        for value in mono[1:]:
            if (last < 0 <= value) or (last >= 0 > value):
                crossings += 1

            last = value

        return crossings / max(len(mono) - 1, 1)

    def waveform_preview_plain(self, mono, points=768):

        if not mono:
            return []

        step = max(1, len(mono) // points)
        preview = [
            mono[index]
            for index in range(0, len(mono), step)
        ][:points]
        peak = max((abs(value) for value in preview), default=1) or 1

        return [
            round(value / peak, 4)
            for value in preview
        ]

    def waveform_preview_librosa(self, mono, points=1024):

        if mono is None or len(mono) == 0 or np is None:
            return []

        indexes = np.linspace(0, len(mono) - 1, points).astype(int)
        preview = mono[indexes]
        peak = float(np.max(np.abs(preview)) or 1)

        return [
            round(float(value / peak), 4)
            for value in preview
        ]

    def phrase_points_from_waveform(self, waveform):

        if not waveform:
            return []

        values = [abs(float(value or 0)) for value in waveform]
        length = len(values)
        peak = max(values) or 1
        normalized = [value / peak for value in values]

        start = self.first_above(normalized, 0.06)
        build = self.first_above(normalized, 0.42)
        peak_index = max(range(length), key=lambda index: normalized[index])
        outro = self.last_above(normalized, 0.16)

        return [
            self.phrase_point("START", start, length),
            self.phrase_point("BUILD", build, length),
            self.phrase_point("PEAK", peak_index, length),
            self.phrase_point("OUTRO", outro, length),
        ]

    def phrase_point(self, label, index, length):

        index = max(0, min(int(index or 0), max(length - 1, 0)))
        position = 0 if length <= 1 else index / (length - 1)

        return {
            "label": label,
            "position": round(position, 3),
        }

    def first_above(self, values, threshold):

        for index, value in enumerate(values):
            if value >= threshold:
                return index

        return 0

    def last_above(self, values, threshold):

        for index in range(len(values) - 1, -1, -1):
            if values[index] >= threshold:
                return index

        return len(values) - 1

    def ensure_stereo(self, y):

        array = np.asarray(y, dtype=float)

        if array.ndim == 1:
            return np.vstack([array, array])

        if array.shape[0] == 1:
            return np.vstack([array[0], array[0]])

        return array[:2]

    def spectral_profile(self, mono, sr):

        stft = np.abs(librosa.stft(mono, n_fft=4096, hop_length=1024))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
        power = np.mean(stft, axis=1) + 1e-9
        total = float(np.sum(power) or 1)

        bands = {
            "sub": self.band_energy(freqs, power, 20, 60, total),
            "bass": self.band_energy(freqs, power, 60, 140, total),
            "low_mid": self.band_energy(freqs, power, 140, 450, total),
            "mid": self.band_energy(freqs, power, 450, 2500, total),
            "presence": self.band_energy(freqs, power, 2500, 6000, total),
            "air": self.band_energy(freqs, power, 6000, 16000, total),
        }
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=mono, sr=sr)))
        rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=mono, sr=sr)))

        return {
            "bands": bands,
            "brightness": round(max(0, min(1, centroid / 5500)), 3),
            "harshness": round(max(0, min(1, (bands["presence"] * 8) + (bands["air"] * 3))), 3),
            "mud_risk": round(max(0, min(1, bands["low_mid"] * 8)), 3),
            "mid_presence": round(max(0, min(1, bands["mid"] * 5)), 3),
            "spectral_centroid_hz": round(centroid, 2),
            "rolloff_hz": round(rolloff, 2),
        }

    def band_energy(self, freqs, power, low, high, total):

        mask = (freqs >= low) & (freqs < high)

        if not np.any(mask):
            return 0

        return round(float(np.sum(power[mask]) / total), 4)

    def dynamic_profile(self, mono):

        peak = float(np.max(np.abs(mono)) or 0)
        rms = float(np.sqrt(np.mean(np.square(mono))) or 0)
        crest = peak / max(rms, 1e-9)
        clipping = float(np.mean(np.abs(mono) >= 0.98))
        energy = max(0, min(1, rms * 8))
        dynamic_range_score = max(0, min(1, (crest - 2.5) / 9))

        return {
            "peak_dbfs": round(self.db(peak), 2),
            "rms_dbfs": round(self.db(rms), 2),
            "lufs_proxy": round(self.db(rms) - 1.5, 2),
            "crest_factor": round(crest, 2),
            "clipping_ratio": round(clipping, 5),
            "energy": round(energy, 3),
            "dynamic_range_score": round(dynamic_range_score, 3),
            "headroom_db": round(max(0, -self.db(peak)), 2),
        }

    def stereo_profile(self, stereo):

        left = stereo[0]
        right = stereo[1]
        mid = (left + right) * 0.5
        side = (left - right) * 0.5
        mid_power = float(np.mean(np.square(mid)) or 1e-9)
        side_power = float(np.mean(np.square(side)) or 0)
        width = max(0, min(1, side_power / mid_power))

        try:
            corr = float(np.corrcoef(left, right)[0, 1])
        except Exception:
            corr = 1.0

        if np.isnan(corr):
            corr = 1.0

        return {
            "width": round(width, 3),
            "correlation": round(max(-1, min(1, corr)), 3),
            "mono_risk": "HIGH" if corr < 0.25 or width > 0.8 else "LOW",
        }

    def transient_profile(self, mono, sr):

        onset = librosa.onset.onset_strength(y=mono, sr=sr)
        punch = float(np.std(onset) / max(np.mean(onset), 1e-9))
        tempo, _beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr)
        tempo = float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else 0

        return {
            "tempo": round(tempo, 2),
            "punch": round(max(0, min(1, punch / 3)), 3),
            "groove_confidence": round(max(0, min(1, float(np.mean(onset)) / 3)), 3),
        }

    def repair_plan(self, spectrum, dynamics, stereo, transient):

        plan = []

        if dynamics["clipping_ratio"] > 0.001:
            plan.append("Clip restore/declip uygula; master limiter ile sorunu gizleme.")

        if dynamics["headroom_db"] < 1:
            plan.append("Gain staging: dosyayi once -6 dB civarina indir.")

        if spectrum["mud_risk"] > 0.45:
            plan.append("180-450 Hz low-mid camurunu dinamik EQ ile temizle.")

        if spectrum["harshness"] > 0.42:
            plan.append("2.5-6 kHz sertlik ve 8-12 kHz yapay parlakligi dinamik kontrol et.")

        if transient["punch"] < 0.22:
            plan.append("Kick transient yenile: parallel transient shaper + soft clipper.")

        if stereo["mono_risk"] == "HIGH":
            plan.append("120 Hz altini mono yap, side low-end temizle, correlation kontrol et.")

        if not plan:
            plan.append("Temel master yeterli; sadece referans A/B ve kontrollu limiter uygula.")

        return plan

    def recreation_dna(self, spectrum, dynamics, stereo, transient):

        bands = spectrum["bands"]

        return {
            "tempo": transient["tempo"],
            "drum_instruction": "Kick punch zayifsa yeni kick layer veya transient layer ekle.",
            "bass_instruction": (
                "Sub kontrollu" if bands["sub"] < 0.22
                else "Sub fazla; bass'i yeniden dengele"
            ),
            "texture_instruction": (
                "Parlak/sert texture azalt"
                if spectrum["harshness"] > 0.42
                else "Air band kontrollu, texture korunabilir"
            ),
            "arrangement_instruction": "16 bar DJ intro, 32 bar build, net drop, temiz outro uret.",
            "stem_priority": ["drums", "bass", "vocal", "music"],
        }

    def master_chain(self, doctor_report):

        return doctor_report.get("mastering_chain", [])

    def studio_verdict(self, spectrum, dynamics, stereo, transient):

        bands = spectrum.get("bands", {})
        score = 100
        actions = []

        if dynamics.get("clipping_ratio", 0) > 0.001:
            score -= 18
            actions.append("True-peak limiter oncesi clip repair ve gain staging uygula.")

        if dynamics.get("crest_factor", 0) < 7:
            score -= 12
            actions.append("Transient alanini geri kazan; limiter input'u 1-2 dB azalt.")

        if bands.get("sub", 0) > 0.34:
            score -= 10
            actions.append("30-55 Hz sub bolgesini dinamik EQ ile kontrol et.")

        if spectrum.get("mud_risk", 0) > 0.42:
            score -= 10
            actions.append("180-350 Hz mud temizligi; kick/bass maskesini azalt.")

        if spectrum.get("harshness", 0) > 0.42:
            score -= 10
            actions.append("2.5-6 kHz harshness icin dynamic de-esser veya multiband uygula.")

        if stereo.get("mono_risk") == "HIGH":
            score -= 12
            actions.append("120 Hz altini mono sabitle; side low-end temizle.")

        if transient.get("punch", 0) < 0.32:
            score -= 8
            actions.append("Kick/snare transient layer veya parallel compression ekle.")

        if not actions:
            actions.append("Master dengeli; referans A/B ve final limiter kontrolu yeterli.")

        score = max(0, min(100, int(score)))

        if score >= 88:
            grade = "RELEASE_READY"
        elif score >= 72:
            grade = "CLUB_READY_WITH_REPAIR"
        elif score >= 55:
            grade = "MIX_REPAIR_REQUIRED"
        else:
            grade = "REBUILD_MIX"

        return {
            "score": score,
            "grade": grade,
            "producer_actions": actions,
            "reference_targets": {
                "club_peak": "-1.0 dBTP",
                "club_lufs": "-8.5 LUFS",
                "streaming_lufs": "-14 LUFS",
                "sub_mono": "120 Hz alti mono",
                "pre_master_headroom": "-6 dB",
            },
        }

    def render_targets(self, track):

        role = str(track.get("role") or "").upper()
        return {
            "format": "WAV 24-bit",
            "true_peak": "-1.0 dBTP",
            "lufs": "-8/-7 LUFS" if role == "PEAK TIME" else "-10/-8.5 LUFS",
            "headroom_before_master": "-6 dB",
            "mono_low_end": "120 Hz alti mono",
        }

    def fallback(self, path, reason, hint=None):

        return {
            "ok": False,
            "path": path,
            "reason": reason,
            "repair_plan": [
                hint or "Ses dosyasi analiz edilemedi; librosa/numpy kurulumunu veya dosya yolunu kontrol et."
            ],
        }

    def db(self, value):

        if value <= 0:
            return -120.0

        return 20 * float(np.log10(value))

    def db_plain(self, value):

        if value <= 0:
            return -120.0

        return 20 * math.log10(value)
