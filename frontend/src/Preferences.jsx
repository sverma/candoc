import React, { useEffect, useId, useState } from "react";
import {
  Globe2,
  ShieldCheck,
  Plus,
  Trash2,
  Save,
  LoaderCircle,
} from "lucide-react";

const defaults = {
  engagement_types: [],
  work_modes: [],
  time_commitment: "flexible",
  preferred_countries: [],
  preferred_regions: [],
  nationalities: [],
  work_authorizations: [],
  share_work_authorization: false,
  share_nationality: false,
  sponsorship_need: "not_specified",
  willing_to_relocate: false,
  relocation_countries: [],
  relocation_regions: [],
  timezone: "",
  languages: [],
  available_from: null,
  notice_days: null,
  hours_per_week: null,
  compensation_min: null,
  compensation_max: null,
  currency: "",
  pay_period: "year",
  portfolio_url: "",
  preferred_title: "",
};
const pretty = (value) => String(value || "").replaceAll("_", " ");
const today = () => new Date().toISOString().slice(0, 10);
const regionNames = {
  EU: "European Union",
  EEA: "European Economic Area",
  EUROPE: "Europe",
  NORTH_AMERICA: "North America",
  SOUTH_AMERICA: "South America",
  APAC: "Asia Pacific",
  MIDDLE_EAST: "Middle East",
  AFRICA: "Africa",
  GLOBAL: "Worldwide",
};
function countryName(code) {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) || code;
  } catch {
    return code;
  }
}

