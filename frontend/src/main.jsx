import React, {
  useEffect,
  useState,
  createContext,
  useContext,
  useRef,
} from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  ArrowLeft,
  Check,
  CheckCheck,
  ChevronRight,
  ChevronDown,
  UploadCloud,
  FileText,
  Search,
  SlidersHorizontal,
  MapPin,
  BriefcaseBusiness,
  Github,
  Gitlab,
  Linkedin,
  ShieldCheck,
  Sparkles,
  CircleCheck,
  X,
  Menu,
  LayoutDashboard,
  Users,
  Mail,
  Settings,
  LogOut,
  Eye,
  EyeOff,
  Download,
  Trash2,
  Plus,
  LoaderCircle,
  ExternalLink,
  HeartHandshake,
  Send,
  Code2,
  LockKeyhole,
  Sprout,
  BarChart3,
  Info,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/dm-sans/700.css";
import "@fontsource/sora/500.css";
import "@fontsource/sora/600.css";
import "./style.css";

const AuthContext = createContext(null);
const useAuth = () => useContext(AuthContext);
async function api(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
    body: options.body && !isForm ? JSON.stringify(options.body) : options.body,
  });
  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.[0]?.msg || "Something went wrong. Please try again.",
    );
  return data;
}
function isPublicSourceUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password && !url.port &&
      ["github.com", "gitlab.com", "linkedin.com", "www.linkedin.com"].includes(url.hostname.toLowerCase());
  } catch { return false; }
}
const initials = (name) =>
  (name || "You")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
const formatDate = (date) =>
  date
    ? new Date(date).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "";
