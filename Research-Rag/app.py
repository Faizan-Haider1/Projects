import streamlit as st
import os
import re
import io
import zipfile
import tempfile
import requests
import numpy as np
import faiss

from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup

from sentence_transformers import SentenceTransformer
from groq import Groq


# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Research Paper RAG",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 1rem;
    }

    .title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }

    .source-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #ddd;
        margin-bottom: 15px;
        background-color: rgba(128, 128, 128, 0.05);
    }

    .metric-card {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #ddd;
        text-align: center;
    }

    .small-text {
        font-size: 13px;
        color: #777;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CONSTANTS
# ============================================================

GROQ_MODEL = "openai/gpt-oss-120b"

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

TOP_K = 5

CHUNK_SIZE = 1000

CHUNK_OVERLAP = 150


# ============================================================
# SESSION STATE
# ============================================================

if "paper_data" not in st.session_state:
    st.session_state.paper_data = None

if "document_name" not in st.session_state:
    st.session_state.document_name = None

if "source_type" not in st.session_state:
    st.session_state.source_type = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_results" not in st.session_state:
    st.session_state.last_results = None

if "last_question" not in st.session_state:
    st.session_state.last_question = None

if "detailed_explanation" not in st.session_state:
    st.session_state.detailed_explanation = None


# ============================================================
# GROQ CLIENT
# ============================================================

def get_groq_client():

    api_key = ""

    # Streamlit Cloud Secrets
    try:
        api_key = st.secrets.get(
            "GROQ_API_KEY",
            ""
        )
    except Exception:
        api_key = ""

    # Environment variable fallback
    if not api_key:
        api_key = os.getenv(
            "GROQ_API_KEY",
            ""
        )

    if not api_key:

        return None

    return Groq(
        api_key=api_key
    )


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

@st.cache_resource(show_spinner=False)
def load_embedding_model():

    model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    return model


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace(
        "\x00",
        " "
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r" *\n *",
        "\n",
        text
    )

    return text.strip()


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_text_from_pdf(file_bytes):

    pdf_file = io.BytesIO(
        file_bytes
    )

    reader = PdfReader(
        pdf_file
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            text = page.extract_text() or ""

        except Exception:

            text = ""

        text = clean_text(
            text
        )

        if text:

            pages.append(
                {
                    "page_number": page_number,
                    "text": text
                }
            )

    return pages


# ============================================================
# DOCX EXTRACTION
# ============================================================

def extract_text_from_docx(file_bytes):

    doc_file = io.BytesIO(
        file_bytes
    )

    document = Document(
        doc_file
    )

    paragraphs = []

    for index, paragraph in enumerate(
        document.paragraphs,
        start=1
    ):

        text = clean_text(
            paragraph.text
        )

        if text:

            paragraphs.append(
                {
                    "page_number": None,
                    "paragraph_number": index,
                    "text": text
                }
            )

    return paragraphs


# ============================================================
# TXT EXTRACTION
# ============================================================

def extract_text_from_txt(file_bytes):

    encodings = [
        "utf-8",
        "utf-8-sig",
        "latin-1"
    ]

    text = None

    for encoding in encodings:

        try:

            text = file_bytes.decode(
                encoding
            )

            break

        except UnicodeDecodeError:

            continue

    if text is None:

        raise ValueError(
            "Unable to read TXT file."
        )

    text = clean_text(
        text
    )

    return [
        {
            "page_number": None,
            "text": text
        }
    ]


# ============================================================
# HTML EXTRACTION
# ============================================================

def extract_text_from_html(file_bytes):

    html = file_bytes.decode(
        "utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "nav",
            "footer"
        ]
    ):

        element.decompose()

    text = soup.get_text(
        separator="\n"
    )

    lines = []

    for line in text.splitlines():

        line = clean_text(
            line
        )

        if line:

            lines.append(
                line
            )

    final_text = "\n".join(
        lines
    )

    return [
        {
            "page_number": None,
            "text": final_text
        }
    ]


# ============================================================
# UNIVERSAL FILE EXTRACTION
# ============================================================

def extract_document(
    file_bytes,
    filename
):

    extension = Path(
        filename
    ).suffix.lower()

    if extension == ".pdf":

        return extract_text_from_pdf(
            file_bytes
        )

    elif extension == ".docx":

        return extract_text_from_docx(
            file_bytes
        )

    elif extension == ".txt":

        return extract_text_from_txt(
            file_bytes
        )

    elif extension in [
        ".html",
        ".htm"
    ]:

        return extract_text_from_html(
            file_bytes
        )

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )


