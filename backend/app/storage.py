import json

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.models import AnalysisRecord, User, VocabularySave, VocabularyTerm
from backend.app.schemas import (
    AnalysisResponse,
    AudioAnalysisResponse,
    ReviewHistoryItem,
    ReviewVocabularyEntry,
    ReviewVocabularyOccurrence,
    SaveVocabularyRequest,
    TextAnalysisResponse,
)


def save_analysis(db: Session, user: User, analysis: AnalysisResponse) -> AnalysisRecord:
    source_text = _source_text(analysis)
    record = AnalysisRecord(
        user_id=user.id,
        input_type=analysis.input_type,
        language=analysis.language,
        source_text=source_text,
        ipa_transcript=getattr(analysis, "ipa_transcript", None),
        english_translation=analysis.english_translation,
        syntax_json=json.dumps([item.model_dump() for item in analysis.syntax_analysis]),
        vocabulary_json=json.dumps([item.model_dump() for item in analysis.vocabulary]),
        notes_json=json.dumps(analysis.notes),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    analysis.analysis_id = record.id
    return record


def list_history(db: Session, user: User) -> list[ReviewHistoryItem]:
    records = db.scalars(
        select(AnalysisRecord).where(AnalysisRecord.user_id == user.id).order_by(desc(AnalysisRecord.created_at))
    ).all()
    counts = dict(
        db.execute(
            select(VocabularySave.analysis_id, func.count(VocabularySave.id))
            .where(VocabularySave.user_id == user.id)
            .group_by(VocabularySave.analysis_id)
        ).all()
    )
    return [history_item(record, counts.get(record.id, 0)) for record in records]


def get_analysis(db: Session, user: User, analysis_id: int) -> AnalysisResponse | None:
    record = db.scalar(
        select(AnalysisRecord).where(AnalysisRecord.id == analysis_id, AnalysisRecord.user_id == user.id)
    )
    if record is None:
        return None
    return analysis_response(record)


def list_vocabulary(db: Session, user: User) -> list[ReviewVocabularyEntry]:
    rows = db.execute(
        select(VocabularyTerm, VocabularySave)
        .join(VocabularySave, VocabularySave.vocabulary_term_id == VocabularyTerm.id)
        .where(VocabularySave.user_id == user.id)
        .order_by(VocabularyTerm.lemma, desc(VocabularySave.created_at))
    ).all()

    grouped: dict[int, tuple[VocabularyTerm, list[VocabularySave]]] = {}
    for term, save in rows:
        grouped.setdefault(term.id, (term, []))[1].append(save)

    return [
        ReviewVocabularyEntry(
            term=term.display_term,
            lemma=term.lemma,
            part_of_speech=term.part_of_speech,
            gender=term.gender,
            definition=term.definition,
            level=term.level,
            occurrences=[
                ReviewVocabularyOccurrence(
                    analysis_id=save.analysis_id,
                    surface_form=save.surface_form,
                    sentence_text=save.sentence_text,
                    created_at=save.created_at,
                )
                for save in saves
            ],
        )
        for term, saves in sorted(grouped.values(), key=lambda item: item[0].lemma.lower())
    ]


def save_vocabulary_selection(db: Session, user: User, item: SaveVocabularyRequest) -> ReviewVocabularyEntry | None:
    analysis = db.scalar(
        select(AnalysisRecord).where(AnalysisRecord.id == item.analysis_id, AnalysisRecord.user_id == user.id)
    )
    if analysis is None:
        return None

    lemma = _canonical_lemma(item)
    term = db.scalar(
        select(VocabularyTerm).where(
            VocabularyTerm.user_id == user.id,
            VocabularyTerm.language == analysis.language,
            VocabularyTerm.lemma == lemma,
        )
    )
    if term is None:
        term = VocabularyTerm(
            user_id=user.id,
            language=analysis.language,
            lemma=lemma,
            display_term=lemma,
            part_of_speech=item.part_of_speech,
            gender=item.gender,
            definition=item.definition,
            level=item.level,
        )
        db.add(term)
        db.flush()
    else:
        term.definition = item.definition
        term.level = item.level
        term.part_of_speech = item.part_of_speech
        term.gender = item.gender

    existing = db.scalar(
        select(VocabularySave).where(
            VocabularySave.user_id == user.id,
            VocabularySave.analysis_id == analysis.id,
            VocabularySave.vocabulary_term_id == term.id,
            VocabularySave.surface_form == item.term,
        )
    )
    if existing is None:
        db.add(
            VocabularySave(
                user_id=user.id,
                analysis_id=analysis.id,
                vocabulary_term_id=term.id,
                surface_form=item.term,
                sentence_text=analysis.source_text,
            )
        )
    db.commit()
    return _term_entry(db, user, term.id)


def history_item(record: AnalysisRecord, vocabulary_count: int = 0) -> ReviewHistoryItem:
    return ReviewHistoryItem(
        id=record.id,
        input_type=record.input_type,
        language=record.language,
        text_preview=_preview(record.source_text),
        english_translation=record.english_translation,
        created_at=record.created_at,
        vocabulary_count=vocabulary_count,
    )


def analysis_response(record: AnalysisRecord) -> AnalysisResponse:
    payload = {
        "input_type": record.input_type,
        "analysis_id": record.id,
        "language": record.language,
        "english_translation": record.english_translation,
        "syntax_analysis": _json_list(record.syntax_json),
        "vocabulary": _json_list(record.vocabulary_json),
        "notes": _json_list(record.notes_json),
    }
    if record.input_type == "audio":
        payload["orthographic_transcript"] = record.source_text
        payload["ipa_transcript"] = record.ipa_transcript or ""
    else:
        payload["source_text"] = record.source_text
    if record.input_type == "text":
        return TextAnalysisResponse.model_validate(payload)
    return AudioAnalysisResponse.model_validate(payload)


def _source_text(analysis: AnalysisResponse) -> str:
    if analysis.input_type == "audio":
        return analysis.orthographic_transcript
    return analysis.source_text


def _canonical_lemma(item: SaveVocabularyRequest) -> str:
    return " ".join((item.lemma or item.term).strip().lower().split())


def _term_entry(db: Session, user: User, term_id: int) -> ReviewVocabularyEntry:
    rows = db.execute(
        select(VocabularyTerm, VocabularySave)
        .join(VocabularySave, VocabularySave.vocabulary_term_id == VocabularyTerm.id)
        .where(VocabularyTerm.id == term_id, VocabularySave.user_id == user.id)
        .order_by(desc(VocabularySave.created_at))
    ).all()
    term = rows[0][0]
    return ReviewVocabularyEntry(
        term=term.display_term,
        lemma=term.lemma,
        part_of_speech=term.part_of_speech,
        gender=term.gender,
        definition=term.definition,
        level=term.level,
        occurrences=[
            ReviewVocabularyOccurrence(
                analysis_id=save.analysis_id,
                surface_form=save.surface_form,
                sentence_text=save.sentence_text,
                created_at=save.created_at,
            )
            for _, save in rows
        ],
    )


def _preview(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= 120:
        return collapsed
    return f"{collapsed[:117]}..."


def _json_list(raw: str) -> list:
    parsed = json.loads(raw or "[]")
    return parsed if isinstance(parsed, list) else []
