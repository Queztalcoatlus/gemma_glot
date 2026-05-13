# GemmaGlot: Multimodal Language Analysis With Gemma 4

GemmaGlot is a language-learning project built for the Gemma 4 Good Hackathon. It helps learners analyze short pieces of language they encounter while studying: text snippets, phrases, examples, or audio clips. For each item, GemmaGlot turns the input into structured analysis with an orthographic transcript, IPA pronunciation, grammar observations, vocabulary terms, and a review history the learner can come back to later. Spanish is the first implemented example language, but the system is designed so more languages can be added.

The project is aimed at a practical education problem: learners constantly run into unfamiliar language outside formal lessons, but most tools either provide a simple translation or require them to search separately for grammar, pronunciation, and vocabulary context. GemmaGlot is designed to be lightweight while still showing how an open multimodal model can power a useful learning workflow.

## What GemmaGlot Does

GemmaGlot accepts either typed language input or a short audio clip. In the current implementation, Spanish is the enabled example language. For each submission, it returns:

- A normalized transcript.
- An IPA transcription.
- A concise grammar explanation.
- Learner-focused vocabulary with lemmas, part of speech, gender when relevant, and example context.
- Notes for uncertainty or limitations.
- Saved history and vocabulary review for the current user session.

## Why This Fits Gemma 4 Good

The hackathon asks builders to use Gemma 4 for applications with real-world benefit. GemmaGlot focuses on education and access: it gives language learners a private, repeatable way to understand language they encounter during study, media consumption, conversation, or independent reading.

This matters because language learning is often unevenly distributed. People with access to classes, immersion programs, or study groups can ask why a phrase works the way it does. People studying independently often get flashcards and translation, but not much structured explanation of the language they actually encounter. GemmaGlot tries to fill that gap with a small, focused workflow:

1. Capture or paste a short piece of language.
2. Get structured analysis immediately.
3. Save useful terms into a reviewable history.
4. Build a personal trail of examples from real learning material.

The initial version uses Spanish as the first example language, but the backend data model is intentionally language-aware. Analysis records and vocabulary terms store a language field, so future languages can be added without redesigning the persistence layer.

## How Gemma 4 Is Used

Gemma 4 is the reasoning layer that turns encountered language into structured learning output. The app prompts the model to respond as JSON with a stable schema containing transcript, IPA, grammar analysis, vocabulary, and notes.

The intended Gemma 4 path is self-hosted inference with vLLM:

- **Self-hosted Gemma 4 with vLLM:** The native-audio path uses Gemma 4 E4B behind vLLM's OpenAI-compatible API. This path lets the app send audio directly to a Gemma 4 model that supports audio input.

The backend also has a provider abstraction so deployment can switch between a self-hosted Gemma model and an externally hosted Gemma API. The public hackathon setup is described separately below so the core product design is not tied to one temporary hosting configuration.

## User Experience

The interface is deliberately simple. A learner opens a session, chooses text or audio mode, submits a short item in the enabled language, and receives analysis in the same workspace.

The app avoids turning the experience into a chatbot because the goal is not open-ended conversation. The goal is repeatable analysis of language artifacts learners want to understand. Each result has the same structure, which makes it easier to compare examples over time and review vocabulary later.

The audio UI also labels the IPA source clearly:

- "IPA from audio" when the model analyzes audio directly.
- "IPA from text" when audio was transcribed first and pronunciation was inferred from the transcript.

That distinction is important because transcript-based IPA cannot preserve every speaker-specific dialect feature.

## Architecture

GemmaGlot is a small full-stack app:

- **Frontend:** Static single-page app served by FastAPI.
- **Backend:** FastAPI API for auth, text analysis, audio analysis, history, and vocabulary.
- **Database:** SQLAlchemy models for users, analysis history, and saved vocabulary.
- **Inference providers:** Google GenAI or vLLM, selected by environment variables.
- **Deployment:** One web app container plus a separately scalable model service for self-hosted Gemma 4.