const number = (value) => Number(value || 0).toFixed(1);
function Logo({ light = false }) {
  return (
    <Link
      to="/"
      className={`logo ${light ? "light" : ""}`}
      aria-label="Candoc home"
    >
      <span className="logo-mark">
        <span />
      </span>
      candoc<span className="logo-dot">.</span>
    </Link>
  );
}
function Spinner({ text = "Loading…" }) {
  return (
    <div className="loading">
      <LoaderCircle className="spin" size={23} />
      <span>{text}</span>
    </div>
  );
}
function Alert({ error, children }) {
  return error || children ? (
    <div
      className={`alert ${error ? "error" : "success"}`}
      role={error ? "alert" : "status"}
    >
      {error ? <Info size={17} /> : <CheckCircle2 size={17} />}
      <span>{error || children}</span>
    </div>
  ) : null;
}
function Empty({ icon: Icon = Sprout, title, children, action }) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={29} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
function Modal({ title, children, close, wide }) {
  const ref = useRef(null);
  useEffect(() => {
    const before = document.activeElement;
    ref.current?.focus();
    const handler = (event) => {
      if (event.key === "Escape") close();
      if (event.key === "Tab") {
        const nodes = ref.current?.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex="0"]',
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
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
        className={`modal ${wide ? "wide" : ""}`}
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
            <X size={21} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
function PublicNav() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <header className="public-nav">
      <div className="container nav-inner">
        <Logo />
        <nav className={open ? "open" : ""}>
          <a href="/#how-it-works" onClick={() => setOpen(false)}>
            How it works
          </a>
          <Link to="/methodology">Our methodology</Link>
          <span className="nav-divider" />
          <Link to={user ? "/app" : "/login"}>
            {user ? "Your workspace" : "Log in"}
          </Link>
          <Link className="button dark small" to={user ? "/app" : "/signup"}>
            {user ? "Open dashboard" : "Get started"}
            <ArrowUpRight size={16} />
          </Link>
        </nav>
        <button
          className="mobile-nav-toggle icon-button"
          onClick={() => setOpen(!open)}
          aria-label="Toggle navigation"
        >
          {open ? <X /> : <Menu />}
        </button>
      </div>
    </header>
  );
}
function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div>
          <Logo />
          <p>Good work. New possibilities.</p>
        </div>
        <div className="footer-links">
          <Link to="/methodology">Evaluation methodology</Link>
          <Link to="/privacy">Privacy & your data</Link>
          <a
            href="https://github.com/sverma/candoc"
            target="_blank"
            rel="noreferrer"
            className="source-link"
          >
            <Code2 size={15} /> Open source · MIT
          </a>
        </div>
        <span className="copyright">© {new Date().getFullYear()} Candoc</span>
      </div>
    </footer>
  );
}
function Landing() {
  const { user } = useAuth();
  return (
    <>
      <PublicNav />
      <main>
        <section className="hero">
          <div className="container hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">
                <span className="live-dot" /> A better direction for hiring
              </div>
              <h1>
                Let your work
                <br />
                open <span>doors.</span>
                <svg viewBox="0 0 240 18" aria-hidden="true">
                  <path d="M4 10c67-12 140-10 229-3M18 16c78-11 139-10 204-6" />
                </svg>
              </h1>
              <p>
                You’ve done the work. Now let the right companies find you. One
                thoughtful profile, an evidence-backed assessment, and
                opportunities that come to you.
              </p>
              <div className="hero-actions">
                <Link to={user ? "/app" : "/signup"} className="button dark">
                  Build my profile <ArrowUpRight size={19} />
                </Link>
                <Link to="/signup?role=company" className="text-link">
                  I’m hiring <ArrowRight size={17} />
                </Link>
              </div>
              <div className="hero-reassurance">
                <span>
                  <Check size={15} /> Free for candidates
                </span>
                <span>
                  <Check size={15} /> You choose who gets in
                </span>
              </div>
            </div>
            <div
              className="hero-art"
              aria-label="Illustrative candidate profile"
            >
              <div className="art-orbit orbit-one" />
              <div className="art-orbit orbit-two" />
              <div className="floating-tag tag-github">
                <Github size={18} />
                <span>Work, with context.</span>
              </div>
              <div className="sample-profile">
                <div className="sample-top">
                  <span className="sample-label">
                    PROFILE PREVIEW · ILLUSTRATIVE
                  </span>
                  <span className="mini-dots">•••</span>
                </div>
                <div className="sample-person">
                  <div className="sample-avatar">
                    AK
                    <span>
                      <Check size={10} />
                    </span>
                  </div>
                  <div>
                    <h3>Alex Kim</h3>
                    <p>Full-stack engineer</p>
                    <span>
                      <MapPin size={12} /> Remote · Open to opportunities
                    </span>
                  </div>
                </div>
                <p className="sample-bio">
                  Building thoughtful products, from the first line of code to
                  the people who use them.
                </p>
                <div className="chips">
                  <span>React</span>
                  <span>Python</span>
                  <span>System design</span>
                </div>
                <div className="sample-evidence">
                  <div className="sample-score">
                    <span>
                      4.2<small>/ 5</small>
                    </span>
                    <div>
                      <b>Evidence score</b>
                      <p>Clear experience. Real contributions.</p>
                    </div>
                    <Sparkles size={23} />
                  </div>
                  <div className="sample-bars">
                    {[
                      ["Skills in practice", 87],
                      ["Experience detail", 80],
                      ["Measurable impact", 76],
                    ].map(([label, width]) => (
                      <div key={label}>
                        <span>{label}</span>
                        <div>
                          <i style={{ width: width + "%" }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="sample-bottom">
                  <ShieldCheck size={14} /> Your profile. Your pace. Your
                  choice.
                </div>
              </div>
              <div className="intro-float">
                <div className="float-company">
                  <BriefcaseBusiness size={21} />
                </div>
                <div>
                  <b>A new introduction</b>
                  <p>A team wants to meet you.</p>
                </div>
                <span>
                  <ArrowUpRight size={17} />
                </span>
              </div>
              <div className="art-caption">
                <span /> A profile that starts a conversation.
              </div>
            </div>
          </div>
        </section>
        <section className="principles">
          <div className="container principles-row">
            <span>
              A little less searching.
              <br />
              <b>A lot more possibility.</b>
            </span>
            <div>
              <FileText size={23} />
              <span>Evidence over keywords</span>
            </div>
            <div>
              <HeartHandshake size={24} />
              <span>Companies make the first move</span>
            </div>
            <div>
              <LockKeyhole size={22} />
              <span>Always on your terms</span>
            </div>
          </div>
        </section>
        <section id="how-it-works" className="how-section container">
          <div className="section-header">
            <div>
              <span className="section-kicker">THE WAY IT SHOULD WORK</span>
              <h2>
                Your next chapter.
                <br />A different first step.
              </h2>
            </div>
            <p>
              No endless applications. No disappearing into a pile of PDFs. Just
              a clearer picture of what you bring, shared with the right people.
            </p>
          </div>
          <div className="step-grid">
            {[
              {
                icon: FileText,
                n: "01",
                title: "Tell your story",
                text: "Upload your resume. Add the work, experience, and skills you want your next team to see.",
              },
              {
                icon: Sparkles,
                n: "02",
                title: "Make your work visible",
                text: "Explore your evidence score, understand every criterion, and strengthen your profile before you publish.",
              },
              {
                icon: HeartHandshake,
                n: "03",
                title: "Let opportunity come to you",
                text: "Companies send thoughtful introductions. You decide which conversations are worth starting.",
              },
            ].map(({ icon: Icon, n, title, text }) => (
              <article className="step-card" key={n}>
                <div>
                  <span className="step-icon">
                    <Icon size={25} />
                  </span>
                  <span className="step-number">{n}</span>
                </div>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="fair-section container">
          <div className="fair-visual">
            <div className="fair-card">
              <span className="fair-icon">
                <ShieldCheck size={32} />
              </span>
              <h3>
                A clearer view.
                <br />A fairer conversation.
              </h3>
              <div className="fair-check">
                <Check size={17} /> Transparent evaluation criteria
              </div>
              <div className="fair-check">
                <Check size={17} /> Evidence you can inspect and correct
              </div>
              <div className="fair-check">
                <Check size={17} /> Human judgment, always
              </div>
            </div>
            <span className="fair-note">Potential deserves context.</span>
          </div>
          <div className="fair-copy">
            <span className="section-kicker">UNDERSTAND THE WHY</span>
            <h2>
              More than a number.
              <br />A story with evidence.
            </h2>
            <p>
              Our five-part assessment looks at how clearly your resume
              demonstrates skills, experience, impact, projects, and
              communication. Every score comes with the evidence behind it.
            </p>
            <p>
              Your age, gender, university prestige, career breaks, and social
              following don’t belong in that equation. Neither does having a
              GitHub or GitLab account.
            </p>
            <Link to="/methodology" className="text-link">
              See how evaluation works <ArrowRight size={17} />
            </Link>
          </div>
        </section>
        <section className="company-cta container">
          <div>
            <span className="section-kicker">FOR COMPANIES</span>
            <h2>
              Meet the person
              <br />
              behind the resume.
            </h2>
            <p>
              Discover people through their work. Start a conversation with
              context, a real role, and a thoughtful introduction.
            </p>
            <Link to="/signup?role=company" className="button lime">
              Find your next teammate <ArrowUpRight size={18} />
            </Link>
          </div>
          <div className="cta-symbol">
            <Users size={72} strokeWidth={1.25} />
            <span className="cta-star">✳</span>
            <div>
              Good teams start
              <br />
              with good conversations.
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function AuthPage({ signup = false }) {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [role, setRole] = useState(
    new URLSearchParams(location.search).get("role") === "company"
      ? "company"
      : "candidate",
  );
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    company_name: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  if (user) return <Navigate to="/app" replace />;
  const change = (event) =>
    setForm({ ...form, [event.target.name]: event.target.value });
  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await api("/auth/" + (signup ? "register" : "login"), {
        method: "POST",
        body: signup
          ? { ...form, role }
          : { email: form.email, password: form.password },
      });
      setUser(result.user);
      navigate("/app");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <aside className="auth-aside">
        <Logo light />
        <div>
          <span className="section-kicker">A NEW DIRECTION</span>
          <h1>
            Your work
            <br />
            speaks.
            <br />
            <em>Let it be heard.</em>
          </h1>
          <p>
            A thoughtful profile. Meaningful introductions. A little more
            possibility.
          </p>
          <div className="auth-art">
            <span>
              <FileText size={30} />
            </span>
            <i />
            <span>
              <HeartHandshake size={33} />
            </span>
          </div>
        </div>
        <span className="auth-aside-footer">
          Built around people. Open by design.
        </span>
      </aside>
      <main className="auth-main">
        <Link to="/" className="back-link">
          <ArrowLeft size={16} /> Back to Candoc
        </Link>
        <div className="auth-form-wrap">
          <span className="section-kicker">
            {signup ? "LET’S GET STARTED" : "GOOD TO SEE YOU"}
          </span>
          <h2>{signup ? "Your next chapter starts here." : "Welcome back."}</h2>
          <p>
            {signup
              ? "Create your account. Make the first step count."
              : "Your next conversation could be waiting."}
          </p>
          {signup && (
            <div className="role-switch">
              <button
                className={role === "candidate" ? "selected" : ""}
                onClick={() => setRole("candidate")}
              >
                <Users size={19} />
                <span>
                  I’m a candidate<small>Let companies find me</small>
                </span>
                {role === "candidate" && <CircleCheck size={17} />}
              </button>
              <button
                className={role === "company" ? "selected" : ""}
                onClick={() => setRole("company")}
              >
                <BriefcaseBusiness size={19} />
                <span>
                  I’m hiring<small>Find my next teammate</small>
                </span>
                {role === "company" && <CircleCheck size={17} />}
              </button>
            </div>
          )}
          <form onSubmit={submit}>
            <Alert error={error} />
            {signup && (
              <Field
                label="Your full name"
                name="name"
                value={form.name}
                onChange={change}
                autoComplete="name"
                required
                maxLength={100}
                placeholder="Alex Kim"
              />
            )}
            {signup && role === "company" && (
              <Field
                label="Company name"
                name="company_name"
                value={form.company_name}
                onChange={change}
                required
                maxLength={150}
                placeholder="Your company"
              />
            )}
            <Field
              label="Email address"
              name="email"
              type="email"
              value={form.email}
              onChange={change}
              autoComplete="email"
              required
              placeholder="you@example.com"
            />
            <label className="field">
              <span>Password</span>
              <div className="password-input">
                <input
                  name="password"
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={change}
                  required
                  minLength={signup ? 12 : undefined}
                  maxLength={128}
                  autoComplete={signup ? "new-password" : "current-password"}
                  placeholder={
                    signup ? "At least 12 characters" : "Your password"
                  }
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
            {!signup && (
              <p className="recovery-link">
                <Link to="/forgot-password">Forgot password?</Link>
              </p>
            )}
            {signup && (
              <p className="form-fine">
                By creating an account, you agree to our{" "}
                <Link to="/privacy">privacy and data practices</Link>. Your
                profile starts private.
              </p>
            )}
            <button className="button dark full" disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={18} /> : null}
              {signup ? "Create my account" : "Log in"}
              {!busy && <ArrowRight size={18} />}
            </button>
          </form>
          <p className="auth-switch">
            {signup ? "Already have an account?" : "New to Candoc?"}{" "}
            <Link to={signup ? "/login" : "/signup"}>
              {signup ? "Log in" : "Create an account"}
            </Link>
          </p>
        </div>
        <span className="auth-bottom">
          <LockKeyhole size={14} /> Your story stays yours.
        </span>
      </main>
    </div>
  );
}
function PasswordRecovery({ reset = false }) {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [token] = useState(
    () => new URLSearchParams(window.location.hash.slice(1)).get("token") || "",
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (reset && window.location.hash)
      navigate("/reset-password", { replace: true });
  }, [reset, navigate]);
  async function submit(event) {
    event.preventDefault();
    setError("");
    if (reset && password !== confirm) {
      setError("Your passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api(reset ? "/auth/reset-password" : "/auth/forgot-password", {
        method: "POST",
        body: reset ? { token, password } : { email },
      });
      if (reset) {
        setUser(null);
        setPassword("");
        setConfirm("");
      }
      setComplete(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="recovery-page">
      <Logo />
      <section className="panel recovery-card">
        <span className="section-kicker">
          {reset ? "A FRESH START" : "LET’S GET YOU BACK IN"}
        </span>
        <h1>
          {complete
            ? reset
              ? "Password updated."
              : "Check your inbox."
            : reset
              ? "Choose a new password."
              : "Forgot your password?"}
        </h1>
        {complete ? (
          <>
            <p role="status">
              {reset
                ? "Your password has been changed and your previous sessions have been signed out. Log in with your new password."
                : "If an account matches this email, we’ll attempt to send a reset link. Check your inbox and spam folder. The link expires after 20 minutes."}
            </p>
            {!reset && (
              <p className="small-muted">
                Only the most recently requested link will work. If an email
                doesn’t arrive, wait a few minutes before trying again.
              </p>
            )}
            <Link className="button dark full" to="/login">
              Back to log in <ArrowRight size={17} />
            </Link>
            {!reset && (
              <button className="text-link" onClick={() => setComplete(false)}>
                Try another request
              </button>
            )}
          </>
        ) : reset && !token ? (
          <>
            <Alert error="This reset link is missing or invalid. Open the complete link from your latest email, or request a new one." />
            <Link className="button dark full" to="/forgot-password">
              Request a new link
            </Link>
          </>
        ) : (
          <>
            <p>
              {reset
                ? "Use at least 12 characters. A successful reset signs your account out on every device."
                : "Enter your account email and we’ll help you reset your password. This works for candidates and companies."}
            </p>
            <form onSubmit={submit}>
              <Alert error={error} />
              {reset ? (
                <>
                  <Field
                    label="New password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={12}
                    maxLength={128}
                    required
                  />
                  <Field
                    label="Confirm new password"
                    name="confirm_password"
                    type="password"
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(event) => setConfirm(event.target.value)}
                    minLength={12}
                    maxLength={128}
                    required
                  />
                </>
              ) : (
                <Field
                  label="Email address"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  maxLength={254}
                  placeholder="you@example.com"
                  required
                />
              )}
              <button className="button dark full" disabled={busy}>
                {busy && <LoaderCircle className="spin" size={18} />}
                {reset ? "Update password" : "Send reset link"}
              </button>
              {reset && error && (
                <Link className="text-link" to="/forgot-password">
                  Request a new reset link
                </Link>
              )}
            </form>
          </>
        )}
        {!complete && (
          <Link className="back-link" to="/login">
            <ArrowLeft size={16} /> Back to log in
          </Link>
        )}
      </section>
      <p className="small-muted">
        <LockKeyhole size={14} /> We never email your password.
      </p>
    </main>
  );
}
function Field({ label, hint, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
      {hint && <small>{hint}</small>}
    </label>
  );
}
function Textarea({ label, hint, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea {...props} />
      {hint && <small>{hint}</small>}
    </label>
  );
}

function Workspace() {
  const { user, setUser } = useAuth();
  const location = useLocation();
  const [menu, setMenu] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const navigate = useNavigate();
  useEffect(() => setMenu(false), [location.pathname]);
  if (!user) return <Navigate to="/login" replace />;
  const company = user.role === "company";
  const links = company
    ? [
        { to: "/app/talent", icon: Users, label: "Discover talent" },
        { to: "/app/inbox", icon: Mail, label: "Introductions" },
      ]
    : [
        { to: "/app", icon: LayoutDashboard, label: "Overview" },
        { to: "/app/profile", icon: FileText, label: "My profile" },
        { to: "/app/assessment", icon: BarChart3, label: "My assessment" },
        { to: "/app/inbox", icon: Mail, label: "Introductions" },
      ];
  const active = (path) =>
    path === "/app"
      ? location.pathname === "/app"
      : location.pathname.startsWith(path);
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      navigate("/");
    } catch (e) {
      setLogoutError(e.message);
    }
  }
  return (
    <div className="workspace">
      <aside className={`sidebar ${menu ? "shown" : ""}`}>
        <Logo />
        <div className="workspace-label">
          {company ? "COMPANY WORKSPACE" : "YOUR WORKSPACE"}
        </div>
        <nav>
          {links.map(({ to, icon: Icon, label }) => (
            <Link key={to} to={to} className={active(to) ? "active" : ""}>
              <Icon size={19} />
              {label}
              {active(to) && <span className="nav-active-dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span>
            <Sprout size={20} />
          </span>
          <b>
            {company
              ? "Start with a conversation."
              : "Your next chapter is yours."}
          </b>
          <p>
            {company
              ? "A thoughtful introduction goes a long way."
              : "Keep your story up to date. Let the right team find you."}
          </p>
          <Link to="/methodology">
            How evaluation works <ArrowUpRight size={13} />
          </Link>
        </div>
        <div className="sidebar-bottom">
          <Link
            to="/app/settings"
            className={active("/app/settings") ? "active" : ""}
          >
            <Settings size={18} /> Account & privacy
          </Link>
          <button onClick={logout}>
            <LogOut size={18} /> Log out
          </button>
          {logoutError && <small className="error-text">{logoutError}</small>}
          <span>Open source. People first.</span>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-shade"
          onClick={() => setMenu(false)}
          aria-label="Close navigation"
        />
      )}
      <div className="workspace-main">
        <header className="workspace-topbar">
          <button
            className="mobile-nav-toggle icon-button"
            onClick={() => setMenu(!menu)}
            aria-label="Toggle sidebar"
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <ChevronRight size={13} />
            <b>
              {links.find((link) => active(link.to))?.label ||
                (location.pathname === "/app/settings"
                  ? "Account & privacy"
                  : "Candidate profile")}
            </b>
          </div>
          <div className="topbar-user">
            <span className="role-pill">
              {company ? "Company" : "Candidate"}
            </span>
            <div className="avatar small">{initials(user.name)}</div>
            <span>{user.name}</span>
          </div>
        </header>
        <div className="workspace-content">
          <Routes>
            <Route
              index
              element={
                company ? <Navigate to="talent" replace /> : <Overview />
              }
            />
            <Route
              path="profile"
              element={
                company ? <Navigate to="/app/talent" /> : <ProfileEditor />
              }
            />
            <Route
              path="assessment"
              element={
                company ? <Navigate to="/app/talent" /> : <MyAssessment />
              }
            />
            <Route
              path="talent"
              element={company ? <TalentDirectory /> : <Navigate to="/app" />}
            />
            <Route
              path="talent/:id"
              element={company ? <TalentDetail /> : <Navigate to="/app" />}
            />
            <Route path="inbox" element={<Inbox />} />
            <Route path="settings" element={<AccountSettings />} />
            <Route path="*" element={<Navigate to="/app" />} />
          </Routes>
        </div>
        <footer className="workspace-footer">
          <span>Made for better conversations.</span>
          <Link to="/privacy">Privacy</Link>
          <Link to="/methodology">Methodology</Link>
        </footer>
      </div>
    </div>
  );
}
function PageHeader({ kicker, title, description, children }) {
  return (
    <div className="page-header">
      <div>
        {kicker && <span className="section-kicker">{kicker}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </div>
  );
}
function Overview() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [inbox, setInbox] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api("/profile"), api("/introductions")])
      .then(([p, i]) => {
        setProfile(p.profile);
        setInbox(i.introductions);
      })
      .catch((e) => setError(e.message));
  }, []);
  if (error) return <Alert error={error} />;
  if (!profile) return <Spinner />;
  const pending = inbox.filter((i) => i.status === "pending").length;
  return (
    <>
      <PageHeader
        kicker="YOUR NEXT CHAPTER"
        title={`Hello, ${user.name.split(" ")[0]}.`}
        description="A little progress today. A new possibility tomorrow."
      >
        <Link to="/app/profile" className="button outline">
          <FileText size={17} /> Edit profile
        </Link>
      </PageHeader>
      <div className="overview-welcome">
        <div>
          <span className="eyebrow">
            <span className="live-dot" />{" "}
            {profile.visible
              ? "Your profile is discoverable"
              : "Your profile is private"}
          </span>
          <h2>
            {profile.visible
              ? "Let your work do the talking."
              : "Great work deserves to be seen."}
          </h2>
          <p>
            {profile.visible
              ? "Companies can discover your profile and request an introduction. Your contact details stay private until you accept."
              : "Build a profile that tells your story. Add your resume, explore your assessment, then publish when you’re ready."}
          </p>
          <Link className="button dark" to="/app/profile">
            {profile.visible ? "Update my story" : "Build my profile"}
            <ArrowRight size={17} />
          </Link>
        </div>
        <div className="welcome-illustration">
          <FileText size={71} strokeWidth={1.2} />
          <span>
            <Sparkles size={28} />
          </span>
          <i />
          <b>Good work, in focus.</b>
        </div>
      </div>
      <div className="metric-grid">
        <div className="metric-card">
          <span>
            <Eye size={19} /> Profile visibility
          </span>
          <h3>{profile.visible ? "Discoverable" : "Private"}</h3>
          <p>
            {profile.visible
              ? "Open to company introductions"
              : "Only you can see your profile"}
          </p>
        </div>
        <div className="metric-card">
          <span>
            <Sparkles size={19} /> Evidence score
          </span>
          <h3>
            {profile.assessment ? (
              <>
                {number(profile.assessment.score)} <small>/ 5</small>
              </>
            ) : (
              "Not assessed"
            )}
          </h3>
          <Link to="/app/assessment">
            {profile.assessment
              ? "Explore your assessment"
              : "Get your first assessment"}{" "}
            <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="metric-card">
          <span>
            <Mail size={19} /> New introductions
          </span>
          <h3>
            {pending}
            <small> awaiting your reply</small>
          </h3>
          <Link to="/app/inbox">
            View conversations <ArrowUpRight size={14} />
          </Link>
        </div>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>A profile that opens doors</h2>
            <p>Three small steps. One stronger story.</p>
          </div>
          <span className="badge neutral">You’re in control</span>
        </div>
        <div className="checklist">
          {[
            {
              done: !!profile.headline && !!profile.skills?.length,
              title: "Add the essentials",
              text: "A headline, your skills, and what you’re looking for.",
              to: "/app/profile",
            },
            {
              done: !!profile.assessment,
              title: "Give your experience context",
              text: "Upload a resume and review your evidence assessment.",
              to: "/app/assessment",
            },
            {
              done: profile.visible,
              title: "Open the door",
              text: "Make your profile discoverable when you’re ready.",
              to: "/app/profile",
            },
          ].map((step, i) => (
            <Link key={step.title} className="checklist-row" to={step.to}>
              <span className={`checklist-number ${step.done ? "done" : ""}`}>
                {step.done ? <Check size={17} /> : `0${i + 1}`}
              </span>
              <div>
                <b>{step.title}</b>
                <p>{step.text}</p>
              </div>
              <ChevronRight size={18} />
            </Link>
          ))}
        </div>
      </div>
      <div className="note-line">
        <ShieldCheck size={18} />
        <p>
          Your profile starts private. You decide when to publish and which
          introductions to accept.
        </p>
      </div>
    </>
  );
}

function ProfileEditor() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState("");
  const [linkedinError, setLinkedinError] = useState("");
  const linkedinRequest = useRef(false);
  const navigate = useNavigate();
  const fileRef = useRef();
  function load(p) {
    setProfile(p);
    setForm({
      headline: p.headline || "",
      location: p.location || "",
      bio: p.bio || "",
      skills: (p.skills || []).join(", "),
      years_experience: p.years_experience || 0,
      availability: p.availability || "Open to opportunities",
      github_url: p.github_url || "",
      gitlab_url: p.gitlab_url || "",
      linkedin_url: p.linkedin_url || "",
      linkedin_text: p.linkedin_text || "",
      visible: !!p.visible,
      consent_public_analysis: !!p.consent_public_analysis,
      consent_gitlab_analysis: !!p.consent_gitlab_analysis,
      consent_external_ai: !!p.consent_external_ai,
    });
  }
  useEffect(() => {
    api("/profile")
      .then((data) => load(data.profile))
      .catch((e) => setError(e.message));
  }, []);
  const change = (event) =>
    setForm({
      ...form,
      [event.target.name]:
        event.target.type === "checkbox"
          ? event.target.checked
          : event.target.value,
    });
  async function save(event) {
    event?.preventDefault();
    setBusy("save");
    setError("");
    setSuccess("");
    try {
      const result = await api("/profile", {
        method: "PUT",
        body: {
          ...form,
          skills: form.skills
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          years_experience: Number(form.years_experience),
        },
      });
      load(result.profile);
      setSuccess("Your profile has been saved.");
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy("");
    }
  }
  async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Please choose a file smaller than 5 MB.");
      return;
    }
    setBusy("upload");
    setError("");
    setSuccess("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api("/profile/resume", { method: "POST", body });
      setProfile(result.profile);
      setSuccess(
        "Resume uploaded. Save any profile changes, then run your assessment.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
      event.target.value = "";
    }
  }
  async function analyze() {
    if (!(await save())) return;
    setBusy("analyze");
    setError("");
    try {
      await api("/profile/analyze", { method: "POST" });
      navigate("/app/assessment");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  async function importLinkedin(file) {
    if (linkedinRequest.current || busy || !file) return;
    if (file.size > 5 * 1024 * 1024) {
      setLinkedinError("Please choose a LinkedIn export smaller than 5 MB.");
      return;
    }
    if (!/\.(pdf|txt|csv|zip)$/i.test(file.name)) {
      setLinkedinError("Please upload a PDF, TXT, CSV, or ZIP file.");
      return;
    }
    linkedinRequest.current = true;
    setLinkedinError("");
    setSuccess("");
    setBusy("linkedin-import");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api("/profile/linkedin/import", { method: "POST", body });
      setProfile(result.profile);
      setSuccess("Your LinkedIn export has been imported. Review the extracted text below, save any profile changes, then run an assessment.");
    } catch (e) {
      setLinkedinError(e.message);
    } finally {
      setBusy("");
      linkedinRequest.current = false;
    }
  }
  async function removeLinkedin() {
    if (linkedinRequest.current || busy) return;
    linkedinRequest.current = true;
    setLinkedinError("");
    setBusy("linkedin-remove");
    try {
      const result = await api("/profile/linkedin/import", { method: "DELETE" });
      setProfile(result.profile);
      setSuccess("Uploaded LinkedIn content removed. You can upload another export at any time.");
    } catch (e) {
      setLinkedinError(e.message);
    } finally {
      setBusy("");
      linkedinRequest.current = false;
    }
  }
  if (!form) return error ? <Alert error={error} /> : <Spinner />;
  return (
    <>
      <PageHeader
        kicker="MAKE IT YOURS"
        title="Your story, in focus."
        description="Help the right team understand what you bring."
      >
        <span className={`badge ${profile.visible ? "green" : "neutral"}`}>
          {profile.visible ? <Eye size={13} /> : <LockKeyhole size={13} />}
          {profile.visible ? "Discoverable" : "Private profile"}
        </span>
      </PageHeader>
      <Alert error={error} />
      <Alert>{success}</Alert>
      <form onSubmit={save}>
        <div className="editor-grid">
          <div className="editor-main">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>The essentials</h2>
                  <p>A clear introduction to you and your work.</p>
                </div>
                <span className="section-number">01</span>
              </div>
              <div className="form-body">
                <Field
                  label="Professional headline"
                  name="headline"
                  value={form.headline}
                  onChange={change}
                  placeholder="e.g. Backend engineer building reliable systems"
                  maxLength={160}
                />
                <div className="form-row">
                  <Field
                    label="Location"
                    name="location"
                    value={form.location}
                    onChange={change}
                    placeholder="City, country or Remote"
                    maxLength={100}
                  />
                  <Field
                    label="Years of experience"
                    name="years_experience"
                    value={form.years_experience}
                    onChange={change}
                    type="number"
                    min="0"
                    max="80"
                    step="0.5"
                  />
                </div>
                <Textarea
                  label="A little about you"
                  name="bio"
                  value={form.bio}
                  onChange={change}
                  rows={4}
                  maxLength={5000}
                  placeholder="What have you built? What matters to you in your next role?"
                />
                <Field
                  label="Skills"
                  hint="Separate each skill with a comma. Focus on skills you can demonstrate."
                  name="skills"
                  value={form.skills}
                  onChange={change}
                  maxLength={2000}
                  placeholder="Python, React, Product strategy, Research"
                />
                <label className="field">
                  <span>Availability</span>
                  <select
                    name="availability"
                    value={form.availability}
                    onChange={change}
                  >
                    <option>Open to opportunities</option>
                    <option>Actively looking</option>
                    <option>Open to conversations</option>
                    <option>Not currently looking</option>
                  </select>
                </label>
              </div>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Your resume</h2>
                  <p>The starting point for your evidence assessment.</p>
                </div>
                <span className="section-number">02</span>
              </div>
              <div className="form-body">
                <input
                  type="file"
                  ref={fileRef}
                  accept=".pdf,.docx,.txt"
                  onChange={upload}
                  hidden
                />
                <button
                  type="button"
                  className="upload-zone"
                  onClick={() => fileRef.current?.click()}
                  disabled={!!busy}
                >
                  {busy === "upload" ? (
                    <LoaderCircle className="spin" size={30} />
                  ) : (
                    <UploadCloud size={31} />
                  )}
                  <b>
                    {profile.resume_filename
                      ? "Replace your resume"
                      : "Choose your resume"}
                  </b>
                  <span>PDF, DOCX or TXT · Up to 5 MB</span>
                  <small>
                    Choose a text-based document. Scanned images aren’t
                    supported yet.
                  </small>
                </button>
                {profile.resume_filename && (
                  <div className="uploaded-file">
                    <FileText size={19} />
                    <div>
                      <b>{profile.resume_filename}</b>
                      <small>
                        Uploaded securely · Not shared with companies
                      </small>
                    </div>
                    <CheckCircle2 size={18} />
                  </div>
                )}
                <div className="note-line compact">
                  <LockKeyhole size={16} />
                  <p>
                    Your original file stays private. Published assessments show
                    selected evidence excerpts.
                  </p>
                </div>
              </div>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Work beyond your resume</h2>
                  <p>Optional context. Always with your permission.</p>
                </div>
                <span className="section-number">03</span>
              </div>
              <div className="form-body">
                <Field
                  label="GitHub profile"
                  name="github_url"
                  type="url"
                  value={form.github_url}
                  onChange={change}
                  placeholder="https://github.com/your-username"
                  maxLength={250}
                  hint="We can review your public repositories and README content. A GitHub account is never required for a strong score."
                />
                <Field
                  label="GitLab.com profile"
                  name="gitlab_url"
                  type="url"
                  value={form.gitlab_url}
                  onChange={change}
                  placeholder="https://gitlab.com/your.username"
                  maxLength={250}
                  hint="Optional GitLab.com personal profile. With your permission, we can read public personal projects, README content, and languages. Having an account does not affect your evidence score."
                />
                <Field
                  label="LinkedIn profile"
                  name="linkedin_url"
                  type="url"
                  value={form.linkedin_url}
                  onChange={change}
                  placeholder="https://www.linkedin.com/in/your-profile"
                  maxLength={350}
                  disabled={!!busy}
                  hint="Optional reference link only. Candoc does not fetch or scrape LinkedIn pages."
                />
                <LinkedinImportControl
                  imported={profile.linkedin_import}
                  aiConsent={form.consent_external_ai}
                  busy={busy}
                  error={linkedinError}
                  onImport={importLinkedin}
                  onRemove={removeLinkedin}
                />
                <Textarea
                  label="Or paste your LinkedIn experience or About section"
                  name="linkedin_text"
                  value={form.linkedin_text}
                  onChange={change}
                  rows={5}
                  maxLength={30000}
                  placeholder="Paste the relevant content from your own LinkedIn profile…"
                  hint="Pasted content stays separate from your uploaded export. Both are candidate-provided context. Missing LinkedIn content never lowers your evidence score."
                />
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    name="consent_public_analysis"
                    checked={form.consent_public_analysis}
                    onChange={change}
                  />
                  <span>
                    I allow Candoc to read public GitHub data from the profile
                    I’ve provided when I run an assessment.
                    <small>
                      You can withdraw this permission at any time. LinkedIn
                      content comes only from an export you upload or text you paste.
                    </small>
                  </span>
                </label>
                <label className="checkbox-row platform-consent">
                  <input
                    type="checkbox"
                    name="consent_gitlab_analysis"
                    checked={form.consent_gitlab_analysis}
                    onChange={change}
                  />
                  <span>
                    I allow Candoc to read public GitLab.com data from the profile
                    I’ve provided when I run an assessment.
                    <small>
                      Optional and separate from GitHub permission. You can
                      withdraw this permission at any time. Public account data
                      does not independently verify authorship or employment.
                    </small>
                  </span>
                </label>
                <label className="checkbox-row ai-consent">
                  <input
                    type="checkbox"
                    name="consent_external_ai"
                    checked={form.consent_external_ai}
                    onChange={change}
                  />
                  <span>
                    I allow Candoc to send relevant resume, pasted or uploaded LinkedIn,
                    and public GitHub and GitLab excerpts to OpenAI for a deeper
                    qualitative review.
                    <small>
                      Optional. The five-part evidence score works without this.
                      AI commentary is supplementary and requires human review.
                      Withdraw permission here at any time.
                    </small>
                  </span>
                </label>
              </div>
            </section>
          </div>
          <aside className="editor-aside">
            <section className="panel publish-panel">
              <span className="panel-icon">
                <Eye size={23} />
              </span>
              <h3>Your profile, your terms.</h3>
              <p>
                When discoverable, signed-in companies can see your profile and
                assessment and send an introduction.
              </p>
              <label className="toggle-row">
                <span>Make me discoverable</span>
                <input
                  type="checkbox"
                  name="visible"
                  checked={form.visible}
                  onChange={change}
                />
                <i />
              </label>
              <p className="small-muted">
                Your email stays private until you accept an introduction.
              </p>
              <button
                className="button dark full"
                type="submit"
                disabled={!!busy}
              >
                {busy === "save" ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Check size={17} />
                )}{" "}
                Save profile
              </button>
              <button
                className="button outline full"
                type="button"
                onClick={analyze}
                disabled={!!busy}
              >
                {busy === "analyze" ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Sparkles size={17} />
                )}
                {busy === "analyze"
                  ? "Reviewing your evidence…"
                  : "Save & run assessment"}
              </button>
              <Link className="aside-link" to="/methodology">
                What goes into my score? <ArrowUpRight size={13} />
              </Link>
            </section>
            <div className="editor-tip">
              <Sprout size={21} />
              <b>A small tip</b>
              <p>
                Specific examples tell a stronger story than long lists of
                keywords. Show what you did, how you did it, and what changed.
              </p>
            </div>
          </aside>
        </div>
      </form>
    </>
  );
}

