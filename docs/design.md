# GemmaGlot Design

## 1. Product Overview

GemmaGlot is a single-page language-learning web app for Spanish text and audio analysis. It helps learners turn short Spanish samples into structured feedback:

- normalized source text or orthographic transcript,
- IPA transcription for audio,
- English translation,
- learner-friendly syntax notes,
- vocabulary worth reviewing,
- saved history and vocabulary review.

The current product is not a real-time tutor. Users submit a bounded text or audio sample, receive one structured analysis response, and can review past analyses from their account.

The app is designed with a language-aware data model, but Spanish is the only enabled language in the current runtime. Requests for other languages are rejected by inference validation until prompts and evaluation behavior are expanded.

## 2. Current Scope

### Included

- Static single-page frontend served by FastAPI.
- Local account registration and login.
- Token-authenticated API requests.
- Spanish text analysis.
- Spanish audio analysis from browser recording or uploaded file.
- In-browser recording capped at 30 seconds.
- Audio upload validation and a 16 MB server-side file limit.
- Structured analysis responses with translation, syntax, vocabulary, and notes.
- IPA output for audio responses.
- Review history for saved analyses.
- Vocabulary save/review flow grouped by learner, language, and lemma.
- Google GenAI provider for text analysis.
- Google Cloud Speech-to-Text fallback for audio when `PROVIDER=google`.
- vLLM provider for OpenAI-compatible Gemma model hosting, including native audio input when the hosted model supports it.
- Docker and Google Cloud Run deployment paths for the app.
- Separate Cloud Run GPU or GPU VM path for vLLM model hosting.

### Deferred

- Additional target languages beyond Spanish.
- Fine-grained pronunciation scoring against a native target.
- Full dialect classification.
- Real-time streaming transcription or coaching.
- Durable production database setup as the default deployment.
- Teacher/classroom workflows.

## 3. Technical Architecture

### Frontend

- Location: `frontend/`
- Entry point: `frontend/index.html`
- App logic: `frontend/app.js`
- Styling: `frontend/styles.css`
- Runtime: browser-based React loaded from CDN.
- Served by FastAPI under `/` and `/static/*`.

The frontend supports authentication, text/audio analysis, browser recording, file upload, structured result display, history, and vocabulary review. The language selector currently exposes Spanish only.

### Backend

- Framework: FastAPI.
- App entry point: `backend/app/main.py`.
- Static serving: mounted `frontend/` directory.
- Persistence: SQLAlchemy models.
- Auth: username/password registration and login with bearer tokens.
- Inference abstraction: `backend/app/inference.py`.

Primary route groups:

- `GET /` serves the frontend.
- `GET /api/health` reports backend health.
- `POST /api/auth/register` creates a user.
- `POST /api/auth/login` issues an auth token.
- `GET /api/auth/me` returns the authenticated user.
- `POST /api/analyze/text` analyzes Spanish text.
- `POST /api/analyze/audio` analyzes Spanish audio.
- `GET /api/review/history` lists saved analyses.
- `GET /api/review/history/{analysis_id}` returns one saved analysis.
- `GET /api/review/vocabulary` lists saved vocabulary.
- `POST /api/review/vocabulary` saves a vocabulary item from an analysis.

## 4. Inference Providers

The backend chooses the inference provider from `PROVIDER`.

### Google Provider

Configuration:

- `PROVIDER=google`
- `GOOGLE_API_KEY`
- `MODEL`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `SPEECH_LANGUAGE_CODE`
- `SPEECH_MODEL`

Text flow:

1. Validate that the requested language is supported.
2. Send the Spanish text and JSON-output prompt to Google GenAI.
3. Parse the model response as JSON.
4. Validate it against the Pydantic response schema.
5. Save the analysis to the database.

Audio flow:

1. Validate that the requested language is supported.
2. Transcribe the audio with Google Cloud Speech-to-Text.
3. Send the transcript and JSON-output prompt to Google GenAI.
4. Infer IPA from the transcript rather than directly from the original audio signal.
5. Parse and validate the JSON response.
6. Replace the model's transcript field with the Speech-to-Text transcript.
7. Save the analysis to the database.

