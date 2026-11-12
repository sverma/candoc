"""Auditable document-evidence rubric. It does not assess a person's employability."""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

VERSION = "evidence-1.0"
DIMENSIONS = [
    {"key": "skills_evidence", "label": "Skills in context", "weight": 0.25,
     "description": "Named skills connected to described actions; skill-list length does not establish ability."},
    {"key": "experience_detail", "label": "Experience detail", "weight": 0.25,
     "description": "Specific responsibilities and the scope of work described, without scoring tenure, gaps, employers or school prestige."},
    {"key": "impact", "label": "Outcomes & impact", "weight": 0.20,
     "description": "Stated outcomes connected to actions and context. Qualitative outcomes count; numerical claims are not verified."},
    {"key": "project_depth", "label": "Work examples", "weight": 0.20,
     "description": "Concrete deliverables, implementation details and validation described in the document; a public code portfolio is optional."},
    {"key": "clarity", "label": "Document clarity", "weight": 0.10,
     "description": "Readable, distinct work statements and useful organization, assessed from extracted text only."},
]
LIMITATIONS = [
    "This deterministic English-language rubric measures how much evidence a document supplies, not candidate quality, job fit or hiring suitability.",
    "An evidence score must never automatically accept, reject or rank a person for a hiring decision. A human must review relevant work and candidate corrections.",
    "Resume and supplied LinkedIn text are self-reported. Employment, metrics, account ownership and repository authorship are not verified.",
    "Public GitHub observations are supplementary and do not affect the score. LinkedIn exports are candidate-supplied documents. Missing, private or unavailable social accounts do not lower the score.",
    "Protected characteristics, names, contact details, age, tenure, career gaps, school or employer prestige, stars and followers are not rubric inputs.",
    "Rules can miss synonyms, non-English content and complex careers. PDF extraction, document formatting and writing style can affect coverage. Scores are not validated predictors of job performance.",
]

ACTION = re.compile(r"\b(built|build|develop(?:ed|ing)?|design(?:ed|ing)?|implement(?:ed|ing)?|deliver(?:ed|ing)?|launch(?:ed|ing)?|led|lead|manage(?:d|s|ment)?|creat(?:ed|ing)|maintain(?:ed|ing)?|migrat(?:ed|ing)|automat(?:ed|ing)|optimi[sz](?:ed|ing)|analy[sz](?:ed|ing)|research(?:ed|ing)?|conduct(?:ed|ing)?|coordinat(?:ed|ing)|wrote|written|author(?:ed)?|produc(?:ed|ing)|deploy(?:ed|ing)|test(?:ed|ing)|resolv(?:ed|ing)|support(?:ed|ing)|train(?:ed|ing)|mentor(?:ed|ing)|negotiat(?:ed|ing)|establish(?:ed|ing)|improv(?:ed|ing)|reduc(?:ed|ing)|increas(?:ed|ing))\b", re.I)
OUTCOME = re.compile(r"\b(reduc(?:ed|tion)|improv(?:ed|ement)|increas(?:ed|e)|sav(?:ed|ings)|grew|growth|achiev(?:ed|ement)|enabl(?:ed|ing)|eliminat(?:ed|ion)|accelerat(?:ed|ion)|prevent(?:ed|ion)|result(?:ed|ing)|deliver(?:ed|ing)|adopt(?:ed|ion)|recover(?:ed|y)|resolv(?:ed|ing)|launch(?:ed|ing)|pass(?:ed|ing)|complian(?:t|ce)|reliab(?:le|ility)|accessib(?:le|ility))\b", re.I)
SCOPE = re.compile(r"\b(customer|client|user|team|service|system|platform|product|process|application|report|dataset|campaign|workflow|database|pipeline|budget|stakeholder|patient|student|operation|project|transaction|request|release|document|research|test|interface|design|api|model|audit|supply|inventory)s?\b", re.I)
DELIVERABLE = re.compile(r"\b(api|application|app|platform|service|website|dashboard|pipeline|model|report|campaign|workflow|system|prototype|product|research|publication|process|curriculum|program|policy|audit|integration|migration|dataset|experiment|analysis|project|tool|document|manual|design|feature)s?\b", re.I)
VALIDATION = re.compile(r"\b(test(?:ed|ing|s)?|benchmark(?:ed|s)?|monitor(?:ed|ing)?|review(?:ed|s)?|validat(?:ed|ion)|evaluat(?:ed|ion)|audit(?:ed)?|experiment(?:ed|s)?|feedback|accessibility|reliability|observability|measur(?:ed|ement)|quality|research|interview(?:ed|s)?|pilot(?:ed)?|compliance)\b", re.I)
QUANTIFIED = re.compile(r"(?:\b\d+(?:\.\d+)?\s*(?:%|percent|ms\b|seconds?\b|minutes?\b|hours?\b|requests?\b|users?\b|customers?\b|transactions?\b|reports?\b|teams?\b|sites?\b)|[$€£₹]\s*\d)", re.I)
HEADER = re.compile(r"^(?:professional\s+)?(?:summary|profile|objective|experience|employment|work experience|work history|employment history|projects|selected projects|skills|technical skills|achievements|publications|education|certifications|professional experience)\s*:?$", re.I)
SENSITIVE = re.compile(r"\b(?:date of birth|dob|born on|marital status|religion|religious affiliation|ethnicity|ethnic origin|race|gender|sexual orientation|pregnan\w*|disabilit\w*|nationality|citizenship|caste|veteran status|political affiliation)\b|\bage\s*[:=]", re.I)
INJECTION = re.compile(r"(?:ignore (?:all |any |the )?(?:previous|prior|instructions)|system\s*:|assistant\s*:|give (?:me|this) (?:a )?(?:5|five)|(?:set|override|change) (?:the |my )?(?:score|rating)|instruction(?:s)?\s*:)", re.I)
COMMON_SKILLS = ["Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "React", "Vue", "Angular", "Node.js", "FastAPI", "Django", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Linux", "Git", "Figma", "Excel", "Tableau", "Power BI", "Salesforce", "machine learning", "data analysis", "user research", "product design", "project management", "financial analysis", "copywriting", "content strategy", "SEO", "accounting", "budgeting", "negotiation", "recruitment", "customer support", "supply chain", "clinical research", "teaching", "mentoring", "testing", "research", "design"]


