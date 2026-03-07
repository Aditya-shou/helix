import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://localhost:8000";

const C = {
  bg: "#0a0a0f",
  surface: "#111118",
  border: "#1e1e2e",
  accent: "#7c6aff",
  accentDim: "#3d3580",
  green: "#3ddc84",
  dim: "#44445a",
  text: "#e2e2f0",
  muted: "#888899",
  red: "#ff4f6d",
};

// ── PDF.js is loaded from CDN via index.html script tag ──────────────────
// Add these two lines to your index.html <head>:
//   <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
//   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf_viewer.min.css"/>

/**
 * PdfReader
 * ---------
 * Props:
 *   book        — full book object from GET /api/books/:id
 *   onPageChange(page) — called whenever page changes (for parent state sync)
 *   onClose     — called when user closes the reader
 */
export default function PdfReader({ book, onPageChange, onClose }) {
  const canvasRef = useRef(null);
  const pdfRef = useRef(null); // loaded PDF document
  const renderTaskRef = useRef(null); // current render task (to cancel)
  const pageOnOpenRef = useRef(book.current_page); // page when reader was opened

  const [currentPage, setCurrentPage] = useState(book.current_page || 1);
  const [totalPages, setTotalPages] = useState(book.total_pages || 0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scale, setScale] = useState(1.4);
  const [saving, setSaving] = useState(false);

  // Save page to backend
  const savePage = useCallback(
    async (page) => {
      if (page === pageOnOpenRef.current) return; // nothing changed
      setSaving(true);
      try {
        await fetch(`${API}/api/books/${book.id}/page`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ page }),
        });
        pageOnOpenRef.current = page;
        onPageChange?.(page);
      } catch (e) {
        console.error("Failed to save page:", e);
      } finally {
        setSaving(false);
      }
    },
    [book.id, onPageChange],
  );

  // Save on close / tab unload
  useEffect(() => {
    const handleUnload = () => {
      // Synchronous beacon so it fires even as window closes
      if (currentPage !== pageOnOpenRef.current) {
        navigator.sendBeacon(
          `${API}/api/books/${book.id}/page`,
          JSON.stringify({ page: currentPage }),
        );
      }
    };
    window.addEventListener("beforeunload", handleUnload);
    return () => window.removeEventListener("beforeunload", handleUnload);
  }, [book.id, currentPage]);

  // Load PDF via pdfjs
  useEffect(() => {
    if (!window.pdfjsLib) {
      setError(
        "PDF.js not loaded. Add the CDN script to index.html — see comment at top of PdfReader.jsx",
      );
      setLoading(false);
      return;
    }

    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

    setLoading(true);
    setError("");

    window.pdfjsLib
      .getDocument(`${API}/api/books/${book.id}/file`)
      .promise.then((pdf) => {
        pdfRef.current = pdf;
        setTotalPages(pdf.numPages);
        setLoading(false);
      })
      .catch((e) => {
        setError(`Could not load PDF: ${e.message}`);
        setLoading(false);
      });

    return () => {
      pdfRef.current = null;
    };
  }, [book.id]);

  // Render current page onto canvas
  useEffect(() => {
    if (!pdfRef.current || loading) return;

    const renderPage = async () => {
      // Cancel any in-progress render
      if (renderTaskRef.current) {
        try {
          await renderTaskRef.current.cancel();
        } catch {}
      }

      const page = await pdfRef.current.getPage(currentPage);
      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current;
      if (!canvas) return;

      canvas.height = viewport.height;
      canvas.width = viewport.width;

      renderTaskRef.current = page.render({
        canvasContext: canvas.getContext("2d"),
        viewport,
      });

      try {
        await renderTaskRef.current.promise;
      } catch (e) {
        if (e?.name !== "RenderingCancelledException") {
          console.error("Render error:", e);
        }
      }
    };

    renderPage();
  }, [currentPage, scale, loading]);

  // Navigation
  const goTo = (page) => {
    const p = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(p);
  };

  // Save page when user navigates away from a page (debounced 2s)
  const saveTimer = useRef(null);
  useEffect(() => {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => savePage(currentPage), 2000);
    return () => clearTimeout(saveTimer.current);
  }, [currentPage, savePage]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown")
        goTo(currentPage + 1);
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") goTo(currentPage - 1);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentPage, totalPages]);

  // Handle close: save then call onClose
  const handleClose = async () => {
    await savePage(currentPage);
    onClose?.();
  };

  // Open in system viewer
  const openExternal = () => {
    window.open(`${API}/api/books/${book.id}/file`, "_blank");
  };

  const progress = totalPages > 0 ? currentPage / totalPages : 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: C.bg,
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "8px 16px",
          background: C.surface,
          borderBottom: `1px solid ${C.border}`,
          flexShrink: 0,
        }}
      >
        <button onClick={handleClose} style={btnStyle(C.dim, C.border)}>
          ← Back
        </button>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontWeight: 600,
              fontSize: 13,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {book.title}
          </div>
          <div style={{ color: C.muted, fontSize: 10 }}>{book.author}</div>
        </div>

        {/* Progress bar */}
        <div style={{ width: 120 }}>
          <div style={{ height: 3, background: C.border, borderRadius: 2 }}>
            <div
              style={{
                height: "100%",
                width: `${progress * 100}%`,
                background: C.green,
                borderRadius: 2,
                transition: "width 0.4s",
              }}
            />
          </div>
          <div
            style={{
              color: C.muted,
              fontSize: 10,
              marginTop: 3,
              textAlign: "right",
            }}
          >
            {Math.round(progress * 100)}%
          </div>
        </div>

        {/* Page controls */}
        <button
          onClick={() => goTo(currentPage - 1)}
          disabled={currentPage <= 1}
          style={btnStyle(C.text, C.border)}
        >
          ‹
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <input
            type="number"
            value={currentPage}
            min={1}
            max={totalPages}
            onChange={(e) => goTo(parseInt(e.target.value) || 1)}
            style={{
              width: 52,
              background: C.bg,
              border: `1px solid ${C.border}`,
              borderRadius: 4,
              color: C.text,
              padding: "3px 6px",
              fontSize: 12,
              textAlign: "center",
            }}
          />
          <span style={{ color: C.muted, fontSize: 12 }}>/ {totalPages}</span>
        </div>

        <button
          onClick={() => goTo(currentPage + 1)}
          disabled={currentPage >= totalPages}
          style={btnStyle(C.text, C.border)}
        >
          ›
        </button>

        {/* Zoom */}
        <button
          onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
          style={btnStyle(C.muted, C.border)}
        >
          −
        </button>
        <span
          style={{
            color: C.muted,
            fontSize: 11,
            minWidth: 36,
            textAlign: "center",
          }}
        >
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={() => setScale((s) => Math.min(3, s + 0.2))}
          style={btnStyle(C.muted, C.border)}
        >
          +
        </button>

        <button
          onClick={openExternal}
          style={btnStyle(C.muted, C.border)}
          title="Open in system viewer"
        >
          ⬡
        </button>

        {saving && <span style={{ color: C.dim, fontSize: 10 }}>saving…</span>}
      </div>

      {/* PDF canvas */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          display: "flex",
          justifyContent: "center",
          padding: "20px 0",
          background: "#1a1a24",
        }}
      >
        {loading && (
          <div style={{ color: C.muted, alignSelf: "center", fontSize: 13 }}>
            Loading PDF…
          </div>
        )}

        {error && (
          <div
            style={{
              color: C.red,
              alignSelf: "center",
              fontSize: 13,
              maxWidth: 400,
              textAlign: "center",
              padding: 20,
            }}
          >
            {error}
          </div>
        )}

        {!loading && !error && (
          <canvas
            ref={canvasRef}
            style={{
              boxShadow: "0 4px 40px rgba(0,0,0,0.6)",
              borderRadius: 2,
              maxWidth: "100%",
            }}
          />
        )}
      </div>
    </div>
  );
}

function btnStyle(color, border) {
  return {
    background: "transparent",
    border: `1px solid ${border}`,
    borderRadius: 4,
    color,
    padding: "4px 10px",
    cursor: "pointer",
    fontSize: 13,
    fontFamily: "JetBrains Mono, monospace",
    flexShrink: 0,
  };
}
