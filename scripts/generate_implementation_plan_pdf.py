"""Generate Architecture & Implementation Plan PDF for HR Policy Chatbot."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = Path(__file__).resolve().parents[1] / "HR_Policy_Chatbot_Implementation_Plan.pdf"

# Brand palette (professional, not purple-slop)
NAVY = colors.HexColor("#1B2A4A")
STEEL = colors.HexColor("#2C3E5A")
ACCENT = colors.HexColor("#1F6F8B")
LIGHT_BG = colors.HexColor("#F4F6F8")
ROW_ALT = colors.HexColor("#EEF2F6")
BORDER = colors.HexColor("#C5CDD8")
MUTED = colors.HexColor("#5A6577")
SUCCESS = colors.HexColor("#1F7A4D")
WARN = colors.HexColor("#9A6B00")
DANGER = colors.HexColor("#9B2C2C")


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=16,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=STEEL,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
            borderPadding=3,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=ACCENT,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=STEEL,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1A1F2C"),
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#1A1F2C"),
            leftIndent=8,
            spaceAfter=2,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1A1F2C"),
        ),
        "cell_header": ParagraphStyle(
            "cell_header",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.white,
        ),
        "code": ParagraphStyle(
            "code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=STEEL,
            backColor=LIGHT_BG,
            leftIndent=6,
            rightIndent=6,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=STEEL,
            leftIndent=4,
            spaceAfter=4,
        ),
    }
    return styles


def table_style(header=True, col_count=3):
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ]
    return TableStyle(style_cmds)


def make_table(headers, rows, col_widths, styles):
    data = [[Paragraph(h, styles["cell_header"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles["cell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(table_style())
    return t


def add_page_number(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    text = f"Internal HR Policy Chatbot — Implementation Plan  |  Page {page}"
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, text)
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.restoreState()


def build():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title="Internal HR Policy Chatbot — Architecture & Implementation Plan",
        author="Grow with Data",
    )

    story = []
    W = A4[0] - 36 * mm  # usable width

    # ── Cover ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph("PROJECT IMPLEMENTATION PLAN", styles["cover_meta"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Internal HR Policy Chatbot", styles["cover_title"]))
    story.append(
        Paragraph(
            "Architecture Design & Phased Implementation Plan",
            styles["cover_sub"],
        )
    )
    story.append(Spacer(1, 8 * mm))

    meta_data = [
        [Paragraph("<b>Project Type</b>", styles["cell"]), Paragraph("Real-life applied AI / backend systems", styles["cell"])],
        [Paragraph("<b>Primary Stack</b>", styles["cell"]), Paragraph("FastAPI, LangChain, LangGraph, Google Gemini", styles["cell"])],
        [Paragraph("<b>Supporting Tech</b>", styles["cell"]), Paragraph("Docling, Qdrant, Pydantic, LangSmith, PostgreSQL", styles["cell"])],
        [Paragraph("<b>Domain</b>", styles["cell"]), Paragraph("Human Resources / Internal Knowledge Management", styles["cell"])],
        [Paragraph("<b>Document</b>", styles["cell"]), Paragraph("Architecture & Implementation Plan (v1.0)", styles["cell"])],
        [Paragraph("<b>Derived From</b>", styles["cell"]), Paragraph("HR_Policy_Chatbot_Project_Proposal.pdf", styles["cell"])],
    ]
    meta_table = Table(meta_data, colWidths=[W * 0.28, W * 0.72])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.8, ACCENT),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 14 * mm))

    summary_stats = [
        [
            Paragraph("<b>8</b><br/>API Endpoints", styles["cover_meta"]),
            Paragraph("<b>5</b><br/>Implementation Phases", styles["cover_meta"]),
            Paragraph("<b>7</b><br/>Database Models", styles["cover_meta"]),
            Paragraph("<b>5</b><br/>LangGraph Nodes", styles["cover_meta"]),
        ]
    ]
    stats = Table(summary_stats, colWidths=[W / 4] * 4)
    stats.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, NAVY),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, STEEL),
            ]
        )
    )
    # Override text color for stats cells
    for i, cell in enumerate(summary_stats[0]):
        summary_stats[0][i] = Paragraph(
            cell.text.replace('styles["cover_meta"]', ""),
            ParagraphStyle(
                f"stat{i}",
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=colors.white,
                alignment=TA_CENTER,
            ),
        )
    # rebuild with white text
    summary_stats = [
        [
            Paragraph("<b>8</b><br/>API Endpoints", ParagraphStyle("s1", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("<b>5</b><br/>Implementation Phases", ParagraphStyle("s2", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("<b>7</b><br/>Database Models", ParagraphStyle("s3", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph("<b>5</b><br/>LangGraph Nodes", ParagraphStyle("s4", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.white, alignment=TA_CENTER)),
        ]
    ]
    stats = Table(summary_stats, colWidths=[W / 4] * 4)
    stats.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BOX", (0, 0), (-1, -1), 0.5, NAVY),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, STEEL),
            ]
        )
    )
    story.append(stats)
    story.append(PageBreak())

    # ── 1. Introduction ────────────────────────────────────────────────
    story.append(Paragraph("1. Introduction & Purpose", styles["h1"]))
    story.append(
        Paragraph(
            "This document translates the Internal HR Policy Chatbot project proposal into a "
            "concrete system architecture and phased implementation plan. The system answers "
            "employee policy questions using Retrieval-Augmented Generation (RAG), routes "
            "sensitive topics to human HR staff, and maintains an auditable decision trail.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "The chatbot is delivered as a production-style FastAPI backend so it can be "
            "integrated with chat UIs, Slack, or internal portals. Answers are grounded only "
            "in indexed company documents; high-sensitivity queries are never answered "
            "automatically.",
            styles["body"],
        )
    )

    # ── 2. System Architecture ─────────────────────────────────────────
    story.append(Paragraph("2. System Architecture Overview", styles["h1"]))
    story.append(
        Paragraph(
            "The system is organised into three layers. An authenticated employee submits a "
            "question to FastAPI. A triage model classifies it. Safe questions go through RAG "
            "retrieval and grounded response generation. Sensitive questions trigger human "
            "escalation. Everything is persisted and traced.",
            styles["body"],
        )
    )

    story.append(Paragraph("2.1 Layer Responsibilities", styles["h2"]))
    story.append(
        make_table(
            ["Layer", "Components", "Responsibility"],
            [
                [
                    "1. API Gateway",
                    "FastAPI, Pydantic, API-key auth, CORS",
                    "REST endpoints for chat, documents, escalations, health. Request validation and access control.",
                ],
                [
                    "2. AI Orchestration",
                    "LangGraph StateGraph, LangChain, Gemini Flash/Pro",
                    "Conditional workflow: triage → retrieve → respond, or escalate. Dual-model routing for cost and quality.",
                ],
                [
                    "3. Data & Storage",
                    "PostgreSQL, Qdrant, LangSmith",
                    "Users, conversations, escalations, audit logs (Postgres). Policy embeddings (Qdrant). LLM traces (LangSmith).",
                ],
            ],
            [W * 0.22, W * 0.32, W * 0.46],
            styles,
        )
    )

    story.append(Paragraph("2.2 Request Lifecycle", styles["h2"]))
    lifecycle = [
        "Employee message received via authenticated FastAPI endpoint.",
        "Triage model (Gemini Flash) produces structured output: category, sensitivity, needs_human.",
        "If safe: retrieve policy chunks from Qdrant and draft a cited answer (Gemini Pro).",
        "If sensitive: create escalation ticket and return a safe acknowledgment (no automated advice).",
        "Persist conversation, retrieval context, and decision metadata for audit.",
        "Return answer, sources, and escalation status to the client.",
    ]
    for i, step in enumerate(lifecycle, 1):
        story.append(Paragraph(f"<b>{i}.</b>  {step}", styles["bullet"]))

    # ── 3. LangGraph Workflow ──────────────────────────────────────────
    story.append(Paragraph("3. LangGraph Workflow (State Graph)", styles["h1"]))
    story.append(
        Paragraph(
            "The core intelligence is a LangGraph StateGraph with conditional edges. The triage "
            "node determines routing: safe queries follow retrieve → respond; sensitive queries "
            "go to escalate. Both paths converge on persist before returning a response.",
            styles["body"],
        )
    )

    story.append(Paragraph("3.1 Graph Topology", styles["h2"]))
    story.append(
        Paragraph(
            "<b>START</b> → <b>Triage</b> ──(safe)──→ <b>Retrieve</b> → <b>Respond</b> → <b>Persist</b> → <b>END</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "└──(sensitive)──→ <b>Escalate</b> ─────────────────→ <b>Persist</b> → <b>END</b>",
            styles["body"],
        )
    )

    story.append(Paragraph("3.2 Node Specifications", styles["h2"]))
    story.append(
        make_table(
            ["Node", "Model / Tool", "Input", "Output"],
            [
                ["Triage", "Gemini Flash", "Employee question + history", "category, sensitivity, needs_human, confidence"],
                ["Retrieve", "Qdrant + Gemini Embeddings", "Query embedding", "Top-k policy chunks with metadata"],
                ["Respond", "Gemini Pro", "Question + retrieved context", "Grounded answer + source citations"],
                ["Escalate", "Service layer", "Triage result + question", "Escalation record + safe refusal text"],
                ["Persist", "PostgreSQL", "Full turn state", "Conversation + audit log entry"],
            ],
            [W * 0.15, W * 0.28, W * 0.27, W * 0.30],
            styles,
        )
    )

    story.append(Paragraph("3.3 Dual-Model Strategy", styles["h2"]))
    story.append(
        Paragraph(
            "Gemini Flash handles lightweight classification (triage) with low latency and cost. "
            "Gemini Pro handles complex response generation where grounding quality matters most. "
            "Embeddings use Gemini text-embedding-004 for dense semantic vectors.",
            styles["body"],
        )
    )
    story.append(
        make_table(
            ["Task", "Model", "Rationale"],
            [
                ["Triage classification", "gemini-2.0-flash", "Fast, cheap, reliable structured output"],
                ["Response generation", "gemini-2.0-pro", "Better grounding, fewer hallucinations"],
                ["Embeddings", "text-embedding-004", "Dense vectors for semantic search"],
            ],
            [W * 0.30, W * 0.28, W * 0.42],
            styles,
        )
    )

    # ── 4. Triage Schema ───────────────────────────────────────────────
    story.append(Paragraph("4. Triage Classification Schema", styles["h1"]))
    story.append(
        Paragraph(
            "Every incoming question is classified into a closed policy category and assigned a "
            "sensitivity level. High-sensitivity topics are routed to human HR handling instead "
            "of automated response.",
            styles["body"],
        )
    )

    story.append(Paragraph("4.1 Policy Categories (Closed Set)", styles["h2"]))
    story.append(
        make_table(
            ["Category", "Example Query", "Typical Sensitivity"],
            [
                ["Leave", "How many sick days do I have?", "Low"],
                ["Benefits", "Does our health plan cover dental?", "Low–Medium"],
                ["Remote Work", "Can I work from another country?", "Low"],
                ["Payroll", "When is the next pay cycle?", "Low"],
                ["Expenses", "What is the limit for meal reimbursement?", "Low"],
                ["Conduct", "What counts as workplace harassment?", "High"],
                ["Termination", "What is the severance policy?", "High"],
                ["Medical", "How do I request medical leave?", "High"],
                ["General", "Where can I find the employee handbook?", "Low"],
            ],
            [W * 0.20, W * 0.50, W * 0.30],
            styles,
        )
    )

    story.append(Paragraph("4.2 Structured Triage Output", styles["h2"]))
    story.append(
        Paragraph(
            "class TriageResult(BaseModel):<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;category: PolicyCategory<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;sensitivity: Literal['low', 'medium', 'high']<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;needs_human: bool<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;reasoning: str<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;confidence: float",
            styles["code"],
        )
    )
    story.append(
        Paragraph(
            "<b>Auto-escalation rule:</b> Any query with sensitivity=high or needs_human=true "
            "bypasses RAG entirely. The system returns a safe acknowledgment and creates an "
            "escalation record for HR review.",
            styles["callout"],
        )
    )

    # ── 5. RAG Pipeline ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("5. RAG Pipeline Architecture", styles["h1"]))
    story.append(
        Paragraph(
            "Documents are ingested via Docling, embedded with Gemini, and stored in Qdrant. "
            "At query time, the retriever fetches the most relevant policy chunks for grounded "
            "response generation. Answers must refuse when retrieved evidence is weak or missing.",
            styles["body"],
        )
    )

    story.append(Paragraph("5.1 Document Ingestion Flow", styles["h2"]))
    ingest_steps = [
        ("Upload", "HR admin uploads PDF/Markdown via POST /documents/upload."),
        ("Parse", "Docling extracts structured text; handles tables, headers, and lists."),
        ("Chunk", "Split into overlapping chunks (~500 tokens, 50-token overlap)."),
        ("Embed", "Gemini text-embedding-004 converts chunks to dense vectors."),
        ("Store", "Vectors upserted into Qdrant with metadata payload (document_id, filename, section, page)."),
    ]
    for title, desc in ingest_steps:
        story.append(Paragraph(f"<b>{title}.</b>  {desc}", styles["bullet"]))

    story.append(Paragraph("5.2 Query-Time Retrieval Flow", styles["h2"]))
    retrieve_steps = [
        ("Embed Query", "Employee question embedded with the same Gemini embedding model."),
        ("Search", "Qdrant cosine similarity search; top-k=5 chunks returned."),
        ("Filter", "Score-threshold filtering to drop low-relevance results."),
        ("Augment", "Retrieved chunks injected into Gemini Pro prompt as context."),
        ("Cite", "Response includes source document name, section, and page when available."),
    ]
    for title, desc in retrieve_steps:
        story.append(Paragraph(f"<b>{title}.</b>  {desc}", styles["bullet"]))

    # ── 6. API Surface ─────────────────────────────────────────────────
    story.append(Paragraph("6. API Surface", styles["h1"]))
    story.append(
        Paragraph(
            "All versioned endpoints are prefixed with <b>/api/v1</b> and require the "
            "<b>x-api-key</b> header. Public health and root endpoints remain unauthenticated.",
            styles["body"],
        )
    )
    story.append(
        make_table(
            ["Method", "Path", "Description", "Phase"],
            [
                ["POST", "/chat", "Submit question; receive answer, sources, escalation status", "P3"],
                ["POST", "/documents/upload", "Upload HR policy PDF/Markdown for indexing", "P2"],
                ["POST", "/documents/reindex", "Rebuild vector indexes after policy updates", "P2"],
                ["GET", "/documents", "List indexed policy documents and metadata", "P2"],
                ["GET", "/conversations/{user_id}", "Retrieve an employee's conversation history", "P4"],
                ["GET", "/escalations", "List open human-review cases for HR staff", "P4"],
                ["POST", "/escalations/{id}/resolve", "Mark an escalation as handled", "P4"],
                ["GET", "/health", "Service health and dependency checks", "P1"],
            ],
            [W * 0.12, W * 0.28, W * 0.48, W * 0.12],
            styles,
        )
    )

    # ── 7. Database Schema ─────────────────────────────────────────────
    story.append(Paragraph("7. Database Schema (PostgreSQL)", styles["h1"]))
    story.append(
        Paragraph(
            "Relational data lives in PostgreSQL. Vector embeddings live in Qdrant. "
            "A thin mapping (document_id, qdrant_point_id) links the two systems. "
            "Per ADR-001, policy responses are stored separately from LangGraph checkpoint blobs "
            "so they remain independently queryable for audit and reporting.",
            styles["body"],
        )
    )
    story.append(
        make_table(
            ["Model", "Key Fields", "Purpose"],
            [
                ["User", "id, employee_id, name, email, role, created_at", "Employee identity & access control"],
                ["Conversation", "id, user_id, thread_id, started_at, last_message_at", "Session tracking per employee"],
                ["Message", "id, conversation_id, role, content, sources, created_at", "Individual turns with source citations"],
                ["PolicyDocument", "id, filename, title, version, uploaded_at, chunk_count", "Metadata for indexed HR documents"],
                ["DocumentChunk", "id, document_id, chunk_text, chunk_index, qdrant_point_id", "Mapping chunks to vectors in Qdrant"],
                ["Escalation", "id, conversation_id, user_id, category, reason, status, created_at, resolved_at, resolved_by", "Human-review case tracking"],
                ["AuditLog", "id, conversation_id, event_type, triage_result, sources_used, model_used, timestamp", "Full decision trail for compliance"],
            ],
            [W * 0.18, W * 0.48, W * 0.34],
            styles,
        )
    )

    # ── 8. Project Structure ───────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("8. Target Project Structure", styles["h1"]))
    story.append(
        Paragraph(
            "Clean separation of concerns: API layer, LLM orchestration, RAG pipeline, "
            "data models, and services.",
            styles["body"],
        )
    )
    tree = """hr-policy-chatbot/