def get_rubric() -> Dict[str, Any]:
    return {"version": VERSION,
            "description": "A 1–5 document evidence score. It helps candidates describe their work and humans review the supporting statements; it is not a talent rating.",
            "dimensions": [dict(item) for item in DIMENSIONS], "limitations": list(LIMITATIONS),
            "anchors": {"1": "Little usable evidence found", "2": "Claims are named, with limited context",
                        "3": "Some concrete supporting statements", "4": "Several specific supporting statements",
                        "5": "Multiple specific statements connect actions, context and outcomes"}}


def _clean_lines(text: str) -> List[str]:
    lines = []
    education = False
    first_content = True
    for raw in text[:60_000].replace("\r", "\n").splitlines():
        line = re.sub(r"\s+", " ", raw).strip(" \t•-*|")
        if not line:
            continue
        if HEADER.fullmatch(line):
            first_content = False
            education = bool(re.fullmatch(r"(?:education|certifications)\s*:?", line, re.I))
            if not education:
                lines.append(line)
            continue
        if first_content:
            first_content = False
            # A leading short name/headline is metadata, not evidence. Avoid interpreting
            # someone's name as a skill simply because it matches a dictionary word.
            if len(line.split()) <= 5 and not ACTION.search(line) and not re.search(r"[:,;]", line):
                continue
        if education or SENSITIVE.search(line) or INJECTION.search(line):
            continue
        # Contact information is not considered evidence and is never emitted in snippets.
        line = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[contact removed]", line)
        line = re.sub(r"https?://\S+", "[link]", line)
        line = re.sub(r"(?<!\w)(?:\+\d{1,3}[ -]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)", "[contact removed]", line)
        line = re.sub(r"(?<!\w)\+?\d{10,15}(?!\w)|(?<!\w)(?:\+?\d{1,3}[ -]?)?\d{5}[ -]\d{5}(?!\w)", "[contact removed]", line)
        # Sentence separation supports resumes pasted as paragraphs without valuing length.
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line):
            if sentence and sentence not in lines:
                lines.append(sentence[:1500])
    return lines[:600]


def _has_skill(line: str, skill: str) -> bool:
    return bool(re.search(r"(?<![\w])" + re.escape(skill) + r"(?![\w])", line, re.I))


def _sample(lines: List[str], maximum: int = 3) -> List[str]:
    return [line[:260] + ("…" if len(line) > 260 else "") for line in lines[:maximum]]


