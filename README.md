# 🎓 Study Buddy - Local AI Study Assistant

An open-source, beginner-friendly academic study assistant built with **FastAPI**, **Local Open-Weight LLMs (Ollama)**, and **Retrieval-Augmented Generation (RAG)** for **Hacktoberfest 2026**.

Upload your study materials (such as lecture notes, textbook chapters, or research papers in PDF format) and ask questions. Study Buddy extracts the text, stores chunk embeddings in a simple local vector store, and uses a locally running AI model to generate grounded answers with document citations.

---

## 💡 The Problem Being Solved

Students and researchers often deal with dense, multi-page PDFs. Generic cloud AI chatbots present major downsides:
1. **Hallucinations:** Standard models often fabricate facts without referencing actual course materials.
2. **Privacy Concerns:** Uploading sensitive research, thesis drafts, or unpublished course slides to third-party cloud APIs poses privacy risks.
3. **API Costs & Rate Limits:** Cloud LLM tokens cost money and require ongoing subscription fees.

**Study Buddy** solves this by running **100% locally on your computer**:
- Your study notes never leave your laptop.
- Answers are strictly grounded in your uploaded documents.
- Every response provides source citations (document name, page number, and relevant excerpt).

---

## 🌟 Key Features

- 📄 **PDF Upload & Extraction:** Upload PDFs via API or web UI; text is cleanly extracted page-by-page.
- ✂️ **Smart Text Chunking:** Text is split into overlapping chunks with preserved document and page metadata.
- 🔢 **Zero-Cloud Embeddings:** Computes vector representations using open-source models via Ollama (with built-in local fallback).
- 💾 **Lightweight Local Vector Store:** Stores chunks and vectors in a transparent `data/vector_store.json` using NumPy cosine similarity—no external vector databases required.
- 🦙 **Local Open-Weight LLM:** Connects to models like **Llama 3**, **Mistral**, or **Phi-3** running locally through Ollama.
- 📑 **Source Citations:** Every answer links back to the exact document, page number, and text snippet used.
- 🛡️ **Anti-Hallucination Prompting:** If information is not in the uploaded documents, the assistant clearly states it cannot find the answer rather than making things up.
- 🖥️ **Interactive Web Interface:** Single-page frontend to upload files, view document status, ask questions, and read cited answers.

---

## 🏗️ Architecture & How RAG Works

```
                                  +-------------------+
                                  |   Study Material  |
                                  |       (PDF)       |
                                  +---------+---------+
                                            |
                                            v
                                  +---------+---------+
                                  |    PDF Loader     | (app/utils/pdf_loader.py)
                                  | (pypdf Extraction)|
                                  +---------+---------+
                                            |
                                            v
                                  +---------+---------+
                                  |   Text Chunker    |
                                  |  (600 chars/page) |
                                  +---------+---------+
                                            |
                                            v
                                  +---------+---------+
                                  | Embedding Service | (Ollama / Local Fallback)
                                  +---------+---------+
                                            |
                                            v
                                  +---------+---------+
                                  | Local Vector Store| (data/vector_store.json)
                                  +---------+---------+
                                            |
=========================================== | ============================================
                                  RAG QUERY PIPELINE
=========================================== | ============================================
                                            |
  +------------------+                      |
  |  User Question   |                      |
  +--------+---------+                      |
           |                                |
           v                                |
  +--------+---------+                      |
  | Query Embedding  |                      |
  +--------+---------+                      |
           |                                |
           v                                v
  +--------+--------------------------------+---------+
  |    Cosine Similarity Search in Vector Store       |
  |            (Top Relevant Chunks)                  |
  +--------------------+------------------------------+
                       |
                       v
  +--------------------+------------------------------+
  |     Augmented Prompt Assembly with Context        |
  |  "Answer strictly based on Context excerpts..."   |
  +--------------------+------------------------------+
                       |
                       v
  +--------------------+------------------------------+
  |               Local Open-Weight LLM               | (Ollama: Llama 3)
  +--------------------+------------------------------+
                       |
                       v
  +--------------------+------------------------------+
  |            Answer + Document Citations            |
  +---------------------------------------------------+
```

---