├── pyproject.toml
├── .env
├── alembic.ini
├── docker-compose.yml
├── src/hr_chatbot/
│   ├── main.py                          # FastAPI app factory
│   ├── core/
│   │   ├── config.py                    # Pydantic settings
│   │   ├── security.py                  # API key auth
│   │   ├── logging_config.py            # Structured logging
│   │   └── database.py                  # Async SQLAlchemy engine + session
│   ├── models/                          # SQLAlchemy ORM models
│   │   ├── user.py / conversation.py / document.py
│   │   ├── escalation.py / audit.py
│   ├── api/v1/
│   │   ├── router.py
│   │   ├── endpoints/                   # chat, documents, conversations, escalations
│   │   └── schemas/                     # Pydantic request/response models
│   ├── llm/
│   │   ├── prompts/                     # triage.yaml, response.yaml
│   │   └── workflows/policy_chat/       # state.py, graph.py, nodes.py
│   ├── rag/
│   │   ├── ingestion.py                 # Docling parse + chunk
│   │   ├── embeddings.py                # Gemini embedding wrapper
│   │   └── retriever.py                 # Qdrant semantic search
│   └── services/                        # escalation_service, audit_service
├── tests/
├── alembic/versions/
├── docs/adr/
└── policies/                            # Sample HR policy files for testing"""
    for line in tree.split("\n"):
        story.append(
            Paragraph(
                line.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;"),
                ParagraphStyle(
                    "tree",
                    fontName="Courier",
                    fontSize=7.5,
                    leading=10,
                    textColor=STEEL,
                ),
            )
        )
    story.append(Spacer(1, 4 * mm))

    # ── 9. Technology Stack ────────────────────────────────────────────
    story.append(Paragraph("9. Technology Stack", styles["h1"]))
    story.append(
        make_table(
            ["Layer", "Technology", "Role"],
            [
                ["API Framework", "FastAPI", "Async REST endpoints, validation, auth hooks, OpenAPI docs"],
                ["LLM Orchestration", "LangChain + LangGraph", "State graph workflow: triage → retrieve → respond / escalate"],
                ["LLM Provider", "Google Gemini", "Flash for triage; Pro for response generation"],
                ["Schema Validation", "Pydantic v2", "Structured outputs, API schemas, settings"],
                ["Document Parsing", "Docling", "PDF/Markdown parsing, intelligent chunking"],
                ["Vector Database", "Qdrant Cloud", "Semantic similarity search over policy embeddings"],
                ["Relational DB", "PostgreSQL", "Users, conversations, escalations, documents, audit"],
                ["ORM", "SQLAlchemy (async)", "Async database access, relationship mapping"],
                ["Migrations", "Alembic", "Schema versioning and evolution"],
                ["Observability", "LangSmith", "End-to-end LLM tracing, latency, prompt debugging"],
                ["Configuration", "python-dotenv + pydantic-settings", "Env-based config with validation"],
            ],
            [W * 0.22, W * 0.28, W * 0.50],
            styles,
        )
    )

    # ── 10. Implementation Roadmap ─────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("10. Implementation Roadmap", styles["h1"]))
    story.append(
        Paragraph(
            "Five phases from foundation to production-ready, spanning approximately ten weeks. "
            "Items already present in the current codebase are marked as Done.",
            styles["body"],
        )
    )

    phases = [
        (
            "Phase 1 — Foundation & Core Infrastructure",
            "Week 1–2",
            "In Progress",
            [
                ("Done", "Project scaffolding (pyproject.toml, src layout, .env)"),
                ("Done", "FastAPI app factory + CORS + health endpoint"),
                ("Done", "Pydantic settings & env-based configuration"),
                ("Done", "API key authentication middleware"),
                ("Done", "Structured logging setup"),
                ("Todo", "PostgreSQL database models (users, conversations, escalations, documents)"),
                ("Todo", "Alembic migration setup for schema versioning"),
                ("Todo", "Database session management (async SQLAlchemy)"),
            ],
        ),
        (
            "Phase 2 — Document Ingestion & RAG Pipeline",
            "Week 3–4",
            "Pending",
            [
                ("Todo", "Docling integration for PDF/Markdown parsing & chunking"),
                ("Todo", "Google Gemini embedding model integration"),
                ("Todo", "Qdrant vector store setup & collection management"),
                ("Todo", "POST /documents/upload endpoint (file upload + parse + embed)"),
                ("Todo", "POST /documents/reindex endpoint (re-chunk + re-embed)"),
                ("Todo", "GET /documents endpoint (list indexed docs + metadata)"),
                ("Todo", "Retriever tool: semantic search over Qdrant with source tracking"),
            ],
        ),
        (
            "Phase 3 — Triage & LangGraph Workflow",
            "Week 5–6",
            "Pending",
            [
                ("Todo", "Triage node: Gemini Flash classifies category + sensitivity + needs_human"),
                ("Todo", "Auto-reply node: Gemini Pro generates grounded response with citations"),
                ("Todo", "Escalation node: creates escalation record, returns safe refusal"),
                ("Todo", "LangGraph StateGraph wiring with conditional edges"),
                ("Todo", "Structured Pydantic output parsing for triage decisions"),
                ("Todo", "Conversation memory via LangGraph PostgreSQL checkpointer"),
            ],
        ),
        (
            "Phase 4 — Escalation, Audit & Admin APIs",
            "Week 7–8",
            "Pending",
            [
                ("Todo", "GET /escalations endpoint (list open cases for HR)"),
                ("Todo", "POST /escalations/{id}/resolve endpoint"),
                ("Todo", "GET /conversations/{user_id} endpoint"),
                ("Todo", "Audit log persistence (questions, retrieved docs, decisions)"),
                ("Todo", "LangSmith tracing integration for full pipeline observability"),
            ],
        ),
        (
            "Phase 5 — Testing, Evaluation & Hardening",
            "Week 9–10",
            "Pending",
            [
                ("Todo", "Unit tests for triage classification accuracy"),
                ("Todo", "Integration tests for full RAG pipeline (upload → query → answer)"),
                ("Todo", "Escalation scenario tests (sensitivity detection)"),
                ("Todo", "Grounding quality evaluation (hallucination checks)"),
                ("Todo", "API contract tests with httpx TestClient"),
                ("Todo", "Docker Compose for local dev (FastAPI + PostgreSQL + Qdrant)"),
            ],
        ),
    ]

    for title, duration, status, tasks in phases:
        story.append(Paragraph(f"{title}  <font color='#5A6577'>({duration} · {status})</font>", styles["h2"]))
        rows = [[s, t] for s, t in tasks]
        story.append(
            make_table(
                ["Status", "Task"],
                rows,
                [W * 0.12, W * 0.88],
                styles,
            )
        )
        story.append(Spacer(1, 2 * mm))

    # ── 11. Current Assessment ─────────────────────────────────────────
    story.append(Paragraph("11. Current Codebase Assessment", styles["h1"]))
    story.append(
        Paragraph(
            "<b>Completed.</b> FastAPI app factory, Pydantic settings, API-key auth, structured "
            "logging, a basic LangGraph skeleton with a single policy-chat node, and project "
            "scaffolding are in place.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "<b>Remaining.</b> Database layer (PostgreSQL models, migrations), RAG pipeline "
            "(Docling + Qdrant), multi-node LangGraph workflow (triage, retrieve, respond, "
            "escalate), escalation APIs, conversation history, audit logging, and testing "
            "are all pending.",
            styles["body"],
        )
    )

    # ── 12. ADRs ───────────────────────────────────────────────────────
    story.append(Paragraph("12. Key Design Decisions (ADRs)", styles["h1"]))

    adrs = [
        (
            "ADR-001 — Policy responses stored separately from LangGraph checkpoints",
            "Policy responses (the chatbot's assessment) are stored in a dedicated PostgreSQL "
            "table, not inside LangGraph checkpoint blobs. This enables independent querying, "
            "auditing, and reporting without deserializing conversation state. A thin mapping "
            "(thread_id → policy_response_id) links the two stores.",
        ),
        (
            "ADR-002 — Externalized prompts in YAML files",
            "System prompts for triage and response generation live in YAML files under "
            "llm/prompts/, not hardcoded in Python. This allows prompt iteration without code "
            "changes and supports versioned prompt management.",
        ),
        (
            "ADR-003 — Qdrant payload metadata for source tracking",
            "Each Qdrant point carries metadata (document_id, filename, section, page_number) "
            "in its payload. This enables the response generator to produce precise source "
            "citations without a secondary database lookup.",
        ),
        (
            "ADR-004 — Conversation memory via LangGraph checkpointer",
            "Short-term conversation memory (multi-turn context) is handled by the LangGraph "
            "PostgreSQL checkpointer using thread_id. The Message table stores clean text for "
            "audit/history, while the checkpointer handles full graph state for continuation.",
        ),
    ]
    for title, body in adrs:
        story.append(Paragraph(title, styles["h3"]))
        story.append(Paragraph(body, styles["body"]))

    # ── 13. Guardrails ─────────────────────────────────────────────────
    story.append(Paragraph("13. Ethical Guardrails & Safety", styles["h1"]))
    story.append(Paragraph("Must refuse when:", styles["h3"]))
    for item in [
        "Retrieved evidence is weak or missing.",
        "The question asks for personalized legal, medical, or disciplinary judgment.",
        "The topic involves harassment, termination, or medical issues (escalate instead).",
    ]:
        story.append(Paragraph(f"•  {item}", styles["bullet"]))

    story.append(Paragraph("Must always:", styles["h3"]))
    for item in [
        "Include document version or effective-date context where available.",
        "Keep employee conversations access-controlled and confidential.",
        "Avoid storing unnecessary sensitive personal details in long-term memory.",
        "Maintain a full audit trail of questions, retrieved sources, and model decisions.",
        "Leave final responsibility for sensitive HR decisions with human staff.",
    ]:
        story.append(Paragraph(f"•  {item}", styles["bullet"]))

    # ── 14. Out of Scope ───────────────────────────────────────────────
    story.append(Paragraph("14. Out of Scope", styles["h1"]))
    for item in [
        "Full HRIS replacement (payroll processing, attendance systems, etc.).",
        "Legal advice generation beyond what is stated in company policy documents.",
        "Public-facing customer support use cases.",
        "Native mobile application development.",
    ]:
        story.append(Paragraph(f"•  {item}", styles["bullet"]))

    # ── 15. Expected Outcomes ──────────────────────────────────────────
    story.append(Paragraph("15. Expected Outcomes", styles["h1"]))
    for item in [
        "A working FastAPI-based HR policy assistant with grounded, cited responses.",
        "Demonstrable reduction of repetitive HR policy inquiries through automation.",
        "Safe escalation behavior for sensitive employee issues.",
        "Reusable architecture for other internal knowledge domains.",
        "A portfolio-ready system showing production-oriented LLM engineering skills.",
    ]:
        story.append(Paragraph(f"•  {item}", styles["bullet"]))

    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "— End of Implementation Plan —",
            styles["cover_meta"],
        )
    )

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote: {path}")
