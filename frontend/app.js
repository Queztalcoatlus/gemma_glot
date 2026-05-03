const { createElement: h, useEffect, useRef, useState } = React;

const SAMPLE_TEXT =
  "Cuando era nino, siempre sonaba con viajar por America Latina, pero nunca imagine que aprender otro idioma cambiaria tanto mi forma de ver el mundo.";
const MAX_RECORDING_SECONDS = 60;
const TOKEN_KEY = "gemmaglot.token";
const USERNAME_KEY = "gemmaglot.username";

function formatTime(value) {
  return `00:${String(value).padStart(2, "0")}`;
}

function vocabularyKey(item) {
  return `${(item.lemma || item.term).toLowerCase()}::${item.term.toLowerCase()}`;
}

async function apiRequest(path, options = {}, token = "") {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail || "Request failed.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function App() {
  const [token, setToken] = useState(() => window.localStorage.getItem(TOKEN_KEY) || "");
  const [username, setUsername] = useState(() => window.localStorage.getItem(USERNAME_KEY) || "");
  const [view, setView] = useState("analyze");
  const [error, setError] = useState("");

  function handleAuth(auth) {
    window.localStorage.setItem(TOKEN_KEY, auth.token);
    window.localStorage.setItem(USERNAME_KEY, auth.username);
    setToken(auth.token);
    setUsername(auth.username);
    setError("");
  }

  function signOut() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USERNAME_KEY);
    setToken("");
    setUsername("");
    setView("analyze");
  }

  function handleAuthExpired(message) {
    signOut();
    setError(message || "Sign in to continue.");
  }

  if (!token) {
    return h(
      "main",
      { className: "app auth-layout" },
      h(Header),
      h(AuthPanel, { onAuth: handleAuth, initialError: error })
    );
  }

  return h(
    "main",
    { className: "app" },
    h(Header, { username, view, setView, signOut }),
    view === "analyze"
      ? h(AnalyzeView, { token, onAuthExpired: handleAuthExpired })
      : h(ReviewPanel, { token, onAuthExpired: handleAuthExpired })
  );
}

function Header({ username, view, setView, signOut } = {}) {
  const authed = Boolean(username);
  return h(
    "header",
    { className: "topbar" },
    h("div", { className: "brand" }, h("div", { className: "brand-mark", "aria-hidden": true }, "Gg"), h("h1", null, "GemmaGlot")),
    authed
      ? h(
          "div",
          { className: "topbar-actions" },
          h(
            "nav",
            { className: "view-switch", "aria-label": "App sections" },
            h("button", { type: "button", className: "nav-action", "aria-current": view === "analyze" ? "page" : undefined, onClick: () => setView("analyze") }, "Analyze"),
            h("button", { type: "button", className: "nav-action", "aria-current": view === "review" ? "page" : undefined, onClick: () => setView("review") }, "Review")
          ),
          h("div", { className: "status-pill", "aria-label": "Signed in user" }, h("span", { className: "status-dot", "aria-hidden": true }), username),
          h("button", { className: "secondary-action compact-action", type: "button", onClick: signOut }, "Sign out")
        )
      : h("div", { className: "status-pill", "aria-label": "Backend status" }, h("span", { className: "status-dot", "aria-hidden": true }), "Google or vLLM")
  );
}

