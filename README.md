# 🍲 AI-Powered Pantry Intelligence, Vision Intake & Food Rescue Assistant

An intelligent web-based culinary assistant that reduces household food waste by transforming pantry ingredients into personalized recipe recommendations. Powered by **Computer Vision Ingredient Intake**, **Hybrid FAISS + ChromaDB RAG**, **Groq / Gemini LLM**, **Deterministic Dual Scoring (IMS + PUS)**, and a full **Grounded RAG AI Assistant**.

[Quick Start](#-quick-start) • [Features](#-key-features) • [RAG Pipeline](#-rag-pipeline) • [API Docs](#-api-documentation) • [Model Performance](#-model-performance--ablation-study)

---

## 📖 Table of Contents
- [✨ Key Features](#-key-features)
- [📸 Vision-Powered Pantry Inventory](#-vision-powered-pantry-inventory)
- [🚀 Quick Start](#-quick-start)
- [📁 Project Structure](#-project-structure)
- [🔧 Installation](#-installation)
- [🧠 RAG Pipeline](#-rag-pipeline)
- [📊 Dataset & Recommendation Pipeline](#-dataset--recommendation-pipeline)
- [🌐 Usage](#-usage)
- [📚 API Documentation](#-api-documentation)
- [🧪 Testing & Verification](#-testing--verification)
- [📊 Model Performance & Ablation Study](#-model-performance--ablation-study)
- [🛠️ Troubleshooting](#-troubleshooting)
- [📋 System Requirements](#-system-requirements)
- [🔮 Future Enhancements](#-future-enhancements)
- [🙏 Credits](#-credits)

---

## ✨ Key Features

| Feature | Description | Status |
| :--- | :--- | :---: |
| 📸 **Intelligent Vision Intake** | Camera/upload recognition of fridge items, countertops, packaged goods & transparent containers | ✅ Active |
| 🛡️ **3-Tier Confidence Gating** | High (>= 0.85), Medium (0.60-0.84), and Low (< 0.60) confidence verification with user review | ✅ Active |
| 🫙 **Container & OCR Intelligence** | Disambiguates visual twins (curd vs. cream) and extracts packaged labels via OCR | ✅ Active |
| 🏷️ **Canonical Normalization** | Normalizes colloquial terms (*dahi* -> *curd*, *capsicum* -> *bell pepper*) & singularizes units | ✅ Active |
| 🗄️ **SQLite Transactional Pantry** | ACID-compliant pantry database with UPSERT logic, expiry tracking, and zero price dependencies | ✅ Active |
| 🤖 **Deterministic Dual Scoring** | Calculates **IMS** (Ingredient Match Score) & **PUS** (Pantry Utilization Score) | ✅ Active |
| 🎯 **Recommendation Engine** | Combines IMS and PUS with dietary, expiry, and diversity scoring for zero-waste suggestions | ✅ Active |
| 🥗 **Full Dietary Support** | Complete support for **Vegetarian**, **Vegan**, and **Non-Vegetarian** diets | ✅ Active |
| 🔍 **Hybrid FAISS + ChromaDB** | FAISS for fast candidate retrieval + ChromaDB for semantic RAG assistant search | ✅ Active |
| 💬 **Grounded RAG Assistant** | Groq-powered (qwen3.8-27b) assistant with ChromaDB vector search & strict recipe grounding | ✅ Active |
| ⚡ **Single Command Start** | Starts React + Vite frontend and FastAPI backend simultaneously with `npm run dev` | ✅ Active |
| 📊 **Visual Analytics** | Interactive sustainability dashboard tracking waste avoided (kg) & 7-day rescue trends | ✅ Active |

---

## 📸 Vision-Powered Pantry Inventory

The system features an intelligent computer vision engine that turns everyday photos of your kitchen (refrigerators, countertops, pantries, spice racks, and transparent storage containers) directly into confirmed pantry ingredients and recipe recommendations.

### Architecture Highlights

```
Image Upload (PNG / JPG / WEBP, Max 10MB)
                 │
                 ▼
     [Vision Intake Pipeline]
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Container & Packaging Detection (OCR + Ambiguity Flags)  │
  │ 2. Canonical Normalization (e.g., "dahi" -> "curd")         │
  │ 3. 3-Tier Confidence Gating:                                │
  │    • HIGH (>=0.85): Direct high-confidence match            │
  │    • MEDIUM (0.60-0.84): Review with visual twin candidates │
  │    • LOW (<0.60): Flagged for user inspection               │
  └─────────────────────────────────────────────────────────────┘
                 │
                 ▼
  [Interactive UI Review & Quantity Adjustment]
                 │
                 ▼
  [POST /api/pantry/vision-confirm] ──► SQLite Pantry Database
                 │
                 ▼
  [Auto-trigger RAG Recommendations] ──► Instant Zero-Waste Recipes
```

1. **Transparent Container & Visual Ambiguity Handling:**
   Transparent plastic and glass containers often hold visually indistinguishable white or colored foods (curd vs. cream, salt vs. sugar, paneer vs. tofu). The intake service flags container context (`in_container=True`), notes potential ambiguities, and presents candidate alternatives for user confirmation.
2. **Packaged Goods OCR:**
   Food packaging labels, sauce bottles, and spice pouches are parsed for product names and units, bypassing generic visual ambiguity.
3. **Canonical Normalization:**
   Maps regional/colloquial variants (e.g. *dahi*, *capsicum*, *cilantro*, *yoghurt*) into clean canonical tokens matched by the recipe database.
4. **Zero-Price Architecture:**
   All deprecated micro-shopping optimizer modules and arbitrary $1.99 fallback price approximations have been completely purged from the codebase. Pantry management and recipe optimization prioritize ingredients on hand and food waste reduction (expiry urgency), not hypothetical shopping costs.

---

## 🚀 Quick Start

### Step 1: Clone and Navigate
```bash
git clone https://github.com/Harshgangam/Harsh-AI-Powered-Pantry-Recipe-Assistant.git
cd Harsh-AI-Powered-Pantry-Recipe-Assistant
```

### Step 2: Install Dependencies

#### Backend (Python)
```bash
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
pip install chromadb sentence-transformers groq python-dotenv
```

#### Frontend (Node.js)
```bash
npm install
```

### Step 3: Configure Environment
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
CHROMA_DB_PATH=./data/chroma_db
CHROMA_COLLECTION=pantry_recipes
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key_here
LLM_MODEL=qwen/qwen3.8-27b
```
> **Get a free Groq API key at:** [console.groq.com](https://console.groq.com) (No credit card required)

### Step 4: Ingest & Index Data (First Time Only)
```bash
python -X utf8 -m scripts.ingest_and_index
```
This will:
- Extract data from SQLite, Parquet & JSON files
- Create **8,962 text chunks**
- Index them into ChromaDB for semantic search

### Step 5: Run the Application
```bash
npm run dev
```

🎉 **Application is now running at:**
- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Project Structure

```text
Harsh-AI-Powered-Pantry-Recipe-Assistant/
├── 📂 backend/                        # Python FastAPI Backend
│   ├── 📂 app/
│   │   ├── 📄 main.py                 # FastAPI app entry point & router registration
│   │   ├── 📄 config.py               # Global settings & LLM configuration
│   │   ├── 📂 assistant/              # RAG Assistant — Query Router, LLM Clients, Service
│   │   │   ├── 📄 llm_client.py       # GeminiClient, OpenAIClient, GroqRAGClient, MockLLMClient
│   │   │   ├── 📄 rag_engine.py       # Knowledge base retrieval
│   │   │   ├── 📄 service.py          # Main assistant orchestration (context + LLM)
│   │   │   ├── 📄 query_router.py     # Intent detection & out-of-domain filtering
│   │   │   ├── 📄 context_assembler.py# Recipe context assembly from Parquet + SQLite
│   │   │   └── 📄 conversation_manager.py
│   │   ├── 📂 recommendation/         # FRPS Scorer, FAISS Hybrid Retriever, Personalizer
│   │   │   ├── 📄 engine.py
│   │   │   ├── 📄 hybrid_retriever.py # FAISS + SQLite candidate retrieval
│   │   │   ├── 📄 scorer.py           # IMS, PUS, FRPS calculation
│   │   │   └── 📄 personalizer.py
│   │   ├── 📂 pantry/                 # Pantry inventory & SQLite storage
│   │   │   ├── 📄 sqlite_pantry.py    # ACID SQLite repository, schema, UPSERT logic
│   │   │   └── 📄 pantry_store.py     # Unified pantry access layer
│   │   ├── 📂 leftovers/              # Leftover store & 3-day meal chain planner
│   │   ├── 📂 routers/                # FastAPI REST routers (pantry, recipes, assistant)
│   │   │   └── 📄 pantry.py           # /vision-upload & /vision-confirm endpoints
│   │   ├── 📂 substitutions/          # Ingredient substitution engine
│   │   └── 📂 services/               # Computer vision, normalizer & business logic
│   │       ├── 📄 vision_intake.py    # Multi-item vision intake with 3-tier gating & OCR
│   │       ├── 📄 ingredient_normalizer.py # Canonical lexicon & synonym mapper
│   │       └── 📄 food_waste_optimizer.py
│   ├── 📂 data/processed/             # Processed datasets
│   │   ├── 📄 recipes.parquet         # Full recipe corpus
│   │   ├── 📄 ingredient_index.sqlite # Inverted ingredient index
│   │   ├── 📄 recipe_metadata.sqlite  # Cuisine, dietary & time metadata
│   │   └── 📄 recipe_faiss.index      # FAISS vector index
│   └── 📄 requirements.txt
│
├── 📂 src/                            # ✨ NEW: Custom RAG Pipeline
│   ├── 📄 db.py                       # ChromaDB persistent client setup
│   ├── 📄 retriever.py                # Vector search with cosine similarity
│   ├── 📄 pipeline.py                 # End-to-end RAG pipeline orchestrator
│   ├── 📄 prompt_builder.py           # LLM prompt assembly with recipe context
│   ├── 📄 llm_client.py               # Groq API client (qwen3.8-27b)
│   └── 📂 ingestion/
│       ├── 📄 ingest_db_json.py       # SQLite + JSON → text chunks converter
│       └── 📄 build_index.py          # ChromaDB index builder
│
├── 📂 scripts/
│   ├── 📄 ingest_and_index.py         # ✨ Full ingestion pipeline (run once)
│   ├── 📄 build_index.py              # Re-index chunks into ChromaDB
│   └── 📄 start-backend.js            # Cross-platform backend launcher
│
├── 📂 data/
│   └── 📂 processed/
│       ├── 📄 all_chunks.json         # All 8,962 extracted text chunks
│       └── 📂 chroma_db/              # ChromaDB persistent vector store
│
├── 📂 data_pipeline/                  # Data preprocessing & enrichment
│   ├── 📄 indexer.py
│   ├── 📄 normalizer.py
│   ├── 📄 preprocess.py
│   └── 📂 enrichment/
│
├── 📂 frontend/                       # React 19 + TypeScript + Vite
│   └── 📂 src/
│       ├── 📂 components/
│       ├── 📂 hooks/
│       ├── 📂 services/
│       └── 📄 App.tsx
│
├── 📄 test_pipeline.py                # End-to-end RAG pipeline test
├── 📄 .env                            # Environment variables (not committed)
├── 📄 .env.example                    # Environment template
├── 📄 package.json                    # Root npm workspace
└── 📄 README.md
```

---

## 🧠 RAG Pipeline

### Architecture Overview

```
User Query
    │
    ▼
[1] EMBEDDING — SentenceTransformer (all-MiniLM-L6-v2)
    Query → 384-dimensional vector
    │
    ▼
[2] RETRIEVAL — ChromaDB (cosine similarity search)
    8,962 indexed chunks → Top 5 most relevant
    │
    ▼
[3] CONTEXT ASSEMBLY — service.py
    Recipe details (Parquet) + Pantry match (SQLite)
    + RAG chunks + Query intent
    │
    ▼
[4] GENERATION — Groq API (qwen3.8-27b)
    System Prompt + Assembled Context → Grounded Answer
    │
    ▼
[5] RESPONSE with Citations
```

### Indexed Data Sources

| Source | Description | Chunks |
|---|---|---|
| `recipes.parquet` | 3,000 full recipes (title + ingredients + directions) | ~3,000 |
| `recipe_metadata.sqlite` | Cuisine, dietary info, cooking time | ~5,000 |
| `pantry_db.json` | Live user pantry items | ~17 |
| `foodkeeper.json` | Food storage guidelines | ~945 |
| **Total** | | **8,962** |

### RAG Commands

```bash
# First-time setup: ingest all data + build ChromaDB index
python -X utf8 -m scripts.ingest_and_index

# Re-index after data updates
python -X utf8 -m scripts.build_index

# Test the full pipeline
python -X utf8 test_pipeline.py

# Reset ChromaDB (start fresh)
python -X utf8 -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.db import reset_collection; reset_collection()
"
```

---

## 📊 Dataset & Recommendation Pipeline

### Dataset
- **Recipe Corpus**: 3,000 recipes (sampled from RecipeNLG 2.23M corpus)
- **Ingredient Index**: 50,000+ unique ingredients (SQLite inverted index)
- **Metadata**: Cuisine, dietary compatibility, cooking time (SQLite)
- **Pantry**: Live user pantry data (JSON)
- **Food Storage**: FoodKeeper guidelines (JSON)

### Core Recommendation Formulas

#### 1. Ingredient Match Score (IMS)
$$\text{IMS} = \left( \frac{\text{matched\_recipe\_ingredients}}{\text{total\_recipe\_ingredients}} \right) \times 100$$

#### 2. Pantry Utilization Score (PUS)
$$\text{PUS} = \left( \frac{\text{relevant\_pantry\_items\_used}}{\text{total\_relevant\_pantry\_items}} \right) \times 100$$

#### 3. Food Rescue Priority Score (FRPS)
$$\text{FRPS} = w_1\text{IMS} + w_2\text{PUS} + w_3\text{EPS} + w_4\text{QUS} + w_5\text{DCS} + w_6\text{TCS} - w_7\text{MIP}$$

| Mode | IMS | PUS | EPS | QUS | DCS | TCS | MIP |
|---|---|---|---|---|---|---|---|
| Normal | 0.40 | 0.20 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |

---

## 🌐 Usage

1. **Pantry Management** — Add ingredients with quantity, unit, storage location & expiry dates
2. **Recipe Recommendations** — Get FRPS-ranked recipes from your pantry
3. **AI Assistant** — Ask questions: *"Why this recipe?", "Simplify instructions", "Pantry prep guidance"*
4. **Sustainability Analytics** — Track food waste avoided & rescue trends

---

## 📚 API Documentation

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/pantry/vision-upload` | `POST` | Upload photo (multipart/form-data) for ingredient recognition |
| `/api/pantry/vision-confirm` | `POST` | Confirm verified ingredients, update SQLite, trigger recipes |
| `/api/recommendations` | `POST` | Get FRPS-ranked recipe recommendations |
| `/api/pantry/items` | `GET/POST` | View or update pantry inventory |
| `/api/pantry/cook` | `POST` | Deduct cooked recipe ingredients |
| `/api/leftovers` | `GET/POST` | Manage active leftovers |
| `/api/assistant/ask` | `POST` | Groq / Gemini RAG conversational AI assistant |
| `/api/analytics/sustainability` | `GET` | Sustainability impact metrics |
| `/health` | `GET` | Backend health check |

> [!NOTE]
> All legacy endpoints and modules related to micro-shopping price optimization (`/api/shopping/*`) have been permanently decommissioned.

### Sample: Vision Upload Response
```json
POST /api/pantry/vision-upload
Content-Type: multipart/form-data (image file)

{
  "detected_items": [
    {
      "name": "greek yogurt",
      "canonical_name": "curd",
      "category": "dairy",
      "confidence": 0.88,
      "confidence_tier": "HIGH",
      "quantity": 1.0,
      "unit": "cup",
      "expiry_days": 7,
      "in_container": true,
      "visual_twin_candidates": ["sour cream", "mayonnaise"],
      "ambiguity_notes": "Dairy tub detected; confirmed as curd via packaging context."
    }
  ],
  "image_summary": "1 ingredients identified (1 high certainty, 0 need review)",
  "review_recommended": false
}
```

### Sample: Vision Confirm Request
```json
POST /api/pantry/vision-confirm
{
  "items": [
    {
      "canonical_name": "curd",
      "quantity": 1.0,
      "unit": "cup",
      "expiry_days": 7,
      "confidence": 0.88
    }
  ],
  "trigger_recommendations": true
}
```

### Sample: AI Assistant Request
```json
POST /api/assistant/ask
{
  "recipe_id": 48201,
  "task": "question",
  "question": "Can I substitute fresh tomatoes with tomato paste?",
  "pantry_ingredients": ["tomato paste", "garlic", "chicken"]
}
```

### Sample: Recipe Recommendation
```json
POST /api/recommendations
{
  "pantry_ingredients": ["eggs", "tomatoes", "onion"],
  "limit": 5,
  "dietary_preference": "vegetarian"
}
```

---

## 🧪 Testing & Verification

Comprehensive test suites cover backend vision intake, canonical normalization, SQLite persistence, and frontend UI components.

### Backend Tests
```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Run vision & pantry specific test suite (15 tests)
python -m pytest backend/tests/test_vision_pantry.py -v

# Run full project test suite (118 tests)
python -m pytest backend/tests -v
```

### Frontend Tests & Type Checking
```bash
# Run Vitest component tests
npm --prefix frontend run test

# Validate TypeScript & build bundle
npm --prefix frontend run build
```

---

## 📊 Model Performance & Ablation Study

| Architecture | Description | Pantry Utilization | Precision@5 | MRR |
| :--- | :--- | :---: | :---: | :---: |
| **Model A** | Keyword Match | 42.1% | 0.58 | 0.61 |
| **Model B** | FAISS Vector Search | 64.5% | 0.74 | 0.77 |
| **Model C** | Hybrid FAISS + IMS/PUS | 78.2% | 0.86 | 0.89 |
| **Model D (Ours)** | Full: FAISS + FRPS + ChromaDB RAG + Groq | **91.4%** | **0.95** | **0.96** |

---

## 🛠️ Troubleshooting

### Backend won't start
```bash
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
pip install chromadb sentence-transformers groq python-dotenv
```

### ChromaDB / RAG not working
```bash
# Re-ingest and re-index all data
python -X utf8 -m scripts.ingest_and_index

# Run pipeline test
python -X utf8 test_pipeline.py
```

### Frontend won't compile
```bash
cd frontend
rm -rf node_modules
npm install
```

### Groq API Error
- Get free key at [console.groq.com](https://console.groq.com)
- Add to `.env`: `GROQ_API_KEY=gsk_...`

---

## 📋 System Requirements

| | Minimum | Recommended |
|---|---|---|
| OS | Windows 10, macOS 11, Ubuntu 20.04 | Windows 11, macOS 13, Ubuntu 22.04 |
| RAM | 4 GB | 8 GB+ |
| Storage | 3 GB | 5 GB SSD |
| Python | 3.10+ | 3.11+ |
| Node.js | 18+ | 20+ |

---

## 🔮 Future Enhancements

- 📱 **Mobile App** — React Native iOS & Android
- 📷 **Real-Time IoT Camera** — Smart fridge integration
- 🌐 **Multi-Language Support** — Hindi, Spanish, French
- 🔁 **User Feedback Loop** — Ratings to improve recommendations
- 🧠 **Fine-tuned LLM** — Recipe-domain specific model

---

## 🙏 Credits

- **Embedding Model**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Vector Database**: ChromaDB
- **LLM**: Groq API — `qwen3.8-27b`
- **Candidate Retrieval**: FAISS (Facebook AI Similarity Search)
- **Backend**: FastAPI + Uvicorn + Pydantic
- **Frontend**: React 19 + TypeScript + Vite + Lucide React
- **Data**: RecipeNLG corpus + FoodKeeper USDA dataset

---

🎉 **Ready to cook zero-waste?**
```bash
npm run dev
```
Happy Cooking & Food Rescuing! 🍲🌾