# ============================================================
# CHUNKING
# ============================================================

def chunk_text(
    text,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
):

    words = text.split()

    chunks = []

    if not words:

        return chunks

    start = 0

    while start < len(words):

        end = min(
            start + chunk_size,
            len(words)
        )

        chunk = " ".join(
            words[start:end]
        )

        if chunk.strip():

            chunks.append(
                chunk.strip()
            )

        if end >= len(words):

            break

        start = end - overlap

    return chunks


# ============================================================
# CREATE CHUNKS WITH METADATA
# ============================================================

def create_chunks(
    pages,
    document_name,
    source
):

    all_chunks = []

    chunk_id = 0

    for page_data in pages:

        text = page_data.get(
            "text",
            ""
        )

        page_number = page_data.get(
            "page_number"
        )

        chunks = chunk_text(
            text
        )

        for chunk in chunks:

            metadata = {
                "chunk_id": chunk_id,
                "document_name": document_name,
                "source": source,
                "page_number": page_number,
                "text": chunk
            }

            all_chunks.append(
                metadata
            )

            chunk_id += 1

    return all_chunks


# ============================================================
# CREATE EMBEDDINGS
# ============================================================

def create_embeddings(
    chunks,
    model
):

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    embeddings = embeddings.astype(
        "float32"
    )

    faiss.normalize_L2(
        embeddings
    )

    return embeddings


# ============================================================
# CREATE FAISS INDEX
# ============================================================

def create_faiss_index(
    embeddings
):

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    return index


# ============================================================
# PROCESS DOCUMENT
# ============================================================

def process_document(
    file_bytes,
    filename,
    source
):

    pages = extract_document(
        file_bytes,
        filename
    )

    if not pages:

        raise ValueError(
            "No readable text was found in the document."
        )

    chunks = create_chunks(
        pages,
        document_name=filename,
        source=source
    )

    if not chunks:

        raise ValueError(
            "No chunks could be created from the document."
        )

    embedding_model = load_embedding_model()

    embeddings = create_embeddings(
        chunks,
        embedding_model
    )

    index = create_faiss_index(
        embeddings
    )

    return {
        "index": index,
        "metadata": chunks,
        "document_name": filename,
        "source": source,
        "pages": pages
    }


# ============================================================
# GOOGLE DRIVE FILE ID
# ============================================================

def extract_google_drive_file_id(
    url
):

    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url
        )

        if match:

            return match.group(1)

    return None


# ============================================================
# GOOGLE DRIVE DOWNLOAD
# ============================================================

