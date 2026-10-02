"""Provider fallback chain (Phase 8.2 P1) — log which provider served the turn."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderChoice:
    role: str  # llm | tts | stt
    primary: str
    backup: str
    active: str
    reason: str = "primary"


@dataclass
class FallbackChain:
    """Select backup when primary is marked failed via FAULTS / health."""

    llm_primary: str = "gemini-3.1-flash-lite"
    llm_backup: str = "gemini-2.5-flash-lite"
    tts_primary_voice: str = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"  # Jacqueline
    tts_backup_voice: str = "f786b574-daa5-4673-aa0c-cbe3e8534c02"  # Katie
    stt_primary: str = "flux-general-en"
    stt_backup: str = "nova-3"
    log: list[ProviderChoice] = field(default_factory=list)

    def choose_llm(self, *, primary_failed: bool) -> ProviderChoice:
        if primary_failed:
            choice = ProviderChoice("llm", self.llm_primary, self.llm_backup, self.llm_backup, "fallback")
        else:
            choice = ProviderChoice("llm", self.llm_primary, self.llm_backup, self.llm_primary, "primary")
        self.log.append(choice)
        return choice

    def choose_tts_voice(self, *, primary_failed: bool) -> ProviderChoice:
        if primary_failed:
            choice = ProviderChoice(
                "tts", self.tts_primary_voice, self.tts_backup_voice, self.tts_backup_voice, "fallback"
            )
        else:
            choice = ProviderChoice(
                "tts", self.tts_primary_voice, self.tts_backup_voice, self.tts_primary_voice, "primary"
            )
        self.log.append(choice)
        return choice

    def choose_stt(self, *, primary_failed: bool) -> ProviderChoice:
        if primary_failed:
            choice = ProviderChoice("stt", self.stt_primary, self.stt_backup, self.stt_backup, "fallback")
        else:
            choice = ProviderChoice("stt", self.stt_primary, self.stt_backup, self.stt_primary, "primary")
        self.log.append(choice)
        return choice