def evaluate_profile(resume_text: str, skills: List[str], linkedin_text: str = "",
                     github_data: Optional[Dict[str, Any]] = None,
                     linkedin_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Assess self-supplied document evidence; external profile availability cannot alter score."""
    resume_lines = _clean_lines(resume_text or "")
    supplied_lines = _clean_lines(linkedin_text or "")
    exported_lines = _clean_lines(str(linkedin_data.get("text", ""))) if (linkedin_data and linkedin_data.get("status") == "available" and linkedin_data.get("type") == "candidate_export") else []
    lines = list(dict.fromkeys(resume_lines + supplied_lines + exported_lines))
    work = [line for line in lines if ACTION.search(line) and len(line.split()) >= 6]
    specific = [line for line in work if SCOPE.search(line)]
    outcomes = [line for line in specific if OUTCOME.search(line)]
    quantified = [line for line in outcomes if QUANTIFIED.search(line)]
    deliverables = [line for line in work if DELIVERABLE.search(line)]
    validated = [line for line in deliverables if VALIDATION.search(line)]
    vocabulary = list(dict.fromkeys([s.strip()[:80] for s in (skills or [])[:60] if isinstance(s, str) and 1 < len(s.strip()) <= 80] + COMMON_SKILLS))
    named_skills = [s for s in vocabulary if any(_has_skill(line, s) for line in lines)]
    contextual = [line for line in work if any(_has_skill(line, s) for s in named_skills)]
    headers = [line for line in lines if HEADER.fullmatch(line)]
    readable = [line for line in lines if 5 <= len(line.split()) <= 65 and not HEADER.fullmatch(line)]

    skill_score = 1 + bool(named_skills) + bool(contextual) + (len(contextual) >= 2) + (len(contextual) >= 3 and any(OUTCOME.search(x) for x in contextual))
    experience_score = 1 + bool(work) + (len(specific) >= 1) + (len(specific) >= 3) + (len(specific) >= 4 and len(outcomes) >= 2)
    impact_score = 1 + bool([line for line in lines if OUTCOME.search(line)]) + bool(outcomes) + (len(outcomes) >= 2) + (len(outcomes) >= 3)
    project_score = 1 + bool(deliverables) + (len(deliverables) >= 2) + bool(validated) + (len(deliverables) >= 3 and len(validated) >= 2)
    clarity_score = 1 + bool(readable) + (len(readable) >= 3) + bool(headers) + (len(readable) >= 5 and len(headers) >= 2)

    scores = [int(skill_score), int(experience_score), int(impact_score), int(project_score), int(clarity_score)]
    evidence = [contextual or [line for line in lines if any(_has_skill(line, s) for s in named_skills)],
                specific or work, quantified + [line for line in outcomes if line not in quantified],
                validated + [line for line in deliverables if line not in validated], headers + readable]
    suggestions = [
        "Connect a relevant skill to an action you took, the work context, and what happened; avoid adding skills solely to raise a score.",
        "Describe your own responsibilities and scope in distinct work examples. Employer prestige, years worked and career gaps do not count.",
        "Explain what changed because of your work and how you know. Qualitative outcomes are welcome; use metrics only when accurate and shareable.",
        "Describe a concrete deliverable, your contribution, implementation choices and how it was tested or reviewed. Private and non-code work count.",
        "Use clear section headings and concise work statements. Check the extracted text if your PDF has columns or unusual formatting.",
    ]
    dimensions = []
    for index, descriptor in enumerate(DIMENSIONS):
        dimensions.append({**descriptor, "score": scores[index], "evidence": _sample(evidence[index]),
                           "improvements": [suggestions[index]] if scores[index] < 5 else []})
    overall = round(sum(item["score"] * item["weight"] for item in dimensions), 2)
    confidence = "high" if len(specific) >= 5 and len(readable) >= 8 else "medium" if len(specific) >= 2 else "low"
    strengths = [item["label"] + ": supporting statements found." for item in dimensions if item["score"] >= 4]
    improvements = [suggestions[index] for index in range(5) if scores[index] < 4]
    sources = [{"type": "resume", "status": "available" if resume_lines else "missing",
                "detail": "Candidate-supplied document; statements and employment are unverified." if resume_lines else "No usable resume text supplied."},
               {"type": "linkedin", "status": "candidate_supplied" if supplied_lines else "not_provided",
                "detail": "Candidate-supplied LinkedIn text; not fetched or verified by LinkedIn." if supplied_lines else "Optional candidate-supplied LinkedIn export or pasted text. Candoc does not fetch LinkedIn profiles."}]
    if linkedin_data and linkedin_data.get("type") == "candidate_export":
        export_source = {"type": "linkedin_export", "status": str(linkedin_data.get("status", "unavailable"))[:40],
                         "detail": "Candidate-provided LinkedIn export. Identity, employment and claims are self-reported and unverified.",
                         "filename": str(linkedin_data.get("filename", ""))[:160],
                         "imported_at": str(linkedin_data.get("imported_at", ""))[:60],
                         "sections": [str(value)[:80] for value in linkedin_data.get("sections", [])[:20]],
                         "evidence": _sample(exported_lines, 4)}
        sources.append(export_source)
    if github_data:
        status = github_data.get("status", "unavailable")
        github_source = {"type": "github", "status": status,
                         "detail": str(github_data.get("detail", "Public source observations are supplementary and do not affect the score."))[:1200]}
        if github_data.get("url"):
            github_source["url"] = str(github_data["url"])[:250]
        observations = github_data.get("evidence", [])
        if status == "available" and isinstance(observations, list):
            github_source["evidence"] = [str(item)[:700] for item in observations[:3]]
            github_source["repositories"] = [{key: str(repo.get(key, ""))[:700] for key in ("name", "description", "url", "language")}
                                               for repo in github_data.get("repositories", [])[:10] if isinstance(repo, dict)]
        sources.append(github_source)
    else:
        sources.append({"type": "github", "status": "not_connected",
                        "detail": "Optional public profile analysis was not requested. This does not lower the score."})
    return {"score": overall, "confidence": confidence,
            "summary": "Your document supplies " + ("substantial" if overall >= 4 else "some" if overall >= 2.5 else "limited") + " work evidence under the published rubric. This is a document evidence score, not a measure of talent or hiring suitability. Confidence describes rule coverage, not whether claims are true.",
            "dimensions": dimensions, "strengths": strengths,
            "improvements": improvements, "sources": sources,
            "analyzed_at": datetime.now(timezone.utc).isoformat(), "version": VERSION}