## 🛠️ Technologies Used

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Programming language |
| **FastAPI** | High-performance, async web framework |
| **Uvicorn** | ASGI web server |
| **Pydantic** | Request/response data validation |
| **pypdf** | PDF document parsing and text extraction |
| **NumPy** | Vector operations and cosine similarity computation |
| **Ollama** | Local runtime for open-weight LLMs and embeddings |
| **HTML5 / CSS3 / Vanilla JS** | Lightweight, responsive web frontend |
| **Pytest** | Automated test suite |

---

## 🚀 Quickstart Guide

### Option 1: One-Click Launch (100% Offline Mode)

If you downloaded or cloned this project to your laptop, you can start everything with a single click:

- **Windows:** Double-click [`run.bat`](file:///d:/Python%20Projects/studyBuddy/run.bat) (or run `.\run.bat` in your terminal).
- **macOS / Linux:** Run `./run.sh` in your terminal.

These scripts automatically check Python, create your virtual environment, install requirements, and open Study Buddy in your default browser at `http://127.0.0.1:8000`!

---

### Option 2: Manual Setup

```bash
# 1. Clone or download the repository
git clone https://github.com/your-username/study-buddy.git
cd study-buddy

# 2. Create a virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## ☁️ Deploying to Vercel (Web Access for Others)

You can deploy Study Buddy to Vercel so anyone can use it online without installing anything on their computer!

### Steps to Deploy on Vercel:

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Add Vercel deployment and offline bundles"
   git push origin main
   ```
2. **Import into Vercel:**
   - Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
   - Select your GitHub repository.
   - Vercel automatically detects [`vercel.json`](file:///d:/Python%20Projects/studyBuddy/vercel.json) and [`api/index.py`](file:///d:/Python%20Projects/studyBuddy/api/index.py).
3. **Configure Environment Variables in Vercel:**
   In your Vercel Project Settings under **Environment Variables**, add:
   - `GROQ_API_KEY`: *(Recommended free key from [console.groq.com](https://console.groq.com) for ultra-fast Llama 3 cloud inference)*
   *(Optional)*: If you prefer OpenAI, set `OPENAI_API_KEY`.
4. **Deploy!**
   - Click **Deploy**. Vercel will build the serverless functions and give you a live HTTPS URL (e.g. `https://your-study-buddy.vercel.app`).
   - Users can visit the link, upload PDFs, and query their materials in their browser!


---

## 🦙 Setting Up the Local LLM (Ollama)

Study Buddy uses **Ollama** to run open-weight AI models locally on your CPU or GPU.

### 1. Install Ollama
- **Windows / macOS / Linux:** Download the installer from [https://ollama.com/download](https://ollama.com/download).

### 2. Download Recommended Models
Open your terminal and pull your preferred models:

```bash
# 1. Pull the primary LLM (Llama 3 8B, or lightweight models like phi3 / mistral)
ollama pull llama3

# 2. Pull the embedding model
ollama pull nomic-embed-text
```

> [!TIP]
> **For low-spec laptops (8GB RAM or CPU only):**  
> You can use lightweight models like `phi3` or `tinyllama`:
> ```bash
> ollama pull phi3
> ```
> Then update `LLM_MODEL_NAME=phi3` in your `.env` file.

### 3. Ensure Ollama is Running
Ollama typically starts automatically as a background service. You can verify it by running:
```bash
ollama list
```

---

## ▶️ Running the Application

### 1. Configure `.env` (Optional)
The application comes preconfigured with sensible defaults in `.env`:
```ini
HOST=127.0.0.1
PORT=8000
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL_NAME=llama3
EMBEDDING_MODEL=nomic-embed-text
DOCUMENTS_DIR=documents
DATA_DIR=data
VECTOR_STORE_PATH=data/vector_store.json
```

### 2. Start the Server

```bash
uvicorn app.main:app --reload
```

### 3. Access the Application
- 🌐 **Web Interface:** Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
- 📚 **Interactive Swagger API Docs:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
- 🩺 **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

---

## 💻 How to Use the Application

### Option A: Using the Web UI
1. Navigate to `http://127.0.0.1:8000`.
2. Under **"1. Upload Study Materials"**, choose a PDF file (e.g. `operating_systems.pdf`) and click **"Upload & Index PDF"**.
3. Under **"2. Ask a Question"**, type your question (e.g. *"What is deadlock and what are the four conditions?"*).
4. Click **"Ask Study Buddy"**.
5. View the synthesized answer along with the source document and page references.

### Option B: Using the REST API

#### 1. Upload a Document
```bash
curl -X POST "http://127.0.0.1:8000/documents" \
     -F "file=@sample_notes.pdf"
```
**Response:**
```json
{
  "status": "success",
  "message": "Successfully processed and indexed 'sample_notes.pdf'.",
  "filename": "sample_notes.pdf",
  "pages_parsed": 5,
  "chunks_stored": 12,
  "total_indexed_chunks": 12
}
```

#### 2. Query the Knowledge Base
```bash
curl -X POST "http://127.0.0.1:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is mutual exclusion?"}'
```
**Response:**
```json
{
  "answer": "Mutual exclusion is a condition where only one process can hold a resource at any given time...",
  "sources": [
    {
      "document": "sample_notes.pdf",
      "page": 2,
      "snippet": "Mutual exclusion ensures that a resource cannot be simultaneously shared...",
      "relevance_score": 0.8421
    }
  ]
}
```

---

## ❓ Example Questions to Ask
- *"What is the main difference between a process and a thread?"*
- *"Explain the four conditions required for deadlock to occur."*
- *"What are the primary stages of cellular respiration?"*
- *"Summarize the key takeaways from Chapter 3."*

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:

```bash
pytest tests/
```

All tests cover:
- Root frontend delivery and `/health` status
- Document listing
- Rejection of invalid non-PDF file formats
- Rejection of empty/zero-byte files
- Chat question validation and error handling
- Page-level text chunking and overlap logic
- Vector store indexing and cosine similarity retrieval
- End-to-end PDF ingestion and chat citation

---

## 📂 Project Structure

```text
study-buddy/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization, middleware, static files
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── documents.py     # Endpoints for PDF upload and document listing
│   │   └── chat.py          # Endpoints for asking questions and returning citations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py           # Local Ollama LLM client with timeout & error handling
│   │   ├── embeddings.py    # Local open-source embeddings with resilient fallback
│   │   ├── vector_store.py  # Lightweight local vector store with NumPy cosine similarity
│   │   └── rag.py           # RAG orchestrator linking retrieval and prompt synthesis
│   ├── static/
│   │   └── index.html       # Clean, responsive single-page web interface
│   └── utils/
│       ├── __init__.py
│       └── pdf_loader.py    # PDF text extraction and chunking utilities
├── data/
│   └── vector_store.json    # Persistent local storage for text chunks and vector embeddings
├── documents/               # Saved raw PDF files uploaded by the user
├── tests/
│   ├── __init__.py
│   └── test_main.py         # Automated test cases
├── requirements.txt         # Minimal, clean project dependencies
├── .env                     # Local environment settings
├── .gitignore               # Git ignore rules for virtualenvs and local files
└── README.md                # Comprehensive documentation
```

---

## 🔒 Why Open-Source & Local AI Was Chosen

1. **Complete Data Privacy:** Academic materials, unpublished papers, exam questions, and lecture slides remain strictly on the user's device.
2. **Cost-Free:** No API tokens, credits, or monthly subscriptions.
3. **Offline Capability:** Once models are downloaded through Ollama, the entire system can function without an internet connection.
4. **Transparency & Control:** You can inspect the exact chunks stored in `data/vector_store.json`, tune chunk sizes, or swap the LLM with any open model (`llama3`, `mistral`, `gemma`, `phi3`).

---

## ⚠️ Known Limitations

- **Scanned/Image-Only PDFs:** Text extraction requires selectable digital text in the PDF. Pure scanned PDFs (images without OCR) will be detected and rejected with a helpful message.
- **Hardware Requirements:** Running larger models (e.g. 70B parameters) requires significant RAM and GPU. For typical laptops, 3B–8B parameter models (`phi3`, `llama3:8b`) are recommended.

---

## 🎃 Contributing

Contributions are warmly welcomed for **Hacktoberfest 2026**! Feel free to open issues or submit pull requests for features such as OCR support, additional file formats (Markdown/EPUB), or hybrid search.