The app service and the model service are intentionally separate. That makes it possible to keep the public web app small and cheap while scaling GPU inference independently.

## Demo Setup

The public hackathon demo uses a practical hosting setup so judges can try the project without creating accounts or waiting for a dedicated GPU model service to be available.

- **Access:** The deployed app includes a "Continue as demo" flow. Each session gets an isolated temporary user record, so history and vocabulary review work without requiring a signup.
- **App hosting:** The FastAPI app and static frontend are deployed on Google Cloud Run.
- **Inference:** The demo can use a Google-hosted Gemma model for text analysis.
- **Audio fallback:** In the Google-hosted path, audio is transcribed with Google Cloud Speech-to-Text before Gemma analyzes the transcript. In this mode, IPA is inferred from text rather than directly from the original audio signal.
- **Data storage:** The short-lived demo deployment can use SQLite inside the app container. A production deployment should use an external database such as Cloud SQL for durable history.
- **Model hosting path:** The intended native-audio setup is still a separate vLLM service running Gemma 4 E4B, either on Cloud Run GPU or a GPU VM.

## Data Model

The app stores analysis and vocabulary as structured records rather than raw free-form text. That gives the project a clear path toward more learning features later:

- Review queues by language.
- Vocabulary search and filtering.
- Per-learner history.
- Multi-language expansion.
- Better progress tracking.

Even though the current product enables Spanish as the first example, the stored analysis schema is not hard-coded to any one language. The runtime currently gates requests to the implemented example because the prompts and tests need to be expanded language by language, but the data shape can support more languages.

## Engineering Decisions

### Structured JSON output

The model is asked for a strict JSON response. This keeps the frontend predictable and makes it possible to save useful vocabulary and grammar data instead of rendering a one-off paragraph.

### Provider abstraction

The backend can switch between a managed Gemma API and a vLLM-hosted Gemma model through configuration. This keeps deployment flexible while preserving a self-hosted open-model path.

### Clear audio limitations

The app distinguishes between direct audio analysis and transcript-based IPA. That prevents the UI from overstating what the system actually heard.

## Current Limitations

GemmaGlot is still a hackathon prototype. The main limitations are:

- Spanish is the first enabled example language; additional languages can be added by extending prompts, UI options, and tests.
- Self-hosted Gemma 4 audio inference depends on GPU availability and the final vLLM deployment.
- The app is designed for short encountered language samples, not long lectures or full tutoring sessions.

## Future Work

The next versions could add:

- Full self-hosted Gemma 4 E4B audio deployment.
- More languages using the existing language-aware data structure.
- Learner level selection, such as beginner, intermediate, and advanced explanations.
- Spaced repetition for saved vocabulary.
- Pronunciation contrast exercises.
- Cloud SQL-backed persistent history.
- Optional teacher/classroom views for shared review.

## Why I Built It This Way

The main design goal was to make Gemma 4 useful inside a real learning loop, not just to show that the model can answer questions. A learner encounters language, brings it into GemmaGlot, and gets an analysis they can save and revisit. That loop is small, but it is real.

Gemma 4 is a good fit because the model family is built for efficient, multilingual, multimodal use. The official Gemma 4 materials describe support for audio and visual understanding, long-context reasoning, and more than 140 languages, while also emphasizing open deployment options. Those properties map directly to the kind of accessible language-learning assistant GemmaGlot is trying to become.

## References

- Ian Ballantyne, Glenn Cameron, María Cruz, Olivier Lacombe, Kristen Quan, and Omar Sanseviero. The Gemma 4 Good Hackathon. https://kaggle.com/competitions/gemma-4-good-hackathon, 2026. Kaggle.
- Google DeepMind Gemma 4 model page: https://deepmind.google/models/gemma/gemma-4/
- Google Gemma 4 announcement: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
