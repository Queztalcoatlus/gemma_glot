import json
from collections import defaultdict

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.models import AnalysisRecord, User, VocabularyOccurrence
from backend.app.schemas import (
    AnalysisResponse,
    AudioAnalysisResponse,
    ReviewHistoryItem,
    ReviewVocabularyEntry,
    ReviewVocabularyOccurrence,
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
    db.flush()

    for item in analysis.vocabulary:
        db.add(
            VocabularyOccurrence(
                user_id=user.id,
                analysis_id=record.id,
                term=item.term,
                definition=item.definition,
                level=item.level,
                sentence_text=source_text,
            )
        )

    db.commit()
    db.refresh(record)
    return record


def list_history(db: Session, user: User) -> list[ReviewHistoryItem]:
    records = db.scalars(
        select(AnalysisRecord).where(AnalysisRecord.user_id == user.id).order_by(desc(AnalysisRecord.created_at))
    ).all()
    return [history_item(record) for record in records]


def get_analysis(db: Session, user: User, analysis_id: int) -> AnalysisResponse | None:
    record = db.scalar(
        select(AnalysisRecord).where(AnalysisRecord.id == analysis_id, AnalysisRecord.user_id == user.id)
    )
    if record is None:
        return None
    return analysis_response(record)


def list_vocabulary(db: Session, user: User) -> list[ReviewVocabularyEntry]:
    occurrences = db.scalars(
        select(VocabularyOccurrence)
        .where(VocabularyOccurrence.user_id == user.id)
        .order_by(VocabularyOccurrence.term, desc(VocabularyOccurrence.created_at))
    ).all()
    grouped: dict[str, list[VocabularyOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[occurrence.term.lower()].append(occurrence)

    entries = []
    for group in grouped.values():
        first = group[0]
        entries.append(
            ReviewVocabularyEntry(
                term=first.term,
                definition=first.definition,
                level=first.level,
                occurrences=[
                    ReviewVocabularyOccurrence(
                        analysis_id=item.analysis_id,
                        sentence_text=item.sentence_text,
                        created_at=item.created_at,
                    )
                    for item in group
                ],
            )
        )

    return sorted(entries, key=lambda item: item.term.lower())


def history_item(record: AnalysisRecord) -> ReviewHistoryItem:
    return ReviewHistoryItem(
        id=record.id,
        input_type=record.input_type,
        language=record.language,
        text_preview=_preview(record.source_text),
        english_translation=record.english_translation,
        created_at=record.created_at,
        vocabulary_count=len(_json_list(record.vocabulary_json)),
    )


def analysis_response(record: AnalysisRecord) -> AnalysisResponse:
    payload = {
        "input_type": record.input_type,
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


def _preview(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= 120:
        return collapsed
    return f"{collapsed[:117]}..."


def _json_list(raw: str) -> list:
    parsed = json.loads(raw or "[]")
    return parsed if isinstance(parsed, list) else []