def download_google_drive_file(
    url
):

    file_id = extract_google_drive_file_id(
        url
    )

    if not file_id:

        raise ValueError(
            "Invalid Google Drive link."
        )

    download_url = (
        "https://drive.usercontent.google.com/download"
        f"?id={file_id}&export=download&confirm=t"
    )

    response = requests.get(
        download_url,
        timeout=90
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    content = response.content

    return content, content_type


# ============================================================
# DIRECT URL DOWNLOAD
# ============================================================

def download_direct_file(
    url
):

    response = requests.get(
        url,
        timeout=90,
        headers={
            "User-Agent":
            "Mozilla/5.0 Research-RAG-App"
        }
    )

    response.raise_for_status()

    content = response.content

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    return content, content_type


# ============================================================
# DETECT FILE TYPE FROM CONTENT
# ============================================================

def detect_file_extension(
    content,
    content_type="",
    url=""
):

    # PDF signature
    if content.startswith(
        b"%PDF"
    ):

        return ".pdf"

    # DOCX is a ZIP file
    if content.startswith(
        b"PK"
    ):

        try:

            with zipfile.ZipFile(
                io.BytesIO(content)
            ) as z:

                if "word/document.xml" in z.namelist():

                    return ".docx"

        except Exception:

            pass

    content_type = content_type.lower()

    if "pdf" in content_type:

        return ".pdf"

    if "word" in content_type:

        return ".docx"

    if "text" in content_type:

        return ".txt"

    parsed = urlparse(
        url
    )

    extension = Path(
        parsed.path
    ).suffix.lower()

    if extension in [
        ".pdf",
        ".docx",
        ".txt",
        ".html",
        ".htm"
    ]:

        return extension

    return ".txt"


# ============================================================
# QUESTION EMBEDDING
# ============================================================

def embed_query(
    query,
    model
):

    embedding = model.encode(
        [query],
        convert_to_numpy=True
    )

    embedding = embedding.astype(
        "float32"
    )

    faiss.normalize_L2(
        embedding
    )

    return embedding


# ============================================================
# FAISS SEARCH
# ============================================================

def search_faiss(
    query,
    paper_data,
    top_k=TOP_K
):

    index = paper_data["index"]

    metadata = paper_data["metadata"]

    model = load_embedding_model()

    query_embedding = embed_query(
        query,
        model
    )

    actual_k = min(
        top_k,
        index.ntotal
    )

    scores, indices = index.search(
        query_embedding,
        actual_k
    )

    results = []

    for score, index_id in zip(
        scores[0],
        indices[0]
    ):

        if index_id < 0:

            continue

        result = metadata[
            index_id
        ].copy()

        result[
            "similarity_score"
        ] = float(score)

        results.append(
            result
        )

    return results


# ============================================================
# BUILD RAG CONTEXT
# ============================================================

def build_context(
    results
):

    context_parts = []

    for i, result in enumerate(
        results,
        start=1
    ):

        page = result.get(
            "page_number"
        )

        if page is None:

            page = "N/A"

        context_parts.append(
            f"""
SOURCE {i}

Document:
{result["document_name"]}

Page:
{page}

Similarity Score:
{result["similarity_score"]:.4f}

Content:
{result["text"]}
"""
        )

    return "\n\n".join(
        context_parts
    )


# ============================================================
# MAIN RAG ANSWER
# ============================================================

def generate_answer(
    question,
    results
):

    client = get_groq_client()

    if client is None:

        raise ValueError(
            "Groq API key is not configured. "
            "Add GROQ_API_KEY to Streamlit Secrets."
        )

    context = build_context(
        results
    )

    prompt = f"""
You are an intelligent research paper assistant.

The user has provided a research paper.

Answer the user's question using the retrieved
research paper context below.

USER QUESTION:
{question}

RETRIEVED RESEARCH PAPER CONTEXT:
{context}

IMPORTANT RULES:

1. Base the answer primarily on the retrieved research paper.

2. Do not invent information.

3. Do not create fake citations, page numbers,
authors, results, or statistics.

4. If the retrieved context does not contain
enough information, clearly say so.

5. Explain technical concepts in beginner-friendly
English.

6. Preserve important scientific terminology.

7. When appropriate, mention the relevant page
number from the retrieved source.

8. Distinguish between what the paper says and
your simple explanation.

Return the answer using this structure:

## Direct Answer

Give a clear answer to the question.

## Evidence From the Paper

Explain what the retrieved research paper says.

## Source

Mention the relevant document and page numbers
when available.

## Simple Beginner Explanation

Explain the answer in very simple English as if
you are teaching someone who has never studied
the topic before.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,

        messages=[
            {
                "role": "system",
                "content":
                    "You are a careful research assistant "
                    "who does not hallucinate sources."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.2,

        max_tokens=2500
    )

    return response.choices[
        0
    ].message.content


# ============================================================
# DETAILED EXPLANATION
# ============================================================

def generate_detailed_explanation(
    question,
    results
):

    client = get_groq_client()

    if client is None:

        raise ValueError(
            "Groq API key is not configured."
        )

    context = build_context(
        results
    )

    prompt = f"""
You are an expert research paper tutor.

The user wants a detailed explanation of a
research-paper question.

QUESTION:
{question}

RETRIEVED PAPER CONTENT:
{context}

Create a detailed explanation based primarily
on the retrieved research paper.

Use this structure:

# Detailed Explanation

## 1. What the Paper Says

Explain the relevant information.

## 2. Main Concept

Explain the central concept involved.

## 3. Step-by-Step Explanation

Break the concept into understandable steps.

## 4. Important Technical Terms

Explain difficult terminology in simple English.

## 5. Simple Example

Give a beginner-friendly example or analogy
when appropriate.

## 6. Why This Matters

Explain the importance of the concept.

## 7. Evidence and Sources

Mention the relevant source and page number
when available.

IMPORTANT:

- Do not invent information.
- Do not create fake citations.
- Do not invent page numbers.
- If information is missing from the retrieved
  context, explicitly state that.
- Maintain scientific accuracy.
- Explain difficult concepts in simple language.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,

        messages=[
            {
                "role": "system",
                "content":
                    "You are a precise research tutor."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.3,

        max_tokens=4000
    )

    return response.choices[
        0
    ].message.content


# ============================================================
# SOURCE DISPLAY
# ============================================================

def display_sources(
    results
):

    st.markdown(
        "## 📚 Retrieved Sources"
    )

    for i, result in enumerate(
        results,
        start=1
    ):

        score = result[
            "similarity_score"
        ]

        page = result.get(
            "page_number"
        )

        if page is None:

            page = "N/A"

        with st.expander(
            f"Source {i} — "
            f"Page {page} — "
            f"Similarity {score:.3f}"
        ):

            st.markdown(
                f"""
                **📄 Document:**  
                {result["document_name"]}

                **📖 Page:**  
                {page}

                **🔎 Similarity Score:**  
                {score:.4f}

                **🔗 Source:**  
                {result["source"]}
                """
            )

            st.markdown(
                "**Retrieved Content:**"
            )

            st.write(
                result["text"]
            )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">📚 Research Paper RAG</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="subtitle">
    Upload a research paper or provide a document link,
    then ask questions and get evidence-based answers.
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Research Paper")

    input_method = st.radio(
        "Choose document source:",
        [
            "📁 Upload File",
            "🔗 Google Drive",
            "🌐 Direct URL"
        ]
    )

    st.divider()

    st.markdown(
        """
        ### Supported Formats

        📄 PDF  
        📝 DOCX  
        📃 TXT  
        🌐 HTML

        ### RAG Pipeline

        Document  
        ↓  
        Text Extraction  
        ↓  
        Chunking  
        ↓  
        Embeddings  
        ↓  
        FAISS  
        ↓  
        Similarity Search  
        ↓  
        Groq LLM
        """
    )

    st.divider()

    st.caption(
        "Embeddings are generated locally using "
        "Sentence Transformers."
    )


# ============================================================
# DOCUMENT INPUT
# ============================================================

file_bytes = None
filename = None
source = None


# ------------------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------------------

if input_method == "📁 Upload File":

    uploaded_file = st.file_uploader(
        "Upload your research paper",
        type=[
            "pdf",
            "docx",
            "txt",
            "html",
            "htm"
        ],
        help="Upload one research paper at a time."
    )

    if uploaded_file is not None:

        file_bytes = uploaded_file.getvalue()

        filename = uploaded_file.name

        source = "Local File Upload"


# ------------------------------------------------------------
# GOOGLE DRIVE
# ------------------------------------------------------------

elif input_method == "🔗 Google Drive":

    st.info(
        "Make sure your Google Drive file is "
        "accessible using the shared link."
    )

    drive_url = st.text_input(
        "Paste Google Drive file link",
        placeholder=
        "https://drive.google.com/file/d/..."
    )

    if st.button(
        "⬇️ Load Google Drive File",
        use_container_width=True
    ):

        if not drive_url.strip():

            st.error(
                "Please enter a Google Drive link."
            )

        else:

            try:

                with st.spinner(
                    "Downloading Google Drive file..."
                ):

                    file_bytes, content_type = (
                        download_google_drive_file(
                            drive_url.strip()
                        )
                    )

                extension = detect_file_extension(
                    file_bytes,
                    content_type,
                    drive_url
                )

                filename = (
                    f"google_drive_paper{extension}"
                )

                source = drive_url.strip()

                st.session_state[
                    "pending_document"
                ] = {
                    "file_bytes": file_bytes,
                    "filename": filename,
                    "source": source
                }

                st.success(
                    "Google Drive file downloaded successfully."
                )

            except Exception as e:

                st.error(
                    f"Could not download the Google Drive file: {e}"
                )


# ------------------------------------------------------------
# DIRECT URL
# ------------------------------------------------------------

elif input_method == "🌐 Direct URL":

    direct_url = st.text_input(
        "Paste direct document URL",
        placeholder=
        "https://example.com/research-paper.pdf"
    )

    if st.button(
        "⬇️ Download Document",
        use_container_width=True
    ):

        if not direct_url.strip():

            st.error(
                "Please enter a document URL."
            )

        else:

            try:

                with st.spinner(
                    "Downloading document..."
                ):

                    file_bytes, content_type = (
                        download_direct_file(
                            direct_url.strip()
                        )
                    )

                extension = detect_file_extension(
                    file_bytes,
                    content_type,
                    direct_url
                )

                filename = (
                    f"online_research_paper{extension}"
                )

                source = direct_url.strip()

                st.session_state[
                    "pending_document"
                ] = {
                    "file_bytes": file_bytes,
                    "filename": filename,
                    "source": source
                }

                st.success(
                    "Document downloaded successfully."
                )

            except Exception as e:

                st.error(
                    f"Could not download the document: {e}"
                )


# ============================================================
# HANDLE PENDING DOCUMENT
# ============================================================

if "pending_document" in st.session_state:

    pending = st.session_state[
        "pending_document"
    ]

    file_bytes = pending[
        "file_bytes"
    ]

    filename = pending[
        "filename"
    ]

    source = pending[
        "source"
    ]


# ============================================================
# PROCESS BUTTON
# ============================================================

if file_bytes is not None:

    st.divider()

    st.subheader(
        f"📄 {filename}"
    )

    st.write(
        f"Source: {source}"
    )

    if st.button(
        "🚀 Process Research Paper",
        type="primary",
        use_container_width=True
    ):

        try:

            with st.spinner(
                """
                Processing research paper...

                1. Extracting text
                2. Cleaning text
                3. Creating chunks
                4. Generating embeddings
                5. Creating FAISS index
                """
            ):

                paper_data = process_document(
                    file_bytes,
                    filename,
                    source
                )

            st.session_state.paper_data = (
                paper_data
            )

            st.session_state.document_name = (
                filename
            )

            st.session_state.source_type = (
                source
            )

            st.session_state.chat_history = []

            st.session_state.last_results = None

            st.session_state.last_question = None

            st.session_state.detailed_explanation = None

            if "pending_document" in st.session_state:

                del st.session_state[
                    "pending_document"
                ]

            st.success(
                "Research paper processed successfully! 🎉"
            )

        except Exception as e:

            st.error(
                f"Processing failed: {e}"
            )


# ============================================================
# DISPLAY PAPER INFORMATION
# ============================================================

paper_data = st.session_state.paper_data

if paper_data is not None:

    st.divider()

    st.markdown(
        "## 📊 Research Paper Information"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "📄 Document",
            paper_data["document_name"]
        )

    with col2:

        st.metric(
            "📑 Pages/Sections",
            len(paper_data["pages"])
        )

    with col3:

        st.metric(
            "🧩 Chunks",
            len(paper_data["metadata"])
        )

    with col4:

        st.metric(
            "🔢 FAISS Vectors",
            paper_data["index"].ntotal
        )


    # ========================================================
    # QUESTION SECTION
    # ========================================================

    st.divider()

    st.markdown(
        "## 💬 Ask Your Research Question"
    )

    question = st.text_area(
        "Enter your question:",
        placeholder=
        "Example: What methodology did the researchers use?",
        height=120
    )

    ask_button = st.button(
        "🔍 Ask Question",
        type="primary",
        use_container_width=True
    )


    # ========================================================
    # ASK QUESTION
    # ========================================================

    if ask_button:

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            try:

                with st.spinner(
                    "Searching the research paper and generating answer..."
                ):

                    results = search_faiss(
                        question,
                        paper_data,
                        TOP_K
                    )

                    answer = generate_answer(
                        question,
                        results
                    )

                st.session_state.last_results = (
                    results
                )

                st.session_state.last_question = (
                    question
                )

                st.session_state.detailed_explanation = (
                    None
                )

                st.session_state.chat_history.append(
                    {
                        "question": question,
                        "answer": answer
                    }
                )

            except Exception as e:

                st.error(
                    f"Could not generate answer: {e}"
                )


    # ========================================================
    # DISPLAY ANSWER
    # ========================================================

    if (
        st.session_state.last_results is not None
        and
        st.session_state.last_question is not None
    ):

        st.divider()

        st.markdown(
            "## 🤖 Answer"
        )

        # Find latest answer
        if st.session_state.chat_history:

            latest_answer = (
                st.session_state
                .chat_history[-1]["answer"]
            )

            st.markdown(
                latest_answer
            )


        # ====================================================
        # DETAILED EXPLANATION BUTTON
        # ====================================================

        st.divider()

        st.markdown(
            "### 🧠 Want to understand it better?"
        )

        if st.button(
            "🔎 Explain in Detail",
            use_container_width=True
        ):

            try:

                with st.spinner(
                    "Generating detailed explanation..."
                ):

                    detailed = (
                        generate_detailed_explanation(
                            st.session_state.last_question,
                            st.session_state.last_results
                        )
                    )

                st.session_state.detailed_explanation = (
                    detailed
                )

            except Exception as e:

                st.error(
                    f"Could not generate detailed explanation: {e}"
                )


        # ====================================================
        # DISPLAY DETAILED EXPLANATION
        # ====================================================

        if (
            st.session_state.detailed_explanation
            is not None
        ):

            st.markdown(
                "## 📖 Detailed Explanation"
            )

            st.markdown(
                st.session_state.detailed_explanation
            )


        # ====================================================
        # DISPLAY SOURCES
        # ====================================================

        st.divider()

        display_sources(
            st.session_state.last_results
        )


    # ========================================================
    # PAPER PREVIEW
    # ========================================================

    st.divider()

    with st.expander(
        "📄 Preview Extracted Paper Text"
    ):

        preview_pages = paper_data[
            "pages"
        ][:3]

        for page in preview_pages:

            page_number = page.get(
                "page_number"
            )

            if page_number:

                st.markdown(
                    f"### Page {page_number}"
                )

            st.write(
                page["text"][:3000]
            )

            st.divider()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    """
    📚 Research Paper RAG | 
    Sentence Transformers + FAISS + Groq
    """
)
