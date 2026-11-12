import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CheckCircle2, LoaderCircle, Mail, ShieldCheck } from "lucide-react";

export function VerificationPanel({ api, user, onVerified }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  if (!user) return null;
  async function request() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api("/auth/request-verification", {
        method: "POST",
      });
      setMessage(result.detail);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const result = await api("/auth/me");
      if (result.user) onVerified?.(result.user);
      setMessage(
        result.user?.email_verified
          ? "Your email is verified."
          : "Not verified yet. Open the latest link in your email first.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel settings-panel verification-panel">
      <div className="panel-heading">
        <h2>
          <Mail size={18} /> Email verification
        </h2>
        <span className={`badge ${user.email_verified ? "green" : "neutral"}`}>
          {user.email_verified ? "Email verified" : "Verification needed"}
        </span>
      </div>
      <div style={{ padding: "24px" }}>
        <p>
          {user.email_verified
            ? "You have confirmed control of your account email."
            : "Verify your email to publish roles or share your contact email in a hiring application."}
        </p>
        <p className="small-muted">
          Email verification confirms email control. Company identity,
          nationality, and work authorization remain separately declared
          information.
        </p>
        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}
        {message && <p role="status">{message}</p>}
        {!user.email_verified && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "12px",
              marginTop: "18px",
            }}
          >
            <button className="button dark" onClick={request} disabled={busy}>
              {busy ? (
                <LoaderCircle size={17} className="spin" />
              ) : (
                <Mail size={17} />
              )}{" "}
              Send verification link
            </button>
            <button
              className="button outline"
              onClick={refresh}
              disabled={busy}
            >
              <ShieldCheck size={17} /> Check verification
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

export function VerifyEmail({ api, onVerified }) {
  const navigate = useNavigate();
  const [token] = useState(
    () => new URLSearchParams(window.location.hash.slice(1)).get("token") || "",
  );
  const started = useRef(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (window.location.hash) navigate("/verify-email", { replace: true });
    if (!token) {
      setError(
        "This verification link is missing. Request a new one from Account & privacy.",
      );
      return;
    }
    async function verify() {
      try {
        await api("/auth/verify-email", { method: "POST", body: { token } });
        setDone(true);
        try {
          const result = await api("/auth/me");
          if (result.user) onVerified?.(result.user);
        } catch {
          /* Verification already succeeded. */
        }
      } catch (e) {
        setError(e.message);
      }
    }
    verify();
  }, [api, navigate, onVerified, token]);
  return (
    <main className="recovery-page">
      <Link className="logo" to="/">
        candoc.
      </Link>
      <section className="panel recovery-card">
        {done ? (
          <CheckCircle2 size={32} />
        ) : !error ? (
          <LoaderCircle size={32} className="spin" />
        ) : (
          <Mail size={32} />
        )}
        <h1>
          {done
            ? "Email verified."
            : error
              ? "Check your verification link."
              : "Verifying your email…"}
        </h1>
        {error ? (
          <p role="alert">{error}</p>
        ) : done ? (
          <p role="status">
            You can continue in the account associated with this email. You may
            need to sign in first.
          </p>
        ) : (
          <p>This should take a moment.</p>
        )}
        <Link className="button dark full" to={done ? "/app" : "/app/settings"}>
          {done ? "Continue to Candoc" : "Account & privacy"}
        </Link>
        <Link className="back-link" to="/login">
          Log in to another account
        </Link>
      </section>
    </main>
  );
}
