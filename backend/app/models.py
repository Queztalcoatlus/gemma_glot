from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    analyses: Mapped[list["AnalysisRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="tokens")


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    input_type: Mapped[str] = mapped_column(String(12), nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    ipa_transcript: Mapped[str | None] = mapped_column(Text)
    english_translation: Mapped[str] = mapped_column(Text, nullable=False)
    syntax_json: Mapped[str] = mapped_column(Text, nullable=False)
    vocabulary_json: Mapped[str] = mapped_column(Text, nullable=False)
    notes_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="analyses")


class VocabularyTerm(Base):
    __tablename__ = "vocabulary_terms"
    __table_args__ = (UniqueConstraint("user_id", "language", "lemma", name="uq_vocabulary_term_user_language_lemma"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False)
    lemma: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    display_term: Mapped[str] = mapped_column(String(255), nullable=False)
    part_of_speech: Mapped[str] = mapped_column(String(16), default="other", nullable=False)
    gender: Mapped[str] = mapped_column(String(8), default="n/a", nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class VocabularySave(Base):
    __tablename__ = "vocabulary_saves"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "analysis_id",
            "vocabulary_term_id",
            "surface_form",
            name="uq_vocabulary_save_user_analysis_term_surface",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analysis_records.id"), index=True, nullable=False)
    vocabulary_term_id: Mapped[int] = mapped_column(ForeignKey("vocabulary_terms.id"), index=True, nullable=False)
    surface_form: Mapped[str] = mapped_column(String(255), nullable=False)
    sentence_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
