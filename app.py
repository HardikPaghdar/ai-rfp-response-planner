from __future__ import annotations

import re
from io import StringIO
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AI RFP Response Planner",
    page_icon="📋",
    layout="wide",
)

CAPABILITIES = [
    {
        "area": "Application development",
        "name": "Custom web application development",
        "description": "Design, development, testing, and maintenance of web applications and APIs.",
        "keywords": ["web application", "web apps", "api", "application development", "software development"],
    },
    {
        "area": "Cloud and infrastructure",
        "name": "Cloud deployment and operations",
        "description": "Cloud deployment, environment configuration, monitoring, and operational support.",
        "keywords": ["cloud", "aws", "azure", "deployment", "infrastructure", "monitoring"],
    },
    {
        "area": "AI and data",
        "name": "AI and data engineering",
        "description": "AI-enabled workflows, data processing, retrieval systems, and model integrations.",
        "keywords": ["artificial intelligence", "machine learning", "llm", "data processing", "rag", "automation"],
    },
    {
        "area": "Quality assurance",
        "name": "Software testing and quality assurance",
        "description": "Functional testing, regression testing, test automation, and release validation.",
        "keywords": ["testing", "quality assurance", "test automation", "regression", "validation"],
    },
    {
        "area": "Security",
        "name": "Application security practices",
        "description": "Secure development practices, access control implementation, and vulnerability remediation.",
        "keywords": ["security", "access control", "authentication", "authorization", "vulnerability"],
    },
    {
        "area": "Support",
        "name": "Technical support and maintenance",
        "description": "Ongoing application support, issue triage, maintenance, and technical documentation.",
        "keywords": ["support", "maintenance", "incident", "documentation", "service desk"],
    },
]

REQUIREMENT_HINTS = (
    "shall", "must", "should", "required", "requirement", "provide", "support",
    "ensure", "comply", "availability", "security", "integration", "deliver",
    "implement", "maintain", "system", "solution",
)


