# GemmaGlot

## 1. Product Overview
GemmaGlot is a web application for language learners. It uses Gemma 4 through the Google API to analyze learner input and return pedagogically useful feedback.

The MVP focuses on two workflows:
- Analyze target-language text for syntax and vocabulary.
- Analyze target-language audio by first transcribing it, then producing IPA and linguistic analysis.

GemmaGlot is not a real-time assistant in the MVP. Users either:
- paste text into the app,
- record audio in the browser, or
- upload an audio file for analysis.

The product should be designed so the user selects a target language before analysis. For the initial version, the only available language option is Spanish.

## 2. MVP Scope

### Included
- Single-page web app.
- Language selection in the UI.
- Text input analysis.
- Audio upload analysis.
- In-browser audio recording with a maximum recording length of 1 minute.
- Standard orthographic transcription for audio input.
- Readable IPA transcription for audio input, with important allophonic detail when feasible.
- English translation for analyzed content.
- Syntax and vocabulary analysis for both text input and audio-derived transcript.
- Google API integration as the primary and only required inference backend for MVP.

### Deferred
- Local LLM or Ollama fallback.
- Regionalism or dialect marker detection.
- Native-target pronunciation comparison or articulatory delta scoring.
- Real-time streaming transcription or coaching.

## 3. Technical Direction
- Frontend: React.
- Backend: Python with FastAPI.
- Database: MySQL.
- Model family: Gemma 4.
- Primary inference provider: Google API.
- Audio input handling: browser recording plus server-side preprocessing as needed.
- Supported audio formats for MVP: `.wav` and `.mp3`.
- Language architecture: the request pipeline should accept a selected target language as an input parameter.
- Initial language availability: Spanish only.

Implementation note:
If the chosen Google API surface does not natively return both orthographic and IPA transcription in one pass, the system may use a staged pipeline:
1. produce transcript,
2. derive IPA,
3. produce English translation,
4. run linguistic analysis on the transcript.

## 4. User Flows

### Flow A: Text Analysis
1. User selects a target language.
2. User pastes target-language text into the app.
3. User submits the text for analysis.
4. System returns syntax analysis and vocabulary notes.

### Flow B: Audio Analysis
1. User selects a target language.
2. User uploads a `.wav` or `.mp3` file, or records audio in the browser.
3. Recording length is capped at 1 minute.
4. System transcribes the audio into standard orthography for the selected language.
5. System generates a readable IPA transcription with useful allophonic detail where possible.
6. System generates an English translation.
7. System runs syntax and vocabulary analysis on the transcript.
8. System returns all results in one response.

## 5. Functional Requirements

### Functionality 1: Linguistic Auditor
Goal: extract pedagogical value from target-language input.

#### Supported Inputs
- Raw target-language text.
- Target-language audio after transcription.

#### Required Analysis
- Identify syntactic structures and explain them in learner-friendly language.
- Extract vocabulary items worth studying.
- Assign CEFR-style vocabulary difficulty labels from A1 to C2.

#### Output Expectations
- Syntax feedback should highlight notable grammatical patterns, not every trivial construction.
- Vocabulary output should prioritize pedagogically useful terms over exhaustive word lists.
- Explanations should be concise, clear, and oriented toward learners of the selected language.

### Functionality 2: Audio Transcriber
Goal: convert target-language audio into standard orthography and IPA.

#### Supported Inputs
- User-recorded audio from the browser.
- Uploaded `.wav` or `.mp3` files.

#### Required Output
- Standard orthographic transcription for the selected language.
- IPA transcription that is readable but still captures important allophones when feasible.
- English translation.

#### IPA Guidance
- Prefer a learner-readable transcription over maximum phonetic density.
- Include major allophonic details when confidence is high and they add learning value.
- Avoid overloading the result with narrow distinctions that are unlikely to help the learner.

## 6. Response Schema

### Text Input Response
```json
{
  "input_type": "text",
  "language": "string",
  "source_text": "string",
  "english_translation": "string",
  "syntax_analysis": [
    {
      "feature": "string",
      "explanation": "string"
    }
  ],
  "vocabulary": [
    {
      "term": "string",
      "definition": "string",
      "level": "A1|A2|B1|B2|C1|C2"
    }
  ],
  "notes": [
    "string"
  ]
}
```

### Audio Input Response
```json
{
  "input_type": "audio",
  "language": "string",
  "orthographic_transcript": "string",
  "ipa_transcript": "string",
  "english_translation": "string",
  "syntax_analysis": [
    {
      "feature": "string",
      "explanation": "string"
    }
  ],
  "vocabulary": [
    {
      "term": "string",
      "definition": "string",
      "level": "A1|A2|B1|B2|C1|C2"
    }
  ],
  "notes": [
    "string"
  ]
}
```

Schema notes:
- `notes` is optional and can hold short pedagogical observations or model caveats.
- Audio responses must include both transcription fields and linguistic analysis fields.
- Text responses do not require transcription fields.
- Confidence scores are omitted for MVP unless the backend later has a reliable provider-derived signal.

## 7. UI Requirements
- The MVP should be a single-page web app.
- The page should provide:
  - a language selector,
  - a text input area,
  - an audio upload control,
  - a record button,
  - a submit/analyze action,
  - a results area for structured output.
- The interface should make it obvious whether the user is analyzing text or audio.
- In the initial version, the language selector should expose Spanish as the only available option.
- The interface should show recording duration and prevent recording beyond 1 minute.

## 8. Non-Functional Requirements
- The app should handle typical learner-sized inputs reliably.
- Audio analysis should be asynchronous from the user's perspective, with a visible loading state.
- Errors should be shown clearly for unsupported files, missing audio, empty text, or inference failures.
- Output should be deterministic in structure even if content quality varies by model certainty.

## 9. MVP Success Criteria
- A user can select Spanish and paste text and receive syntax and vocabulary analysis.
- A user can select Spanish and record or upload up to 1 minute of audio and receive:
  - orthographic transcription,
  - IPA transcription,
  - English translation,
  - syntax analysis,
  - vocabulary analysis.
- The system uses the Google API as the primary working backend.

## 10. Explicit Non-Goals for MVP
- Accent scoring against a native reference.
- Fine-grained dialect classification.
- Live conversation mode.
- Offline-first or local-only inference.