function AuthPanel({ onAuth, initialError }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(initialError || "");

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const auth = await apiRequest(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      onAuth(auth);
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return h(
    "section",
    { className: "panel auth-panel", "aria-label": "Authentication" },
    h("div", { className: "panel-header" }, h("h2", { className: "panel-title" }, mode === "login" ? "Sign in" : "Create account")),
    h(
      "div",
      { className: "mode-tabs auth-tabs", role: "tablist", "aria-label": "Authentication mode" },
      h("button", { className: "tab", type: "button", role: "tab", "aria-selected": mode === "login", onClick: () => setMode("login") }, "Sign in"),
      h("button", { className: "tab", type: "button", role: "tab", "aria-selected": mode === "register", onClick: () => setMode("register") }, "Register")
    ),
    h(
      "form",
      { className: "auth-form", onSubmit: submit },
      h("label", null, "Username", h("input", { value: username, minLength: 3, maxLength: 80, required: true, autoComplete: "username", onChange: (event) => setUsername(event.target.value) })),
      h("label", null, "Password", h("input", { value: password, minLength: 8, maxLength: 128, required: true, type: "password", autoComplete: mode === "login" ? "current-password" : "new-password", onChange: (event) => setPassword(event.target.value) })),
      error ? h("p", { className: "error", role: "alert" }, error) : null,
      h("button", { className: "primary-action", type: "submit", disabled: loading }, loading ? "Working..." : mode === "login" ? "Sign in" : "Create account")
    )
  );
}

function AnalyzeView({ token, onAuthExpired }) {
  const [language, setLanguage] = useState("Spanish");
  const [mode, setMode] = useState("text");
  const [text, setText] = useState(SAMPLE_TEXT);
  const [file, setFile] = useState(null);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [result, setResult] = useState(null);
  const [savedWords, setSavedWords] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    if (!recording) return undefined;
    const timer = window.setInterval(() => {
      setSeconds((current) => {
        if (current + 1 >= MAX_RECORDING_SECONDS) {
          stopRecording();
          return MAX_RECORDING_SECONDS;
        }
        return current + 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  async function startRecording() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setRecordedBlob(blob);
        setFile(null);
      };
      mediaRecorderRef.current = recorder;
      setSeconds(0);
      setRecording(true);
      recorder.start();
    } catch {
      setError("Microphone access was not available.");
    }
  }

  function stopRecording() {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    setRecording(false);
  }

  function clearInput() {
    setError("");
    setResult(null);
    setSavedWords(new Set());
    if (mode === "text") {
      setText("");
    } else {
      if (recording) stopRecording();
      setFile(null);
      setRecordedBlob(null);
      setSeconds(0);
    }
  }

  async function analyze() {
    setError("");
    setLoading(true);
    try {
      if (mode === "text") {
        if (!text.trim()) throw new Error("Enter Spanish text to analyze.");
        const analysis = await apiRequest(
          "/api/analyze/text",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ language, text }),
          },
          token
        );
        setResult(analysis);
        setSavedWords(new Set());
      } else {
        const audio = file || recordedBlob;
        if (!audio) throw new Error("Upload or record audio before analyzing.");
        const formData = new FormData();
        formData.append("language", language);
        formData.append("file", audio, file ? file.name : "recording.webm");
        const analysis = await apiRequest("/api/analyze/audio", { method: "POST", body: formData }, token);
        setResult(analysis);
        setSavedWords(new Set());
      }
    } catch (err) {
      if (err.status === 401) onAuthExpired(err.message);
      else setError(err.message || "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function saveWord(item) {
    if (!result?.analysis_id) {
      setError("Analyze this text before saving vocabulary.");
      return;
    }
    setError("");
    try {
      await apiRequest(
        "/api/review/vocabulary",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            analysis_id: result.analysis_id,
            term: item.term,
            lemma: item.lemma || item.term,
            definition: item.definition,
            level: item.level,
          }),
        },
        token
      );
      setSavedWords((current) => new Set([...current, vocabularyKey(item)]));
    } catch (err) {
      if (err.status === 401) onAuthExpired(err.message);
      else setError(err.message || "Could not save vocabulary.");
    }
  }

  const selectedAudioLabel = file
    ? file.name
    : recordedBlob
      ? `Recorded audio (${formatTime(seconds)})`
      : "";

  return h(
    React.Fragment,
    null,
    h(
      "section",
      { className: "workspace", "aria-label": "GemmaGlot workspace" },
      h(InputPanel, {
        language,
        setLanguage,
        mode,
        setMode,
        text,
        setText,
        setFile,
        selectedAudioLabel,
        recording,
        seconds,
        startRecording,
        stopRecording,
        clearInput,
        analyze,
        loading,
        setRecordedBlob,
        setSeconds,
      }),
      h(ResultPanel, { result, loading, onSaveWord: saveWord, savedWords })
    ),
    error ? h("p", { className: "error", role: "alert" }, error) : null
  );
}

function InputPanel(props) {
  const {
    language,
    setLanguage,
    mode,
    setMode,
    text,
    setText,
    setFile,
    selectedAudioLabel,
    recording,
    seconds,
    startRecording,
    stopRecording,
    clearInput,
    analyze,
    loading,
    setRecordedBlob,
    setSeconds,
  } = props;

  return h(
    "section",
    { className: "panel input-panel" },
    h(
      "div",
      { className: "panel-header" },
      h("h2", { className: "panel-title" }, "Analyze"),
      h(
        "label",
        { className: "language-select" },
        "Language",
        h("select", { "aria-label": "Target language", value: language, onChange: (event) => setLanguage(event.target.value) }, h("option", { value: "Spanish" }, "Spanish"))
      )
    ),
    h(
      "div",
      { className: "mode-tabs", role: "tablist", "aria-label": "Input type" },
      h("button", { className: "tab", type: "button", role: "tab", "aria-selected": mode === "text", onClick: () => setMode("text") }, "Text"),
      h("button", { className: "tab", type: "button", role: "tab", "aria-selected": mode === "audio", onClick: () => setMode("audio") }, "Audio")
    ),
    h(
      "div",
      { className: "input-body" },
      mode === "text"
        ? h("textarea", { "aria-label": "Text to analyze", value: text, onChange: (event) => setText(event.target.value) })
        : h(AudioPane, {
            setFile,
            selectedAudioLabel,
            recording,
            seconds,
            startRecording,
            stopRecording,
            setRecordedBlob,
            setSeconds,
          }),
      h(
        "div",
        { className: "actions" },
        h("button", { className: "secondary-action", type: "button", onClick: clearInput, disabled: loading }, "Clear"),
        h("button", { className: "primary-action", type: "button", onClick: analyze, disabled: loading || recording }, loading ? "Analyzing..." : "Analyze")
      )
    )
  );
}

