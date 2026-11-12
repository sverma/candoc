import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  Clock,
  Download,
  ExternalLink,
  FileText,
  Heart,
  Info,
  LoaderCircle,
  MapPin,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { MobilitySummary } from "./Preferences.jsx";
import "./hiring.css";

const ENGAGEMENTS = [
  "permanent",
  "contract",
  "freelance",
  "consulting",
  "temporary",
  "internship",
  "apprenticeship",
  "volunteer",
];
const STAGES = [
  "invited",
  "applied",
  "reviewing",
  "interviewing",
  "offer",
  "hired",
  "rejected",
  "withdrawn",
  "declined",
];
const TERMINAL = ["hired", "rejected", "withdrawn", "declined"];
const SUPPORT = ["not_specified", "available", "case_by_case", "not_available"];
const PERIODS = ["hour", "day", "week", "month", "year", "project"];
const label = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
const when = (value) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Not specified";
const date = (value) =>
  value
    ? new Date(value).toLocaleDateString(undefined, { dateStyle: "medium" })
    : "Not specified";
const emptyToNull = (value) =>
  value === "" || value === undefined ? null : Number(value);
function safeLink(value) {
  try {
    const url = new URL(value);
    return (
      ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password
    );
  } catch {
    return false;
  }
}
function ErrorNotice({ error, success }) {
  return error || success ? (
    <div
      className={`alert ${error ? "error" : "success"}`}
      role={error ? "alert" : "status"}
    >
      <Info size={17} />
      <span>{error || success}</span>
    </div>
  ) : null;
}
function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spin" size={21} />
      Loading your workspace…
    </div>
  );
}
function Empty({ title, children, action }) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <BriefcaseBusiness size={28} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
function Header({
  kicker = "HIRING, WITH CONTEXT",
  title,
  children,
  description,
}) {
  return (
    <div className="page-header">
      <div>
        <span className="section-kicker">{kicker}</span>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </div>
  );
}
function Field({ label: caption, hint, ...props }) {
  return (
    <label className="field">
      <span>{caption}</span>
      <input {...props} />
      {hint && <small>{hint}</small>}
    </label>
  );
}
function Textarea({ label: caption, hint, ...props }) {
  return (
    <label className="field">
      <span>{caption}</span>
      <textarea {...props} />
      {hint && <small>{hint}</small>}
    </label>
  );
}
function Select({ label: caption, options, ...props }) {
  return (
    <label className="field">
      <span>{caption}</span>
      <select {...props}>
        {options.map((item) => {
          const value =
            typeof item === "string" ? item : (item.value ?? item.code);
          return (
            <option key={value} value={value}>
              {typeof item === "string"
                ? label(item)
                : (item.label ?? item.name)}
            </option>
          );
        })}
      </select>
    </label>
  );
}
function MultiSelect({ label: caption, options, value, onChange, hint }) {
  return (
    <label className="field">
      <span>{caption}</span>
      <select
        multiple
        value={value || []}
        onChange={(e) =>
          onChange(
            Array.from(e.target.selectedOptions, (option) => option.value),
          )
        }
      >
        {options.map((item) => (
          <option value={item.code ?? item.value} key={item.code ?? item.value}>
            {item.name ?? item.label}
          </option>
        ))}
      </select>
      <small>
        {hint ||
          "Select multiple with Ctrl or Command. Leave empty for no stated preference."}
      </small>
    </label>
  );
}
function Dialog({ title, close, children }) {
  const ref = useRef();
  useEffect(() => {
    const before = document.activeElement;
    ref.current?.focus();
    const key = (e) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const nodes = ref.current?.querySelectorAll(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = "";
      before?.focus?.();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && close()}
    >
      <section
        className="modal hiring-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={ref}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button
            type="button"
            className="icon-button"
            onClick={close}
            aria-label="Close dialog"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
function useResource(api, path) {
  const [resource, setResource] = useState({
    path: null,
    data: null,
    error: "",
    loading: true,
  });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let alive = true;
    setResource((previous) => ({
      path,
      data: previous.path === path ? previous.data : null,
      error: "",
      loading: true,
    }));
    api(path)
      .then((result) => {
        if (alive)
          setResource({ path, data: result, error: "", loading: false });
      })
      .catch((e) => {
        if (alive)
          setResource((previous) => ({
            path,
            data: previous.path === path ? previous.data : null,
            error: e.message,
            loading: false,
          }));
      });
    return () => {
      alive = false;
    };
  }, [api, path, revision]);
  // Route identity is checked during render, before the fetching effect runs.
  // Same-resource refreshes may retain data; another record can never borrow it.
  const current = resource.path === path;
  const reload = useCallback(() => setRevision((n) => n + 1), []);
  return {
    data: current ? resource.data : null,
    error: current ? resource.error : "",
    loading: !current || resource.loading,
    reload,
    setData: (data) => setResource((previous) => ({ ...previous, path, data })),
  };
}
function useCatalogs(api) {
  const { data } = useResource(api, "/hiring/catalogs");
  return data || { countries: [], regions: [], currencies: [] };
}
function Badge({ value }) {
  return (
    <span
      className={`badge ${["published", "accepted", "hired", "completed"].includes(value) ? "green" : ["pending", "invited", "offer", "sent"].includes(value) ? "amber" : "neutral"}`}
    >
      {label(value)}
    </span>
  );
}
function payText(item) {
  const min = item.compensation_min,
    max = item.compensation_max;
  if (min == null && max == null) return "Compensation not specified";
  const value = (n) =>
    new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n);
  return `${item.currency || ""} ${min != null && max != null ? value(min) + " – " + value(max) : min != null ? "from " + value(min) : "up to " + value(max)} / ${label(item.pay_period || "year").toLowerCase()}`.trim();
}
function JobFacts({ job }) {
  return (
    <div className="hiring-facts">
      <span>
        <BriefcaseBusiness size={14} />
        {label(job.engagement_type)} · {label(job.time_commitment)}
      </span>
      <span>
        <MapPin size={14} />
        {label(job.work_mode)}
        {job.city ? ` · ${job.city}` : ""}
        {job.country_codes?.length ? ` · ${job.country_codes.join(", ")}` : ""}
        {job.region_codes?.length ? ` · ${job.region_codes.join(", ")}` : ""}
      </span>
      <span>{payText(job)}</span>
      {job.duration_months && (
        <span>
          <Clock size={14} />
          {job.duration_months} month duration
        </span>
      )}
      {job.hours_per_week && <span>{job.hours_per_week} hours / week</span>}
    </div>
  );
}
function JobCard({ job, user, onSave, saving, owned }) {
  return (
    <article className="panel hiring-job-card">
      <div className="hiring-job-top">
        <span className="hiring-company-icon">
          <BriefcaseBusiness size={23} />
        </span>
        <div>
          <span className="section-kicker">
            {job.company_name || job.company?.name || "Company"}
          </span>
          <Link to={`/jobs/${job.id}`}>
            <h2>{job.title}</h2>
          </Link>
        </div>
        {owned ? (
          <Badge value={job.status} />
        ) : (
          user?.role === "candidate" && (
            <button
              className={`icon-button hiring-save ${job.saved ? "saved" : ""}`}
              aria-label={job.saved ? "Unsave role" : "Save role"}
              onClick={() => onSave(job)}
              disabled={saving === job.id}
            >
              <Heart size={19} fill={job.saved ? "currentColor" : "none"} />
            </button>
          )
        )}
      </div>
      <JobFacts job={job} />
      <p className="hiring-excerpt">
        {job.description?.slice(0, 230)}
        {job.description?.length > 230 ? "…" : ""}
      </p>
      <div className="chips">
        {job.skills?.slice(0, 8).map((skill) => (
          <span key={skill}>{skill}</span>
        ))}
      </div>
      <div className="hiring-job-bottom">
        <span>
          <ShieldCheck size={14} />
          Visa: {label(job.visa_sponsorship)} · Relocation:{" "}
          {label(job.relocation_support)}
        </span>
        <div>
          {owned && (
            <>
              <Link className="text-link" to={`/app/jobs/${job.id}/edit`}>
                Edit role
              </Link>
              <Link
                className="text-link"
                to={`/app/applications?job_id=${job.id}`}
              >
                {job.application_count ?? 0} applications
              </Link>
            </>
          )}
          <Link className="button outline small" to={`/jobs/${job.id}`}>
            {owned ? "Manage role" : "View role"}
            <ArrowUpRight size={14} />
          </Link>
        </div>
      </div>
    </article>
  );
}