function Field({ label, children, note }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {note && <small>{note}</small>}
    </label>
  );
}
function MultiChoice({ label, choices, value = [], onChange, note }) {
  const [search, setSearch] = useState("");
  const id = useId();
  const selected = new Set(value);
  return (
    <div className="field">
      <label htmlFor={id}>
        <span>{label}</span>
      </label>
      <input
        aria-label={`Search ${label.toLowerCase()}`}
        placeholder="Search to add…"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <select
        id={id}
        value=""
        onChange={(event) => {
          if (event.target.value) onChange([...value, event.target.value]);
          setSearch("");
        }}
      >
        <option value="">Choose an option…</option>
        {choices
          .filter(
            (choice) =>
              !selected.has(choice.code) &&
              `${choice.code} ${choice.name}`
                .toLowerCase()
                .includes(search.toLowerCase()),
          )
          .map((choice) => (
            <option key={choice.code} value={choice.code}>
              {choice.name} ({choice.code})
            </option>
          ))}
      </select>
      <div className="preference-chips">
        {value.map((code) => (
          <button
            className="preference-chip"
            key={code}
            type="button"
            onClick={() => onChange(value.filter((item) => item !== code))}
            aria-label={`Remove ${choices.find((choice) => choice.code === code)?.name || code}`}
          >
            {choices.find((choice) => choice.code === code)?.name || code} ×
          </button>
        ))}
      </div>
      {note && <small>{note}</small>}
    </div>
  );
}
function CheckChoices({ legend, choices, selected, onChange }) {
  return (
    <fieldset className="preference-fieldset">
      <legend>{legend}</legend>
      <div className="preference-checks">
        {choices.map(({ value, label }) => (
          <label key={value}>
            <input
              type="checkbox"
              checked={selected.includes(value)}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...selected, value]
                    : selected.filter((item) => item !== value),
                )
              }
            />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function Preferences({ api }) {
  const [data, setData] = useState(null),
    [catalog, setCatalog] = useState(null),
    [saved, setSaved] = useState(null);
  const [loading, setLoading] = useState(true),
    [saving, setSaving] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [preferences, catalogs] = await Promise.all([
        api("/hiring/preferences"),
        api("/hiring/catalogs"),
      ]);
      const value = { ...defaults, ...preferences.preferences };
      setData(value);
      setSaved(value);
      setCatalog(catalogs);
    } catch (failure) {
      setError(failure.message || "Preferences could not be loaded.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);
  const update = (key, value) => {
    setData((previous) => ({ ...previous, [key]: value }));
    setNotice("");
  };
  const authorization = (index, key, value) =>
    update(
      "work_authorizations",
      data.work_authorizations.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              [key]: value,
              ...(key === "scope_type" ? { scope_code: "" } : {}),
            }
          : item,
      ),
    );
  const number = (event) =>
    event.target.value === "" ? null : Number(event.target.value);
  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await api("/hiring/preferences", {
        method: "PUT",
        body: data,
      });
      setData(response.preferences);
      setSaved(response.preferences);
      setNotice("Your preferences have been saved.");
    } catch (failure) {
      setError(failure.message || "Preferences could not be saved.");
    } finally {
      setSaving(false);
    }
  };
  if (loading)
    return (
      <div className="empty-state" role="status">
        <LoaderCircle className="spin" /> Loading your work preferences…
      </div>
    );
  if (!data || !catalog)
    return (
      <div className="panel" style={{ padding: 24 }}>
        <p role="alert">{error}</p>
        <button className="button dark" onClick={load}>
          Try again
        </button>
      </div>
    );
  return (
    <div className="preferences-page">
      <style>{`.preferences-page{max-width:1080px}.preferences-page h1{font-size:30px;letter-spacing:-1px;margin-bottom:8px}.preferences-page>p{color:#66715e;line-height:1.6;margin-bottom:24px}.preferences-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:18px}.preferences-page .field{display:flex;flex-direction:column;gap:7px}.preferences-page .field>label{font-size:12px;font-weight:600}.preferences-page .form-body{padding:24px}.preference-fieldset{border:0;padding:0;margin:0 0 20px}.preference-fieldset legend{font-size:13px;font-weight:600;margin-bottom:12px}.preference-checks{display:flex;flex-wrap:wrap;gap:12px 20px}.preference-checks label{display:flex;align-items:center;gap:8px;font-size:13px}.preference-chips{display:flex;flex-wrap:wrap;gap:6px}.preference-chip{border:1px solid #d8e2ce;border-radius:20px;padding:5px 10px;font-size:12px;background:#eef4e5;color:#34442a;cursor:pointer}.preference-row{border:1px solid #e0e7d5;border-radius:9px;padding:18px;margin-bottom:14px}.preference-row-actions{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;gap:10px}.preference-note{padding:14px 16px;background:#f1f5ea;border-radius:8px;font-size:13px;line-height:1.6;margin:15px 0}.preference-error{background:#fff0ec;color:#842f1e;padding:14px;border-radius:8px;margin-bottom:16px}.preference-save{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:22px 0}.mobility-summary{font-size:13px;line-height:1.7}.mobility-summary p{margin:6px 0}.mobility-summary ul{padding-left:20px}.preference-checkbox{display:flex;align-items:flex-start;gap:10px;font-size:13px;line-height:1.5;margin:14px 0}.preference-checkbox input{margin-top:4px;flex-shrink:0}`}</style>
      <h1>Work & mobility preferences</h1>
      <p>
        Describe the opportunities you want. Choose what to share about
        nationality and work authorization. These declarations never enter your
        evidence score or AI review.
      </p>
      {error && (
        <div className="preference-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="preference-note" role="status">
          {notice}
        </div>
      )}
      <form onSubmit={save}>
        <section className="panel">
          <div className="panel-heading">
            <h2>Work that fits your plans</h2>
          </div>
          <div className="form-body">
            <CheckChoices
              legend="Engagement types"
              choices={catalog.engagement_types}
              selected={data.engagement_types}
              onChange={(value) => update("engagement_types", value)}
            />
            <CheckChoices
              legend="Work arrangement"
              choices={catalog.work_modes}
              selected={data.work_modes}
              onChange={(value) => update("work_modes", value)}
            />
            <div className="preferences-grid">
              <Field label="Preferred role title">
                <input
                  value={data.preferred_title}
                  maxLength={160}
                  onChange={(event) =>
                    update("preferred_title", event.target.value)
                  }
                />
              </Field>
              <Field label="Time commitment">
                <select
                  value={data.time_commitment}
                  onChange={(event) =>
                    update("time_commitment", event.target.value)
                  }
                >
                  {catalog.time_commitments.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>
              <Globe2 size={17} /> Location & relocation
            </h2>
          </div>
          <div className="form-body">
            <div className="preferences-grid">
              <MultiChoice
                label="Preferred countries or territories"
                choices={catalog.countries}
                value={data.preferred_countries}
                onChange={(value) => update("preferred_countries", value)}
              />
              <MultiChoice
                label="Preferred regions"
                choices={catalog.regions}
                value={data.preferred_regions}
                onChange={(value) => update("preferred_regions", value)}
              />
            </div>
            <p className="preference-note">
              Regions describe geography. Choosing the EU, EEA or another region
              does not declare or grant a right to work there.
            </p>
            <label className="preference-checkbox">
              <input
                type="checkbox"
                checked={data.willing_to_relocate}
                onChange={(event) =>
                  update("willing_to_relocate", event.target.checked)
                }
              />
              I am willing to discuss relocation.
            </label>
            {data.willing_to_relocate && (
              <div className="preferences-grid">
                <MultiChoice
                  label="Relocation countries or territories"
                  choices={catalog.countries}
                  value={data.relocation_countries}
                  onChange={(value) => update("relocation_countries", value)}
                />
                <MultiChoice
                  label="Relocation regions"
                  choices={catalog.regions}
                  value={data.relocation_regions}
                  onChange={(value) => update("relocation_regions", value)}
                />
              </div>
            )}
            <Field label="Sponsorship preference">
              <select
                value={data.sponsorship_need}
                onChange={(event) =>
                  update("sponsorship_need", event.target.value)
                }
              >
                <option value="not_specified">Prefer not to specify</option>
                <option value="not_required">
                  I do not expect to need sponsorship
                </option>
                <option value="required">I expect to need sponsorship</option>
                <option value="discuss">I would like to discuss this</option>
              </select>
            </Field>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>
              <ShieldCheck size={17} /> Optional nationality & work declarations
            </h2>
          </div>
          <div className="form-body">
            <p className="preference-note">
              Both sections are private by default. Sharing is optional and
              independent. Work declarations are self-reported, do not establish
              legal eligibility, and are never inferred from nationality. Do not
              upload identity documents or permit numbers.
            </p>
            <MultiChoice
              label="Nationalities (optional)"
              choices={catalog.countries}
              value={data.nationalities}
              onChange={(value) => update("nationalities", value)}
            />
            <label className="preference-checkbox">
              <input
                type="checkbox"
                checked={data.share_nationality}
                onChange={(event) =>
                  update("share_nationality", event.target.checked)
                }
              />
              Share my selected nationalities with companies that can view my
              professional profile.
            </label>
            <h3 style={{ fontSize: 15, margin: "24px 0 14px" }}>
              Work authorization declarations
            </h3>
            {data.work_authorizations.map((item, index) => (
              <div className="preference-row" key={index}>
                <div className="preference-row-actions">
                  <strong>Declaration {index + 1}</strong>
                  <button
                    type="button"
                    className="button small outline"
                    onClick={() =>
                      update(
                        "work_authorizations",
                        data.work_authorizations.filter(
                          (_, itemIndex) => itemIndex !== index,
                        ),
                      )
                    }
                  >
                    <Trash2 size={14} /> Remove
                  </button>
                </div>
                <div className="preferences-grid">
                  <Field label="Scope type">
                    <select
                      value={item.scope_type}
                      onChange={(event) =>
                        authorization(index, "scope_type", event.target.value)
                      }
                    >
                      <option value="country">Country or territory</option>
                      <option value="region">Geographic region</option>
                    </select>
                  </Field>
                  <Field label="Declared scope">
                    <select
                      required
                      value={item.scope_code}
                      onChange={(event) =>
                        authorization(index, "scope_code", event.target.value)
                      }
                    >
                      <option value="">Choose a scope…</option>
                      {(item.scope_type === "country"
                        ? catalog.countries
                        : catalog.regions
                      ).map((choice) => (
                        <option key={choice.code} value={choice.code}>
                          {choice.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Declaration">
                    <select
                      value={item.status}
                      onChange={(event) =>
                        authorization(index, "status", event.target.value)
                      }
                    >
                      <option value="unknown">
                        I need to confirm my position
                      </option>
                      <option value="unrestricted">
                        I declare unrestricted authorization
                      </option>
                      <option value="permit_held">
                        I declare that I hold a permit
                      </option>
                      <option value="needs_sponsorship">
                        I expect to need sponsorship
                      </option>
                    </select>
                  </Field>
                  <Field label="Valid until (optional)">
                    <input
                      type="date"
                      value={item.valid_until || ""}
                      onChange={(event) =>
                        authorization(
                          index,
                          "valid_until",
                          event.target.value || null,
                        )
                      }
                    />
                  </Field>
                </div>
                {item.valid_until && item.valid_until < today() && (
                  <p className="preference-note">
                    This declared validity date has passed. It is marked expired
                    and does not establish current authorization.
                  </p>
                )}
                <Field
                  label="Private notes"
                  note="Notes stay private even when you share the declaration. Avoid passport, permit and identity numbers."
                >
                  <textarea
                    maxLength={1000}
                    rows={2}
                    value={item.notes}
                    onChange={(event) =>
                      authorization(index, "notes", event.target.value)
                    }
                  />
                </Field>
              </div>
            ))}
            <button
              type="button"
              className="button outline small"
              disabled={data.work_authorizations.length >= 50}
              onClick={() =>
                update("work_authorizations", [
                  ...data.work_authorizations,
                  {
                    scope_type: "country",
                    scope_code: "",
                    status: "unknown",
                    valid_until: null,
                    notes: "",
                  },
                ])
              }
            >
              <Plus size={15} /> Add a declaration
            </button>
            <label className="preference-checkbox">
              <input
                type="checkbox"
                checked={data.share_work_authorization}
                onChange={(event) =>
                  update("share_work_authorization", event.target.checked)
                }
              />
              Share my work authorization declarations, without private notes,
              with companies that can view my professional profile.
            </label>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Availability & languages</h2>
          </div>
          <div className="form-body">
            <div className="preferences-grid">
              <Field label="Available from">
                <input
                  type="date"
                  value={data.available_from || ""}
                  onChange={(event) =>
                    update("available_from", event.target.value || null)
                  }
                />
              </Field>
              <Field label="Notice period (days)">
                <input
                  type="number"
                  min={0}
                  max={365}
                  step={1}
                  value={data.notice_days ?? ""}
                  onChange={(event) => update("notice_days", number(event))}
                />
              </Field>
              <Field label="Hours per week">
                <input
                  type="number"
                  min={0}
                  max={168}
                  step="any"
                  value={data.hours_per_week ?? ""}
                  onChange={(event) => update("hours_per_week", number(event))}
                />
              </Field>
              <Field
                label="Timezone"
                note="Use an IANA timezone, for example Asia/Kolkata or Europe/London."
              >
                <input
                  value={data.timezone}
                  maxLength={100}
                  placeholder="Asia/Kolkata"
                  onChange={(event) => update("timezone", event.target.value)}
                />
              </Field>
            </div>
            <h3 style={{ fontSize: 15, margin: "24px 0 14px" }}>
              Languages you choose to list
            </h3>
            {data.languages.map((item, index) => (
              <div className="preference-row" key={index}>
                <div className="preferences-grid">
                  <Field label="Language">
                    <input
                      required
                      maxLength={80}
                      value={item.name}
                      onChange={(event) =>
                        update(
                          "languages",
                          data.languages.map((language, languageIndex) =>
                            languageIndex === index
                              ? { ...language, name: event.target.value }
                              : language,
                          ),
                        )
                      }
                    />
                  </Field>
                  <Field label="Self-described proficiency">
                    <select
                      value={item.proficiency}
                      onChange={(event) =>
                        update(
                          "languages",
                          data.languages.map((language, languageIndex) =>
                            languageIndex === index
                              ? { ...language, proficiency: event.target.value }
                              : language,
                          ),
                        )
                      }
                    >
                      {[
                        "basic",
                        "conversational",
                        "professional",
                        "native",
                      ].map((value) => (
                        <option key={value} value={value}>
                          {pretty(value)}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
                <button
                  type="button"
                  className="button outline small"
                  style={{ marginTop: 12 }}
                  onClick={() =>
                    update(
                      "languages",
                      data.languages.filter(
                        (_, languageIndex) => languageIndex !== index,
                      ),
                    )
                  }
                >
                  Remove language
                </button>
              </div>
            ))}
            <button
              className="button small outline"
              type="button"
              disabled={data.languages.length >= 30}
              onClick={() =>
                update("languages", [
                  ...data.languages,
                  { name: "", proficiency: "professional" },
                ])
              }
            >
              <Plus size={15} /> Add a language
            </button>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Compensation & portfolio</h2>
          </div>
          <div className="form-body">
            <div className="preferences-grid">
              <Field label="Preferred minimum">
                <input
                  type="number"
                  min={0}
                  max={1e12}
                  step="any"
                  value={data.compensation_min ?? ""}
                  onChange={(event) =>
                    update("compensation_min", number(event))
                  }
                />
              </Field>
              <Field label="Preferred maximum">
                <input
                  type="number"
                  min={data.compensation_min ?? 0}
                  max={1e12}
                  step="any"
                  value={data.compensation_max ?? ""}
                  onChange={(event) =>
                    update("compensation_max", number(event))
                  }
                />
              </Field>
              <Field label="Currency">
                <select
                  value={data.currency}
                  required={
                    data.compensation_min !== null ||
                    data.compensation_max !== null
                  }
                  onChange={(event) => update("currency", event.target.value)}
                >
                  <option value="">Not specified</option>
                  {catalog.currencies.map((item) => (
                    <option key={item.code} value={item.code}>
                      {item.code} — {item.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Pay period">
                <select
                  value={data.pay_period}
                  onChange={(event) => update("pay_period", event.target.value)}
                >
                  {(
                    catalog.pay_periods ||
                    ["hour", "day", "week", "month", "year", "project"].map(
                      (value) => ({ value, label: value }),
                    )
                  ).map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div style={{ marginTop: 18 }}>
              <Field label="Portfolio URL (optional)">
                <input
                  type="url"
                  value={data.portfolio_url}
                  maxLength={500}
                  placeholder="https://your-portfolio.example"
                  onChange={(event) =>
                    update("portfolio_url", event.target.value)
                  }
                />
              </Field>
            </div>
          </div>
        </section>
        <div className="preference-save">
          <button type="submit" className="button dark" disabled={saving}>
            {saving ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              <Save size={16} />
            )}
            {saving ? "Saving…" : "Save preferences"}
          </button>
          <button
            type="button"
            className="button outline"
            disabled={saving}
            onClick={() => {
              setData(saved);
              setError("");
              setNotice("Unsaved changes discarded.");
            }}
          >
            Discard changes
          </button>
        </div>
      </form>
    </div>
  );
}

export function MobilitySummary({ preferences }) {
  if (!preferences || !Object.keys(preferences).length) return null;
  const countries = (values) => (values || []).map(countryName).join(", ");
  const regions = (values) =>
    (values || []).map((value) => regionNames[value] || value).join(", ");
  const nationalities =
    preferences.share_nationality === false
      ? []
      : preferences.nationalities || [];
  const authorizations =
    preferences.share_work_authorization === false
      ? []
      : preferences.work_authorizations || [];
  return (
    <div className="mobility-summary">
      <h3>Work & mobility preferences</h3>
      {preferences.preferred_title && (
        <p>
          <strong>Preferred role:</strong> {preferences.preferred_title}
        </p>
      )}
      {!!preferences.engagement_types?.length && (
        <p>
          <strong>Engagement:</strong>{" "}
          {preferences.engagement_types.map(pretty).join(", ")}
        </p>
      )}
      {!!preferences.work_modes?.length && (
        <p>
          <strong>Arrangement:</strong>{" "}
          {preferences.work_modes.map(pretty).join(", ")}
        </p>
      )}
      {preferences.time_commitment && (
        <p>
          <strong>Commitment:</strong> {pretty(preferences.time_commitment)}
        </p>
      )}
      {!!preferences.preferred_countries?.length && (
        <p>
          <strong>Preferred locations:</strong>{" "}
          {countries(preferences.preferred_countries)}
        </p>
      )}
      {!!preferences.preferred_regions?.length && (
        <p>
          <strong>Geographic regions:</strong>{" "}
          {regions(preferences.preferred_regions)}
        </p>
      )}
      {preferences.willing_to_relocate && (
        <p>
          <strong>Open to relocation:</strong>{" "}
          {[
            countries(preferences.relocation_countries),
            regions(preferences.relocation_regions),
          ]
            .filter(Boolean)
            .join("; ") || "Discuss with candidate"}
        </p>
      )}
      {preferences.sponsorship_need &&
        preferences.sponsorship_need !== "not_specified" && (
          <p>
            <strong>Sponsorship preference:</strong>{" "}
            {pretty(preferences.sponsorship_need)} (self-declared)
          </p>
        )}
      {!!nationalities.length && (
        <p>
          <strong>Nationalities shared by candidate:</strong>{" "}
          {countries(nationalities)}
        </p>
      )}
      {!!authorizations.length && (
        <>
          <p>
            <strong>Candidate-shared work declarations:</strong>
          </p>
          <ul>
            {authorizations.map((item, index) => (
              <li key={index}>
                {item.scope_type === "country"
                  ? countryName(item.scope_code)
                  : regionNames[item.scope_code] || item.scope_code}
                : {pretty(item.status)}
                {item.valid_until
                  ? `; declared valid until ${item.valid_until}`
                  : ""}
                {item.expired ||
                (item.valid_until && item.valid_until < today())
                  ? " — expired declaration"
                  : ""}
                . Self-declared, unverified.
              </li>
            ))}
          </ul>
          <p>Region scope is geography, not proof of legal work rights.</p>
        </>
      )}
      {preferences.available_from && (
        <p>
          <strong>Available from:</strong> {preferences.available_from}
        </p>
      )}
      {preferences.notice_days !== null &&
        preferences.notice_days !== undefined && (
          <p>
            <strong>Notice:</strong> {preferences.notice_days} days
          </p>
        )}
      {preferences.hours_per_week !== null &&
        preferences.hours_per_week !== undefined && (
          <p>
            <strong>Availability:</strong> {preferences.hours_per_week}{" "}
            hours/week
          </p>
        )}
      {preferences.timezone && (
        <p>
          <strong>Timezone:</strong> {preferences.timezone}
        </p>
      )}
      {!!preferences.languages?.length && (
        <p>
          <strong>Languages:</strong>{" "}
          {preferences.languages
            .map((item) => `${item.name} (${item.proficiency})`)
            .join(", ")}
        </p>
      )}
      {preferences.portfolio_url &&
        /^https?:\/\//i.test(preferences.portfolio_url) && (
          <p>
            <a
              href={preferences.portfolio_url}
              target="_blank"
              rel="noreferrer"
            >
              Candidate portfolio
            </a>
          </p>
        )}
      {((preferences.compensation_min !== null &&
        preferences.compensation_min !== undefined) ||
        (preferences.compensation_max !== null &&
          preferences.compensation_max !== undefined)) && (
        <p>
          <strong>Compensation preference:</strong> {preferences.currency}{" "}
          {preferences.compensation_min ?? "Discuss"} –{" "}
          {preferences.compensation_max ?? "Discuss"} / {preferences.pay_period}
        </p>
      )}
    </div>
  );
}