function AudioPane({ setFile, selectedAudioLabel, recording, seconds, startRecording, stopRecording, setRecordedBlob, setSeconds }) {
  return h(
    "div",
    { className: "audio-grid" },
    h(
      "label",
      { className: "dropzone" },
      h(
        "span",
        null,
        h("span", { className: "dropzone-icon", "aria-hidden": true }, "^"),
        h("strong", null, "Upload audio"),
        h("input", {
          className: "file-input",
          type: "file",
          accept: ".wav,.mp3,audio/wav,audio/mpeg",
          onChange: (event) => {
            const nextFile = event.target.files[0] || null;
            setFile(nextFile);
            if (nextFile) {
              setRecordedBlob(null);
              setSeconds(0);
            }
          },
        }),
        h("p", { className: "file-name" }, selectedAudioLabel)
      )
    ),
    h(
      "div",
      { className: "recorder" },
      h(
        "div",
        null,
        h("div", { className: "meter", "aria-hidden": true }, h("div", { className: "meter-fill", style: { width: `${(seconds / MAX_RECORDING_SECONDS) * 100}%` } })),
        h("div", { className: "time" }, `${formatTime(seconds)} / 01:00`)
      ),
      h("button", { className: `record-action${recording ? " recording" : ""}`, type: "button", onClick: recording ? stopRecording : startRecording }, recording ? "Stop" : "Record")
    )
  );
}

function ResultPanel({ result, loading, onSaveWord, savedWords }) {
  return h(
    "section",
    { className: "panel result-panel", "aria-label": "Analysis result" },
    h("div", { className: "result-header" }, h("div", null, h("h2", null, result ? "Analysis result" : "Ready"), h("p", null, result ? `${result.language} ${result.input_type} analysis` : "Submit text or audio to begin."))),
    loading ? h("p", { className: "loading-state" }, "GemmaGlot is analyzing...") : null,
    !loading && !result ? h("p", { className: "empty-state" }, "Structured transcription, translation, syntax, and vocabulary will appear here.") : null,
    result ? h(ResultContent, { result, onSaveWord, savedWords }) : null
  );
}

function ReviewPanel({ token, onAuthExpired }) {
  const [tab, setTab] = useState("history");
  const [history, setHistory] = useState([]);
  const [vocabulary, setVocabulary] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    refresh();
  }, [tab]);

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      if (tab === "history") {
        setHistory(await apiRequest("/api/review/history", {}, token));
      } else {
        setVocabulary(await apiRequest("/api/review/vocabulary", {}, token));
      }
    } catch (err) {
      if (err.status === 401) onAuthExpired(err.message);
      else setError(err.message || "Could not load review data.");
    } finally {
      setLoading(false);
    }
  }

  async function openAnalysis(analysisId) {
    setLoading(true);
    setError("");
    try {
      setSelected(await apiRequest(`/api/review/history/${analysisId}`, {}, token));
    } catch (err) {
      if (err.status === 401) onAuthExpired(err.message);
      else setError(err.message || "Could not load analysis.");
    } finally {
      setLoading(false);
    }
  }

  return h(
    "section",
    { className: "review-layout", "aria-label": "Review" },
    h(
      "div",
      { className: "panel review-list-panel" },
      h("div", { className: "panel-header" }, h("h2", { className: "panel-title" }, "Review"), h("button", { type: "button", className: "secondary-action compact-action", onClick: refresh, disabled: loading }, "Refresh")),
      h(
        "div",
        { className: "mode-tabs", role: "tablist", "aria-label": "Review type" },
        h("button", { className: "tab", type: "button", role: "tab", "aria-selected": tab === "history", onClick: () => setTab("history") }, "Sentences"),
        h("button", { className: "tab", type: "button", role: "tab", "aria-selected": tab === "vocabulary", onClick: () => setTab("vocabulary") }, "Words")
      ),
      h(
        "div",
        { className: "review-list" },
        error ? h("p", { className: "error", role: "alert" }, error) : null,
        loading && !selected ? h("p", { className: "loading-state" }, "Loading review...") : null,
        !loading && tab === "history" ? h(HistoryList, { history, openAnalysis }) : null,
        !loading && tab === "vocabulary" ? h(VocabularyList, { vocabulary, openAnalysis }) : null
      )
    ),
    h(
      "section",
      { className: "panel result-panel", "aria-label": "Selected review item" },
      h("div", { className: "result-header" }, h("div", null, h("h2", null, selected ? "Saved analysis" : "Select an item"), h("p", null, selected ? `${selected.language} ${selected.input_type} analysis` : "Open a sentence or word occurrence to review the full explanation."))),
      selected ? h(ResultContent, { result: selected }) : h("p", { className: "empty-state" }, "Your saved analysis will appear here.")
    )
  );
}