export function JobsPage({ api, user }) {
  const catalogs = useCatalogs(api),
    location = useLocation(),
    company = user?.role === "company" && location.pathname.startsWith("/app");
  const [filters, setFilters] = useState({
    search: "",
    engagement_type: "",
    work_mode: "",
    country: "",
    region: "",
    visa_sponsorship: "",
    relocation_support: "",
    status: "",
    saved: new URLSearchParams(location.search).get("saved") === "true",
  });
  const [debounced, setDebounced] = useState(""),
    [offset, setOffset] = useState(0),
    [expanded, setExpanded] = useState(false),
    [error, setError] = useState(""),
    [saving, setSaving] = useState("");
  useEffect(() => {
    const timeout = setTimeout(() => setDebounced(filters.search), 250);
    return () => clearTimeout(timeout);
  }, [filters.search]);
  const query = new URLSearchParams({ limit: "20", offset: String(offset) });
  Object.entries({ ...filters, search: debounced }).forEach(([key, value]) => {
    if (value !== "" && value !== false) query.set(key, String(value));
  });
  if (company) query.set("mine", "true");
  const resource = useResource(api, "/hiring/jobs?" + query.toString());
  const jobs = resource.data?.jobs || [];
  const change = (e) => {
    setOffset(0);
    setFilters({
      ...filters,
      [e.target.name]:
        e.target.type === "checkbox" ? e.target.checked : e.target.value,
    });
  };
  async function save(job) {
    setSaving(job.id);
    setError("");
    try {
      await api(`/hiring/jobs/${job.id}/save`, {
        method: "PUT",
        body: { saved: !job.saved },
      });
      resource.reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving("");
    }
  }
  return (
    <div className="hiring-page">
      <Header
        title={
          company
            ? "Roles with a real purpose."
            : "Find work that fits your next chapter."
        }
        description={
          company
            ? "Publish clear roles, invite people through their work, and manage every conversation."
            : "Explore permanent roles, projects, flexible work, and everything in between."
        }
      >
        {company && (
          <Link to="/app/jobs/new" className="button dark">
            <Plus size={16} />
            Create role
          </Link>
        )}
      </Header>
      <ErrorNotice error={error || resource.error} />
      <div className="directory-toolbar">
        <label className="search-input">
          <Search size={18} />
          <input
            aria-label="Search roles"
            placeholder="Search roles, skills, companies…"
            name="search"
            value={filters.search}
            onChange={change}
          />
        </label>
        <button
          className="button outline"
          onClick={() => setExpanded(!expanded)}
        >
          <Settings size={16} />
          Filters
        </button>
        {user?.role === "candidate" && (
          <label className="hiring-checkbox">
            <input
              name="saved"
              type="checkbox"
              checked={filters.saved}
              onChange={change}
            />
            Saved roles
          </label>
        )}
      </div>
      {expanded && (
        <div className="hiring-filter-grid">
          <Select
            label="Engagement"
            name="engagement_type"
            value={filters.engagement_type}
            onChange={change}
            options={[
              { value: "", label: "Any engagement" },
              ...ENGAGEMENTS.map((v) => ({ value: v, label: label(v) })),
            ]}
          />
          <Select
            label="Work arrangement"
            name="work_mode"
            value={filters.work_mode}
            onChange={change}
            options={[
              { value: "", label: "Any arrangement" },
              ...["remote", "hybrid", "onsite"].map((v) => ({
                value: v,
                label: label(v),
              })),
            ]}
          />
          <Select
            label="Country"
            name="country"
            value={filters.country}
            onChange={change}
            options={[
              { value: "", label: "Any country" },
              ...catalogs.countries.map((v) => ({
                value: v.code,
                label: v.name,
              })),
            ]}
          />
          <Select
            label="Region"
            name="region"
            value={filters.region}
            onChange={change}
            options={[
              { value: "", label: "Any region" },
              ...catalogs.regions.map((v) => ({
                value: v.code,
                label: v.name,
              })),
            ]}
          />
          <Select
            label="Visa sponsorship"
            name="visa_sponsorship"
            value={filters.visa_sponsorship}
            onChange={change}
            options={[
              { value: "", label: "Any policy" },
              ...SUPPORT.map((v) => ({ value: v, label: label(v) })),
            ]}
          />
          <Select
            label="Relocation"
            name="relocation_support"
            value={filters.relocation_support}
            onChange={change}
            options={[
              { value: "", label: "Any policy" },
              ...SUPPORT.map((v) => ({ value: v, label: label(v) })),
            ]}
          />
          {company && (
            <Select
              label="Role status"
              name="status"
              value={filters.status}
              onChange={change}
              options={[
                { value: "", label: "All my roles" },
                ...["draft", "published", "paused", "closed"].map((v) => ({
                  value: v,
                  label: label(v),
                })),
              ]}
            />
          )}
          <button
            className="text-link"
            onClick={() => {
              setOffset(0);
              setFilters({
                search: "",
                engagement_type: "",
                work_mode: "",
                country: "",
                region: "",
                visa_sponsorship: "",
                relocation_support: "",
                status: "",
                saved: false,
              });
            }}
          >
            Clear filters
          </button>
        </div>
      )}
      <div className="directory-info">
        <span>{resource.data?.total ?? 0} roles</span>
        <span>
          <Info size={14} />
          Work rights and nationality are never ranking inputs
        </span>
      </div>
      {resource.loading ? (
        <Loading />
      ) : jobs.length ? (
        <div>
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              user={user}
              owned={company}
              onSave={save}
              saving={saving}
            />
          ))}
          <div className="hiring-pagination">
            <button
              className="button outline small"
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              Previous
            </button>
            <span>Page {Math.floor(offset / 20) + 1}</span>
            <button
              className="button outline small"
              disabled={offset + 20 >= (resource.data?.total || 0)}
              onClick={() => setOffset(offset + 20)}
            >
              Next
            </button>
          </div>
        </div>
      ) : (
        !resource.error && (
          <div className="panel">
            <Empty
              title={
                company
                  ? "Your next teammate starts with a clear role."
                  : "No roles match yet."
              }
              action={
                company ? (
                  <Link to="/app/jobs/new" className="button dark">
                    <Plus size={16} />
                    Create your first role
                  </Link>
                ) : null
              }
            >
              {company
                ? "Draft a role, explain the work and support you can offer, and publish when ready."
                : "Try a broader search or check back as companies publish new opportunities."}
            </Empty>
          </div>
        )
      )}
    </div>
  );
}

