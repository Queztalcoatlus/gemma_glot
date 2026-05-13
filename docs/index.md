# GemmaGlot: Multimodal Spanish Practice With Gemma 4

GemmaGlot is a language-learning demo built for the Gemma 4 Good Hackathon. It helps Spanish learners turn short text or speech samples into structured feedback: an orthographic transcript, IPA pronunciation, grammar observations, vocabulary terms, and a review history they can come back to later.

The project is aimed at a practical education problem: learners often need feedback while practicing alone, but most tools either focus only on translation or require a teacher, a paid subscription, or a polished classroom environment. GemmaGlot is designed to be lightweight enough for a public demo while still showing how an open multimodal model can power a useful learning workflow.

## What GemmaGlot Does

GemmaGlot accepts either typed Spanish or a short audio recording. For each submission, it returns:

- A normalized Spanish transcript.
- An IPA transcription.
- A concise grammar explanation.
- Learner-focused vocabulary with lemmas, part of speech, gender when relevant, and example context.
- Notes for uncertainty or limitations.
- Saved history and vocabulary review for the current user session.

The public demo includes a "Continue as demo" flow so judges can try the app without creating an account. Behind the scenes, each demo session gets an isolated temporary user record, which keeps the history feature usable without requiring a login or exposing another user's data.

## Why This Fits Gemma 4 Good

The hackathon asks builders to use Gemma 4 for applications with real-world benefit. GemmaGlot focuses on education and access: it gives language learners a private, repeatable way to practice pronunciation and grammar with immediate feedback.

This matters because language learning is often unevenly distributed. People with access to tutors, immersion programs, or formal classes get correction. People studying independently often get flashcards and translation, but not much analysis of what they actually said or wrote. GemmaGlot tries to fill that gap with a small, focused workflow:

1. Speak or type something in Spanish.
2. Get structured feedback immediately.
3. Save useful terms into a reviewable history.
4. Repeat with short, low-pressure practice.

The initial version supports Spanish only, but the backend data model is intentionally language-aware. Analysis records and vocabulary terms store a language field, so future languages can be added without redesigning the persistence layer.

## How Gemma 4 Is Used

Gemma 4 is the reasoning layer that turns language input into structured learning output. The app prompts the model to respond as JSON with a stable schema containing transcript, IPA, grammar feedback, vocabulary, and notes.

There are two inference paths:

- **Self-hosted Gemma 4 with vLLM:** The target native-audio path uses Gemma 4 E4B behind vLLM's OpenAI-compatible API. This path lets the app send audio directly to a Gemma 4 model that supports audio input.
- **Google-hosted Gemma API fallback:** The public app can also use a Google-hosted Gemma model for availability. Because the Google API path does not provide the same native audio input behavior, audio is first transcribed with Google Cloud Speech-to-Text, then Gemma analyzes the transcript. In that mode, IPA is inferred from text rather than directly from the audio signal.

This split keeps the app usable while GPU deployment is being finalized, but preserves the architecture needed for full Gemma 4 multimodal audio analysis.

## User Experience

The interface is deliberately simple. A learner signs in or starts a demo session, chooses text or audio mode, submits a short Spanish sample, and receives feedback in the same workspace.

The app avoids turning the experience into a chatbot because the goal is not open-ended conversation. The goal is repeatable analysis. Each result has the same structure, which makes it easier for learners to compare attempts over time and review vocabulary later.

The audio UI also labels the IPA source clearly:

- "IPA from audio" when the model analyzes audio directly.
- "IPA from text" when audio was transcribed first and pronunciation was inferred from the transcript.

That distinction is important because transcript-based IPA cannot preserve every speaker-specific dialect feature.

## Architecture

GemmaGlot is a small full-stack app:

- **Frontend:** Static single-page app served by FastAPI.
- **Backend:** FastAPI API for auth, text analysis, audio analysis, history, and vocabulary.
- **Database:** SQLAlchemy models with SQLite for the demo deployment, with a path to Cloud SQL for durable production history.
- **Inference providers:** Google GenAI or vLLM, selected by environment variables.
- **Speech fallback:** Google Cloud Speech-to-Text is automatically used for audio when the Google provider is selected.
- **Deployment:** Google Cloud Run for the app container; a separate Cloud Run GPU or GPU VM path for vLLM-hosted Gemma 4.

The app service and the model service are intentionally separate. That makes it possible to keep the public web app small and cheap while scaling GPU inference independently.

## Data Model

The app stores analysis and vocabulary as structured records rather than raw free-form text. That gives the project a clear path toward more learning features later:

- Review queues by language.
- Vocabulary search and filtering.
- Per-learner history.
- Multi-language expansion.
- Better progress tracking.

Even though the current product only enables Spanish, the stored analysis schema is not hard-coded to Spanish. The runtime inference gate is Spanish-only for now because the prompts and evaluation expectations are Spanish-specific, but the data shape can support more languages.

## Engineering Decisions

### Structured JSON output

The model is asked for a strict JSON response. This keeps the frontend predictable and makes it possible to save useful vocabulary and grammar data instead of rendering a one-off paragraph.

### Provider abstraction

The backend can switch between Google-hosted Gemma and a vLLM-hosted Gemma model through configuration. This keeps development and judging practical while preserving a self-hosted open-model path.

### Public demo without passwords

The demo endpoint creates isolated temporary accounts. Judges can experience history and saved vocabulary without needing a login, and without all public users sharing one global dummy account.

### Clear audio limitations

The app distinguishes between direct audio analysis and transcript-based IPA. That prevents the UI from overstating what the system actually heard.

## Current Limitations

GemmaGlot is still a hackathon prototype. The main limitations are:

- Spanish is the only enabled language.
- SQLite is acceptable for a short demo, but Cloud SQL would be better for durable production history.
- The Google provider audio path depends on ASR, so IPA may lose speaker-specific pronunciation details.
- Self-hosted Gemma 4 audio inference depends on GPU availability and the final vLLM deployment.
- The app is designed for short learning samples, not long lectures or full tutoring sessions.

## Future Work

The next versions could add:

- Full self-hosted Gemma 4 E4B audio deployment for the public demo.
- More languages using the existing language-aware data structure.
- Learner level selection, such as beginner, intermediate, and advanced feedback.
- Spaced repetition for saved vocabulary.
- Pronunciation contrast exercises.
- Cloud SQL-backed persistent history.
- Optional teacher/classroom views for shared review.

## Why I Built It This Way

The main design goal was to make Gemma 4 useful inside a real learning loop, not just to show that the model can answer questions. A learner gives the app language. GemmaGlot turns it into feedback. The learner can save and revisit that feedback. That loop is small, but it is real.

Gemma 4 is a good fit because the model family is built for efficient, multilingual, multimodal use. The official Gemma 4 materials describe support for audio and visual understanding, long-context reasoning, and more than 140 languages, while also emphasizing open deployment options. Those properties map directly to the kind of accessible language-learning assistant GemmaGlot is trying to become.

## References

- Ian Ballantyne, Glenn Cameron, María Cruz, Olivier Lacombe, Kristen Quan, and Omar Sanseviero. The Gemma 4 Good Hackathon. https://kaggle.com/competitions/gemma-4-good-hackathon, 2026. Kaggle.
- Google DeepMind Gemma 4 model page: https://deepmind.google/models/gemma/gemma-4/
- Google Gemma 4 announcement: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
