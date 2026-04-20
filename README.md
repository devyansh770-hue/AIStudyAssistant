# 🚀 StudyAI: Advanced Cognitive Learning Ecosystem

**Developed for the National Level Hackathon 2026** — *Status: Production Ready*

StudyAI is not just another study app; it is a high-performance **AI-Powered Learning Management System (LMS)** designed to optimize student retention through real-time cognitive modeling, heuristic error analysis, and autonomous knowledge extraction.

---

## 🎨 Design Philosophy: "Focus through Aesthetics"
StudyAI features a **Premium Glassmorphism Design System** built from scratch with Vanilla CSS. The UI is engineered to reduce visual fatigue while maintaining a futuristic, high-end feel that encourages deep-work sessions.

---

## 🧠 Advanced Engineering Features

### 1. 📉 Hybrid NLP Mistake Pattern Analyzer
Instead of basic error logging, StudyAI uses a **Hybrid NLP Engine** that combines statistical thresholding with LLM orchestration. 
- **Pattern Recognition**: Heuristically clusters errors into categories: *Conceptual Confusion, Difficulty Ceilings, or Time-Pressure Fatigue*.
- **Semantic Synthesis**: Uses **Gemini 1.5 Pro** to generate actionable, natural-language insights from structured performance data.

### 2. 🔥 Adaptive Cognitive Load Optimizer
An implementation of a **Heuristic State-Space Model** that tracks student engagement in real-time.
- **Dynamic Load Estimation**: Adjusts a load variable ($L$) based on time-weighted performance rewards (+0.07) and difficulty-scaled penalties (-0.12).
- **Flow Zone Detection**: Automatically recommends difficulty shifts or breaks to keep the student in the "Flow Zone"—the optimal balance between challenge and skill.

### 3. 🕸️ Autonomous Knowledge Graph Construction
StudyAI performs **Entity-Relationship Extraction (ERE)** on unstructured course syllabus and question banks.
- **Relational Mapping**: Generates a dynamic adjacency list of concepts (Nodes) and dependencies (Edges: *requires, part_of, leads_to*).
- **Mastery Visualization**: Uses **vis.js** to render a force-directed graph where node colors dynamically reflect real-time mastery levels across disparate courses.

### 4. 📅 Neural Spaced-Repetition Scheduler
A data-driven study planner that prioritizes topics based on the **Spaced Repetition** logic, ensuring long-term memory consolidation by analyzing historical quiz decay and upcoming exam proximity.

---

## 🛠️ High-Performance Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | **Python 3.13**, **Django 6**, **PostgreSQL** (Prod) / SQLite (Dev) |
| **AI / Orchestration** | **Google Gemini 1.5 Pro**, **GenAI SDK**, Heuristic Modeling |
| **Frontend Architecture** | **Vanilla CSS (Glassmorphism)**, JavaScript (ES6+), vis.js |
| **Security & Ops** | **Google OAuth 2.0**, WhiteNoise, Gunicorn, OTP-Auth, Rate-Limiting |

---

## 🛡️ Security & Scalability
- **Production-Ready**: Configured with WhiteNoise for efficient static file serving and PostgreSQL for robust data integrity.
- **Enhanced Auth**: Multi-layered security including Session Management, CSRF Protection, and Email OTP verification.
- **Rate-Limiting**: Protection against automated scraping and brute-force attempts on API endpoints.

---

## 👥 The Team
**Developed by:**
- **Devyansh Verma** — Lead Architect & AI Engineer
- **Jyotsna Chaudhary** — Frontend Strategist & Content Systems

---

## 🚀 Quick Start
```bash
# Clone the repository
git clone https://github.com/your-username/studyai.git && cd studyai/ai_study_assistant

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Launch local server
python manage.py runserver
```

---

*“Intelligent Systems for a Smarter Future” — Computing & AI Innovation Expo 2026*