export function JobDetail({ api, user }) {
  const { id } = useParams(),
    resource = useResource(api, "/hiring/jobs/" + id),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false),
    [apply, setApply] = useState(false),
    [invite, setInvite] = useState(false),
    [applicationRecord, setApplicationRecord] = useState(null);
  const navigate = useNavigate();
  const application =
    applicationRecord?.jobId === id ? applicationRecord.value : null;
  const job = resource.data?.job,
    owner = job && user?.role === "company" && job.company_id === user.id;
  useEffect(() => {
    let alive = true;
    setApply(false);
    setInvite(false);
    if (user)
      api("/hiring/applications?job_id=" + encodeURIComponent(id))
        .then((d) => {
          if (alive)
            setApplicationRecord({
              jobId: id,
              value: d.applications?.[0] || null,
            });
        })
        .catch(() => {});
    return () => {
      alive = false;
    };
  }, [api, id, user]);
  async function status(value) {
    setBusy(true);
    setError("");
    try {
      await api("/hiring/jobs/" + id, {
        method: "PATCH",
        body: { status: value },
      });
      resource.reload();
      setSuccess("Role status updated.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (resource.loading) return <Loading />;
  if (!job)
    return (
      <ErrorNotice error={resource.error || "This role is unavailable."} />
    );
  return (
    <div className="hiring-page">
      <Link className="back-link" to={owner ? "/app/jobs" : "/jobs"}>
        <ArrowLeft size={15} />
        Back to roles
      </Link>
      <Header
        kicker={job.company_name || job.company?.name}
        title={job.title}
        description={job.company?.industry}
      >
        {owner ? (
          <>
            <Link to={`/app/jobs/${id}/edit`} className="button outline">
              Edit role
            </Link>
            <Badge value={job.status} />
          </>
        ) : (
          <Badge value={job.status} />
        )}
      </Header>
      <ErrorNotice error={error || resource.error} success={success} />
      <div className="hiring-detail-grid">
        <main>
          <section className="panel">
            <div className="form-body">
              <JobFacts job={job} />
              <h2 className="hiring-section-title">The work, in context.</h2>
              <p className="hiring-long-text">{job.description}</p>
              {job.skills?.length > 0 && (
                <>
                  <h3 className="hiring-section-title">Skills for this role</h3>
                  <div className="chips">
                    {job.skills.map((s) => (
                      <span key={s}>{s}</span>
                    ))}
                  </div>
                </>
              )}
              <div className="hiring-support">
                <div>
                  <h3>Visa sponsorship</h3>
                  <Badge value={job.visa_sponsorship} />
                  <p>
                    {job.visa_details ||
                      "Ask the hiring team for further details."}
                  </p>
                </div>
                <div>
                  <h3>Relocation support</h3>
                  <Badge value={job.relocation_support} />
                  <p>
                    {job.relocation_details ||
                      "Ask the hiring team for further details."}
                  </p>
                </div>
              </div>
              <p className="small-muted">
                Company policies are stated by the hiring team. They do not
                establish legal eligibility. Scope and individual requirements
                need a human conversation.
              </p>
            </div>
          </section>
          {job.company && (
            <section className="panel">
              <div className="panel-heading">
                <h2>About {job.company.name || job.company_name}</h2>
              </div>
              <div className="form-body">
                <p className="hiring-long-text">
                  {job.company.about ||
                    "The company is still adding its story."}
                </p>
                <div className="hiring-facts">
                  <span>{job.company.industry}</span>
                  <span>{job.company.size}</span>
                  <span>{job.company.headquarters}</span>
                </div>
                {safeLink(job.company.website) && (
                  <a
                    className="text-link"
                    href={job.company.website}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Company website
                    <ExternalLink size={14} />
                  </a>
                )}
                <p className="small-muted">
                  Email verification confirms control of an email address; it
                  does not verify a company’s identity.
                </p>
              </div>
            </section>
          )}
        </main>
        <aside className="hiring-sticky">
          <section className="panel">
            <div className="form-body">
              <BriefcaseBusiness className="hiring-side-icon" size={29} />
              <h3>
                {owner
                  ? "Make the next move."
                  : "A conversation worth starting?"}
              </h3>
              <p className="small-muted">
                {owner
                  ? "Find someone through their work and invite them to this role."
                  : "Send the team a short introduction. Your original resume stays private."}
              </p>
              {owner ? (
                <>
                  <button
                    className="button dark full"
                    disabled={busy || job.status === "closed"}
                    aria-describedby={
                      job.status !== "published"
                        ? "role-invitation-help"
                        : undefined
                    }
                    onClick={() => setInvite(true)}
                  >
                    <Users size={16} />
                    Invite a candidate
                  </button>
                  {job.status !== "published" && (
                    <p id="role-invitation-help" className="small-muted">
                      {job.status === "closed"
                        ? "This role is closed. Create a new role to send invitations."
                        : "Publish this role before inviting candidates. The invitation dialog will guide you."}
                    </p>
                  )}
                  <Link
                    className="button outline full"
                    to={`/app/applications?job_id=${id}`}
                  >
                    View applications
                  </Link>
                  <div className="hiring-status-controls">
                    {!user.email_verified && (
                      <p className="small-muted">
                        <Link to="/app/settings">Verify your email</Link> before
                        publishing.
                      </p>
                    )}
                    <Select
                      label="Role visibility"
                      value={job.status}
                      disabled={busy}
                      onChange={(e) => status(e.target.value)}
                      options={["draft", "published", "paused", "closed"]}
                    />
                  </div>
                </>
              ) : user?.role === "candidate" ? (
                application ? (
                  <>
                    <Badge value={application.stage} />
                    <Link
                      className="button dark full"
                      to={`/app/applications/${application.id}`}
                    >
                      Open your application
                      <ArrowRight size={15} />
                    </Link>
                  </>
                ) : (
                  <>
                    <button
                      className="button dark full"
                      disabled={job.status !== "published"}
                      onClick={() => setApply(true)}
                    >
                      Apply to this role
                      <ArrowUpRight size={16} />
                    </button>
                    <button
                      className="button outline full"
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await api("/hiring/jobs/" + id + "/save", {
                            method: "PUT",
                            body: { saved: !job.saved },
                          });
                          resource.reload();
                        } catch (e) {
                          setError(e.message);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      <Heart
                        size={16}
                        fill={job.saved ? "currentColor" : "none"}
                      />
                      {job.saved ? "Saved role" : "Save for later"}
                    </button>
                  </>
                )
              ) : !user ? (
                <>
                  <Link
                    className="button dark full"
                    to={`/login?next=${encodeURIComponent("/jobs/" + id)}`}
                  >
                    Log in to apply
                    <ArrowRight size={15} />
                  </Link>
                  <Link
                    className="aside-link"
                    to={`/signup?next=${encodeURIComponent("/jobs/" + id)}`}
                  >
                    Create a candidate account
                  </Link>
                </>
              ) : (
                <p className="small-muted">
                  Candidate accounts can apply. Explore your own roles from your
                  workspace.
                </p>
              )}
            </div>
          </section>
        </aside>
      </div>
      {apply && (
        <ApplyDialog
          api={api}
          job={job}
          user={user}
          close={() => setApply(false)}
          done={(item) => navigate("/app/applications/" + item.id)}
        />
      )}{" "}
      {invite && (
        <InviteDialog
          api={api}
          job={job}
          user={user}
          onPublished={(publishedJob) =>
            resource.setData({ job: publishedJob })
          }
          close={() => setInvite(false)}
          done={(item) => navigate("/app/applications/" + item.id)}
        />
      )}
    </div>
  );
}
function ApplyDialog({ api, job, user, close, done }) {
  const [message, setMessage] = useState(""),
    [share, setShare] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const d = await api("/hiring/jobs/" + job.id + "/apply", {
        method: "POST",
        body: { message, share_contact: share },
      });
      done(d.application);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog title="Put your work in the conversation." close={close}>
      <p className="modal-description">
        Introduce yourself for {job.title} at {job.company_name}. Applying
        shares your professional profile with this hiring team for this
        application.
      </p>
      <form onSubmit={submit}>
        <ErrorNotice error={error} />
        <Textarea
          label="Your introduction"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          minLength={20}
          maxLength={5000}
          rows={6}
          placeholder="What interests you in this work? What relevant experience would you bring?"
        />
        <label className="hiring-checkbox">
          <input
            type="checkbox"
            checked={share}
            onChange={(e) => setShare(e.target.checked)}
          />
          Share my account email with this hiring team (optional)
        </label>
        <p className="small-muted">
          You can message in Candoc without sharing your email. You can revoke
          future contact visibility later.
          {!user.email_verified && (
            <>
              {" "}
              <Link to="/app/settings">Verify your account email</Link> before
              choosing to share it.
            </>
          )}
        </p>
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancel
          </button>
          <button className="button dark" disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Send size={16} />
            )}
            Send application
          </button>
        </div>
      </form>
    </Dialog>
  );
}
function InviteDialog({ api, job, user, onPublished, close, done }) {
  const [search, setSearch] = useState(""),
    [candidates, setCandidates] = useState([]),
    [candidate, setCandidate] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const ready = job.status === "published";
  const selectedCandidate = candidates.some((item) => item.id === candidate);
  useEffect(() => {
    if (!ready) return;
    let active = true;
    setLoading(true);
    setCandidates([]);
    setCandidate("");
    setError("");
    const timeout = setTimeout(
      () =>
        api("/candidates?search=" + encodeURIComponent(search))
          .then((d) => {
            if (active) setCandidates(d.candidates || []);
          })
          .catch((e) => {
            if (active) setError(e.message);
          })
          .finally(() => {
            if (active) setLoading(false);
          }),
      250,
    );
    return () => {
      active = false;
      clearTimeout(timeout);
    };
  }, [search, api, ready, job.id]);
  async function publish() {
    setBusy(true);
    setError("");
    try {
      const result = await api("/hiring/jobs/" + job.id, {
        method: "PATCH",
        body: { status: "published" },
      });
      onPublished(result.job);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function submit(e) {
    e.preventDefault();
    if (!ready || loading || !selectedCandidate || busy) return;
    setBusy(true);
    setError("");
    try {
      const d = await api("/hiring/jobs/" + job.id + "/invite", {
        method: "POST",
        body: { candidate_id: candidate, message },
      });
      done(d.application);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog title="Invite someone through their work." close={close}>
      <p className="modal-description">
        A personal invitation to {job.title}. The candidate decides whether to
        start a conversation.
      </p>
      <ErrorNotice error={error} />
      {!ready ? (
        <div>
          <p className="small-muted">
            This role is {label(job.status).toLowerCase()}. Publish it first so
            candidates can review the work and terms before responding.
            Publishing makes the role public; it does not send an invitation.
          </p>
          {!user.email_verified && (
            <p className="small-muted">
              Verify your company account email in Account &amp; privacy before
              publishing. Then return here to continue.
            </p>
          )}
          <div className="modal-actions">
            <button
              type="button"
              className="button outline"
              onClick={close}
              disabled={busy}
            >
              Cancel
            </button>
            {job.status === "closed" ? (
              <Link className="button dark" to="/app/jobs/new">
                Create a new role
              </Link>
            ) : !user.email_verified ? (
              <Link className="button dark" to="/app/settings">
                Verify your email
              </Link>
            ) : (
              <button
                type="button"
                className="button dark"
                onClick={publish}
                disabled={busy}
              >
                {busy && <LoaderCircle className="spin" size={16} />}
                Publish role
              </button>
            )}
          </div>
        </div>
      ) : (
        <form onSubmit={submit}>
          <Field
            label="Find a discoverable candidate"
            autoFocus
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCandidate("");
            }}
            placeholder="Name, skill, or role"
          />
          <Select
            label="Candidate"
            value={candidate}
            onChange={(e) => setCandidate(e.target.value)}
            disabled={loading || busy}
            required
            options={[
              { value: "", label: "Choose a candidate" },
              ...candidates.map((c) => ({
                value: c.id,
                label: `${c.name} · ${c.headline || "Professional profile"}`,
              })),
            ]}
          />
          {loading ? (
            <p className="small-muted" role="status">
              Loading discoverable candidates…
            </p>
          ) : (
            !error &&
            !candidates.length && (
              <p className="small-muted">
                No discoverable profiles match. Try a broader search.
              </p>
            )
          )}
          <Textarea
            label="Your invitation"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
            minLength={20}
            maxLength={5000}
            rows={5}
            placeholder="What stood out about their work? Why this role?"
          />
          <div className="modal-actions">
            <button
              type="button"
              className="button outline"
              onClick={close}
              disabled={busy}
            >
              Cancel
            </button>
            <button
              className="button dark"
              disabled={busy || loading || !selectedCandidate}
            >
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Send size={16} />
              )}
              Send invitation
            </button>
          </div>
        </form>
      )}
    </Dialog>
  );
}

