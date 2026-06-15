from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlayerSettings(BaseModel):
    stem_gain_default_db: int = Field(alias="stemGainDefaultDb", ge=-60, le=12)
    stem_gain_min_db: int = Field(alias="stemGainMinDb", ge=-60, le=12)
    stem_gain_max_db: int = Field(alias="stemGainMaxDb", ge=-60, le=12)
    stem_gain_step_db: int = Field(alias="stemGainStepDb", ge=1, le=12)
    focus_gain_default_db: int = Field(alias="focusGainDefaultDb", ge=-60, le=12)
    focus_gain_min_db: int = Field(alias="focusGainMinDb", ge=-60, le=12)
    focus_gain_max_db: int = Field(alias="focusGainMaxDb", ge=-60, le=12)
    background_gain_default_db: int = Field(alias="backgroundGainDefaultDb", ge=-60, le=12)
    background_gain_min_db: int = Field(alias="backgroundGainMinDb", ge=-60, le=12)
    background_gain_max_db: int = Field(alias="backgroundGainMaxDb", ge=-60, le=12)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="after")
    def validate_ranges(self) -> "PlayerSettings":
        ranges = (
            ("stem gain", self.stem_gain_min_db, self.stem_gain_default_db, self.stem_gain_max_db),
            ("focus gain", self.focus_gain_min_db, self.focus_gain_default_db, self.focus_gain_max_db),
            (
                "background gain",
                self.background_gain_min_db,
                self.background_gain_default_db,
                self.background_gain_max_db,
            ),
        )
        for name, minimum, default, maximum in ranges:
            if not minimum <= default <= maximum:
                raise ValueError(f"{name} must satisfy minimum <= default <= maximum")
        return self


class AppSettingsRead(PlayerSettings):
    mono_bitrate_kbps: int = Field(alias="monoBitrateKbps", ge=32, le=512)
    stereo_bitrate_kbps: int = Field(alias="stereoBitrateKbps", ge=32, le=512)
    target_sample_rate: int = Field(alias="targetSampleRate")
    duration_tolerance_ms: int = Field(alias="durationToleranceMs", ge=0, le=10000)

    @model_validator(mode="after")
    def validate_conversion(self) -> "AppSettingsRead":
        if self.target_sample_rate not in (44100, 48000):
            raise ValueError("targetSampleRate must be 44100 or 48000")
        return self


class AppSettingsUpdate(AppSettingsRead):
    pass