function LinkedinImportControl({ imported, aiConsent, busy, error, onImport, onRemove }) {
  const [confirmRemove, setConfirmRemove] = useState(false);
  const fileRef = useRef(null);
  async function choose(event) {
    const file = event.target.files?.[0];
    if (file) await onImport(file);
    event.target.value = "";
  }
  return (
    <div className="linkedin-import">
      <div className="linkedin-import-heading"><Linkedin size={18} /><h3>Upload your LinkedIn profile export</h3></div>
      <p>Bring your LinkedIn experience into focus with a file you export yourself. Upload your profile PDF or a data export ZIP containing professional information such as Profile, Positions, Education, and Skills.</p>
      <details className="linkedin-export-help"><summary>How to get your export</summary><ol><li><b>PDF (recommended):</b> On LinkedIn desktop, open Me → your profile → More or Resources → Save to PDF. This option is available for some members and English profiles; it is not available in the mobile app.</li><li><b>ZIP alternative:</b> Open Me → Settings &amp; Privacy → Data Privacy → How LinkedIn uses your data → Download your data. Select professional categories, then Request archive.</li><li>Upload the file here, review the extracted text, and run your Candoc assessment. Choose professional data only and keep the file under 5 MB.</li></ol><p>LinkedIn’s guides: <a href="https://www.linkedin.com/help/linkedin/answer/a541960" target="_blank" rel="noreferrer">Save profile as PDF <ExternalLink size={11} /></a> · <a href="https://www.linkedin.com/help/linkedin/answer/a1339364" target="_blank" rel="noreferrer">Download your data <ExternalLink size={11} /></a></p></details>
      <input type="file" ref={fileRef} accept=".pdf,.txt,.csv,.zip" onChange={choose} hidden />
      <Alert error={error} />
      <button type="button" className="upload-zone linkedin-export-zone" onClick={() => fileRef.current?.click()} disabled={!!busy}>{busy === "linkedin-import" ? <LoaderCircle className="spin" size={27} /> : <UploadCloud size={28} />}<b>{busy === "linkedin-import" ? "Reading your export…" : imported ? "Replace your LinkedIn export" : "Choose your LinkedIn export"}</b><span>PDF, TXT, CSV or ZIP · Up to 5 MB</span><small>Only upload your own profile information.</small></button>
      <p className="linkedin-export-privacy">We retain extracted professional text, not the original uploaded file. For ZIP exports, only supported professional CSV sections are read; connections, messages, and other personal files are ignored. Imported statements remain candidate-provided and are not independently verified.</p>
      {imported && <div className="linkedin-import-result" role="status"><span className="badge green">Candidate-provided export</span>{imported.filename && <strong className="linkedin-export-filename"><FileText size={15} />{imported.filename}</strong>}{imported.imported_at && <small>Imported {formatDate(imported.imported_at)}</small>}<p>{imported.detail}</p>{imported.sections?.length > 0 && <div className="chips linkedin-export-sections">{imported.sections.map((section, i) => <span key={i}>{typeof section === "string" ? section : section?.name || section?.type || "Professional section"}</span>)}</div>}{imported.text && <label className="field"><span>Review extracted professional text</span><textarea value={imported.text} readOnly rows={7} aria-label="Uploaded LinkedIn export text, read only" /><small>Replace the file or remove the import if this content does not reflect what you want to share.</small></label>}<button type="button" className="button outline small" onClick={() => setConfirmRemove(true)} disabled={!!busy}><Trash2 size={14} />Remove uploaded content</button></div>}
      <p className="linkedin-ai-note">{aiConsent ? "Your separate AI permission is on. Uploaded LinkedIn excerpts may be sent to OpenAI when you run an assessment." : "Uploading does not authorize OpenAI processing. That requires the separate AI checkbox below."}</p>
      {confirmRemove && <Modal title="Remove uploaded LinkedIn content?" close={() => setConfirmRemove(false)}><p className="modal-description">This removes the extracted text from this upload and clears its assessment context. Your separately pasted LinkedIn content is kept. You can upload another file whenever you choose.</p><div className="modal-actions"><button type="button" className="button outline" onClick={() => setConfirmRemove(false)}>Keep content</button><button type="button" className="button danger" disabled={!!busy} onClick={async () => { await onRemove(); setConfirmRemove(false); }}>{busy === "linkedin-remove" ? <LoaderCircle className="spin" size={16} /> : <Trash2 size={16} />}Remove content</button></div></Modal>}
    </div>
  );
}

