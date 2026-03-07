import { useState, useEffect, useRef, useCallback } from "react";
import PdfReader from "./PdfReader.jsx";

const API = "http://localhost:8000";

const C = {
  bg: "#0a0a0f",
  surface: "#111118",
  border: "#1e1e2e",
  accent: "#7c6aff",
  accentDim: "#3d3580",
  green: "#3ddc84",
  yellow: "#f5c842",
  red: "#ff4f6d",
  dim: "#44445a",
  text: "#e2e2f0",
  muted: "#888899",
};

const css = String.raw;

const globalStyle = css`
  @import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Syne:wght@400;600;800&display=swap");
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  body {
    background: ${C.bg};
    color: ${C.text};
    font-family: "JetBrains Mono", monospace;
    font-size: 13px;
  }
  ::-webkit-scrollbar {
    width: 4px;
  }
  ::-webkit-scrollbar-thumb {
    background: ${C.border};
    border-radius: 2px;
  }
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.4;
    }
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

// API helpers
const api = {
  get: (path) => fetch(`${API}${path}`).then((r) => r.json()),
  post: (path, body) =>
    fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  put: (path, body) =>
    fetch(`${API}${path}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  del: (path) =>
    fetch(`${API}${path}`, { method: "DELETE" }).then((r) => r.json()),
  upload: (path, form) =>
    fetch(`${API}${path}`, { method: "POST", body: form }).then((r) =>
      r.json(),
    ),
};

// Priority badge
function PriorityBadge({ p }) {
  const color = p === "P0" ? C.red : p === "P1" ? C.yellow : C.dim;
  return (
    <span
      style={{
        color,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 1,
        border: `1px solid ${color}`,
        padding: "1px 5px",
        borderRadius: 2,
      }}
    >
      {p}
    </span>
  );
}