The Google audio path is a compatibility fallback. It is useful when native Gemma audio hosting is unavailable, but it cannot preserve all speaker-specific pronunciation details.

### vLLM Provider

Configuration:

- `PROVIDER=vllm`
- `MODEL`
- `VLLM_BASE_URL`
- `VLLM_API_KEY`
- `VLLM_TIMEOUT_SECONDS`

Text flow:

1. Validate that the requested language is supported.
2. Send a chat completion request to vLLM's OpenAI-compatible API.
3. Parse and validate the JSON response.
4. Save the analysis to the database.

Audio flow:

1. Validate that the requested language is supported.
2. Base64-encode the uploaded or recorded audio.
3. Send a multimodal chat completion request using `input_audio`.
4. Ask Gemma to produce orthographic transcript, IPA, translation, syntax, and vocabulary in one JSON response.
5. Parse and validate the response.
6. Save the analysis to the database.

The vLLM audio path is the intended native Gemma audio path. It requires the hosted model and vLLM build to support audio input through the OpenAI-compatible API.

### Development Mocking

If `PROVIDER=google` and no Google API key is configured, the backend returns deterministic mock analyses. This keeps frontend and API development usable without external inference credentials.

## 5. Data Model

The database is user-scoped and language-aware.

### Users

`users`: `id`, `username`, `password_hash`, `created_at`.

### Auth Tokens

`auth_tokens`: `id`, `token_hash`, `user_id`, `created_at`.

Tokens are stored as hashes. API clients receive the raw bearer token once at login.

### Analysis Records

`analysis_records`: `id`, `user_id`, `input_type`, `language`, `source_text`, `ipa_transcript`, `english_translation`, `syntax_json`, `vocabulary_json`, `notes_json`, `created_at`.

For text analyses, `source_text` is the submitted text. For audio analyses, `source_text` is the orthographic transcript.

### Vocabulary Terms

`vocabulary_terms`: `id`, `user_id`, `language`, `lemma`, `display_term`, `part_of_speech`, `gender`, `definition`, `level`, `created_at`.

Vocabulary terms are unique per `(user_id, language, lemma)`.

### Vocabulary Saves

`vocabulary_saves`: `id`, `user_id`, `analysis_id`, `vocabulary_term_id`, `surface_form`, `sentence_text`, `created_at`.

Vocabulary saves connect a normalized term to the analysis occurrence where the learner saved it.

## 6. Response Schema

All analysis responses share these fields:

```json
{
  "analysis_id": 123,
  "language": "Spanish",
  "english_translation": "string",
  "syntax_analysis": [
    {
      "feature": "string",
      "explanation": "string"
    }
  ],
  "vocabulary": [
    {
      "term": "surface form from input",
      "lemma": "dictionary form",
      "part_of_speech": "n.|v.|adj.|adv.|pron.|prep.|conj.|interj.|expr.|other",
      "gender": "m.|f.|m./f.|n/a",
      "definition": "string",
      "level": "A1|A2|B1|B2|C1|C2|N/A"
    }
  ],
  "notes": ["string"]
}
```

### Text Analysis Response

```json
{
  "input_type": "text",
  "analysis_id": 123,
  "language": "Spanish",
  "source_text": "string",
  "english_translation": "string",
  "syntax_analysis": [],
  "vocabulary": [],
  "notes": []
}
```

### Audio Analysis Response

```json
{
  "input_type": "audio",
  "analysis_id": 123,
  "language": "Spanish",
  "orthographic_transcript": "string",
  "ipa_transcript": "string",
  "english_translation": "string",
  "syntax_analysis": [],
  "vocabulary": [],
  "notes": []
}
```

Schema notes:

- `analysis_id` is added after persistence and may be `null` before a response is saved.
- Text responses use `source_text`.
- Audio responses use `orthographic_transcript` and `ipa_transcript`.
- `notes` is for short model caveats or pedagogical observations.
- Vocabulary includes both surface form and lemma so review can group inflected forms.
- Gender is used only when relevant; otherwise it should be `n/a`.