function AssessmentReport({ assessment, name, compact = false }) {
  const [expanded, setExpanded] = useState({});
  if (!assessment)
    return (
      <Empty icon={BarChart3} title="Your story is still taking shape.">
        An assessment will appear here once a resume has been uploaded and
        reviewed.
      </Empty>
    );
  return (
    <div className={compact ? "assessment compact-report" : "assessment"}>
      <section className="assessment-summary">
        <div
          className="score-ring"
          style={{
            "--score":
              Math.max(0, Math.min(100, (Number(assessment.score) / 5) * 100)) +
              "%",
          }}
        >
          <div>
            <b>{number(assessment.score)}</b>
            <span>out of 5</span>
          </div>
        </div>
        <div>
          <span className="section-kicker">EVIDENCE SCORE</span>
          <h2>
            {name
              ? `${name.split(" ")[0]}’s work, in context.`
              : "A clearer picture of your experience."}
          </h2>
          <p>{assessment.summary}</p>
          <div className="report-meta">
            <span className="badge neutral">
              {assessment.confidence || "Limited"} confidence
            </span>
            <span>Reviewed {formatDate(assessment.analyzed_at)}</span>
            <span>Rubric {assessment.version || "v1"}</span>
          </div>
        </div>
      </section>
      <div className="assessment-notice">
        <ShieldCheck size={19} />
        <p>
          This score describes evidence in the supplied material, not a person’s
          potential or suitability for a job. It supports a conversation and
          always requires human review.
        </p>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>The story behind the score</h2>
            <p>Five dimensions. Visible evidence. Practical next steps.</p>
          </div>
        </div>
        <div className="dimensions">
          {(assessment.dimensions || []).map((d) => (
            <div className="dimension" key={d.key}>
              <button
                className="dimension-toggle"
                onClick={() =>
                  setExpanded({ ...expanded, [d.key]: !expanded[d.key] })
                }
                aria-expanded={!!expanded[d.key]}
              >
                <div>
                  <b>{d.label}</b>
                  <small>
                    {Math.round(Number(d.weight) * 100)}% of assessment
                  </small>
                </div>
                <div className="dimension-bar">
                  <i style={{ width: (Number(d.score) / 5) * 100 + "%" }} />
                </div>
                <strong>
                  {number(d.score)}
                  <small>/5</small>
                </strong>
                <ChevronDown
                  className={expanded[d.key] ? "rotated" : ""}
                  size={17}
                />
              </button>
              {expanded[d.key] && (
                <div className="dimension-evidence">
                  <div>
                    <span className="section-kicker">SUPPORTING EVIDENCE</span>
                    {d.evidence?.length ? (
                      d.evidence.map((e, i) => (
                        <blockquote key={i}>
                          {typeof e === "string" ? e : JSON.stringify(e)}
                        </blockquote>
                      ))
                    ) : (
                      <p>
                        No specific supporting excerpt was found in the supplied
                        material.
                      </p>
                    )}
                  </div>
                  {!!d.improvements?.length && (
                    <div>
                      <span className="section-kicker">MAKE IT CLEARER</span>
                      <ul>
                        {d.improvements.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
      <SemanticReview review={assessment.semantic_review} />
      <div className="report-columns">
        <section className="panel">
          <div className="panel-heading">
            <h2>
              <CheckCircle2 size={19} /> What comes through
            </h2>
          </div>
          <div className="form-body">
            {assessment.strengths?.length ? (
              <ul className="insight-list">
                {assessment.strengths.map((s, i) => (
                  <li key={i}>
                    <Check size={16} />
                    {s}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="small-muted">
                More evidence will help surface your strengths.
              </p>
            )}
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>
              <Sprout size={19} /> Room for more context
            </h2>
          </div>
          <div className="form-body">
            {assessment.improvements?.length ? (
              <ul className="insight-list">
                {assessment.improvements.map((s, i) => (
                  <li key={i}>
                    <Plus size={16} />
                    {s}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="small-muted">
                Keep your profile current as your work evolves.
              </p>
            )}
          </div>
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Sources & transparency</h2>
            <p>Exactly what was available for this assessment.</p>
          </div>
        </div>
        <div className="sources">
          {(assessment.sources || []).map((source, i) => (
            <div className="source-row" key={i}>
              <span className="source-icon">
                {source.type?.toLowerCase().includes("github") ? (
                  <Github size={19} />
                ) : source.type?.toLowerCase().includes("gitlab") ? (
                  <Gitlab size={19} />
                ) : source.type?.toLowerCase().includes("linkedin") ? (
                  <Linkedin size={19} />
                ) : (
                  <FileText size={19} />
                )}
              </span>
              <div>
                <b>{source.type?.includes("linkedin") ? (source.type === "linkedin_export" ? "LinkedIn export · Candidate provided" : "LinkedIn content · Candidate provided") : source.type === "gitlab" ? "GitLab public work" : source.type?.replaceAll("_", " ")}</b>
                <p>{source.detail}</p>
                {source.url && isPublicSourceUrl(source.url) && (
                    <a href={source.url} target="_blank" rel="noreferrer">
                      View source <ExternalLink size={11} />
                    </a>
                  )}
              </div>
              <span className="badge neutral">
                {source.status?.replaceAll("_", " ")}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
function SemanticReview({ review }) {
  const status = review?.status || "not_configured";
  const labels = {
    complete: "Review available",
    consent_required: "Your permission needed",
    not_configured: "Not configured",
    unavailable: "Temporarily unavailable",
  };
  return (
    <section className="panel semantic-panel">
      <div className="panel-heading">
        <div>
          <h2>
            <Sparkles size={18} /> A deeper look at your work
          </h2>
          <p>Optional AI commentary · Separate from your evidence score</p>
        </div>
        <span
          className={`badge ${status === "complete" ? "green" : "neutral"}`}
        >
          {labels[status] || status}
        </span>
      </div>
      <div className="form-body">
        {status === "complete" ? (
          <>
            <p className="semantic-detail">
              {review.detail ||
                "AI-assisted observations from the material you chose to share. Treat these as conversation starters, with human review."}
            </p>
            <div className="semantic-observations">
              {review.observations?.map((item, i) => (
                <article key={i}>
                  <span className="section-kicker">
                    {item.source?.replaceAll("_", " ")}
                  </span>
                  <blockquote>{item.quote}</blockquote>
                  <p>{item.interpretation}</p>
                </article>
              ))}
            </div>
            {review.questions?.length > 0 && (
              <>
                <h3 className="semantic-subtitle">
                  Questions for a better conversation
                </h3>
                <ul className="document-list">
                  {review.questions.map((question, i) => (
                    <li key={i}>{question}</li>
                  ))}
                </ul>
              </>
            )}
            {review.limitations?.length > 0 && (
              <div className="semantic-limits">
                <Info size={15} />
                <p>{review.limitations.join(" ")}</p>
              </div>
            )}
            <p className="semantic-provider">
              Generated with {review.provider || "OpenAI"}
              {review.model ? ` · ${review.model}` : ""}. Commentary can be
              incorrect and does not verify employment or determine suitability.
            </p>
          </>
        ) : (
          <>
            <p className="semantic-detail">
              {review?.detail ||
                (status === "consent_required"
                  ? "A deeper review is optional. You can allow it in your profile settings. Relevant excerpts are sent to OpenAI only with your separate permission."
                  : status === "unavailable"
                    ? "The optional AI review could not be completed. Your transparent evidence assessment is still available."
                    : "The optional AI review has not been configured by the operator. Your transparent evidence assessment works independently.")}
            </p>
            {status === "consent_required" && (
              <Link to="/app/profile" className="text-link semantic-manage">
                Manage my permissions <ArrowUpRight size={14} />
              </Link>
            )}
          </>
        )}
      </div>
    </section>
  );
}
function MyAssessment() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/profile")
      .then((d) => setProfile(d.profile))
      .catch((e) => setError(e.message));
  }, []);
  async function analyze() {
    setBusy(true);
    setError("");
    try {
      const data = await api("/profile/analyze", { method: "POST" });
      setProfile(data.profile);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        kicker="UNDERSTAND YOUR EVIDENCE"
        title="More than a number."
        description="Explore what your experience communicates, and where a little context helps."
      >
        <button
          className="button outline"
          onClick={analyze}
          disabled={busy || !profile}
        >
          {busy ? (
            <LoaderCircle className="spin" size={17} />
          ) : (
            <RefreshCw size={17} />
          )}
          {busy ? "Reviewing evidence…" : "Run assessment"}
        </button>
      </PageHeader>
      <Alert error={error} />
      {profile ? (
        profile.assessment ? (
          <AssessmentReport assessment={profile.assessment} />
        ) : (
          <div className="panel">
            <Empty
              icon={Sparkles}
              title="Let’s bring your experience into focus."
              action={
                <Link className="button dark" to="/app/profile">
                  Upload your resume <ArrowRight size={17} />
                </Link>
              }
            >
              Start with a text-based resume. We’ll review the evidence using
              five transparent criteria and give you useful ways to strengthen
              your story.
            </Empty>
          </div>
        )
      ) : (
        !error && <Spinner />
      )}
      <div className="note-line">
        <Info size={17} />
        <p>
          Missing external profiles never lower your score.{" "}
          <Link to="/methodology">Read the full methodology.</Link>
        </p>
      </div>
    </>
  );
}

function TalentDirectory() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    search: "",
    skill: "",
    location: "",
    min_score: "",
    sort: "recent",
  });
  const [showFilters, setShowFilters] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError("");
      const query = new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v !== ""),
      );
      api("/candidates?" + query, { signal: controller.signal })
        .then((d) => setCandidates(d.candidates))
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [filters]);
  function change(e) {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  }
  return (
    <>
      <PageHeader
        kicker="GOOD PEOPLE. REAL WORK."
        title="Meet your next teammate."
        description="Look beyond the keywords. Start with the person and the evidence."
      />
      <div className="directory-toolbar">
        <label className="search-input">
          <Search size={19} />
          <input
            aria-label="Search candidates"
            placeholder="Search by name, role, or skill…"
            name="search"
            value={filters.search}
            onChange={change}
          />
        </label>
        <button
          className={`button outline ${showFilters ? "selected" : ""}`}
          onClick={() => setShowFilters(!showFilters)}
        >
          <SlidersHorizontal size={17} /> Filters
        </button>
        <label className="sort-label">
          <span>Sort by</span>
          <select
            name="sort"
            value={filters.sort}
            onChange={change}
            aria-label="Sort candidates"
          >
            <option value="recent">Recently joined</option>
            <option value="score">Evidence score</option>
          </select>
        </label>
      </div>
      {showFilters && (
        <div className="directory-filters">
          <Field
            label="Skill"
            name="skill"
            value={filters.skill}
            onChange={change}
            placeholder="e.g. Python"
          />
          <Field
            label="Location"
            name="location"
            value={filters.location}
            onChange={change}
            placeholder="e.g. Remote"
          />
          <label className="field">
            <span>Minimum evidence score</span>
            <select
              name="min_score"
              value={filters.min_score}
              onChange={change}
            >
              <option value="">Any score</option>
              <option value="2">2.0 and above</option>
              <option value="3">3.0 and above</option>
              <option value="4">4.0 and above</option>
            </select>
          </label>
          <button
            className="text-link"
            onClick={() =>
              setFilters({
                search: "",
                skill: "",
                location: "",
                min_score: "",
                sort: "recent",
              })
            }
          >
            Clear all
          </button>
        </div>
      )}
      <div className="directory-info">
        <span>
          {loading
            ? "Finding people…"
            : `${candidates.length} ${candidates.length === 1 ? "person" : "people"} to meet`}
        </span>
        <span>
          <ShieldCheck size={14} /> Shared by candidates, on their terms
        </span>
      </div>
      <Alert error={error} />
      {loading ? (
        <Spinner text="Finding your next conversation…" />
      ) : candidates.length ? (
        <div className="candidate-grid">
          {candidates.map((p) => (
            <CandidateCard key={p.id} profile={p} />
          ))}
        </div>
      ) : (
        !error && (
          <div className="panel">
            <Empty
              icon={Users}
              title={
                Object.values(filters).some((v) => v && v !== "recent")
                  ? "No profiles match just yet."
                  : "Good conversations start here."
              }
            >
              {Object.values(filters).some((v) => v && v !== "recent")
                ? "Try a broader search or remove a filter. New people and new possibilities arrive over time."
                : "This is a new community. As candidates publish their profiles, you’ll find them here. There are no sample candidates in this directory."}
            </Empty>
          </div>
        )
      )}
      <div className="note-line">
        <Info size={17} />
        <p>
          Evidence scores describe the supplied material. They aren’t a hiring
          recommendation. Review every profile in the context of your role.
        </p>
      </div>
    </>
  );
}
function CandidateCard({ profile: p }) {
  return (
    <article className="candidate-card">
      <div className="candidate-card-top">
        <div className="avatar">{initials(p.name)}</div>
        {p.assessment && (
          <div className="card-score">
            <Sparkles size={13} />
            <b>{number(p.assessment.score)}</b>
            <span>/5</span>
          </div>
        )}
      </div>
      <Link to={`/app/talent/${p.id}`} className="candidate-name">
        <h3>{p.name}</h3>
      </Link>
      <p className="candidate-headline">
        {p.headline || "Professional profile"}
      </p>
      <div className="candidate-meta">
        {p.location && (
          <span>
            <MapPin size={13} />
            {p.location}
          </span>
        )}
        {Number(p.years_experience) > 0 && (
          <span>
            <BriefcaseBusiness size={13} />
            {p.years_experience} years of experience
          </span>
        )}
      </div>
      <p className="candidate-bio">
        {p.bio ||
          "Explore this profile to learn more about their work and experience."}
      </p>
      <div className="chips">
        {(p.skills || []).slice(0, 4).map((skill) => (
          <span key={skill}>{skill}</span>
        ))}
        {p.skills?.length > 4 && <span>+{p.skills.length - 4}</span>}
      </div>
      <div className="candidate-card-bottom">
        <span>
          <i />
          {p.availability || "Open to conversations"}
        </span>
        <Link
          to={`/app/talent/${p.id}`}
          aria-label={`View ${p.name}’s profile`}
        >
          <ArrowUpRight size={20} />
        </Link>
      </div>
      {p.assessment && (
        <span className="score-caption">
          Evidence score · Not a hiring recommendation
        </span>
      )}
    </article>
  );
}
function TalentDetail() {
  const location = useLocation();
  const id = location.pathname.split("/").pop();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [intro, setIntro] = useState(false);
  const [success, setSuccess] = useState("");
  useEffect(() => {
    api("/candidates/" + encodeURIComponent(id))
      .then((d) => setProfile(d.candidate))
      .catch((e) => setError(e.message));
  }, [id]);
  if (!profile) return error ? <Alert error={error} /> : <Spinner />;
  return (
    <>
      <Link className="back-link" to="/app/talent">
        <ArrowLeft size={16} /> Back to discovery
      </Link>
      <section className="detail-hero">
        <div className="avatar large">{initials(profile.name)}</div>
        <div>
          <span className="section-kicker">A PERSON WORTH KNOWING</span>
          <h1>{profile.name}</h1>
          <h2>{profile.headline || "Professional profile"}</h2>
          <div className="detail-meta">
            {profile.location && (
              <span>
                <MapPin size={15} />
                {profile.location}
              </span>
            )}
            {Number(profile.years_experience) > 0 && (
              <span>
                <BriefcaseBusiness size={15} />
                {profile.years_experience} years of experience
              </span>
            )}
            <span>
              <span className="live-dot" />
              {profile.availability || "Open to conversations"}
            </span>
          </div>
        </div>
        <button className="button dark" onClick={() => setIntro(true)}>
          Request an introduction <ArrowUpRight size={17} />
        </button>
      </section>
      <Alert>{success}</Alert>
      <section className="panel">
        <div className="panel-heading">
          <h2>The person behind the profile</h2>
          <div className="social-links">
            {profile.github_url && (
              <a
                href={profile.github_url}
                target="_blank"
                rel="noreferrer"
                aria-label="GitHub profile"
              >
                <Github size={19} />
              </a>
            )}
            {profile.gitlab_url && isPublicSourceUrl(profile.gitlab_url) && (
              <a href={profile.gitlab_url} target="_blank" rel="noreferrer" aria-label="GitLab profile" title="GitLab.com profile">
                <Gitlab size={19} />
              </a>
            )}
            {profile.linkedin_url && (
              <a
                href={profile.linkedin_url}
                target="_blank"
                rel="noreferrer"
                aria-label="LinkedIn profile"
              >
                <Linkedin size={19} />
              </a>
            )}
          </div>
        </div>
        <div className="form-body">
          <p className="profile-bio">
            {profile.bio || "This person is still adding to their story."}
          </p>
          <div className="chips">
            {(profile.skills || []).map((skill) => (
              <span key={skill}>{skill}</span>
            ))}
          </div>
        </div>
      </section>
      <h2 className="subsection-title">Experience, with evidence.</h2>
      <AssessmentReport assessment={profile.assessment} name={profile.name} />
      {intro && (
        <IntroModal
          candidate={profile}
          close={() => setIntro(false)}
          onSuccess={() => {
            setIntro(false);
            setSuccess(
              "Your introduction has been sent. They’ll choose whether to connect.",
            );
          }}
        />
      )}
    </>
  );
}
function IntroModal({ candidate, close, onSuccess }) {
  const [form, setForm] = useState({
    role_title: "",
    message: "",
    salary_range: "",
    work_mode: "Remote",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/introductions", {
        method: "POST",
        body: { candidate_id: candidate.id, ...form },
      });
      onSuccess();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Start a good conversation." close={close}>
      <p className="modal-description">
        Tell {candidate.name.split(" ")[0]} why their work caught your eye and
        what you have in mind.
      </p>
      <form onSubmit={submit}>
        <Alert error={error} />
        <Field
          label="Role title"
          value={form.role_title}
          name="role_title"
          onChange={change}
          required
          maxLength={160}
          placeholder="e.g. Senior Backend Engineer"
        />
        <div className="form-row">
          <Field
            label="Compensation range (optional)"
            value={form.salary_range}
            name="salary_range"
            onChange={change}
            maxLength={100}
            placeholder="Include amount, currency & period"
          />
          <label className="field">
            <span>Work arrangement</span>
            <select name="work_mode" value={form.work_mode} onChange={change}>
              <option>Remote</option>
              <option>Hybrid</option>
              <option>On-site</option>
              <option>Flexible</option>
            </select>
          </label>
        </div>
        <Textarea
          label="Your introduction"
          name="message"
          value={form.message}
          onChange={change}
          required
          minLength={20}
          maxLength={5000}
          rows={5}
          placeholder="What stood out? What would they work on? Why might this be a good conversation?"
        />
        <div className="note-line compact">
          <LockKeyhole size={15} />
          <p>
            Contact details are shared only if they accept your introduction.
          </p>
        </div>
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancel
          </button>
          <button className="button dark" disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <Send size={16} />
            )}{" "}
            Send introduction
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Inbox() {
  const { user } = useAuth();
  const company = user.role === "company";
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(null);
  const [confirm, setConfirm] = useState(null);
  useEffect(() => {
    api("/introductions")
      .then((d) => setItems(d.introductions))
      .catch((e) => setError(e.message));
  }, []);
  async function update(id, status) {
    setBusy(id);
    setError("");
    try {
      const data = await api("/introductions/" + id, {
        method: "PATCH",
        body: { status },
      });
      setItems(
        items.map((i) =>
          i.id === id ? data.introduction || { ...i, status } : i,
        ),
      );
      setConfirm(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }
  const visible = items?.filter((i) => filter === "all" || i.status === filter);
  return (
    <>
      <PageHeader
        kicker="MEANINGFUL CONNECTIONS"
        title={
          company
            ? "Conversations worth starting."
            : "A new possibility starts here."
        }
        description={
          company
            ? "Keep track of the introductions you’ve sent and the doors that open."
            : "Thoughtful introductions from companies. You decide what comes next."
        }
      />
      <Alert error={error} />
      <div className="tabs">
        {["all", "pending", "accepted", "declined"].map((status) => (
          <button
            className={filter === status ? "active" : ""}
            key={status}
            onClick={() => setFilter(status)}
          >
            {status === "all"
              ? "All introductions"
              : status[0].toUpperCase() + status.slice(1)}
            <span>
              {items?.filter((i) => status === "all" || i.status === status)
                .length || 0}
            </span>
          </button>
        ))}
      </div>
      {items === null ? (
        !error && <Spinner />
      ) : visible.length ? (
        <div className="introduction-list">
          {visible.map((item) => (
            <article className="introduction-card" key={item.id}>
              <div className="introduction-top">
                <span className="avatar company">
                  <BriefcaseBusiness size={24} />
                </span>
                <div>
                  <h3>{company ? item.candidate_name : item.company_name}</h3>
                  <p>{item.role_title}</p>
                </div>
                <span
                  className={`badge ${item.status === "accepted" ? "green" : item.status === "declined" ? "neutral" : "amber"}`}
                >
                  {item.status}
                </span>
              </div>
              <div className="introduction-details">
                {item.work_mode && (
                  <span>
                    <MapPin size={14} />
                    {item.work_mode}
                  </span>
                )}
                {item.salary_range && <span>{item.salary_range}</span>}
                <span>{formatDate(item.created_at)}</span>
              </div>
              <p className="introduction-message">{item.message}</p>
              <div className="introduction-bottom">
                {item.status === "accepted" ? (
                  <div className="accepted-contact">
                    <CheckCheck size={18} />
                    <span>
                      {item.contact_email ? (
                        <>
                          You’re connected.{" "}
                          <a href={`mailto:${item.contact_email}`}>
                            {item.contact_email}
                          </a>
                        </>
                      ) : (
                        "Introduction accepted. Your contact details have been shared with this company."
                      )}
                    </span>
                  </div>
                ) : company ? (
                  <span className="small-muted">
                    {item.status === "pending"
                      ? "Awaiting their response. We’ll show the status here."
                      : "They’ve chosen to pass on this introduction."}
                  </span>
                ) : item.status === "pending" ? (
                  <>
                    <p className="small-muted">
                      <LockKeyhole size={13} /> Your email stays private until
                      you accept.
                    </p>
                    <div>
                      <button
                        className="button outline small"
                        onClick={() => update(item.id, "declined")}
                        disabled={busy === item.id}
                      >
                        Pass for now
                      </button>
                      <button
                        className="button dark small"
                        onClick={() => setConfirm(item)}
                        disabled={busy === item.id}
                      >
                        <Check size={15} /> Accept introduction
                      </button>
                    </div>
                  </>
                ) : (
                  <span className="small-muted">
                    You’ve passed on this introduction. Your contact details
                    remain private.
                  </span>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="panel">
          <Empty
            icon={Mail}
            title={
              filter === "all"
                ? company
                  ? "A thoughtful hello can open a door."
                  : "Your next hello is on its way."
                : `No ${filter} introductions.`
            }
            action={
              company && filter === "all" ? (
                <Link to="/app/talent" className="button dark">
                  Discover talent <ArrowRight size={17} />
                </Link>
              ) : null
            }
          >
            {filter === "all"
              ? company
                ? "Find someone whose work stands out and send a personal introduction. Every conversation starts somewhere."
                : "Publish your profile so companies can discover your work. When an introduction arrives, you’ll find it here."
              : "Introductions with this status will appear here."}
          </Empty>
        </div>
      )}
      {confirm && (
        <Modal
          title="Ready to start a conversation?"
          close={() => setConfirm(null)}
        >
          <p className="modal-description">
            Accepting shares your account email with{" "}
            <b>{confirm.company_name}</b> so you can discuss the{" "}
            {confirm.role_title} opportunity directly.
          </p>
          <Alert error={error} />
          <div className="modal-actions">
            <button className="button outline" onClick={() => setConfirm(null)}>
              Not yet
            </button>
            <button
              className="button dark"
              disabled={busy === confirm.id}
              onClick={() => update(confirm.id, "accepted")}
            >
              {busy === confirm.id ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Check size={16} />
              )}{" "}
              Accept & share email
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
function AccountSettings() {
  const { user, setUser } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [phrase, setPhrase] = useState("");
  const navigate = useNavigate();
  async function download() {
    setBusy("export");
    setError("");
    try {
      const data = await api("/account/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "candoc-my-data.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  async function remove() {
    setBusy("delete");
    setError("");
    try {
      await api("/account", { method: "DELETE" });
      setUser(null);
      navigate("/");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <PageHeader
        kicker="YOU’RE IN CONTROL"
        title="Your account. Your data."
        description="A clear view of what you share, and the controls to manage it."
      />
      <Alert error={error} />
      <section className="panel settings-panel">
        <div className="panel-heading">
          <h2>Account details</h2>
          <span className="badge neutral">{user.role}</span>
        </div>
        <div className="account-details">
          <div>
            <span>Name</span>
            <b>{user.name}</b>
          </div>
          <div>
            <span>Email</span>
            <b>{user.email}</b>
          </div>
          {user.company_name && (
            <div>
              <span>Company</span>
              <b>{user.company_name}</b>
            </div>
          )}
        </div>
      </section>
      <section className="panel settings-panel">
        <div className="panel-heading">
          <h2>Your data belongs to you</h2>
          <ShieldCheck size={20} />
        </div>
        <div className="settings-action">
          <span className="settings-action-icon">
            <Download size={23} />
          </span>
          <div>
            <h3>Take your story with you</h3>
            <p>
              Download a JSON copy of your account, profile, assessment, and
              introductions.
            </p>
          </div>
          <button
            className="button outline"
            onClick={download}
            disabled={!!busy}
          >
            {busy === "export" ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <Download size={17} />
            )}{" "}
            Export my data
          </button>
        </div>
        <div className="settings-action">
          <span className="settings-action-icon danger">
            <Trash2 size={22} />
          </span>
          <div>
            <h3>Delete your account</h3>
            <p>
              Permanently remove your account, resume, profile, and associated
              records.
            </p>
          </div>
          <button
            className="button danger-outline"
            onClick={() => setConfirm(true)}
          >
            Delete account
          </button>
        </div>
      </section>
      <div className="note-line">
        <LockKeyhole size={17} />
        <p>
          Read our <Link to="/privacy">privacy and data practices</Link> to
          understand how information moves through Candoc.
        </p>
      </div>
      {confirm && (
        <Modal
          title="Delete your Candoc account?"
          close={() => setConfirm(false)}
        >
          <p className="modal-description">
            This permanently deletes your account and associated data. You’ll be
            signed out, and your profile will no longer be discoverable. This
            action cannot be undone.
          </p>
          <Field
            label="Type DELETE to confirm"
            value={phrase}
            onChange={(e) => setPhrase(e.target.value)}
            placeholder="DELETE"
            autoComplete="off"
          />
          <Alert error={error} />
          <div className="modal-actions">
            <button
              className="button outline"
              onClick={() => setConfirm(false)}
            >
              Keep my account
            </button>
            <button
              className="button danger"
              onClick={remove}
              disabled={phrase !== "DELETE" || !!busy}
            >
              {busy === "delete" ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Trash2 size={16} />
              )}{" "}
              Permanently delete
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

function Methodology() {
  const [rubric, setRubric] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/rubric")
      .then(setRubric)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <PublicNav />
      <main className="document-page container">
        <Link className="back-link" to="/">
          <ArrowLeft size={16} /> Back to Candoc
        </Link>
        <span className="section-kicker">OPEN BY DESIGN</span>
        <h1>
          Understand the evidence.
          <br />
          <em>Keep the human perspective.</em>
        </h1>
        <p className="document-lead">
          A resume can show what someone has done. It can’t capture everything
          they could become. Our assessment helps make the supplied evidence
          easier to understand.
        </p>
        <div className="assessment-notice">
          <ShieldCheck size={21} />
          <p>
            Candoc’s evidence score is a transparent document assessment, not a
            hiring decision, employment verification, or prediction of
            performance. People make the decisions.
          </p>
        </div>
        <h2>Five dimensions. A visible rationale.</h2>
        <p>
          {rubric?.description ||
            "We use a published, deterministic rubric to review the clarity and detail of job-relevant evidence. Each dimension is scored from 1 to 5, then combined using the weights below."}
        </p>
        <Alert error={error} />
        {rubric ? (
          <div className="rubric-grid">
            {rubric.dimensions.map((d, i) => (
              <article className="rubric-card" key={d.key}>
                <span>0{i + 1}</span>
                <h3>
                  {d.label}
                  <small>{Math.round(d.weight * 100)}%</small>
                </h3>
                <p>{d.description}</p>
              </article>
            ))}
          </div>
        ) : (
          !error && <Spinner />
        )}
        <h2>How to read a score</h2>
        <p>
          The 1–5 scale describes the amount and specificity of supporting
          evidence in your supplied material. A higher score means more context
          is visible to a reader. It never means someone is a better person or
          automatically more qualified for a role.
        </p>
        <div className="score-scale">
          {[
            ["1", "Limited evidence"],
            ["2", "Some context"],
            ["3", "Developing detail"],
            ["4", "Strong evidence"],
            ["5", "Extensive detail"],
          ].map(([n, label]) => (
            <div key={n}>
              <b>{n}</b>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <h2>What stays out of the equation</h2>
        <p>
          Protected characteristics, name, age, gender, photographs, university
          or employer prestige, career gaps, and social popularity are excluded.
          Missing GitHub, GitLab, or LinkedIn content does not reduce the score.
          Stars, followers, and other popularity counts do not measure professional ability.
        </p>
        <h2>Sources, consent, and limits</h2>
        <p>
          Resume text is extracted from the document you upload. When you opt
          in separately for each service, we can review public GitHub repositories
          or GitLab.com personal projects, README content, and languages from
          your provided profiles. These optional sources add context and do not
          change the numeric evidence score. Linked accounts do not independently
          verify authorship or employment. LinkedIn context comes from a profile export
          you upload or content you paste yourself. Candoc does not fetch or
          scrape LinkedIn pages. PDF, TXT, CSV, and supported professional CSV
          sections in data export ZIPs can be imported. Extracted professional
          text is retained; original upload files are discarded. ZIP connections,
          messages, and other personal files are ignored. Uploaded or pasted
          statements are candidate-provided context, not independent employment
          verification.
        </p>
        <p>
          The numerical evidence assessment uses transparent text-based rules.
          With separate candidate consent, an optional OpenAI review provides
          supplementary qualitative observations and interview questions; it
          does not alter the evidence score. This commentary can be wrong and
          requires human review. The numerical assessment can miss nuance,
          informal experience, nontechnical work, and context outside the
          supplied material. Extracted information is self-reported unless a
          source directly supports it. A source link does not independently
          verify employment or ownership.
        </p>
        {rubric?.limitations?.length > 0 && (
          <ul className="document-list">
            {rubric.limitations.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        )}
        <h2>You can change the story</h2>
        <p>
          Inspect the evidence, edit your profile, replace your resume, and run
          the assessment again. Keep your profile private until you’re
          comfortable with it, and accept only the introductions you want.
          Scores should lead to better questions, never automatic rejection.
        </p>
        <div className="document-end">
          <span>Published rubric · {rubric?.version || "v1"}</span>
          <Link className="button dark" to="/signup">
            Build your profile <ArrowUpRight size={17} />
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
function Privacy() {
  return (
    <>
      <PublicNav />
      <main className="document-page container">
        <Link className="back-link" to="/">
          <ArrowLeft size={16} /> Back to Candoc
        </Link>
        <span className="section-kicker">YOUR STORY STAYS YOURS</span>
        <h1>
          Clear choices.
          <br />
          <em>Thoughtful privacy.</em>
        </h1>
        <p className="document-lead">
          Candoc helps candidates share professional evidence with companies.
          Here’s what we collect, what becomes visible, and what stays in your
          control.
        </p>
        <h2>What we store</h2>
        <p>
          Your account includes your name, email, account type, and a securely
          hashed password. Candidate accounts may include a resume, extracted
          resume text, professional profile, candidate-supplied LinkedIn
          content, extracted professional text from a LinkedIn export you upload,
          public GitHub and GitLab evidence if separately requested, and assessment results.
          We also store introductions and their status.
        </p>
        <h2>Private until you choose otherwise</h2>
        <p>
          Candidate profiles start private. Making a profile discoverable allows
          signed-in company accounts to view its professional information,
          linked public profiles, and assessment, including selected evidence
          excerpts. Your original resume file and account email are not included
          in the directory.
        </p>
        <p>
          Review your resume for sensitive information before assessment:
          evidence excerpts can quote professional material you supplied. Keep
          personal identifiers, confidential employer information, and unrelated
          private details out of uploaded content.
        </p>
        <h2>Introductions and contact details</h2>
        <p>
          Companies send role details and a personal message. If you accept,
          your account email is shared with the company that requested the
          introduction so you can continue the conversation. Declining does not
          share your email. Candoc cannot retract information someone has
          already received.
        </p>
        <h2>Connected professional profiles</h2>
        <p>
          GitHub and GitLab.com enrichment each require their own permission
          and read only public information from the personal profiles you supply.
          GitLab support includes public personal projects, README content, and
          languages on GitLab.com. Account availability does not affect your
          evidence score, and linked work does not independently verify
          authorship or employment. You can withdraw either permission
          in your profile settings and rerun your assessment. LinkedIn profile
          URLs are reference links only and are not fetched or scraped. You can
          upload your own LinkedIn profile PDF, TXT, CSV, or data export ZIP, or
          paste relevant profile text. We retain extracted professional text,
          not the original uploaded file. ZIP imports read only supported
          professional CSV sections such as Profile, Positions, Education, and
          Skills; connections, messages, and unrelated personal files are ignored.
          You can review, replace, or remove your uploaded content at any time.
          Pasted LinkedIn content stays separate. These are candidate-provided
          statements and do not independently verify employment.
          If you separately opt in to deeper AI review, relevant resume,
          pasted or uploaded LinkedIn, and public GitHub and GitLab excerpts are transmitted to OpenAI to
          produce supplementary qualitative commentary. This is optional; the
          evidence score does not require it. Automated filtering limits direct
          contact details before transmission, but you should remove
          confidential or unrelated personal information yourself. The provider
          processes these excerpts under its API data policies.
        </p>
        <h2>Export, visibility, and deletion</h2>
        <p>
          Hide your profile at any time in My profile. Export your data or
          permanently delete your account from Account & privacy. Deletion
          removes your live account, profile, uploaded resume, assessments,
          sessions, and associated introductions. Encrypted transport and access
          controls protect the live service. Root-only daily local backups are
          retained for seven days, so deleted information may persist in those
          backups for up to seven days. There is currently no offsite backup
          replication.
        </p>
        <h2>Cookies and security</h2>
        <p>
          Company identities and email addresses are not independently verified
          in this initial release. Use your own judgment before sharing
          additional information. Password recovery uses an expiring, single-use
          link sent to the account email through our configured mail service. A
          successful reset signs out existing sessions. Email verification on
          signup is not available yet. We use an essential session cookie to
          keep you signed in. Access controls separate candidate and company
          data. The production service uses HTTPS. We do not use advertising
          trackers in the application.
        </p>
        <h2>Responsible use</h2>
        <p>
          Only upload your own resume and profile information, or information
          you are authorized to provide. Companies must use candidate
          information for relevant professional introductions and review people
          in the context of a real role. Evidence scores support human review;
          they must not be used as an automatic employment decision.
        </p>
        <div className="document-end">
          <span>Initial release · November 2026</span>
          <Link className="text-link" to="/methodology">
            Read the evaluation methodology <ArrowRight size={16} />
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
function NotFound() {
  return (
    <>
      <PublicNav />
      <main className="container not-found">
        <span className="section-kicker">A SMALL DETOUR</span>
        <h1>This door doesn’t open here.</h1>
        <p>The page may have moved. Let’s get you back to familiar ground.</p>
        <Link to="/" className="button dark">
          Back to Candoc <ArrowRight size={17} />
        </Link>
      </main>
      <Footer />
    </>
  );
}
function ScrollReset() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}
function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function boot() {
    setLoading(true);
    setError("");
    try {
      const result = await api("/auth/me");
      setUser(result.user);
    } catch (e) {
      setError(
        "We couldn’t reach Candoc. Please check your connection and try again.",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    boot();
  }, []);
  if (loading)
    return (
      <div className="boot-screen">
        <Logo />
        <Spinner text="A new direction for hiring." />
      </div>
    );
  if (error)
    return (
      <div className="boot-screen">
        <Logo />
        <Alert error={error} />
        <button className="button dark" onClick={boot}>
          <RefreshCw size={17} /> Try again
        </button>
      </div>
    );
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      <ScrollReset />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/signup" element={<AuthPage signup />} />
        <Route
          path="/forgot-password"
          element={<PasswordRecovery key="forgot" />}
        />
        <Route
          path="/reset-password"
          element={<PasswordRecovery key="reset" reset />}
        />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/app/*" element={<Workspace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AuthContext.Provider>
  );
}
createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
);