// Progress bar
function ProgressBar({ value, color = C.accent }) {
  return (
    <div
      style={{
        height: 3,
        background: C.border,
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${Math.round(value * 100)}%`,
          background: color,
          borderRadius: 2,
          transition: "width 0.6s ease",
        }}
      />
    </div>
  );
}

// Sidebar
function Sidebar({ view, setView, projects, books }) {
  const navItem = (id, label, icon, badge) => {
    const active = view === id;
    return (
      <button
        key={id}
        onClick={() => setView(id)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "7px 12px",
          background: active ? C.accentDim : "transparent",
          border: "none",
          borderRadius: 4,
          color: active ? C.text : C.muted,
          cursor: "pointer",
          textAlign: "left",
          fontSize: 12,
          transition: "all 0.15s",
        }}
      >
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ flex: 1 }}>{label}</span>
        {badge != null && (
          <span
            style={{
              background: C.red,
              color: "#fff",
              fontSize: 9,
              padding: "1px 5px",
              borderRadius: 10,
              fontWeight: 700,
            }}
          >
            {badge}
          </span>
        )}
      </button>
    );
  };

  const totalP0 = projects.reduce((s, p) => s + (p.p0_tasks || 0), 0);

  return (
    <aside
      style={{
        width: 200,
        background: C.surface,
        borderRight: `1px solid ${C.border}`,
        display: "flex",
        flexDirection: "column",
        padding: "16px 8px",
        gap: 2,
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: "0 8px 16px",
          borderBottom: `1px solid ${C.border}`,
          marginBottom: 8,
        }}
      >
        <div
          style={{
            fontFamily: "Syne",
            fontSize: 18,
            fontWeight: 800,
            color: C.accent,
            letterSpacing: -0.5,
          }}
        >
          HELIX
        </div>
        <div style={{ color: C.dim, fontSize: 10, marginTop: 2 }}>
          engineering OS
        </div>
      </div>

      <div
        style={{
          color: C.dim,
          fontSize: 10,
          padding: "4px 12px",
          letterSpacing: 1,
          marginBottom: 2,
        }}
      >
        WORKSPACE
      </div>
      {navItem("dashboard", "Dashboard", "◈", totalP0 > 0 ? totalP0 : null)}
      {navItem("chat", "Chat", "◎")}
      {navItem("run", "Run Analysis", "▷")}

      <div
        style={{
          color: C.dim,
          fontSize: 10,
          padding: "12px 12px 4px",
          letterSpacing: 1,
        }}
      >
        PROJECTS
      </div>
      {projects.map((p) =>
        navItem(
          `project-${p.id}`,
          p.name,
          "⬡",
          p.p0_tasks > 0 ? p.p0_tasks : null,
        ),
      )}

      <div
        style={{
          color: C.dim,
          fontSize: 10,
          padding: "12px 12px 4px",
          letterSpacing: 1,
        }}
      >
        BOOKS
      </div>
      {navItem("books", "All Books", "◫")}
      {books
        .slice(0, 4)
        .map((b) => navItem(`book-${b.id}`, b.title.slice(0, 18), "◻"))}
      {navItem("upload-book", "+ Add Book", "+")}
    </aside>
  );
}

//  Dashboard
function Dashboard({ projects, books, setView }) {
  return (
    <div
      style={{ padding: 28, animation: "fadeIn 0.3s ease", overflow: "auto" }}
    >
      <h1
        style={{
          fontFamily: "Syne",
          fontSize: 22,
          fontWeight: 800,
          marginBottom: 4,
        }}
      >
        Dashboard
      </h1>
      <p style={{ color: C.muted, marginBottom: 24, fontSize: 12 }}>
        Overview of all tracked work
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 12,
          marginBottom: 28,
        }}
      >
        {projects.map((p) => (
          <div
            key={p.id}
            onClick={() => setView(`project-${p.id}`)}
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 16,
              cursor: "pointer",
              transition: "border-color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.accent)}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 10,
              }}
            >
              <div style={{ fontWeight: 500 }}>{p.name}</div>
              {p.p0_tasks > 0 && <PriorityBadge p="P0" />}
            </div>
            <ProgressBar
              value={p.progress_score}
              color={p.progress_score > 0.5 ? C.green : C.accent}
            />
            <div
              style={{
                marginTop: 8,
                display: "flex",
                gap: 12,
                color: C.muted,
                fontSize: 11,
              }}
            >
              <span>{Math.round(p.progress_score * 100)}% done</span>
              <span>{p.open_tasks} open</span>
              <span style={{ color: C.red }}>{p.p0_tasks} P0</span>
            </div>
          </div>
        ))}
      </div>

      <h2
        style={{
          fontFamily: "Syne",
          fontSize: 15,
          fontWeight: 700,
          marginBottom: 12,
        }}
      >
        Reading
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 10,
        }}
      >
        {books.map((b) => (
          <div
            key={b.id}
            onClick={() => setView(`book-${b.id}`)}
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 14,
              cursor: "pointer",
              transition: "border-color 0.2s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.borderColor = C.accentDim)
            }
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
          >
            <div style={{ fontWeight: 500, marginBottom: 6, fontSize: 12 }}>
              {b.title}
            </div>
            <div style={{ color: C.muted, fontSize: 11, marginBottom: 8 }}>
              {b.author}
            </div>
            <ProgressBar value={b.progress} color={C.green} />
            <div style={{ marginTop: 6, color: C.muted, fontSize: 11 }}>
              p.{b.current_page} / {b.total_pages}
            </div>
          </div>
        ))}
        {books.length === 0 && (
          <div style={{ color: C.muted, fontSize: 12 }}>
            No books yet. Add one →
          </div>
        )}
      </div>
    </div>
  );
}

// Project detail
function ProjectDetail({ project }) {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState("open");

  useEffect(() => {
    api
      .get(`/api/projects/${project.id}/tasks?status=${filter}`)
      .then(setTasks);
  }, [project.id, filter]);

  const markDone = async (taskId) => {
    await api.put(`/api/tasks/${taskId}/status`, { status: "completed" });
    setTasks((ts) => ts.filter((t) => t.id !== taskId));
  };

  return (
    <div
      style={{ padding: 28, animation: "fadeIn 0.3s ease", overflow: "auto" }}
    >
      <h1
        style={{
          fontFamily: "Syne",
          fontSize: 20,
          fontWeight: 800,
          marginBottom: 4,
        }}
      >
        {project.name}
      </h1>
      <p style={{ color: C.muted, fontSize: 12, marginBottom: 16 }}>
        {project.description}
      </p>

      <div style={{ display: "flex", gap: 20, marginBottom: 20 }}>
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 14,
            minWidth: 120,
          }}
        >
          <div style={{ color: C.muted, fontSize: 10, marginBottom: 6 }}>
            PROGRESS
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: C.accent }}>
            {Math.round(project.progress_score * 100)}%
          </div>
          <ProgressBar value={project.progress_score} />
        </div>
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 14,
            minWidth: 100,
          }}
        >
          <div style={{ color: C.muted, fontSize: 10, marginBottom: 6 }}>
            OPEN
          </div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>
            {project.open_tasks}
          </div>
        </div>
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 14,
            minWidth: 100,
          }}
        >
          <div style={{ color: C.muted, fontSize: 10, marginBottom: 6 }}>
            DONE
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: C.green }}>
            {project.completed_tasks}
          </div>
        </div>
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 14,
            minWidth: 100,
          }}
        >
          <div style={{ color: C.muted, fontSize: 10, marginBottom: 6 }}>
            P0
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: C.red }}>
            {project.p0_tasks}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {["open", "completed", "all"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s === "all" ? "" : s)}
            style={{
              padding: "4px 12px",
              borderRadius: 4,
              border: `1px solid ${filter === (s === "all" ? "" : s) ? C.accent : C.border}`,
              background:
                filter === (s === "all" ? "" : s) ? C.accentDim : "transparent",
              color: C.text,
              cursor: "pointer",
              fontSize: 11,
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {tasks.map((t) => (
          <div
            key={t.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 6,
              padding: "10px 14px",
            }}
          >
            <PriorityBadge p={t.priority} />
            <span style={{ flex: 1, fontWeight: 500 }}>{t.task_key}</span>
            <span style={{ color: C.muted, fontSize: 11, flex: 2 }}>
              {t.description.slice(0, 70)}…
            </span>
            <span style={{ color: C.dim, fontSize: 11 }}>
              {t.estimated_hours}h
            </span>
            {t.status === "open" && (
              <button
                onClick={() => markDone(t.id)}
                style={{
                  padding: "2px 8px",
                  fontSize: 10,
                  borderRadius: 3,
                  border: `1px solid ${C.green}`,
                  background: "transparent",
                  color: C.green,
                  cursor: "pointer",
                }}
              >
                ✓ done
              </button>
            )}
          </div>
        ))}
        {tasks.length === 0 && (
          <div style={{ color: C.muted, fontSize: 12 }}>No tasks.</div>
        )}
      </div>
    </div>
  );
}

// Book detail
function BookDetail({ book: initialBook, onRead }) {
  const [book, setBook] = useState(initialBook);
  const [noteText, setNoteText] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryText, setSummaryText] = useState("");
  const [pageInput, setPageInput] = useState(String(initialBook.current_page));
  const [rangeStart, setRangeStart] = useState("1");
  const [rangeEnd, setRangeEnd] = useState("30");

  const refreshBook = () => api.get(`/api/books/${book.id}`).then(setBook);

  const savePage = async () => {
    const p = parseInt(pageInput);
    if (!isNaN(p)) {
      const res = await api.put(`/api/books/${book.id}/page`, { page: p });
      setBook((b) => ({
        ...b,
        current_page: res.current_page,
        progress: res.progress,
      }));
    }
  };

  const addNote = async () => {
    if (!noteText.trim()) return;
    await api.post(`/api/books/${book.id}/notes`, {
      page: book.current_page,
      content: noteText,
    });
    setNoteText("");
    refreshBook();
  };

  const summarizeRange = async () => {
    setSummaryLoading(true);
    setSummaryText("");
    try {
      const res = await api.post(`/api/books/${book.id}/summarize`, {
        page_start: parseInt(rangeStart),
        page_end: parseInt(rangeEnd),
      });
      setSummaryText(res.summary);
      refreshBook();
    } finally {
      setSummaryLoading(false);
    }
  };

  const summarizeFull = async () => {
    setSummaryLoading(true);
    setSummaryText("");
    try {
      const res = await api.post(`/api/books/${book.id}/summarize/full`);
      setSummaryText(res.summary);
      refreshBook();
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div
      style={{
        padding: 28,
        animation: "fadeIn 0.3s ease",
        overflow: "auto",
        display: "flex",
        gap: 20,
      }}
    >
      {/* Left column */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 2,
          }}
        >
          <h1 style={{ fontFamily: "Syne", fontSize: 20, fontWeight: 800 }}>
            {book.title}
          </h1>
          <button
            onClick={onRead}
            style={{
              padding: "5px 16px",
              background: C.accentDim,
              border: `1px solid ${C.accent}`,
              borderRadius: 4,
              color: C.accent,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            ▶ Read
          </button>
        </div>
        <p style={{ color: C.muted, fontSize: 12, marginBottom: 16 }}>
          {book.author}
        </p>

        <ProgressBar value={book.progress} color={C.green} />
        <div
          style={{
            color: C.muted,
            fontSize: 11,
            marginTop: 6,
            marginBottom: 20,
          }}
        >
          {Math.round(book.progress * 100)}% complete — page {book.current_page}{" "}
          of {book.total_pages}
        </div>

        {/* Page tracker */}
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
          }}
        >
          <div
            style={{
              color: C.muted,
              fontSize: 10,
              marginBottom: 8,
              letterSpacing: 1,
            }}
          >
            UPDATE POSITION
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="number"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              min={1}
              max={book.total_pages}
              style={{
                background: C.bg,
                border: `1px solid ${C.border}`,
                borderRadius: 4,
                color: C.text,
                padding: "6px 10px",
                width: 80,
                fontSize: 13,
              }}
            />
            <button
              onClick={savePage}
              style={{
                background: C.accentDim,
                border: `1px solid ${C.accent}`,
                borderRadius: 4,
                color: C.accent,
                padding: "6px 14px",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Save page
            </button>
          </div>
        </div>

        {/* Notes */}
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
          }}
        >
          <div
            style={{
              color: C.muted,
              fontSize: 10,
              marginBottom: 10,
              letterSpacing: 1,
            }}
          >
            NOTES (page {book.current_page})
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a note for this page..."
              onKeyDown={(e) => e.key === "Enter" && addNote()}
              style={{
                flex: 1,
                background: C.bg,
                border: `1px solid ${C.border}`,
                borderRadius: 4,
                color: C.text,
                padding: "6px 10px",
                fontSize: 12,
              }}
            />
            <button
              onClick={addNote}
              style={{
                background: C.accentDim,
                border: `1px solid ${C.accent}`,
                borderRadius: 4,
                color: C.accent,
                padding: "6px 12px",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              +
            </button>
          </div>
          {(book.notes || []).map((n) => (
            <div
              key={n.id}
              style={{
                borderTop: `1px solid ${C.border}`,
                paddingTop: 8,
                marginTop: 8,
                fontSize: 12,
              }}
            >
              <span style={{ color: C.accent, fontSize: 10 }}>p.{n.page}</span>
              <span style={{ color: C.muted, margin: "0 8px", fontSize: 10 }}>
                —
              </span>
              {n.content}
            </div>
          ))}
        </div>

        {/* Saved summaries */}
        {(book.summaries || []).length > 0 && (
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 16,
            }}
          >
            <div
              style={{
                color: C.muted,
                fontSize: 10,
                marginBottom: 10,
                letterSpacing: 1,
              }}
            >
              SAVED SUMMARIES
            </div>
            {(book.summaries || []).map((s) => (
              <details key={s.id} style={{ marginBottom: 10 }}>
                <summary
                  style={{
                    cursor: "pointer",
                    color: C.accent,
                    fontSize: 12,
                    marginBottom: 6,
                  }}
                >
                  {s.chapter} (p.{s.page_start}–{s.page_end})
                </summary>
                <p
                  style={{
                    color: C.text,
                    fontSize: 12,
                    lineHeight: 1.7,
                    paddingLeft: 12,
                  }}
                >
                  {s.summary}
                </p>
              </details>
            ))}
          </div>
        )}
      </div>

      {/* Right column — summarizer */}
      <div style={{ width: 320, flexShrink: 0 }}>
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
          }}
        >
          <div
            style={{
              color: C.muted,
              fontSize: 10,
              marginBottom: 12,
              letterSpacing: 1,
            }}
          >
            SUMMARIZE RANGE
          </div>
          <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
            <input
              type="number"
              value={rangeStart}
              onChange={(e) => setRangeStart(e.target.value)}
              placeholder="from"
              style={{
                width: 70,
                background: C.bg,
                border: `1px solid ${C.border}`,
                borderRadius: 4,
                color: C.text,
                padding: "6px 8px",
                fontSize: 12,
              }}
            />
            <span style={{ color: C.muted, alignSelf: "center" }}>to</span>
            <input
              type="number"
              value={rangeEnd}
              onChange={(e) => setRangeEnd(e.target.value)}
              placeholder="to"
              style={{
                width: 70,
                background: C.bg,
                border: `1px solid ${C.border}`,
                borderRadius: 4,
                color: C.text,
                padding: "6px 8px",
                fontSize: 12,
              }}
            />
          </div>
          <button
            onClick={summarizeRange}
            disabled={summaryLoading}
            style={{
              width: "100%",
              padding: "8px",
              background: C.accentDim,
              border: `1px solid ${C.accent}`,
              borderRadius: 4,
              color: C.accent,
              cursor: "pointer",
              fontSize: 12,
              marginBottom: 8,
            }}
          >
            Summarize pages
          </button>
          <button
            onClick={summarizeFull}
            disabled={summaryLoading}
            style={{
              width: "100%",
              padding: "8px",
              background: "transparent",
              border: `1px solid ${C.dim}`,
              borderRadius: 4,
              color: C.muted,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Summarize full book
          </button>
        </div>

        {summaryLoading && (
          <div
            style={{
              color: C.muted,
              fontSize: 12,
              padding: 12,
              textAlign: "center",
            }}
          >
            <span
              style={{
                display: "inline-block",
                animation: "spin 1s linear infinite",
                marginRight: 8,
                fontSize: 14,
              }}
            >
              ◌
            </span>
            Reading and summarizing...
          </div>
        )}

        {summaryText && (
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 16,
            }}
          >
            <div
              style={{
                color: C.muted,
                fontSize: 10,
                marginBottom: 10,
                letterSpacing: 1,
              }}
            >
              SUMMARY
            </div>
            <p style={{ fontSize: 12, lineHeight: 1.8, color: C.text }}>
              {summaryText}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Upload book
function UploadBook({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [file, setFile] = useState(null);
  const inputRef = useRef();

  const handleFile = (f) => {
    if (f && f.name.endsWith(".pdf")) setFile(f);
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("title", title || file.name.replace(".pdf", ""));
    form.append("author", author || "Unknown");
    try {
      await api.upload("/api/books/upload", form);
      onUploaded();
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: 28, animation: "fadeIn 0.3s ease", maxWidth: 480 }}>
      <h1
        style={{
          fontFamily: "Syne",
          fontSize: 20,
          fontWeight: 800,
          marginBottom: 4,
        }}
      >
        Add Book
      </h1>
      <p style={{ color: C.muted, fontSize: 12, marginBottom: 24 }}>
        Upload a PDF to track your reading
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current.click()}
        style={{
          border: `2px dashed ${dragging ? C.accent : C.border}`,
          borderRadius: 10,
          padding: "40px 20px",
          textAlign: "center",
          cursor: "pointer",
          background: dragging ? C.accentDim + "22" : "transparent",
          marginBottom: 20,
          transition: "all 0.2s",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
        <div style={{ fontSize: 28, marginBottom: 8 }}>◫</div>
        {file ? (
          <div style={{ color: C.green }}>{file.name}</div>
        ) : (
          <div style={{ color: C.muted, fontSize: 12 }}>
            Drop a PDF here or click to browse
          </div>
        )}
      </div>

      {["Title", "Author"].map((label, i) => (
        <div key={label} style={{ marginBottom: 12 }}>
          <label
            style={{
              display: "block",
              color: C.muted,
              fontSize: 10,
              letterSpacing: 1,
              marginBottom: 5,
            }}
          >
            {label.toUpperCase()}
          </label>
          <input
            placeholder={`${label} (optional)`}
            value={i === 0 ? title : author}
            onChange={(e) =>
              i === 0 ? setTitle(e.target.value) : setAuthor(e.target.value)
            }
            style={{
              width: "100%",
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 4,
              color: C.text,
              padding: "8px 12px",
              fontSize: 13,
            }}
          />
        </div>
      ))}

      <button
        onClick={upload}
        disabled={!file || uploading}
        style={{
          width: "100%",
          padding: 10,
          background: file ? C.accentDim : C.border,
          border: `1px solid ${file ? C.accent : C.dim}`,
          borderRadius: 6,
          color: file ? C.accent : C.dim,
          cursor: file ? "pointer" : "default",
          fontSize: 13,
          fontFamily: "JetBrains Mono",
          marginTop: 8,
        }}
      >
        {uploading ? "Uploading..." : "Add Book →"}
      </button>
    </div>
  );
}

// Chat
function Chat() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hey — ask me about your projects or books. What should you focus on?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const userMsg = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post("/api/chat", {
        message: text,
        history: messages,
      });
      setMessages((m) => [...m, { role: "assistant", content: res.response }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        padding: "20px 28px",
      }}
    >
      <h1
        style={{
          fontFamily: "Syne",
          fontSize: 20,
          fontWeight: 800,
          marginBottom: 20,
        }}
      >
        Chat
      </h1>
      <div
        style={{
          flex: 1,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 14,
          paddingBottom: 12,
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              maxWidth: "75%",
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              animation: "fadeIn 0.2s ease",
            }}
          >
            <div
              style={{
                fontSize: 9,
                color: C.dim,
                marginBottom: 4,
                textAlign: m.role === "user" ? "right" : "left",
                letterSpacing: 1,
              }}
            >
              {m.role === "user" ? "YOU" : "HELIX"}
            </div>
            <div
              style={{
                background: m.role === "user" ? C.accentDim : C.surface,
                border: `1px solid ${m.role === "user" ? C.accent : C.border}`,
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 13,
                lineHeight: 1.7,
                color: C.text,
              }}
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div
            style={{
              alignSelf: "flex-start",
              color: C.muted,
              fontSize: 12,
              animation: "pulse 1s ease infinite",
            }}
          >
            Helix is thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div
        style={{
          display: "flex",
          gap: 8,
          borderTop: `1px solid ${C.border}`,
          paddingTop: 14,
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask Helix anything..."
          style={{
            flex: 1,
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 6,
            color: C.text,
            padding: "10px 14px",
            fontSize: 13,
          }}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            padding: "10px 18px",
            background: C.accentDim,
            border: `1px solid ${C.accent}`,
            borderRadius: 6,
            color: C.accent,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

// Run panel
function RunPanel() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const run = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await api.post("/api/run", {});
      setResult(res);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ padding: 28, animation: "fadeIn 0.3s ease" }}>
      <h1
        style={{
          fontFamily: "Syne",
          fontSize: 20,
          fontWeight: 800,
          marginBottom: 4,
        }}
      >
        Run Analysis
      </h1>
      <p style={{ color: C.muted, fontSize: 12, marginBottom: 24 }}>
        Trigger a full Helix pipeline across all projects
      </p>
      <button
        onClick={run}
        disabled={running}
        style={{
          padding: "12px 24px",
          background: running ? C.border : C.accentDim,
          border: `1px solid ${running ? C.dim : C.accent}`,
          borderRadius: 6,
          color: running ? C.dim : C.accent,
          cursor: running ? "default" : "pointer",
          fontSize: 13,
          fontFamily: "JetBrains Mono",
          marginBottom: 24,
        }}
      >
        {running ? "◌  Running..." : "▷  Run Now"}
      </button>

      {result && (
        <div style={{ animation: "fadeIn 0.3s ease" }}>
          <div style={{ color: C.green, marginBottom: 16, fontSize: 13 }}>
            ✓ Analyzed {result.projects_analyzed} project(s)
          </div>
          {result.summaries?.map((s, i) => (
            <div
              key={i}
              style={{
                background: C.surface,
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                padding: 16,
                marginBottom: 10,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 6 }}>
                {s.project}
              </div>
              <div style={{ color: C.muted, fontSize: 11, marginBottom: 6 }}>
                {Math.round(s.progress * 100)}% — {s.task_count} tasks
              </div>
              {s.delta && (
                <div style={{ color: C.dim, fontSize: 11 }}>{s.delta}</div>
              )}
              {s.auto_completed?.length > 0 && (
                <div style={{ color: C.green, fontSize: 11, marginTop: 4 }}>
                  ✓ Auto-completed: {s.auto_completed.join(", ")}
                </div>
              )}
            </div>
          ))}
          {result.portfolio && (
            <div
              style={{
                background: C.surface,
                border: `1px solid ${C.accentDim}`,
                borderRadius: 8,
                padding: 16,
              }}
            >
              <div
                style={{
                  color: C.accent,
                  fontSize: 10,
                  letterSpacing: 1,
                  marginBottom: 10,
                }}
              >
                FOCUS
              </div>
              <p
                style={{
                  fontSize: 12,
                  lineHeight: 1.8,
                  color: C.text,
                  whiteSpace: "pre-line",
                }}
              >
                {result.portfolio}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Books list
function BooksList({ books, setView }) {
  return (
    <div style={{ padding: 28, animation: "fadeIn 0.3s ease" }}>
      <h1
        style={{
          fontFamily: "Syne",
          fontSize: 20,
          fontWeight: 800,
          marginBottom: 20,
        }}
      >
        Books
      </h1>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {books.map((b) => (
          <div
            key={b.id}
            onClick={() => setView(`book-${b.id}`)}
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 16,
              cursor: "pointer",
              transition: "border-color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.accent)}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
          >
            <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 13 }}>
              {b.title}
            </div>
            <div style={{ color: C.muted, fontSize: 11, marginBottom: 10 }}>
              {b.author}
            </div>
            <ProgressBar value={b.progress} color={C.green} />
            <div style={{ marginTop: 8, color: C.muted, fontSize: 11 }}>
              p.{b.current_page} / {b.total_pages} ·{" "}
              {Math.round(b.progress * 100)}%
            </div>
          </div>
        ))}
        <div
          onClick={() => setView("upload-book")}
          style={{
            background: "transparent",
            border: `2px dashed ${C.border}`,
            borderRadius: 8,
            padding: 16,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: C.dim,
            fontSize: 12,
            minHeight: 100,
            transition: "border-color 0.2s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.accent)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
        >
          + Add Book
        </div>
      </div>
    </div>
  );
}

// Root app
export default function App() {
  const [view, setView] = useState("dashboard");
  const [projects, setProjects] = useState([]);
  const [books, setBooks] = useState([]);
  const [bookDetails, setBookDetails] = useState({});

  const loadProjects = useCallback(
    () => api.get("/api/projects").then(setProjects),
    [],
  );
  const loadBooks = useCallback(() => api.get("/api/books").then(setBooks), []);

  useEffect(() => {
    loadProjects();
    loadBooks();
  }, []);

  // Lazy-load full book detail when navigating to it
  useEffect(() => {
    if (view.startsWith("book-")) {
      const id = parseInt(view.split("-")[1]);
      api
        .get(`/api/books/${id}`)
        .then((b) => setBookDetails((d) => ({ ...d, [id]: b })));
    }
  }, [view]);

  const renderMain = () => {
    if (view === "dashboard")
      return <Dashboard projects={projects} books={books} setView={setView} />;
    if (view === "chat") return <Chat />;
    if (view === "run") return <RunPanel />;
    if (view === "books") return <BooksList books={books} setView={setView} />;
    if (view === "upload-book")
      return (
        <UploadBook
          onUploaded={() => {
            loadBooks();
            setView("books");
          }}
        />
      );

    if (view.startsWith("project-")) {
      const id = parseInt(view.split("-")[1]);
      const p = projects.find((p) => p.id === id);
      return p ? <ProjectDetail project={p} /> : null;
    }

    if (view.startsWith("read-")) {
      const id = parseInt(view.split("-")[1]);
      const b = bookDetails[id];
      return b ? (
        <PdfReader
          book={b}
          onPageChange={(page) => {
            setBookDetails((d) => ({
              ...d,
              [id]: { ...d[id], current_page: page },
            }));
            setBooks((bs) =>
              bs.map((bk) =>
                bk.id === id ? { ...bk, current_page: page } : bk,
              ),
            );
          }}
          onClose={() => setView(`book-${id}`)}
        />
      ) : (
        <div style={{ padding: 28, color: C.muted }}>Loading...</div>
      );
    }

    if (view.startsWith("book-")) {
      const id = parseInt(view.split("-")[1]);
      const b = bookDetails[id];
      return b ? (
        <BookDetail book={b} onRead={() => setView(`read-${id}`)} />
      ) : (
        <div style={{ padding: 28, color: C.muted }}>Loading...</div>
      );
    }

    return null;
  };

  return (
    <>
      <style>{globalStyle}</style>
      <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
        <Sidebar
          view={view}
          setView={setView}
          projects={projects}
          books={books}
        />
        <main style={{ flex: 1, overflow: "auto" }}>{renderMain()}</main>
      </div>
    </>
  );
}
