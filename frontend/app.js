const { createElement: h, useEffect, useRef, useState } = React;

const SAMPLE_TEXT =
  "Cuando era nino, siempre sonaba con viajar por America Latina, pero nunca imagine que aprender otro idioma cambiaria tanto mi forma de ver el mundo.";
const MAX_RECORDING_SECONDS = 60;

function formatTime(value) {
  return `00:${String(value).padStart(2, "0")}`;
}

function App() {
  const [language, setLanguage] = useState("Spanish");
  const [mode, setMode] = useState("text");
  const [text, setText] = useState(SAMPLE_TEXT);
  const [file, setFile] = useState(null);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [result, setResult] = useState(null);
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
        const response = await fetch("/api/analyze/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language, text }),
        });
        setResult(await readResponse(response));
      } else {
        const audio = file || recordedBlob;
        if (!audio) throw new Error("Upload or record audio before analyzing.");
        const formData = new FormData();
        formData.append("language", language);
        formData.append("file", audio, file ? file.name : "recording.webm");
        const response = await fetch("/api/analyze/audio", {
          method: "POST",
          body: formData,
        });
        setResult(await readResponse(response));
      }
    } catch (err) {
      setError(err.message || "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function readResponse(response) {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Analysis failed.");
    return payload;
  }

  const selectedAudioLabel = file
    ? file.name
    : recordedBlob
      ? `Recorded audio (${formatTime(seconds)})`
      : "";

  return h(
    "main",
    { className: "app" },
    h(Header),
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
        file,
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
      h(ResultPanel, { result, loading })
    ),
    error ? h("p", { className: "error", role: "alert" }, error) : null
  );
}

function Header() {
  return h(
    "header",
    { className: "topbar" },
    h("div", { className: "brand" }, h("div", { className: "brand-mark", "aria-hidden": true }, "Gg"), h("h1", null, "GemmaGlot")),
    h("div", { className: "status-pill", "aria-label": "Backend status" }, h("span", { className: "status-dot", "aria-hidden": true }), "Google API first")
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

function ResultPanel({ result, loading }) {
  return h(
    "section",
    { className: "panel result-panel", "aria-label": "Analysis result" },
    h("div", { className: "result-header" }, h("div", null, h("h2", null, result ? "Analysis result" : "Ready"), h("p", null, result ? `${result.language} ${result.input_type} analysis` : "Submit text or audio to begin."))),
    loading ? h("p", { className: "loading-state" }, "GemmaGlot is analyzing...") : null,
    !loading && !result ? h("p", { className: "empty-state" }, "Structured transcription, translation, syntax, and vocabulary will appear here.") : null,
    result ? h(ResultContent, { result }) : null
  );
}

function ResultContent({ result }) {
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
          h("article", { className: "vocab-card", key: `${item.term}-${index}` }, h("strong", null, item.term), h("span", { className: "level" }, item.level), h("p", null, item.definition))
        )
      )
    ),
    result.notes && result.notes.length
      ? h("section", { className: "result-section" }, h("h3", { className: "section-label" }, "Notes"), h("ul", { className: "notes" }, result.notes.map((note, index) => h("li", { key: index }, note))))
      : null
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(h(App));
