from typing import Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["Spanish"]
Level = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class SyntaxFeature(BaseModel):
    feature: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class VocabularyItem(BaseModel):
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    level: Level


class AnalysisBase(BaseModel):
    language: LanguageCode
    english_translation: str
    syntax_analysis: list[SyntaxFeature]
    vocabulary: list[VocabularyItem]
    notes: list[str] = Field(default_factory=list)


class TextAnalysisResponse(AnalysisBase):
    input_type: Literal["text"] = "text"
    source_text: str


class AudioAnalysisResponse(AnalysisBase):
    input_type: Literal["audio"] = "audio"
    orthographic_transcript: str
    ipa_transcript: str


AnalysisResponse = TextAnalysisResponse | AudioAnalysisResponse
