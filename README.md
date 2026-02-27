# DocuMind: RAG-Based AI for Document Processing

DocuMind is an intelligent, web-based application that allows users to chat with their PDF documents. By leveraging Retrieval-Augmented Generation (RAG), DocuMind converts static PDF content into a dynamic knowledge base, enabling semantic search and context-aware question answering.

## 🚀 Features

* **Document Ingestion:** Upload and process multiple PDF files simultaneously.
* **Hybrid Inference:** Switch between Cloud LLMs (Google Gemini 2.5 Flash) for speed and Local LLMs (Gemma 2 2B via LlamaCpp) for privacy.
* **Local Vectorization:** Uses HuggingFace embeddings (`BAAI/bge-base-en-v1.5`) and FAISS locally to ensure document data remains private.
* **Persistent Sessions:** Chat history and uploaded files are saved automatically using a local SQLite database.
* **Modern UI:** A responsive Single Page Application (SPA) built with Vanilla JS and CSS variables (Dark/Light mode support).
* **Secure:** Supports "Bring Your Own Key" (BYOK) for Google API keys via client-side storage.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.10** or higher
* **Git**
* **C++ Build Tools** (Required for installing `llama-cpp-python` on Windows/Linux)
    * *Windows:* Visual Studio Community with "Desktop development with C++".
    * *Linux:* `build-essential` (`sudo apt install build-essential`).

## 🛠️ Installation

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd documind
    ```

2.  **Create a Virtual Environment**
    It is recommended to use a virtual environment to manage dependencies.
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If `llama-cpp-python` fails to install, ensure you have C++ build tools installed. You may need to install it separately with pre-built wheels if compilation fails.*

## ⚙️ Configuration

1.  **Create an `.env` file**
    Create a file named `.env` in the root directory of the project.

2.  **Add Environment Variables**
    Copy the following configuration into your `.env` file:

    ```ini
    # --- API Keys ---
    # Required if using Google Model server-side. 
    # Users can also provide this via the UI Settings panel.
    GOOGLE_API_KEY=your_google_api_key_here

    # --- Model Configuration ---
    # Options: google, local
    MODEL_TYPE=google
    
    # Options: huggingface
    EMBEDDING_TYPE=huggingface

    # --- Local Model Path (Optional) ---
    # Required only if you plan to use the "Local (Gemma 2 2B)" option.
    # You must download the GGUF model file manually.
    MODEL_PATH=models/gemma-2-2b-it.q4_k_m.gguf

    # --- RAG Parameters ---
    CHUNK_SIZE=1000
    CHUNK_OVERLAP=200
    ```

3.  **(Optional) Setup Local Model**
    If you want to use the Local LLM feature:
    * Create a folder named `models` in the root directory.
    * Download the `gemma-2-2b-it.q4_k_m.gguf` file from Hugging Face (e.g., from `bartowski/gemma-2-2b-it-GGUF`).
    * Place the file inside the `models/` folder.

## ▶️ Running the Application

1.  **Start the Flask Server**
    ```bash
    python app.py
    ```

2.  **Access the App**
    Open your web browser and navigate to:
    ```
    [http://127.0.0.1:5001](http://127.0.0.1:5001)
    ```

## 📂 Project Structure

```
documind/
├── app.py                 \# Main Flask Controller
├── requirements.txt       \# Python Dependencies
├── .env                   \# Environment Variables
├── vectorstores/          \# Local FAISS indexes (auto-created)
├── workspace.db           \# SQLite Database (auto-created)
├── models/                \# Directory for Local GGUF models
├── src/
│   ├── **init**.py
│   ├── config.py          \# Configuration logic
│   ├── conversation.py    \# LangChain RAG pipeline
│   ├── embeddings.py      \# Vector generation logic
│   ├── notes\_manager.py   \# Database DAO
│   ├── pdf\_processing.py  \# PDF text extraction
│   └── utils.py           \# Helper functions
├── static/
│   ├── css/               \# Stylesheets (main, chat, sidebar)
│   ├── js/                \# Frontend logic (chat, upload, settings)
│   └── logo.png
└── templates/
├── base.html          \# Base Jinja2 template
└── index.html         \# Main application view
```
## 🐛 Troubleshooting

* **`ModuleNotFoundError: No module named 'llama_cpp'`**:
    Re-install the package: `pip install llama-cpp-python`. If this fails, ensure C++ build tools are installed.

* **Google API Key Error**:
    Ensure `GOOGLE_API_KEY` is set in `.env` OR enter your key in the "Settings" panel within the web interface.

* **Address already in use**:
    The app runs on port 5001. If this port is busy, modify the `app.run(port=5001)` line in `app.py`.