const jobDefaults = {
  title: "",
  description: "",
  engagement_type: "permanent",
  time_commitment: "full_time",
  work_mode: "remote",
  country_codes: [],
  region_codes: [],
  city: "",
  compensation_min: "",
  compensation_max: "",
  currency: "",
  pay_period: "year",
  duration_months: "",
  hours_per_week: "",
  skills: "",
  experience_level: "any",
  visa_sponsorship: "not_specified",
  visa_details: "",
  relocation_support: "not_specified",
  relocation_details: "",
  status: "draft",
};
export function RoleEditor({ api, user }) {
  const { id } = useParams(),
    catalogs = useCatalogs(api),
    navigate = useNavigate(),
    [form, setForm] = useState(null),
    [formIdentity, setFormIdentity] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    setForm(null);
    setFormIdentity(null);
    setError("");
    if (id)
      api("/hiring/jobs/" + id)
        .then((d) => {
          if (!alive) return;
          const values = { ...jobDefaults };
          Object.keys(values).forEach((k) => {
            values[k] = d.job[k] ?? jobDefaults[k];
          });
          values.skills = (d.job.skills || []).join(", ");
          setForm(values);
          setFormIdentity(id);
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    else {
      setForm({ ...jobDefaults });
      setFormIdentity("new");
    }
    return () => {
      alive = false;
    };
  }, [id, api]);
  if (user?.role !== "company")
    return <ErrorNotice error="Company accounts manage roles." />;
  if (!form || formIdentity !== (id || "new"))
    return error ? <ErrorNotice error={error} /> : <Loading />;
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {
        ...form,
        compensation_min: emptyToNull(form.compensation_min),
        compensation_max: emptyToNull(form.compensation_max),
        duration_months: emptyToNull(form.duration_months),
        hours_per_week: emptyToNull(form.hours_per_week),
        skills: form.skills
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),
      };
      const d = await api("/hiring/jobs" + (id ? "/" + id : ""), {
        method: id ? "PATCH" : "POST",
        body,
      });
      navigate("/jobs/" + d.job.id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="hiring-page">
      <Link className="back-link" to="/app/jobs">
        <ArrowLeft size={15} />
        Back to your roles
      </Link>
      <Header
        title={id ? "Make the work clear." : "A good role starts with context."}
        description="A real role, transparent terms, and a thoughtful first conversation."
      />
      <ErrorNotice error={error} />
      <form onSubmit={save}>
        <section className="panel">
          <div className="panel-heading">
            <h2>The role</h2>
          </div>
          <div className="form-body">
            <Field
              label="Role title"
              name="title"
              value={form.title}
              onChange={change}
              required
              maxLength={160}
            />
            <Textarea
              label="The work, responsibilities, and expectations"
              name="description"
              value={form.description}
              onChange={change}
              required
              minLength={20}
              maxLength={30000}
              rows={8}
            />
            <div className="hiring-form-grid">
              <Select
                label="Engagement type"
                name="engagement_type"
                value={form.engagement_type}
                onChange={change}
                options={ENGAGEMENTS}
              />
              <Select
                label="Time commitment"
                name="time_commitment"
                value={form.time_commitment}
                onChange={change}
                options={["full_time", "part_time", "flexible"]}
              />
              <Select
                label="Work arrangement"
                name="work_mode"
                value={form.work_mode}
                onChange={change}
                options={["remote", "hybrid", "onsite"]}
              />
              <Select
                label="Experience level"
                name="experience_level"
                value={form.experience_level}
                onChange={change}
                options={[
                  "any",
                  "entry",
                  "junior",
                  "mid",
                  "senior",
                  "lead",
                  "executive",
                ]}
              />
            </div>
            <Field
              label="Skills (comma separated)"
              name="skills"
              value={form.skills}
              onChange={change}
              maxLength={2500}
            />
            <div className="hiring-form-grid">
              <Field
                label="Duration in months (optional)"
                type="number"
                name="duration_months"
                value={form.duration_months}
                onChange={change}
                min="0.25"
                step="0.25"
              />
              <Field
                label="Hours per week (optional)"
                type="number"
                name="hours_per_week"
                value={form.hours_per_week}
                onChange={change}
                min="1"
                max="168"
                step="0.5"
              />
            </div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Location & support</h2>
          </div>
          <div className="form-body">
            <Field
              label="City or location description"
              name="city"
              value={form.city}
              onChange={change}
              maxLength={150}
            />
            <div className="hiring-form-grid">
              <MultiSelect
                label="Eligible work locations — countries"
                options={catalogs.countries}
                value={form.country_codes}
                onChange={(v) => setForm({ ...form, country_codes: v })}
                hint="Publish onsite or hybrid roles with at least one country. Location scope is not a legal work entitlement."
              />
              <MultiSelect
                label="Geographic regions"
                options={catalogs.regions}
                value={form.region_codes}
                onChange={(v) => setForm({ ...form, region_codes: v })}
              />
              <Select
                label="Visa sponsorship"
                name="visa_sponsorship"
                value={form.visa_sponsorship}
                onChange={change}
                options={SUPPORT}
              />
              <Select
                label="Relocation support"
                name="relocation_support"
                value={form.relocation_support}
                onChange={change}
                options={SUPPORT}
              />
              <Textarea
                label="Visa policy details"
                name="visa_details"
                value={form.visa_details}
                onChange={change}
                rows={3}
                maxLength={3000}
              />
              <Textarea
                label="Relocation details"
                name="relocation_details"
                value={form.relocation_details}
                onChange={change}
                rows={3}
                maxLength={3000}
              />
            </div>
            <p className="small-muted">
              Describe what the company can support. Legal eligibility is
              candidate-declared and requires a human review; it is never
              inferred from nationality.
            </p>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Compensation & publication</h2>
          </div>
          <div className="form-body">
            <CompensationFields
              catalogs={catalogs}
              form={form}
              change={change}
            />
            {!user.email_verified && (
              <div className="hiring-verified-note">
                Save a draft anytime.{" "}
                <Link to="/app/settings">Verify your account email</Link> before
                publishing a role. Email verification confirms email control,
                not company identity.
              </div>
            )}
            <Select
              label="Publication status"
              name="status"
              value={form.status}
              onChange={change}
              options={["draft", "published", "paused", "closed"]}
            />
            <p className="small-muted">
              Only published roles are public and accept new applications or
              invitations. Paused and closed roles retain existing application
              conversations.
            </p>
            <div className="hiring-form-actions">
              <Link to="/app/jobs" className="button outline">
                Cancel
              </Link>
              <button className="button dark" disabled={busy}>
                {busy ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <Check size={16} />
                )}
                Save role
              </button>
            </div>
          </div>
        </section>
      </form>
    </div>
  );
}
function CompensationFields({ catalogs, form, change }) {
  return (
    <div className="hiring-form-grid">
      <Field
        label="Minimum compensation (optional)"
        name="compensation_min"
        type="number"
        min="0"
        step="0.01"
        value={form.compensation_min ?? ""}
        onChange={change}
      />
      <Field
        label="Maximum compensation (optional)"
        name="compensation_max"
        type="number"
        min="0"
        step="0.01"
        value={form.compensation_max ?? ""}
        onChange={change}
      />
      <Select
        label="Currency"
        name="currency"
        value={form.currency}
        onChange={change}
        options={[
          { value: "", label: "Choose a currency" },
          ...catalogs.currencies.map((x) => ({
            value: x.code,
            label: `${x.code} · ${x.name}`,
          })),
        ]}
      />
      <Select
        label="Pay period"
        name="pay_period"
        value={form.pay_period}
        onChange={change}
        options={PERIODS}
      />
    </div>
  );
}

