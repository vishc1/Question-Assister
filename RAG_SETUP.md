# RAG Pipeline Setup Guide

Complete guide for setting up and using the Retrieval-Augmented Generation (RAG) pipeline.

## Overview

The RAG pipeline allows the application to search through your personal documents (PDFs, Word docs, ChatGPT exports) to provide relevant context during interviews.

**Key Features:**
- 📄 Supports PDF, DOCX, and JSON (ChatGPT export) files
- 🔪 Chunks text into 500-character segments with 50-character overlap
- 🧮 Uses OpenAI embeddings (text-embedding-3-small)
- 🗄️ FAISS vector database for fast similarity search
- 💾 Persistent storage - no re-indexing on restart
- 🔍 Returns top 5 most relevant paragraphs for any query

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG Pipeline Flow                        │
└─────────────────────────────────────────────────────────────┘

/identity/                    Data Ingestion
├── resume.pdf          ────► Load Documents
├── projects.docx       ────► (PDF, DOCX, JSON loaders)
└── chatgpt.json              │
                              ▼
                        Text Chunking
                        (500 chars, 50 overlap)
                              │
                              ▼
                        OpenAI Embeddings
                        (text-embedding-3-small)
                              │
                              ▼
                        FAISS Vector Store
                        (similarity search)
                              │
                              ▼
                        /vector_store/
                        ├── faiss_index/
                        └── metadata.json

Query: "Tell me about Python projects" ──► Similarity Search
                                          │
                                          ▼
                                    Top 5 Results
                                    (relevant paragraphs)
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langchain` - Document processing and chunking
- `langchain-openai` - OpenAI integration
- `faiss-cpu` - Vector database
- `pypdf` - PDF loader
- `python-docx` - Word document loader
- `python-dotenv` - Environment variable management

### 2. Set Up OpenAI API Key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Prepare Your Documents

Create an `identity` directory and add your documents:

```bash
mkdir identity
```

Add files to the `identity/` directory:
- **PDFs**: Resume, certificates, project reports
- **DOCX**: Cover letters, project descriptions, notes
- **JSON**: ChatGPT conversation exports

**Supported file types:**
- `.pdf` - Any PDF document
- `.docx` - Microsoft Word documents
- `.json` - ChatGPT export format or generic JSON

### 4. Build the Index

```bash
python rag_pipeline.py build
```

This will:
1. Scan the `identity/` directory
2. Load all supported documents
3. Chunk text into 500-character segments
4. Create embeddings using OpenAI API
5. Build FAISS vector index
6. Save to `vector_store/` directory

**Expected output:**
```
============================================================
                     RAG INDEX BUILD
============================================================

============================================================
Initializing RAG Pipeline Components
============================================================

✓ OpenAI Embeddings initialized (model: text-embedding-3-small)
✓ Text splitter initialized (size: 500, overlap: 50)

============================================================
Data Ingestion: Loading Documents
============================================================

Found 5 files to process:

✓ Loaded PDF: resume.pdf (2 pages)
✓ Loaded DOCX: projects.docx
✓ Loaded ChatGPT JSON: conversations.json (127 messages)

============================================================
✓ Loaded 130 documents from 3 files
============================================================

============================================================
Chunking Documents
============================================================

✓ Split 130 documents into 456 chunks
  Chunk size: 500 characters
  Overlap: 50 characters

============================================================
Creating Vector Store
============================================================

Creating embeddings for 456 chunks...
✓ Vector store created with 456 vectors

============================================================
Saving Vector Store
============================================================

✓ FAISS index saved to: ./vector_store/faiss_index
✓ Metadata saved to: ./vector_store/metadata.json

============================================================
✓ RAG INDEX BUILD COMPLETE
============================================================
```

### 5. Test the Index

#### Interactive Search

```bash
python rag_pipeline.py search
```

Try queries like:
- "Python projects"
- "Machine learning experience"
- "Leadership examples"
- "Technical challenges"

#### Programmatic Usage

```python
from rag_pipeline import RAGPipeline

# Initialize and load index
rag = RAGPipeline()
rag.load_vector_store()

# Query for context
results = rag.get_personal_context("Tell me about your Python experience")

# Display results
for result in results:
    print(f"Rank {result['rank']}: {result['content']}")
    print(f"Score: {result['similarity_score']:.4f}")
    print()
