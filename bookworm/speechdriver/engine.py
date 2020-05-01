# coding: utf-8

from abc import ABCMeta, abstractmethod
from dataclasses import field, dataclass
from bookworm.logger import logger
from .utterance import SpeechUtterance


log = logger.getChild(__name__)


@dataclass(order=True)
class VoiceInfo:
    id: str = field(compare=False)
    name: str = field(compare=False)
    desc: str = field(compare=False)
    language: str = field(compare=False)
    sort_key: int = 0
    gender: int = field(default=None, compare=False)
    age: int = field(default=None, compare=False)
    data: dict = field(default_factory=dict, compare=False)

    @property
    def display_name(self):
        return self.desc or self.name

    def speaks_language(self, language):
        language = language.lower()
        locale, _h, country_code = self.language.lower().partition("-")
        if self.language.lower() == language:
            self.sort_key = 0
            return True
        elif language == locale:
            self.sort_key = 1
            return True
        return False


class BaseSpeechEngine(metaclass=ABCMeta):
    """The base class for speech engines."""

    name = None
    """The name of this speech engine."""
    display_name = None

    def __init__(self):
        if not self.check():
            raise RuntimeError(f"Synthesizer {type(self)} is unavailable")

    @classmethod
    @abstractmethod
    def check(self):
        """Return a bool to indicate whether this engine should be made available."""

    @abstractmethod
    def close(self):
        """Performe any necessary cleanups."""

    def __del__(self):
        self.close()

    def configure(self, engine_config):
        if engine_config["voice"]:
            try:
                self.set_voice_from_string(engine_config["voice"])
            except ValueError:
                self.voice = self.get_first_available_voice()
        try:
            self.rate = engine_config["rate"]
        except ValueError:
            self.rate = 50
        try:
            self.volume = engine_config["volume"]
        except ValueError:
            self.volume = 75

    @abstractmethod
    def get_voices(self):
        """Return a list of VoiceInfo objects."""

    def get_voices_by_language(self, language):
        return sorted(
            voice for voice in self.get_voices() if voice.speaks_language(language)
        )

    @property
    @abstractmethod
    def state(self):
        """Return one of the members of synth state enumeration."""

    @property
    @abstractmethod
    def voice(self):
        """Return the currently configured voice."""

    @voice.setter
    @abstractmethod
    def voice(self, value):
        """Set the current voice."""

    @property
    @abstractmethod
    def rate(self):
        """Get the current speech rate."""

    @rate.setter
    @abstractmethod
    def rate(self, value):
        """Set the speech rate."""

    @property
    @abstractmethod
    def volume(self):
        """Get the current volume level."""

    @volume.setter
    @abstractmethod
    def volume(self, value):
        """Set the current volume level."""

    def speak(self, utterance):
        """Asynchronously speak the given text."""
        if not isinstance(utterance, SpeechUtterance):
            raise TypeError(f"Invalid utterance {utterance}")
        processed_utterance = self.preprocess_utterance(utterance)
        self.speak_utterance(processed_utterance)

    @abstractmethod
    def speak_utterance(self, utterance):
        """Do the actual speech output."""

    @abstractmethod
    def stop(self):
        """Stop the speech."""

    @abstractmethod
    def pause(self):
        """Pause the speech."""

    @abstractmethod
    def resume(self):
        """Resume the speech."""

    @abstractmethod
    def bind(self, event, handler):
        """Bind a member of `EngineEvents` enum to a handler."""

    def set_voice_from_string(self, voice_ident):
        for voice in self.get_voices():
            if voice.id == voice_ident:
                self.voice = voice
                return
        raise ValueError(f"Invalid voice {voice_ident}")

    @classmethod
    def get_first_available_voice(cls, language=None):
        _test_engine = cls()
        for voice in _test_engine.get_voices_by_language(language=language):
            try:
                _test_engine.set_voice_from_string(voice.id)
                return voice
            except ValueError:
                continue

    def preprocess_utterance(self, utterance):
        """Return engine-specific speech utterance (if necessary)."""
        return utterance