export function CompanyProfile({ api, user }) {
  const [form, setForm] = useState(null),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/hiring/company")
      .then((d) => {
        const c = d.company || {};
        setForm({
          name: c.name || user.company_name || "",
          website: c.website || "",
          industry: c.industry || "",
          size: c.size || "",
          headquarters: c.headquarters || "",
          about: c.about || "",
        });
      })
      .catch((e) => setError(e.message));
  }, [api, user]);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function save(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await api("/hiring/company", { method: "PUT", body: form });
      setSuccess("Company profile saved.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="hiring-page">
      <Header
        title="The team behind the opportunity."
        description="Give candidates a clear picture of your company and the work you do."
      />
      <ErrorNotice error={error} success={success} />
      {form ? (
        <form onSubmit={save} className="panel">
          <div className="form-body">
            <Field
              label="Company name"
              name="name"
              value={form.name}
              onChange={change}
              required
              maxLength={150}
            />
            <Field
              label="Company website"
              name="website"
              type="url"
              value={form.website}
              onChange={change}
              maxLength={350}
            />
            <div className="hiring-form-grid">
              <Field
                label="Industry"
                name="industry"
                value={form.industry}
                onChange={change}
                maxLength={100}
              />
              <Field
                label="Company size"
                name="size"
                value={form.size}
                onChange={change}
                maxLength={80}
                placeholder="e.g. 11–50 people"
              />
            </div>
            <Field
              label="Headquarters"
              name="headquarters"
              value={form.headquarters}
              onChange={change}
              maxLength={150}
            />
            <Textarea
              label="About your company"
              name="about"
              value={form.about}
              onChange={change}
              rows={7}
              maxLength={10000}
            />
            <p className="small-muted">
              Your company profile is public with published roles. Email control
              verification does not establish company identity.
            </p>
            <div className="hiring-form-actions">
              <button className="button dark" disabled={busy}>
                {busy ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <Check size={16} />
                )}
                Save company profile
              </button>
            </div>
          </div>
        </form>
      ) : (
        !error && <Loading />
      )}
    </div>
  );
}

