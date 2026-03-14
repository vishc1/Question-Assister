# Quick Reference Card

Fast reference for common tasks and commands.

## 🚀 Quick Start

### First Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Add your documents
mkdir identity
# Copy your PDF, DOCX, JSON files to identity/

# 4. Build RAG index
python rag_pipeline.py build

# 5. Test the application
python rag_integration_example.py demo
```

## 📋 Common Commands

### Interview Application

```bash
# Run with GUI
python main.py

# Test audio (console only)
python main.py monitor

# List audio devices
python main.py devices

# Show help
python main.py help
```

### RAG Pipeline

```bash
# Build index (first time)
python rag_pipeline.py build

# Rebuild index (after adding documents)
python rag_pipeline.py build --force

# Interactive search
python rag_pipeline.py search

# View index info
python rag_pipeline.py info
```

### Testing

```bash
# Test setup
python test_setup.py

# Test RAG components
python test_rag.py

# Create sample documents
python test_rag.py create-samples

# Run RAG demo
python rag_integration_example.py demo
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional
IDENTITY_DIR=./identity
VECTOR_STORE_PATH=./vector_store
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
```

## 📂 Directory Structure

```
Question Assister/
├── identity/           # Your documents (PDF, DOCX, JSON)
├── vector_store/       # FAISS index (auto-generated)
├── .env               # Your API keys (create from .env.example)
├── main.py            # Main application
├── rag_pipeline.py    # RAG pipeline
└── requirements.txt   # Dependencies
```

## 💻 Python API

### Basic RAG Usage

```python
from rag_pipeline import RAGPipeline

# Initialize and load
rag = RAGPipeline()
rag.load_vector_store()

# Query
results = rag.get_personal_context("Python experience", top_k=5)

# Use results
for result in results:
    print(result['content'])
    print(result['similarity_score'])
```

### With Interview App

```python
from rag_pipeline import RAGPipeline
from stealth_overlay import StealthOverlay

# Initialize
rag = RAGPipeline()
rag.load_vector_store()
overlay = StealthOverlay()

# On question detected
def handle_question(question_text):
    results = rag.get_personal_context(question_text)
    for result in results:
        overlay.add_transcript("context", result['content'])
```

## 🎯 Common Tasks

### Add New Documents

```bash
# 1. Copy files to identity/
cp ~/new_resume.pdf identity/

# 2. Rebuild index
python rag_pipeline.py build --force

# 3. Test
python rag_pipeline.py search
```

### Update API Key

```bash
# Edit .env file
nano .env

# Add: OPENAI_API_KEY=sk-your-new-key
```

### Check Everything Works

```bash
# 1. Test dependencies
python test_setup.py

# 2. Test RAG
python test_rag.py

# 3. Run demo
python rag_integration_example.py demo
```

## 🐛 Quick Fixes

### "No module named..."

```bash
pip install -r requirements.txt
```

### "OPENAI_API_KEY not set"

```bash
cp .env.example .env
# Edit .env and add key
```

### "No vector store found"

```bash
python rag_pipeline.py build
```

### "No documents found"

```bash
# Add files to identity/
mkdir -p identity
cp ~/resume.pdf identity/
python rag_pipeline.py build
```

### Overlay visible in screen share

```bash
# Restart application
# Ensure Windows 10/11
# Check screen capture software
```

### No audio captured

```bash
# Check devices
python main.py devices

# Test monitor mode
python main.py monitor

# Verify microphone permissions
```

## 📊 File Types

### Supported Document Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| PDF | `.pdf` | Resume, certificates, reports |
| Word | `.docx` | Project descriptions, notes |
| JSON | `.json` | ChatGPT exports, structured data |

### Audio Formats (for future)

| Format | Extension | Quality |
|--------|-----------|---------|
| WAV | `.wav` | Lossless, best for STT |
| MP3 | `.mp3` | Compressed, smaller |
| FLAC | `.flac` | Lossless, compressed |

## 🔗 Quick Links

- **Setup Guide**: [QUICKSTART.md](QUICKSTART.md)
- **RAG Setup**: [RAG_SETUP.md](RAG_SETUP.md)
- **Full Documentation**: [README.md](README.md)
- **RAG Implementation**: [RAG_IMPLEMENTATION.md](RAG_IMPLEMENTATION.md)
- **Project Overview**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

## 📝 Usage Examples

### Example 1: Build and Query

```bash
# Setup
python rag_pipeline.py build

# Query
python rag_pipeline.py search
Query: Tell me about Python projects
```

### Example 2: Integration

```python
# In your code
rag = RAGPipeline()
if rag.load_vector_store():
    context = rag.get_personal_context("leadership examples")
    print(f"Found {len(context)} relevant items")
```

### Example 3: Demo Mode

```bash
# Run demo with simulated questions
python rag_integration_example.py demo

# Questions appear every 15 seconds
# Context is automatically retrieved and displayed
```

## ⚡ Performance Tips

### Speed Up Index Building

```python
# Use smaller chunks (fewer API calls)
rag.chunk_size = 1000
rag.chunk_overlap = 100
```

### Improve Query Accuracy

```python
# Get more results
results = rag.get_personal_context(query, top_k=10)

# Use better embedding model (slower, more expensive)
rag.embedding_model = "text-embedding-3-large"
```

### Reduce Costs

```python
# Use smallest model (default)
rag.embedding_model = "text-embedding-3-small"

# Build index once, query many times
# No cost for queries!
```

## 🎓 Learning Path

1. **Day 1**: Setup + Basic Usage
   - Install dependencies
   - Set up .env
   - Add sample documents
   - Build index
   - Test search

2. **Day 2**: Integration
   - Run demo mode
   - Understand integration example
   - Test with main app
   - Customize queries

3. **Day 3**: Advanced
   - Add real documents
   - Optimize chunk size
   - Filter by metadata
   - Integrate with transcription

## 🔐 Security Checklist

- [ ] .env file not committed to Git
- [ ] identity/ directory in .gitignore
- [ ] vector_store/ directory in .gitignore
- [ ] API keys kept private
- [ ] Documents reviewed before adding
- [ ] Regular backups of important files

## 📞 Support

### Common Questions

**Q: How much does it cost?**
A: ~$0.001-0.01 to build index. Queries are free!

**Q: How long to build index?**
A: 15-30 seconds for typical document set.

**Q: Can I use other embedding models?**
A: Yes! Edit EMBEDDING_MODEL in .env

**Q: Does it work offline?**
A: No, requires OpenAI API for building. Queries need API too.

**Q: How to add more documents?**
A: Add to identity/ then run `python rag_pipeline.py build --force`

### Where to Get Help

1. Check this guide
2. Read [RAG_SETUP.md](RAG_SETUP.md)
3. Run test scripts
4. Check error messages
5. Review code comments

## 🎯 Next Steps

After setup:
1. Add your real documents (resume, projects, etc.)
2. Build the index
3. Test with interactive search
4. Run the demo
5. Integrate with main application
6. Add speech-to-text for real transcription
7. Customize UI and behavior

---

**Pro Tip**: Keep this file open while working with the application!