```

## Document Formats

### PDF Files

Any PDF document is supported. Each page becomes a separate document.

**Example:**
```
identity/
├── resume.pdf
├── certificate.pdf
└── project_report.pdf
```

### DOCX Files

Microsoft Word documents (.docx format only, not .doc).

**Example:**
```
identity/
├── cover_letter.docx
├── project_descriptions.docx
└── technical_notes.docx
```

### JSON Files - ChatGPT Export

Export your ChatGPT conversations:
1. Go to ChatGPT Settings → Data Controls → Export Data
2. Download the export (you'll receive an email)
3. Extract `conversations.json`
4. Place in `identity/` directory

The pipeline automatically parses:
- Conversation titles
- User messages
- Assistant responses
- Timestamps

**Expected format:**
```json
[
  {
    "id": "...",
    "title": "Python Project Discussion",
    "create_time": 1234567890,
    "mapping": {
      "node_id": {
        "message": {
          "content": {
            "parts": ["Your conversation text here"]
          },
          "author": {"role": "user"},
          "create_time": 1234567890
        }
      }
    }
  }
]
```

### JSON Files - Generic Format

For other JSON files, the pipeline extracts all text fields recursively.

**Example:**
```json
{
  "projects": [
    {
      "name": "Web Scraper",
      "description": "Built a Python web scraper...",
      "technologies": ["Python", "BeautifulSoup", "Selenium"]
    }
  ]
}
```

## Configuration

### Environment Variables

Edit `.env` to customize:

```env
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (defaults shown)
IDENTITY_DIR=./identity
VECTOR_STORE_PATH=./vector_store
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
EMBEDDING_MODEL=text-embedding-3-small
```

### Programmatic Configuration

```python
from rag_pipeline import RAGPipeline
from pathlib import Path

rag = RAGPipeline(
    identity_dir=Path("./my_documents"),
    vector_store_path=Path("./my_index"),
    openai_api_key="sk-..."
)

# Override defaults
rag.chunk_size = 1000
rag.chunk_overlap = 100
rag.top_k = 10
```

## Usage Examples

### Example 1: Basic Query

```python
from rag_pipeline import RAGPipeline

# Load the index
rag = RAGPipeline()
rag.load_vector_store()

# Get context
query = "What Python projects have I worked on?"
results = rag.get_personal_context(query)

# Print results
for result in results:
    print(f"\n[Rank {result['rank']}]")
    print(result['content'])
```

### Example 2: Integration with Interview App

```python
from rag_pipeline import RAGPipeline

# Initialize once at startup
rag = RAGPipeline()
if not rag.load_vector_store():
    print("Error: No index found. Run 'python rag_pipeline.py build' first")
    exit(1)

# During interview, when question is transcribed
def handle_transcribed_question(question_text):
    # Get relevant context
    context = rag.get_personal_context(question_text, top_k=5)

    # Format for display
    relevant_info = []
    for result in context:
        relevant_info.append({
            'text': result['content'],
            'source': result['metadata']['file_name'],
            'score': result['similarity_score']
        })

    # Display in overlay
    display_context(relevant_info)
```

### Example 3: Filtering by Source

```python
# Get results with metadata
results = rag.get_personal_context("leadership", include_metadata=True)

# Filter by source file
resume_results = [
    r for r in results
    if r['metadata'].get('file_name') == 'resume.pdf'
]

# Filter by document type
chatgpt_results = [
    r for r in results
    if r['metadata'].get('file_type') == 'chatgpt_json'
]
```

### Example 4: Bulk Processing

```python
# Multiple queries
queries = [
    "Python experience",
    "Machine learning projects",
    "Leadership examples",
    "Technical challenges faced"
]

for query in queries:
    print(f"\n=== {query} ===")
    results = rag.get_personal_context(query, top_k=3)

    for result in results:
        print(f"- {result['content'][:100]}...")
```

## Command-Line Interface

### Build Index

```bash
# Build index (first time)
python rag_pipeline.py build

# Force rebuild (if documents changed)
python rag_pipeline.py build --force
```

### Interactive Search

```bash
python rag_pipeline.py search
```

Enter queries interactively and see results in real-time.

### View Index Info

```bash
python rag_pipeline.py info
```

Shows:
- Creation timestamp
- Number of documents
- Number of chunks
- Source files
- Configuration used

## Maintenance

### Updating Documents

When you add/remove/modify documents:

1. Update files in `identity/` directory
2. Rebuild the index:
   ```bash
   python rag_pipeline.py build --force
   ```

### Index Location

The vector store is saved in `vector_store/`:
```
vector_store/
├── faiss_index/
│   ├── index.faiss
│   └── index.pkl
└── metadata.json
```

**Important:** Don't commit this to Git (it's in `.gitignore`). Rebuild on each machine.

### Backup

To backup your index:
```bash
# Backup
tar -czf vector_store_backup.tar.gz vector_store/

# Restore
tar -xzf vector_store_backup.tar.gz
```

## Performance

### Embedding Costs

OpenAI embeddings cost (as of 2025):
- **text-embedding-3-small**: $0.02 / 1M tokens

**Example calculation:**
- 100 documents
- Average 2000 words per document
- ~1.3 tokens per word
- Total: ~260,000 tokens
- Cost: ~$0.005 (half a cent)

Building the index is very cheap!

### Speed

- **Index building**: 2-5 seconds per 100 chunks (depends on API)
- **Loading index**: < 1 second
- **Query time**: ~100-200ms per query

### Storage

- **FAISS index size**: ~4KB per chunk
- **Example**: 1000 chunks = ~4MB

## Troubleshooting

### Error: "OPENAI_API_KEY not set"

**Solution:**
```bash
# Create .env file
cp .env.example .env