function ApplicationCard({ item, user }) {
  return (
    <Link
      className="hiring-application-row"
      to={`/app/applications/${item.id}`}
    >
      <span className="hiring-company-icon">
        <BriefcaseBusiness size={21} />
      </span>
      <div>
        <h3>
          {user.role === "company" ? item.candidate_name : item.company_name}
        </h3>
        <p>{item.job_title || item.title || item.job?.title}</p>
        <small>
          {item.origin === "invitation" ? "Company invitation" : "Application"}{" "}
          · {date(item.created_at)}
        </small>
      </div>
      <Badge value={item.stage} />
      <ArrowUpRight size={18} />
    </Link>
  );
}
export function HiringDashboard({ api, user }) {
  const resource = useResource(api, "/hiring/dashboard"),
    data = resource.data;
  const counts = data?.counts || {},
    labels = {
      jobs: "Your roles",
      published_jobs: "Published roles",
      applications: "Applications & invitations",
      unread_notifications: "Unread updates",
      saved_jobs: "Saved roles",
      upcoming_interviews: "Upcoming interviews",
    };
  return (
    <div className="hiring-page">
      <Header
        kicker="YOUR NEXT CHAPTER"
        title={`Hello, ${user.name?.split(" ")[0] || "there"}.`}
        description={
          user.role === "company"
            ? "Clear roles. Thoughtful introductions. Every conversation, in one place."
            : "Your opportunities, conversations, and next steps, in one place."
        }
      >
        <Link
          className="button dark"
          to={user.role === "company" ? "/app/jobs/new" : "/app/jobs"}
        >
          {user.role === "company" ? <Plus size={16} /> : <Search size={16} />}
          {user.role === "company" ? "Create a role" : "Explore roles"}
        </Link>
      </Header>
      <ErrorNotice error={resource.error} />
      {resource.loading ? (
        <Loading />
      ) : (
        data && (
          <>
            <div className="hiring-dashboard-banner">
              <span>
                <Heart size={29} />
              </span>
              <div>
                <h2>
                  {user.role === "company"
                    ? "Good teams start with good conversations."
                    : "Let the right work find its way to you."}
                </h2>
                <p>
                  {user.role === "company"
                    ? "Publish a role, invite candidates through their work, and keep every decision human."
                    : "Set your preferences, tell your professional story, and choose the opportunities you want to explore."}
                </p>
                <Link
                  className="text-link"
                  to={
                    user.role === "company" ? "/app/talent" : "/app/preferences"
                  }
                >
                  {user.role === "company"
                    ? "Discover people"
                    : "Set work preferences"}
                  <ArrowRight size={15} />
                </Link>
              </div>
            </div>
            <div className="hiring-metrics">
              {Object.entries(counts)
                .filter(([key]) =>
                  user.role === "company"
                    ? !["saved_jobs"].includes(key)
                    : !["jobs", "published_jobs"].includes(key),
                )
                .map(([key, value]) => (
                  <Link
                    key={key}
                    to={
                      key.includes("job")
                        ? key === "saved_jobs"
                          ? "/app/jobs?saved=true"
                          : "/app/jobs"
                        : key === "unread_notifications"
                          ? "/app/notifications"
                          : "/app/applications"
                    }
                    className="panel"
                  >
                    <span>{labels[key] || label(key)}</span>
                    <b>{typeof value === "number" ? value : 0}</b>
                    <ArrowUpRight size={17} />
                  </Link>
                ))}
            </div>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Your hiring journey</h2>
                  <p>Live stages. Every move made by a person.</p>
                </div>
                <Link className="text-link" to="/app/applications">
                  View all
                  <ArrowRight size={14} />
                </Link>
              </div>
              <div className="hiring-pipeline">
                {STAGES.filter(
                  (stage) =>
                    !["declined", "withdrawn", "rejected"].includes(stage),
                ).map((stage) => (
                  <Link key={stage} to={"/app/applications?stage=" + stage}>
                    <span>{label(stage)}</span>
                    <b>{data.pipeline?.[stage] ?? 0}</b>
                  </Link>
                ))}
              </div>
            </section>
            <div className="hiring-dashboard-grid">
              <section className="panel">
                <div className="panel-heading">
                  <h2>Recent conversations</h2>
                </div>
                {data.recent_applications?.length ? (
                  data.recent_applications.map((item) => (
                    <ApplicationCard key={item.id} item={item} user={user} />
                  ))
                ) : (
                  <Empty title="Your next conversation starts here.">
                    Applications and role invitations will appear here as they
                    arrive.
                  </Empty>
                )}
              </section>
              <section className="panel">
                <div className="panel-heading">
                  <h2>
                    <CalendarDays size={18} />
                    Coming up
                  </h2>
                </div>
                {data.upcoming_interviews?.length ? (
                  <div className="hiring-upcoming">
                    {data.upcoming_interviews.map((item) => (
                      <Link
                        key={item.id}
                        to={"/app/applications/" + item.application_id}
                      >
                        <b>{item.job_title || "Interview"}</b>
                        <span>{when(item.starts_at)}</span>
                        <small>
                          {item.duration_minutes} minutes ·{" "}
                          {label(item.rsvp || "pending")}
                        </small>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <Empty title="A little room in your calendar.">
                    Scheduled interviews will appear here. Invitations and RSVPs
                    stay in Candoc.
                  </Empty>
                )}
              </section>
            </div>
          </>
        )
      )}
    </div>
  );
}
export function ApplicationsPage({ api, user }) {
  const location = useLocation(),
    params = new URLSearchParams(location.search),
    [stage, setStage] = useState(params.get("stage") || ""),
    jobId = params.get("job_id") || "";
  const query = new URLSearchParams();
  if (stage) query.set("stage", stage);
  if (jobId) query.set("job_id", jobId);
  const resource = useResource(api, "/hiring/applications?" + query);
  return (
    <div className="hiring-page">
      <Header
        title={
          user.role === "company"
            ? "People, not a pile of resumes."
            : "Your opportunities, in motion."
        }
        description="Applications and invitations share one clear journey, from a first hello to an offer."
      />
      <div className="hiring-application-filters">
        <Select
          label="Stage"
          value={stage}
          onChange={(e) => setStage(e.target.value)}
          options={[
            { value: "", label: "All stages" },
            ...STAGES.map((value) => ({ value, label: label(value) })),
          ]}
        />
        {jobId && (
          <Link className="text-link" to="/app/applications">
            Show all roles
            <X size={13} />
          </Link>
        )}
        <span className="small-muted">
          {resource.data?.applications?.length ?? 0} conversations
        </span>
      </div>
      <ErrorNotice error={resource.error} />
      {resource.loading ? (
        <Loading />
      ) : resource.data?.applications?.length ? (
        <section className="panel">
          {resource.data.applications.map((item) => (
            <ApplicationCard key={item.id} item={item} user={user} />
          ))}
        </section>
      ) : (
        !resource.error && (
          <section className="panel">
            <Empty
              title="A good conversation is a good start."
              action={
                <Link
                  to={user.role === "company" ? "/app/jobs" : "/app/jobs"}
                  className="button dark"
                >
                  {user.role === "company"
                    ? "Manage your roles"
                    : "Explore roles"}
                  <ArrowRight size={15} />
                </Link>
              }
            >
              {user.role === "company"
                ? "Invite a candidate from a published role, or wait for your first application."
                : "Your applications and company invitations will appear here. You choose which doors to open."}
            </Empty>
          </section>
        )
      )}
    </div>
  );
}

export function ApplicationDetail({ api, user }) {
  const { id } = useParams(),
    resource = useResource(api, "/hiring/applications/" + id),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(""),
    [message, setMessage] = useState(""),
    [dialog, setDialog] = useState(null),
    [contact, setContact] = useState(false);
  const company = user.role === "company",
    a = resource.data?.application,
    offers = resource.data?.offers || [],
    interviews = resource.data?.interviews || [],
    messages = resource.data?.messages || [],
    terminal = a && TERMINAL.includes(a.stage);
  useEffect(() => {
    setDialog(null);
    setMessage("");
    setContact(false);
    setError("");
    setSuccess("");
  }, [id]);
  useEffect(() => {
    if (a) setContact(!!a.share_contact);
  }, [a?.share_contact, a?.id]);
  async function action(path, method, body, key = "action") {
    setBusy(key);
    setError("");
    setSuccess("");
    try {
      const d = await api(path, { method, body });
      resource.reload();
      return d;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setBusy("");
    }
  }
  async function candidateAction(value) {
    const d = await action("/hiring/applications/" + id, "PATCH", {
      action: value,
      ...(value === "accept_invitation" ? { share_contact: contact } : {}),
    });
    if (d) {
      setDialog(null);
      setSuccess("Your response has been recorded.");
    }
  }
  async function send(e) {
    e.preventDefault();
    const d = await action(
      "/hiring/applications/" + id + "/messages",
      "POST",
      { body: message },
      "message",
    );
    if (d) setMessage("");
  }
  if (resource.loading && !resource.data) return <Loading />;
  if (!a)
    return (
      <ErrorNotice
        error={resource.error || "This application is unavailable."}
      />
    );
  return (
    <div className="hiring-page">
      <Link className="back-link" to="/app/applications">
        <ArrowLeft size={15} />
        Back to conversations
      </Link>
      <Header
        kicker={company ? a.candidate_name : a.company_name}
        title={a.job_title || a.title || a.job?.title}
        description={
          a.origin === "invitation"
            ? "This conversation began with a company invitation."
            : "A professional conversation, with the next steps in view."
        }
      >
        <Badge value={a.stage} />
        <Link className="button outline" to={"/jobs/" + a.job_id}>
          View role
          <ArrowUpRight size={14} />
        </Link>
      </Header>
      <ErrorNotice error={error || resource.error} success={success} />
      {!company && a.stage === "invited" && (
        <section className="hiring-invitation-banner">
          <h2>A team wants to meet you.</h2>
          <p>
            {a.company_name} invited you to explore this role. Accepting shares
            your professional profile for this application. It does not accept
            an offer or share your email unless you choose that option.
          </p>
          <label className="hiring-checkbox">
            <input
              type="checkbox"
              checked={contact}
              onChange={(e) => setContact(e.target.checked)}
            />
            Also share my account email (optional)
            {!user.email_verified && (
              <Link to="/app/settings"> · Verify email first</Link>
            )}
          </label>
          <div>
            <button
              className="button outline"
              disabled={!!busy}
              onClick={() => setDialog({ type: "decline_invitation" })}
            >
              Decline invitation
            </button>
            <button
              className="button dark"
              disabled={!!busy}
              onClick={() => setDialog({ type: "accept_invitation" })}
            >
              Accept invitation
              <Check size={16} />
            </button>
          </div>
        </section>
      )}
      <div className="hiring-application-layout">
        <main>
          <section className="panel">
            <div className="panel-heading">
              <h2>
                <MessageSquare size={18} />
                The conversation
              </h2>
              <span className="badge neutral">In Candoc only</span>
            </div>
            <div className="hiring-thread">
              {a.message && (
                <div className="hiring-message initial">
                  <span>
                    Initial{" "}
                    {a.origin === "invitation" ? "invitation" : "application"}
                  </span>
                  <p>{a.message}</p>
                  <small>{when(a.created_at)}</small>
                </div>
              )}
              {messages.length ? (
                messages.map((item) => (
                  <div
                    key={item.id}
                    className={`hiring-message ${item.sender_id === user.id ? "own" : ""}`}
                  >
                    <span>
                      {item.sender_id === user.id
                        ? "You"
                        : item.sender_name ||
                          item.author_name ||
                          (company ? a.candidate_name : a.company_name)}
                    </span>
                    <p>{item.body}</p>
                    <small>{when(item.created_at)}</small>
                  </div>
                ))
              ) : (
                <p className="small-muted">
                  Keep the conversation here. Messages are shared only with the
                  participants of this application.
                </p>
              )}
            </div>
            {!["declined", "rejected", "withdrawn"].includes(a.stage) && (
              <form onSubmit={send} className="hiring-message-form">
                <Textarea
                  label="Send a message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                  maxLength={5000}
                  rows={3}
                  placeholder="A thoughtful next question, an update, or a little more context…"
                />
                <button
                  className="button dark small"
                  disabled={!!busy || !message.trim()}
                >
                  {busy === "message" ? (
                    <LoaderCircle className="spin" size={15} />
                  ) : (
                    <Send size={15} />
                  )}
                  Send message
                </button>
              </form>
            )}
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  <CalendarDays size={18} />
                  Interviews
                </h2>
                <p>
                  Schedule and RSVP here. No calendar events or external
                  messages are sent.
                </p>
              </div>
              {company && !terminal && a.stage !== "invited" && (
                <button
                  className="button outline small"
                  onClick={() => setDialog({ type: "interview" })}
                >
                  <Plus size={14} />
                  Schedule
                </button>
              )}
            </div>
            {interviews.length ? (
              <div className="hiring-event-list">
                {interviews.map((item) => (
                  <article className="hiring-event" key={item.id}>
                    <div className="hiring-event-top">
                      <CalendarDays size={20} />
                      <div>
                        <h3>{when(item.starts_at)}</h3>
                        <p>
                          {item.duration_minutes} minutes · RSVP:{" "}
                          {label(item.rsvp || "pending")}
                        </p>
                      </div>
                      <Badge value={item.status || "scheduled"} />
                    </div>
                    {item.location_or_url && (
                      <p>
                        {safeLink(item.location_or_url) ? (
                          <a
                            href={item.location_or_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Join interview
                            <ExternalLink size={12} />
                          </a>
                        ) : (
                          item.location_or_url
                        )}
                      </p>
                    )}
                    {item.notes && (
                      <p className="hiring-preline">{item.notes}</p>
                    )}
                    {!["cancelled", "completed"].includes(item.status) &&
                      !terminal && (
                        <div className="hiring-inline-actions">
                          {company ? (
                            <>
                              <button
                                className="button outline small"
                                onClick={() =>
                                  setDialog({ type: "interview", item })
                                }
                              >
                                Reschedule / edit
                              </button>
                              <button
                                className="button outline small"
                                disabled={!!busy}
                                onClick={() =>
                                  action(
                                    "/hiring/interviews/" + item.id,
                                    "PATCH",
                                    { status: "completed" },
                                  )
                                }
                              >
                                Mark complete
                              </button>
                              <button
                                className="text-link"
                                disabled={!!busy}
                                onClick={() =>
                                  setDialog({ type: "cancel_interview", item })
                                }
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                className="button dark small"
                                disabled={!!busy || item.rsvp === "accepted"}
                                onClick={() =>
                                  action(
                                    "/hiring/interviews/" + item.id,
                                    "PATCH",
                                    { rsvp: "accepted" },
                                  )
                                }
                              >
                                <Check size={14} />
                                Accept time
                              </button>
                              <button
                                className="button outline small"
                                disabled={!!busy || item.rsvp === "declined"}
                                onClick={() =>
                                  action(
                                    "/hiring/interviews/" + item.id,
                                    "PATCH",
                                    { rsvp: "declined" },
                                  )
                                }
                              >
                                Decline time
                              </button>
                            </>
                          )}
                        </div>
                      )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="hiring-panel-empty">
                No interviews scheduled yet. A proposed time will appear here
                when the team is ready.
              </p>
            )}
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  <FileText size={18} />
                  Offers & terms
                </h2>
                <p>
                  A hiring record. Contract signing and payments happen
                  separately.
                </p>
              </div>
              {company &&
                !terminal &&
                a.stage !== "invited" &&
                !offers.some(
                  (o) => o.status === "sent" || o.status === "accepted",
                ) && (
                  <button
                    className="button outline small"
                    onClick={() => setDialog({ type: "offer" })}
                  >
                    <Plus size={14} />
                    Send offer
                  </button>
                )}
            </div>
            {offers.length ? (
              <div className="hiring-event-list">
                {offers.map((offer) => (
                  <OfferCard
                    key={offer.id}
                    offer={offer}
                    company={company}
                    disabled={!!busy || terminal}
                    respond={(status) =>
                      setDialog({ type: "offer_response", offer, status })
                    }
                  />
                ))}
              </div>
            ) : (
              <p className="hiring-panel-empty">
                No offers yet. When terms are sent, they’ll appear here with a
                clear response path.
              </p>
            )}
          </section>
          {company && a.candidate && (
            <section className="panel">
              <div className="panel-heading">
                <h2>The person behind the application</h2>
              </div>
              <div className="form-body">
                <h3>{a.candidate.name || a.candidate_name}</h3>
                <p className="hiring-preline">{a.candidate.headline}</p>
                <p className="hiring-long-text">{a.candidate.bio}</p>
                <div className="chips">
                  {a.candidate.skills?.map((skill) => (
                    <span key={skill}>{skill}</span>
                  ))}
                </div>
                {a.candidate.work_preferences && (
                  <MobilitySummary preferences={a.candidate.work_preferences} />
                )}
                <p className="small-muted">
                  Professional information shared for this conversation.
                  Original resume files are never automatically shared. Any
                  mobility declarations are self-reported and require a human
                  review.
                </p>
              </div>
            </section>
          )}
        </main>
        <aside className="hiring-sticky">
          <section className="panel">
            <div className="form-body">
              <h3>Next steps, with care.</h3>
              <p className="small-muted">
                Every stage change is an explicit human decision. Evidence
                scores and nationality never make a hiring decision.
              </p>
              {company && !terminal && a.stage !== "invited" && (
                <Select
                  label="Move to stage"
                  value=""
                  onChange={(e) =>
                    e.target.value &&
                    setDialog({ type: "stage", stage: e.target.value })
                  }
                  options={[
                    { value: "", label: "Choose a next step" },
                    ...(
                      {
                        applied: ["reviewing", "interviewing", "rejected"],
                        reviewing: ["interviewing", "rejected"],
                        interviewing: ["reviewing", "rejected"],
                        offer: [
                          "rejected",
                          ...(offers.some((o) => o.status === "accepted")
                            ? ["hired"]
                            : []),
                        ],
                      }[a.stage] || []
                    ).map((s) => ({ value: s, label: label(s) })),
                  ]}
                />
              )}
              <div className="hiring-application-meta">
                <span>Current stage</span>
                <Badge value={a.stage} />
                <span>Started</span>
                <b>{date(a.created_at)}</b>
                {a.contact_email && (
                  <>
                    <span>Shared contact</span>
                    <a href={"mailto:" + a.contact_email}>{a.contact_email}</a>
                  </>
                )}
              </div>
              {!company && a.stage !== "invited" && (
                <>
                  <label className="hiring-checkbox">
                    <input
                      type="checkbox"
                      checked={contact}
                      onChange={(e) => setContact(e.target.checked)}
                      disabled={!!busy}
                    />
                    Share my account email
                  </label>
                  <button
                    className="button outline full"
                    disabled={!!busy || contact === !!a.share_contact}
                    onClick={async () => {
                      const d = await action(
                        "/hiring/applications/" + id,
                        "PATCH",
                        { share_contact: contact },
                      );
                      if (d)
                        setSuccess(
                          "Contact sharing updated. Previous disclosures cannot be retracted.",
                        );
                    }}
                  >
                    Update contact visibility
                  </button>
                  {!user.email_verified && (
                    <Link to="/app/settings" className="aside-link">
                      Verify your email before sharing
                    </Link>
                  )}
                  <p className="small-muted">
                    Revoking stops future access to your email. It cannot
                    retract details the company has already seen.
                  </p>
                </>
              )}
              {!company && !terminal && a.stage !== "invited" && (
                <button
                  className="button outline full"
                  disabled={!!busy}
                  onClick={() => setDialog({ type: "withdraw" })}
                >
                  Withdraw application
                </button>
              )}
              {company && a.stage === "invited" && (
                <p className="small-muted">
                  The candidate decides whether to accept. Further hiring steps
                  open after they join the conversation.
                </p>
              )}
              {terminal && (
                <p className="small-muted">
                  This conversation is {label(a.stage).toLowerCase()}. Its
                  history remains available.
                </p>
              )}
            </div>
          </section>
        </aside>
      </div>
      {dialog?.type === "interview" && (
        <InterviewDialog
          api={api}
          application={a}
          item={dialog.item}
          close={() => setDialog(null)}
          done={() => {
            setDialog(null);
            resource.reload();
            setSuccess(
              "Interview details saved. RSVP resets when the time changes.",
            );
          }}
        />
      )}
      {dialog?.type === "offer" && (
        <OfferDialog
          api={api}
          application={a}
          close={() => setDialog(null)}
          done={() => {
            setDialog(null);
            resource.reload();
            setSuccess("Offer sent in Candoc.");
          }}
        />
      )}
      {dialog && !["interview", "offer"].includes(dialog.type) && (
        <Dialog
          title={
            dialog.type === "accept_invitation"
              ? "Start this conversation?"
              : dialog.type === "offer_response"
                ? `${{ accepted: "Accept", declined: "Decline", withdrawn: "Withdraw" }[dialog.status] || "Respond to"} this offer?`
                : dialog.type === "stage"
                  ? `Move this application to ${label(dialog.stage).toLowerCase()}?`
                  : dialog.type === "cancel_interview"
                    ? "Cancel this interview?"
                    : dialog.type === "decline_invitation"
                      ? "Decline this invitation?"
                      : "Withdraw this application?"
          }
          close={() => setDialog(null)}
        >
          <p className="modal-description">
            {dialog.type === "accept_invitation"
              ? "Accepting gives the hiring team access to your professional profile in this application. Your email is shared only if you selected that option."
              : dialog.type === "offer_response"
                ? "Your response is recorded against these terms. Please review compensation, dates, visa, and relocation details carefully. Formal contract execution and payments are handled separately."
                : dialog.type === "stage"
                  ? "This action records your team’s explicit decision and notifies the candidate in Candoc. Terminal decisions cannot silently reopen."
                  : dialog.type === "cancel_interview"
                    ? "The interview remains in the history with a cancelled status. No external calendar change or email is sent."
                    : "This closes your active participation. The conversation history remains available, and this action cannot silently reopen it."}
          </p>
          <ErrorNotice error={error} />
          <div className="modal-actions">
            <button
              className="button outline"
              disabled={!!busy}
              onClick={() => setDialog(null)}
            >
              Go back
            </button>
            <button
              className="button dark"
              disabled={!!busy}
              onClick={async () => {
                if (
                  [
                    "accept_invitation",
                    "decline_invitation",
                    "withdraw",
                  ].includes(dialog.type)
                )
                  return candidateAction(dialog.type);
                let d;
                if (dialog.type === "stage")
                  d = await action(
                    "/hiring/applications/" + id + "/stage",
                    "PATCH",
                    { stage: dialog.stage },
                  );
                else if (dialog.type === "offer_response")
                  d = await action(
                    "/hiring/offers/" + dialog.offer.id,
                    "PATCH",
                    { status: dialog.status },
                  );
                else if (dialog.type === "cancel_interview")
                  d = await action(
                    "/hiring/interviews/" + dialog.item.id,
                    "PATCH",
                    { status: "cancelled" },
                  );
                if (d) {
                  setDialog(null);
                  setSuccess("Your update has been recorded.");
                }
              }}
            >
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Check size={16} />
              )}
              Confirm
            </button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
function toLocalInput(value) {
  if (!value) return "";
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
function InterviewDialog({ api, application, item, close, done }) {
  const [form, setForm] = useState({
      starts_at: toLocalInput(item?.starts_at),
      duration_minutes: item?.duration_minutes || 45,
      location_or_url: item?.location_or_url || "",
      notes: item?.notes || "",
    }),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {
        ...form,
        starts_at: new Date(form.starts_at).toISOString(),
        duration_minutes: Number(form.duration_minutes),
      };
      await api(
        item
          ? "/hiring/interviews/" + item.id
          : "/hiring/applications/" + application.id + "/interviews",
        { method: item ? "PATCH" : "POST", body },
      );
      done();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      title={item ? "Update the interview." : "Make time for a conversation."}
      close={close}
    >
      <form onSubmit={submit}>
        <ErrorNotice error={error} />
        <Field
          label="Start date and time"
          type="datetime-local"
          name="starts_at"
          value={form.starts_at}
          onChange={change}
          required
          hint={`Your local time (${Intl.DateTimeFormat().resolvedOptions().timeZone}). Stored as UTC and shown in each participant’s local timezone.`}
        />
        <Field
          label="Duration in minutes"
          type="number"
          name="duration_minutes"
          min="15"
          max="240"
          value={form.duration_minutes}
          onChange={change}
          required
        />
        <Field
          label="Meeting link or location"
          name="location_or_url"
          value={form.location_or_url}
          onChange={change}
          required
          maxLength={1000}
          placeholder="HTTPS meeting link or physical location"
        />
        <Textarea
          label="Notes and preparation"
          name="notes"
          value={form.notes}
          onChange={change}
          rows={4}
          maxLength={5000}
        />
        <p className="small-muted">
          The candidate can accept or decline the time. Rescheduling resets the
          RSVP. This records the interview in Candoc; it does not create a
          calendar event.
        </p>
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancel
          </button>
          <button className="button dark" disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <CalendarDays size={16} />
            )}
            Save interview
          </button>
        </div>
      </form>
    </Dialog>
  );
}
function OfferCard({ offer, company, disabled, respond }) {
  const expired = offer.expires_at && new Date(offer.expires_at) < new Date(),
    canRespond = offer.status === "sent" && !expired;
  return (
    <article className="hiring-event hiring-offer">
      <div className="hiring-event-top">
        <FileText size={21} />
        <div>
          <h3>{payText(offer)}</h3>
          <p>Proposed start: {date(offer.start_date)}</p>
        </div>
        <Badge
          value={expired && offer.status === "sent" ? "expired" : offer.status}
        />
      </div>
      <p className="hiring-preline">{offer.summary}</p>
      <div className="hiring-support">
        <div>
          <b>Visa: {label(offer.visa_sponsorship)}</b>
          <p>{offer.visa_details || "No further details supplied."}</p>
        </div>
        <div>
          <b>Relocation: {label(offer.relocation_support)}</b>
          <p>{offer.relocation_details || "No further details supplied."}</p>
        </div>
      </div>
      {offer.expires_at && (
        <p className="small-muted">Expires {when(offer.expires_at)}</p>
      )}
      {canRespond && !disabled && (
        <div className="hiring-inline-actions">
          {company ? (
            <button
              className="button outline small"
              onClick={() => respond("withdrawn")}
            >
              Withdraw offer
            </button>
          ) : (
            <>
              <button
                className="button dark small"
                onClick={() => respond("accepted")}
              >
                <Check size={14} />
                Accept terms
              </button>
              <button
                className="button outline small"
                onClick={() => respond("declined")}
              >
                Decline offer
              </button>
            </>
          )}
        </div>
      )}
    </article>
  );
}
function OfferDialog({ api, application, close, done }) {
  const catalogs = useCatalogs(api),
    [form, setForm] = useState({
      summary: "",
      compensation_min: "",
      compensation_max: "",
      currency: application.job?.currency || "",
      pay_period: application.job?.pay_period || "year",
      start_date: "",
      expires_at: "",
      visa_sponsorship: application.job?.visa_sponsorship || "not_specified",
      visa_details: application.job?.visa_details || "",
      relocation_support:
        application.job?.relocation_support || "not_specified",
      relocation_details: application.job?.relocation_details || "",
    }),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/hiring/applications/" + application.id + "/offers", {
        method: "POST",
        body: {
          ...form,
          compensation_min: emptyToNull(form.compensation_min),
          compensation_max: emptyToNull(form.compensation_max),
          start_date: form.start_date || null,
          expires_at: form.expires_at
            ? new Date(form.expires_at).toISOString()
            : null,
        },
      });
      done();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog title="Put the terms on the table." close={close}>
      <form onSubmit={submit}>
        <ErrorNotice error={error} />
        <Textarea
          label="Offer summary and terms"
          name="summary"
          value={form.summary}
          onChange={change}
          required
          minLength={10}
          maxLength={10000}
          rows={5}
        />
        <CompensationFields catalogs={catalogs} form={form} change={change} />
        <div className="hiring-form-grid">
          <Field
            label="Proposed start date"
            type="date"
            name="start_date"
            value={form.start_date}
            onChange={change}
          />
          <Field
            label="Offer expires (local time, optional)"
            type="datetime-local"
            name="expires_at"
            value={form.expires_at}
            onChange={change}
          />
          <Select
            label="Visa sponsorship"
            name="visa_sponsorship"
            value={form.visa_sponsorship}
            onChange={change}
            options={SUPPORT}
          />
          <Select
            label="Relocation support"
            name="relocation_support"
            value={form.relocation_support}
            onChange={change}
            options={SUPPORT}
          />
        </div>
        <Textarea
          label="Visa details"
          name="visa_details"
          value={form.visa_details}
          onChange={change}
          rows={3}
          maxLength={3000}
        />
        <Textarea
          label="Relocation details"
          name="relocation_details"
          value={form.relocation_details}
          onChange={change}
          rows={3}
          maxLength={3000}
        />
        <p className="small-muted">
          Sending records these terms and lets the candidate respond in Candoc.
          It does not execute an employment contract, transfer money, or mark
          the candidate hired.
        </p>
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancel
          </button>
          <button className="button dark" disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Send size={16} />
            )}
            Send offer
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function NotificationsPage({ api }) {
  const resource = useResource(api, "/hiring/notifications"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState("");
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === "visible") resource.reload();
    };
    const timer = window.setInterval(refresh, 30000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [resource.reload]);
  async function mark(id) {
    setBusy(id || "all");
    setError("");
    try {
      await api(
        id ? "/hiring/notifications/" + id : "/hiring/notifications/read-all",
        {
          method: id ? "PATCH" : "POST",
          ...(id ? { body: { read: true } } : {}),
        },
      );
      resource.reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  return (
    <div className="hiring-page">
      <Header
        title="Stay close to what’s next."
        description="Introductions, application updates, interview invitations, and new conversations, in Candoc."
      >
        <button
          className="button outline"
          onClick={resource.reload}
          disabled={resource.loading}
        >
          <RefreshCw size={16} className={resource.loading ? "spin" : ""} />
          Refresh
        </button>
        <button
          className="button outline"
          onClick={() => mark()}
          disabled={!!busy || !resource.data?.unread_count}
        >
          <CheckCheck size={16} />
          Mark all read
        </button>
      </Header>
      <ErrorNotice error={error || resource.error} />
      {resource.loading && !resource.data ? (
        <Loading />
      ) : resource.data?.notifications?.length ? (
        <section className="panel">
          {resource.data.notifications.map((item) => (
            <article
              className={`hiring-notification ${item.read ? "read" : ""}`}
              key={item.id}
            >
              <span className="hiring-company-icon">
                <Bell size={20} />
              </span>
              <div>
                <b>{label(item.kind)}</b>
                <p>{item.body}</p>
                <small>{when(item.created_at)}</small>
                <div>
                  {item.introduction_id ? (
                    <Link
                      className="text-link"
                      to={
                        "/app/inbox?introduction_id=" +
                        encodeURIComponent(item.introduction_id)
                      }
                    >
                      Open introduction
                      <ArrowRight size={13} />
                    </Link>
                  ) : item.application_id ? (
                    <Link
                      className="text-link"
                      to={"/app/applications/" + item.application_id}
                    >
                      Open conversation
                      <ArrowRight size={13} />
                    </Link>
                  ) : item.job_id ? (
                    <Link className="text-link" to={"/jobs/" + item.job_id}>
                      View role
                      <ArrowRight size={13} />
                    </Link>
                  ) : null}
                </div>
              </div>
              {!item.read && (
                <button
                  className="icon-button"
                  onClick={() => mark(item.id)}
                  disabled={!!busy}
                  aria-label="Mark notification read"
                >
                  <Check size={17} />
                </button>
              )}
            </article>
          ))}
        </section>
      ) : (
        !resource.error && (
          <section className="panel">
            <Empty title="You’re all caught up.">
              When a conversation moves forward, you’ll see it here.
            </Empty>
          </section>
        )
      )}
    </div>
  );
}