## 7. Audio Handling

Supported request content types and extensions:

- `audio/wav`, `.wav`
- `audio/wave`
- `audio/x-wav`
- `audio/mpeg`, `.mp3`
- `audio/mp3`
- `audio/webm`, `.webm`

Server constraints:

- Empty uploads are rejected.
- Unsupported audio types are rejected.
- Files larger than 16 MB are rejected.

Browser constraints:

- Recording is capped at 30 seconds.
- The UI shows recording duration.
- The UI exposes text and audio as distinct modes.

IPA behavior:

- vLLM native audio mode asks the model to base IPA on the audio signal.
- Google provider mode uses Speech-to-Text first, so IPA is inferred from the transcript.
- The UI labels whether IPA came from audio or text-derived analysis.

## 8. Configuration

Environment values are loaded from the shell first, then `.env` files without overriding shell values.

Core app values:

- `PROVIDER`: `google` or `vllm`.
- `MODEL`: model id used by the configured provider.
- `DATABASE_URL`: SQLAlchemy database URL. If omitted, SQLite is used at `.data/gemma_glot.db`.

Google GenAI:

- `GOOGLE_API_KEY`
- `GEMINI_API_KEY` is also accepted as a fallback key name.

Google Cloud Speech-to-Text:

- `GOOGLE_CLOUD_PROJECT`
- `GCLOUD_PROJECT` is accepted as a fallback project variable.
- `GOOGLE_CLOUD_LOCATION`, default `us`.
- `SPEECH_LANGUAGE_CODE`, default `es-US`.
- `SPEECH_MODEL`, default `chirp_3`.

vLLM:

- `VLLM_BASE_URL`, default `http://localhost:8001/v1`.
- `VLLM_API_KEY`, optional.
- `VLLM_TIMEOUT_SECONDS`, default `300`.

## 9. Deployment Shape

### App Container

The app container serves both FastAPI API endpoints and static frontend assets.

The Dockerfile for the app lives at `deploy/app/Dockerfile`, and the Cloud Build config lives at `deploy/app/cloudbuild.yaml`.

The current Cloud Run app deployment can use Google GenAI for text, Google Cloud Speech-to-Text for audio transcription, and SQLite inside the container for short-lived data.

For durable production history, the app should use an external database such as Cloud SQL through `DATABASE_URL`.

### vLLM Container

The vLLM deployment lives under `deploy/cloud-run-vllm/`.

It is a separate model service because GPU inference should be scaled, secured, and cost-managed independently from the web app.

The app talks to vLLM through `VLLM_BASE_URL` and, when configured, `VLLM_API_KEY`.

## 10. Non-Functional Requirements

- The API should return stable JSON shapes even when model content varies.
- Learner-sized text inputs should be handled reliably.
- Audio analysis should show a clear loading state.
- Errors should be clear for empty text, missing audio, unsupported audio, oversized audio, auth failures, and inference failures.
- Model provider failures should surface as `502` API responses.
- Database records should be scoped to the authenticated user.
- Review endpoints should never expose another user's history or vocabulary.
- Secrets should be provided through environment variables or cloud secrets, not committed files.

## 11. Success Criteria

- A user can create an account, sign in, and submit Spanish text.
- The text response includes translation, syntax, vocabulary, and notes.
- A user can record or upload Spanish audio up to the MVP limits.
- The audio response includes transcript, IPA, translation, syntax, vocabulary, and notes.
- Analyses are saved and visible in the user's history.
- Vocabulary items can be saved from an analysis and reviewed later.
- The backend can run locally with mock responses, Google provider responses, or vLLM provider responses depending on configuration.
- The app can be deployed to Google Cloud Run with Google provider mode.

## 12. Non-Goals

- Real-time conversation.
- Accent grading or pronunciation score.
- Fine-grained dialect identification.
- Offline-first inference in the shipped web app.
- Shared classrooms or teacher dashboards.
- Full multilingual product behavior before language-specific prompts and tests are added.