def split_into_candidates(text: str) -> list[str]:
    """Split pasted RFP text into candidate requirement statements."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    # Prefer line and bullet boundaries, then split long paragraphs into sentences.
    raw_lines = re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in raw_lines:
        item = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", raw)
        item = re.sub(r"\s+", " ", item).strip(" \t\r\n-•")
        if len(item) < 18 or len(item) > 700:
            continue
        lowered = item.lower()
        if not any(hint in lowered for hint in REQUIREMENT_HINTS):
            continue
        key = lowered.rstrip(".;:")
        if key not in seen:
            seen.add(key)
            candidates.append(item)
    return candidates


def assess_requirement(requirement: str) -> tuple[str, str, str]:
    """Return a transparent keyword-based suggestion, never a compliance verdict."""
    lowered = requirement.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for capability in CAPABILITIES:
        score = sum(1 for keyword in capability["keywords"] if keyword in lowered)
        if score:
            scored.append((score, capability))

    if not scored:
        return "Needs review", "No clear capability keyword match", "Confirm with a subject-matter expert"

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best = scored[0][1]
    if scored[0][0] >= 2:
        return "Potential match", best["name"], "Attach approved evidence and validate scope"
    return "Needs evidence", best["name"], "Reviewer must confirm the match and attach proof"


def build_dataframe(requirements: list[str]) -> pd.DataFrame:
    rows = []
    for index, requirement in enumerate(requirements, start=1):
        status, capability, next_step = assess_requirement(requirement)
        rows.append(
            {
                "ID": f"REQ-{index:03d}",
                "Requirement": requirement,
                "Assessment": status,
                "Suggested capability": capability,
                "Evidence / response notes": "",
                "Owner": "",
                "Next step": next_step,
            }
        )
    return pd.DataFrame(rows)


def make_response_outline(frame: pd.DataFrame) -> str:
    sections = ["# Draft RFP Response Outline", ""]
    for _, row in frame.iterrows():
        sections.extend(
            [
                f"## {row['ID']} — {row['Requirement']}",
                f"- Assessment: {row['Assessment']}",
                f"- Suggested capability: {row['Suggested capability']}",
                f"- Evidence / response notes: {row['Evidence / response notes'] or 'To be supplied by reviewer'}",
                f"- Owner: {row['Owner'] or 'Unassigned'}",
                "",
            ]
        )
    sections.append("> Draft outline only. Validate every statement and supporting document before submission.")
    return "\n".join(sections)


st.title("📋 AI RFP Response Planner")
st.caption("Turn RFP text into a reviewable requirements checklist, evidence map, and response outline.")

with st.sidebar:
    st.header("About this demo")
    st.write("A lightweight, human-reviewed RFP planning prototype.")
    st.divider()
    st.markdown("**Assessment labels**")
    st.markdown("- 🟢 Potential match")
    st.markdown("- 🟡 Needs evidence / review")
    st.markdown("- 🔴 No clear match")
    st.info("Keyword matches are suggestions, not proof of compliance.")

sample_text = """The supplier must provide a secure web application with role-based access control.
The solution shall support integration with existing REST APIs.
The service must maintain 99.9% monthly availability.
The supplier should provide functional testing and regression test documentation.
The platform must comply with our data residency requirements.
The supplier shall provide ongoing technical support and incident response.
All customer data must be encrypted at rest and in transit.
The implementation team must provide a project delivery plan and milestones."""

if "rfp_text" not in st.session_state:
    st.session_state.rfp_text = sample_text
if "requirements_df" not in st.session_state:
    st.session_state.requirements_df = None

st.subheader("1. Add RFP content")
st.caption("Paste text copied from an RFP. This demo does not upload or transmit documents to an external AI service.")
st.text_area("RFP text", key="rfp_text", height=220, label_visibility="collapsed")

col_a, col_b = st.columns([1, 4])
with col_a:
    analyze = st.button("Analyze requirements", type="primary", use_container_width=True)
with col_b:
    st.caption("The prototype uses transparent sentence splitting and keyword matching. It does not use an LLM.")

if analyze:
    extracted = split_into_candidates(st.session_state.rfp_text)
    if extracted:
        st.session_state.requirements_df = build_dataframe(extracted)
        st.success(f"Extracted {len(extracted)} candidate requirement(s). Review each item before using it.")
    else:
        st.session_state.requirements_df = pd.DataFrame()
        st.warning("No candidate requirements were detected. Try pasting more complete RFP sentences.")

frame = st.session_state.requirements_df
if frame is not None:
    st.divider()
    st.subheader("2. Review requirement mapping")
    if frame.empty:
        st.info("No requirements to review yet.")
    else:
        potential = int((frame["Assessment"] == "Potential match").sum())
        needs_review = int(frame["Assessment"].isin(["Needs evidence", "Needs review"]).sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Requirements", len(frame))
        m2.metric("Potential matches", potential)
        m3.metric("Need reviewer attention", needs_review)

        st.warning("A suggested match does not establish that your organization meets a requirement. Verify the scope and attach approved evidence.")
        edited = st.data_editor(
            frame,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "ID": st.column_config.TextColumn(disabled=True, width="small"),
                "Requirement": st.column_config.TextColumn(disabled=True, width="large"),
                "Assessment": st.column_config.SelectboxColumn(
                    options=["Potential match", "Needs evidence", "Needs review", "Gap identified"],
                    required=True,
                ),
                "Suggested capability": st.column_config.TextColumn(width="medium"),
                "Evidence / response notes": st.column_config.TextColumn(width="large"),
                "Owner": st.column_config.TextColumn(width="medium"),
                "Next step": st.column_config.TextColumn(disabled=True, width="large"),
            },
        )
        st.session_state.requirements_df = edited

        st.divider()
        st.subheader("3. Proposal response outline")
        outline = make_response_outline(edited)
        st.text_area("Editable outline preview", value=outline, height=280)
        csv_data = edited.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download requirements checklist (CSV)",
            data=csv_data,
            file_name="rfp_requirements_checklist.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download response outline (Markdown)",
            data=outline.encode("utf-8"),
            file_name="rfp_response_outline.md",
            mime="text/markdown",
        )

with st.expander("Capability library used by this demo"):
    st.dataframe(
        pd.DataFrame(
            [
                {"Area": item["area"], "Capability": item["name"], "Description": item["description"]}
                for item in CAPABILITIES
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.caption(
    "Demo limitations: extraction and matching are heuristic; no certifications, SLAs, legal terms, "
    "security controls, or contractual obligations are verified. Use synthetic or sanitized text and "
    "obtain qualified human approval before submitting any proposal."
)
