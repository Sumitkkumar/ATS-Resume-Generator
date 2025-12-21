import { useState } from "react";

export default function ResumeGenerator() {
  const [jdUrl, setJdUrl] = useState("");
  const [greyHat, setGreyHat] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    if (!jdUrl.trim()) {
      setError("Please paste a Job Description URL");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL;
      const res = await fetch(`${API_BASE}/generate-resume-from-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jd_url: jdUrl,
          grey_hat: greyHat,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to generate resume");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "ATS_Resume.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <div className="container">
        <h1>ATS Resume Generator</h1>
        <p className="subtitle">
          Generate an ATS-optimized resume using AI
        </p>

        <input
          placeholder="Paste Job Description URL"
          value={jdUrl}
          onChange={(e) => setJdUrl(e.target.value)}
        />

        {/* Toggle */}
        <div className="checkbox-row">
            <label className="checkbox-label">
                <input
                type="checkbox"
                checked={greyHat}
                onChange={() => setGreyHat(!greyHat)}
                />
                <span className="checkbox-text">Grey-Hat Skill Expansion</span>
            </label>
        </div>

        <button onClick={generate} disabled={loading}>
          {loading ? "Generating…" : "Generate Resume"}
        </button>

        {/* Loader */}
        {loading && (
          <div className="loader">
            <div className="spinner" />
            <span>Building ATS-optimized resume…</span>
          </div>
        )}

        {/* Error Toast */}
        {error && <div className="toast">{error}</div>}
      </div>
    </div>
  );
}
