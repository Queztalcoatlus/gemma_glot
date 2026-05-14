# GemmaGlot: Multimodal Language Analysis With Gemma 4

GemmaGlot is a language-learning project built for the Kaggle Gemma 4 Good Hackathon. It helps learners analyze short pieces of language they encounter while studying: a sentence from a video, a phrase from a book, a message, or a short audio clip.

The app is not a chatbot and it is not mainly a correction tool. Its purpose is to turn encountered language into structured learning material: transcript, IPA, grammar observations, vocabulary, notes, and review history. Spanish is the first implemented language, but the data model and API are designed so additional languages can be added later.

## Learning Use Case

Independent learners often move between disconnected tools: translation apps, dictionaries, grammar references, pronunciation websites, and flashcards. GemmaGlot brings those steps into one workflow for short, high-value examples.

1. Capture or paste a short language sample.
2. Receive structured linguistic analysis.
3. Save useful vocabulary and examples.
4. Build a personal review trail from authentic material.

This fits the Gemma 4 Good theme through education and access. The project gives learners a private, repeatable way to understand language from study, media, travel, and conversation, especially when they do not have a class or study group nearby.

## Core Workflow

GemmaGlot accepts typed text or short audio clips. Each analysis can include:

- A normalized transcript.
- IPA pronunciation.
- Concise grammar observations.
- Vocabulary with lemmas, part of speech, grammatical gender when relevant, and contextual definitions.
- Notes about uncertainty or transcription limits.
- Saved history and vocabulary review.

The interface keeps this workflow intentionally narrow. Learners submit one language item, review one structured result, and optionally save vocabulary for later.

## Gemma 4 Integration

Gemma 4 is the reasoning layer that transforms text or audio into structured learning output. The backend prompts the model to return strict JSON rather than free-form prose, which keeps frontend rendering predictable and allows analysis data to be stored for review.

The intended model path is self-hosted Gemma 4 E4B through vLLM's OpenAI-compatible API. In that setup, audio can be sent directly to a multimodal Gemma model for transcription, IPA, grammar analysis, and vocabulary extraction.

The backend also includes a provider abstraction, so the app can switch between self-hosted vLLM and managed Gemma APIs through configuration without changing the product flow.

## Architecture

The implementation is a lightweight full-stack application:

- **Frontend:** static single-page app served by FastAPI.
- **Backend:** FastAPI routes for authentication, text analysis, audio analysis, history, and vocabulary.
- **Database:** SQLAlchemy models for users, analysis records, and saved vocabulary.
- **Inference:** configurable provider layer for vLLM or managed Gemma APIs.
- **Deployment:** app container separated from model inference service.

That separation keeps the web app simple while allowing GPU inference to scale independently.

## Public Demo Setup

The public hackathon deployment uses a practical setup so judges can try the project immediately:

- **Access:** a demo session flow creates isolated temporary user records, so history and vocabulary review work without signup.
- **Hosting:** the FastAPI app and frontend run on Google Cloud Run.
- **Inference:** the demo can use a managed Gemma API for text analysis.
- **Audio fallback:** when using the managed API path, audio is first transcribed with Google Cloud Speech-to-Text, then Gemma analyzes the transcript. In this mode, IPA is inferred from text rather than directly from the original audio signal.
- **Storage:** the short-lived demo can use SQLite in the app container; a production deployment would use external storage such as Cloud SQL.
- **Native audio path:** the intended full setup uses a dedicated vLLM service running Gemma 4 E4B on GPU infrastructure.

## Data and Extensibility

Analysis results and vocabulary are stored as structured records rather than one-off generated text. The schema tracks language, source text or transcript, IPA, translation, syntax observations, vocabulary, notes, and saved vocabulary occurrences.

This makes future features straightforward:

- Additional languages.
- Vocabulary filtering and search.
- Review queues by language.
- Learner-level explanation settings.
- Progress tracking over saved examples.

## Limitations

This is still an early-stage hackathon prototype:

- Spanish is the first implemented language.
- Native Gemma 4 audio inference depends on GPU availability and vLLM deployment.
- The app is optimized for short language samples, not lecture-scale transcription.

## Next Steps

Planned improvements include adding more languages, completing the self-hosted Gemma 4 E4B audio deployment, expanding vocabulary review, and moving demo storage to a durable database.

## References

- Ian Ballantyne, Glenn Cameron, María Cruz, Olivier Lacombe, Kristen Quan, and Omar Sanseviero. The Gemma 4 Good Hackathon. https://kaggle.com/competitions/gemma-4-good-hackathon, 2026. Kaggle.
- Google DeepMind Gemma 4 model page: https://deepmind.google/models/gemma/gemma-4/
- Google Gemma 4 announcement: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
