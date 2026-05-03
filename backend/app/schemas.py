from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["Spanish"]
Level = Literal["A1", "A2", "B1", "B2", "C1", "C2", "N/A"]


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


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    token: str
    username: str


class UserResponse(BaseModel):
    username: str


class ReviewHistoryItem(BaseModel):
    id: int
    input_type: Literal["text", "audio"]
    language: str
    text_preview: str
    english_translation: str
    vocabulary_count: int
    created_at: datetime


class ReviewVocabularyOccurrence(BaseModel):
    analysis_id: int
    sentence_text: str
    created_at: datetime


class ReviewVocabularyEntry(BaseModel):
    term: str
    definition: str
    level: Level
    occurrences: list[ReviewVocabularyOccurrence]