# Edit and add your key
nano .env
```

### Error: "No documents found to index"

**Solution:**
```bash
# Check directory exists
ls identity/

# Add some documents
cp ~/resume.pdf identity/
```

### Error: "No vector store found"

**Solution:**
```bash
# Build the index first
python rag_pipeline.py build
```

### Poor Search Results

**Possible causes:**
1. **Documents too generic**: Add more specific personal information
2. **Chunk size wrong**: Try increasing to 1000 characters
3. **Not enough documents**: Add more source material
4. **Query too vague**: Be more specific in queries

**Solutions:**
```python
# Increase chunk size
rag.chunk_size = 1000
rag.chunk_overlap = 100

# Get more results
results = rag.get_personal_context(query, top_k=10)

# Try different embedding model
rag.embedding_model = "text-embedding-3-large"  # More accurate but slower
```

### Large File Handling

For very large PDFs or many documents:

1. **Increase chunk size**: Fewer chunks = faster indexing
2. **Process incrementally**: Build index in batches
3. **Use better hardware**: More RAM helps with large indexes

## Advanced Usage

### Custom Document Loaders

Add support for more file types by editing [data_ingestion.py](data_ingestion.py):

```python
def load_txt(self, file_path: Path) -> List[Document]:
    """Load plain text files"""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    return [Document(
        page_content=text,
        metadata={
            "source": str(file_path),
            "file_type": "txt",
            "file_name": file_path.name
        }
    )]
```

### Custom Metadata

Add custom metadata to improve filtering:

```python
# In data_ingestion.py
doc.metadata.update({
    "category": "technical",
    "importance": "high",
    "date": "2024-01"
})
```

### Hybrid Search

Combine semantic search with keyword filtering:

```python
# Get results
results = rag.get_personal_context("Python projects")

# Filter by keyword
python_results = [
    r for r in results
    if "Python" in r['content'] or "python" in r['content']
]
```

## Integration with Main App

To integrate with the interview assistant:

```python
# In main.py or audio_capture.py

from rag_pipeline import RAGPipeline

# Initialize RAG at startup
rag = RAGPipeline()
if rag.load_vector_store():
    print("✓ RAG pipeline loaded")
else:
    print("⚠ RAG pipeline not available (run 'python rag_pipeline.py build')")
    rag = None

# When question is transcribed
def on_speaker_transcription(text):
    if rag and is_question(text):
        # Get relevant context
        context = rag.get_personal_context(text, top_k=5)

        # Display in overlay
        for result in context:
            overlay.add_transcript("context", result['content'])
```

## Best Practices

1. **Organize Documents**: Keep related documents together
2. **Use Descriptive Names**: `python_projects.pdf` not `doc1.pdf`
3. **Update Regularly**: Rebuild index when documents change
4. **Test Queries**: Use interactive search to verify results
5. **Check Costs**: Monitor OpenAI API usage
6. **Backup Index**: Save `vector_store/` after building

## Example Document Structure

```
identity/
├── resume/
│   ├── resume_2024.pdf
│   └── cover_letter.docx
├── projects/
│   ├── project_descriptions.docx
│   ├── technical_spec.pdf
│   └── architecture.pdf
├── education/
│   ├── transcripts.pdf
│   └── certificates.pdf
└── chatgpt/
    └── conversations.json
```

## API Reference

### RAGPipeline Class

```python
class RAGPipeline:
    def __init__(
        identity_dir: Path = None,
        vector_store_path: Path = None,
        openai_api_key: str = None
    )

    def build_index(force_rebuild: bool = False) -> bool
    def load_vector_store(path: Path = None) -> bool
    def get_personal_context(
        query: str,
        top_k: int = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]
```

### Result Format

```python
{
    "rank": 1,
    "content": "Your relevant text here...",
    "similarity_score": 0.8542,
    "metadata": {
        "source": "/path/to/file.pdf",
        "file_type": "pdf",
        "file_name": "resume.pdf",
        "page": 1
    }
}
```

## Support

For issues or questions:
1. Check this guide
2. Review [README.md](README.md)
3. Check configuration in `.env`
4. Verify API key is valid
5. Test with `python rag_pipeline.py search`

## Next Steps

1. ✅ Set up OpenAI API key
2. ✅ Add documents to `identity/`
3. ✅ Build index: `python rag_pipeline.py build`
4. ✅ Test search: `python rag_pipeline.py search`
5. ✅ Integrate with main app

Happy interviewing! 🎯
