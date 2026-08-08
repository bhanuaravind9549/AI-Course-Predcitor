import { useEffect, useMemo, useState } from "react";

const EXAMPLE =
  "I am interested in machine learning and data engineering and I want courses that involve Python and real world applications.";

function scorePercent(score) {
  return Math.round(Math.max(0, Math.min(1, score || 0)) * 100);
}

export default function App() {
  const [query, setQuery] = useState("");
  const [term, setTerm] = useState("");
  const [department, setDepartment] = useState("");
  const [level, setLevel] = useState("");
  const [meta, setMeta] = useState({ terms: [], departments: [], course_count: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch("/api/meta")
      .then((res) => res.json())
      .then(setMeta)
      .catch(() => setMeta({ terms: [], departments: [], course_count: 0 }));
  }, []);

  const canSearch = query.trim().length >= 3 && !loading;

  async function onSubmit(event) {
    event.preventDefault();
    if (!canSearch) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          term: term || null,
          department: department || null,
          level: level || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Recommendation failed");
      }
      setResult(data);
    } catch (err) {
      setError(err.message || "Could not reach the advisor API.");
    } finally {
      setLoading(false);
    }
  }

  const departmentLabel = useMemo(() => {
    const match = meta.departments?.find((d) => d.code === department);
    return match?.name || department;
  }, [department, meta.departments]);

  return (
    <div className="min-h-screen text-ink">
      <header className="border-b border-crimson/15 bg-crimson-deep text-cream">
        <div className="mx-auto flex max-w-6xl items-end justify-between gap-6 px-6 py-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gold">
              Indiana University Bloomington
            </p>
            <h1 className="font-display mt-1 text-3xl font-semibold tracking-tight md:text-4xl">
              Course Compass
            </h1>
          </div>
          <p className="hidden max-w-sm text-right text-sm text-cream/75 md:block">
            Semantic search over the official Schedule of Classes, with grounded
            advisor explanations.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <section className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-crimson">
              Ask in plain language
            </p>
            <h2 className="font-display mt-2 text-4xl leading-tight text-crimson-deep md:text-5xl">
              Find the IU courses that actually match what you want to learn.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-7 text-ink/75">
              Describe your interests, career direction, or the skills you want.
              Compass retrieves the closest catalog courses, then an LLM explains
              why they fit — without inventing classes that are not in the dump.
            </p>
          </div>

          <aside className="rounded-2xl border border-crimson/10 bg-white/70 p-5 shadow-card">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-crimson/70">
              Catalog coverage
            </p>
            <p className="font-display mt-2 text-4xl text-crimson-deep">
              {meta.course_count ? meta.course_count.toLocaleString() : "—"}
            </p>
            <p className="mt-1 text-sm text-ink/65">
              unique IU Bloomington courses indexed from Registrar research dumps.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-ink/70">
              {(meta.terms || []).map((item) => (
                <span
                  key={item}
                  className="rounded-full bg-parchment px-3 py-1 font-medium"
                >
                  {item}
                </span>
              ))}
            </div>
          </aside>
        </section>

        <form
          onSubmit={onSubmit}
          className="mt-10 rounded-3xl border border-crimson/10 bg-white p-5 shadow-card md:p-7"
        >
          <label htmlFor="query" className="text-sm font-semibold text-crimson-deep">
            What do you want to take?
          </label>
          <textarea
            id="query"
            rows={4}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={EXAMPLE}
            className="mt-3 w-full resize-y rounded-2xl border border-parchment bg-cream/60 px-4 py-3 text-base leading-7 outline-none ring-crimson/30 focus:bg-white focus:ring-2"
          />

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <FilterSelect
              label="Term"
              value={term}
              onChange={setTerm}
              options={[
                { value: "", label: "All terms" },
                ...(meta.terms || []).map((item) => ({ value: item, label: item })),
              ]}
            />
            <FilterSelect
              label="Department"
              value={department}
              onChange={setDepartment}
              options={[
                { value: "", label: "All departments" },
                ...(meta.departments || []).map((d) => ({
                  value: d.code,
                  label: `${d.code} — ${d.name}`,
                })),
              ]}
            />
            <FilterSelect
              label="Level"
              value={level}
              onChange={setLevel}
              options={[
                { value: "", label: "All levels" },
                { value: "undergraduate", label: "Undergraduate" },
                { value: "graduate", label: "Graduate" },
              ]}
            />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={!canSearch}
              className="rounded-full bg-crimson px-6 py-3 text-sm font-semibold text-cream transition hover:bg-crimson-bright disabled:cursor-not-allowed disabled:bg-crimson/40"
            >
              {loading ? "Searching the catalog…" : "Recommend courses"}
            </button>
            <button
              type="button"
              onClick={() => setQuery(EXAMPLE)}
              className="rounded-full border border-crimson/20 px-5 py-3 text-sm font-medium text-crimson hover:bg-cream"
            >
              Use example query
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-6 rounded-2xl border border-crimson/30 bg-white px-5 py-4 text-sm text-crimson">
            {error}
          </div>
        )}

        {loading && <LoadingState />}

        {result && !loading && (
          <section className="mt-10">
            <div className="rounded-3xl bg-crimson-deep px-6 py-6 text-cream md:px-8">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">
                Advisor summary
              </p>
              <p className="font-display mt-2 text-2xl leading-snug md:text-3xl">
                {result.summary}
              </p>
              {(term || department || level) && (
                <p className="mt-3 text-sm text-cream/70">
                  Filters: {[term, departmentLabel, level].filter(Boolean).join(" · ")}
                </p>
              )}
            </div>

            {!result.courses?.length ? (
              <p className="mt-6 text-ink/70">
                No grounded recommendations came back. Broaden the query or clear a
                filter.
              </p>
            ) : (
              <div className="mt-6 grid gap-5">
                {result.courses.map((course) => (
                  <CourseCard key={`${course.code}-${course.term}`} course={course} />
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="border-t border-crimson/10 px-6 py-8 text-center text-xs text-ink/50">
        Built as a retrieval-augmented advisor. Course records come from IU
        Registrar Schedule of Classes research dumps. Not an official IU advising
        tool.
      </footer>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-ink/55">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-2 w-full rounded-xl border border-parchment bg-cream/50 px-3 py-2.5 text-sm font-medium text-ink outline-none focus:ring-2 focus:ring-crimson/30"
      >
        {options.map((option) => (
          <option key={option.value || option.label} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function CourseCard({ course }) {
  const percent = scorePercent(course.score);
  return (
    <article className="overflow-hidden rounded-3xl border border-crimson/10 bg-white shadow-card">
      <div className="grid md:grid-cols-[8px_1fr]">
        <div className="hidden bg-crimson md:block" />
        <div className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-crimson">
                {course.code} · {course.term}
              </p>
              <h3 className="font-display mt-1 text-2xl text-crimson-deep">
                {course.title}
              </h3>
              <p className="mt-1 text-sm text-ink/65">
                {course.department_name || course.department}
                {course.credits ? ` · ${course.credits} cr` : ""}
                {course.level ? ` · ${course.level}` : ""}
              </p>
            </div>
            <div className="min-w-[120px] text-right">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink/45">
                Match
              </p>
              <p className="font-display text-3xl text-crimson">{percent}</p>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-parchment">
                <div
                  className="h-full bg-gold"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          </div>

          {course.reason && (
            <div className="mt-4 rounded-2xl bg-cream px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-crimson/70">
                Why this course
              </p>
              <p className="mt-1 text-sm leading-6 text-ink/85">{course.reason}</p>
            </div>
          )}

          <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink/45">
                Prerequisites
              </dt>
              <dd className="mt-1 text-ink/80">
                {course.prerequisites || "None listed in this dump"}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink/45">
                Meetings
              </dt>
              <dd className="mt-1 text-ink/80">
                {(course.meetings || []).slice(0, 4).join(" · ") || "See catalog"}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </article>
  );
}

function LoadingState() {
  return (
    <div className="mt-8 rounded-3xl border border-dashed border-crimson/20 bg-white/60 px-6 py-10 text-center">
      <p className="font-display text-2xl text-crimson-deep">Retrieving, then reasoning</p>
      <p className="mt-2 text-sm text-ink/60">
        Embedding your query, searching Chroma, and asking the model to explain
        only the retrieved courses.
      </p>
    </div>
  );
}