function HistoryList({ history, openAnalysis }) {
  if (!history.length) return h("p", { className: "empty-state" }, "No saved sentences yet.");
  return h(
    "div",
    { className: "history-list" },
    history.map((item) =>
      h(
        "button",
        { className: "history-item", type: "button", key: item.id, onClick: () => openAnalysis(item.id) },
        h("span", { className: "history-meta" }, `${item.input_type} - ${new Date(item.created_at).toLocaleString()}`),
        h("strong", null, item.text_preview),
        h("span", null, item.english_translation),
        h("span", { className: "level" }, `${item.vocabulary_count} words`)
      )
    )
  );
}

function VocabularyList({ vocabulary, openAnalysis }) {
  if (!vocabulary.length) return h("p", { className: "empty-state" }, "No saved vocabulary yet.");
  return h(
    "div",
    { className: "word-list" },
    vocabulary.map((entry) =>
      h(
        "article",
        { className: "word-item", key: entry.term },
        h("div", { className: "word-heading" }, h("strong", null, entry.term), h("span", { className: "level" }, entry.level)),
        h("p", null, entry.definition),
        h(
          "div",
          { className: "occurrence-list" },
          entry.occurrences.map((occurrence) =>
            h(
              "button",
              { className: "occurrence-link", type: "button", key: `${entry.term}-${occurrence.analysis_id}-${occurrence.created_at}`, onClick: () => openAnalysis(occurrence.analysis_id) },
              h("span", null, occurrence.surface_form),
              occurrence.sentence_text
            )
          )
        )
      )
    )
  );
}

function ResultContent({ result, onSaveWord, savedWords = new Set() }) {
  const transcript = result.input_type === "audio" ? result.orthographic_transcript : result.source_text;
  return h(
    React.Fragment,
    null,
    h(
      "section",
      { className: "result-section" },
      h("h3", { className: "section-label" }, result.input_type === "audio" ? "Transcription" : "Source"),
      h(
        "div",
        { className: "transcript" },
        h("p", { className: "quote" }, h("span", { className: "quote-label" }, "Text"), transcript),
        result.input_type === "audio" ? h("p", { className: "quote ipa" }, h("span", { className: "quote-label" }, "IPA"), result.ipa_transcript) : null
      )
    ),
    h("section", { className: "result-section" }, h("h3", { className: "section-label" }, "Translation"), h("p", { className: "quote translation" }, result.english_translation)),
    h(
      "section",
      { className: "result-section" },
      h("h3", { className: "section-label" }, "Syntax"),
      h(
        "ul",
        { className: "analysis-list" },
        result.syntax_analysis.map((item, index) =>
          h("li", { className: "analysis-item", key: `${item.feature}-${index}` }, h("strong", null, item.feature), h("span", null, item.explanation))
        )
      )
    ),
    h(
      "section",
      { className: "result-section" },
      h("h3", { className: "section-label" }, "Vocabulary"),
      h(
        "div",
        { className: "vocab-grid" },
        result.vocabulary.map((item, index) =>
          h(
            "article",
            { className: "vocab-card", key: `${item.term}-${index}` },
            h("div", { className: "vocab-card-header" }, h("strong", null, item.term), h("span", { className: "level" }, item.level)),
            h("span", { className: "base-form-label" }, item.lemma && item.lemma !== item.term ? `Base form: ${item.lemma}` : "Base form matches term"),
            h("p", null, item.definition),
            onSaveWord
              ? h(
                  "button",
                  {
                    className: "secondary-action compact-action save-word-action",
                    type: "button",
                    onClick: () => onSaveWord(item),
                    disabled: savedWords.has(vocabularyKey(item)),
                  },
                  savedWords.has(vocabularyKey(item)) ? "Saved" : "Save"
                )
              : null
          )
        )
      )
    ),
    result.notes && result.notes.length
      ? h("section", { className: "result-section" }, h("h3", { className: "section-label" }, "Notes"), h("ul", { className: "notes" }, result.notes.map((note, index) => h("li", { key: index }, note))))
      : null
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(h(App));
