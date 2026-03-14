# Complete Setup Guide

End-to-end setup guide for the Live Interview Assistant.

## Overview

Complete setup takes about **15-20 minutes** and includes:

1. Installing Python dependencies
2. Setting up API keys (OpenAI + Deepgram)
3. Adding your personal documents
4. Building the RAG index
5. Testing the system

## Prerequisites

- **Windows 10/11** (for screen capture exclusion)
- **Python 3.8+**
- **Working microphone**
- **System audio output**
- **Internet connection**

## Step-by-Step Setup

### Step 1: Install Python Dependencies (5 minutes)

```bash
# Navigate to project directory
cd "Question Assister"

# Install all requirements
pip install -r requirements.txt
```

This installs:
- UI framework (customtkinter)
- Audio capture (pyaudiowpatch)
- Transcription (deepgram-sdk)
- AI/ML (openai, langchain, faiss)
- Document processing (pypdf, python-docx)

**Verify installation:**
```bash
python test_setup.py
```

### Step 2: Get API Keys (5 minutes)

#### OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Cost:**
- $5 minimum credit
- ~$0.27 per 60-minute interview
- Free tier available

#### Deepgram API Key

1. Go to https://console.deepgram.com/
2. Sign up (email or GitHub)
3. Go to "API Keys" section
4. Copy your API key

**Cost:**
- $200 free credit on signup
- ~$0.26 per 60-minute interview
- Enough for ~770 hours free

### Step 3: Configure Environment (2 minutes)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env   # or use any text editor
```

Add your API keys:

```env
# Required
OPENAI_API_KEY=sk-your-key-here
DEEPGRAM_API_KEY=your-key-here

# Optional (defaults are fine)
IDENTITY_DIR=./identity
VECTOR_STORE_PATH=./vector_store
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
EMBEDDING_MODEL=text-embedding-3-small
SILENCE_THRESHOLD=1.5
MIN_QUERY_LENGTH=10
GPT_MODEL=gpt-4o-mini
MAX_BULLET_POINTS=3
```

### Step 4: Add Your Documents (5 minutes)

Create the identity directory:

```bash
mkdir identity
```

Add your documents:

```bash
# Copy your files
cp ~/Documents/resume.pdf identity/
cp ~/Documents/projects.docx identity/
cp ~/Downloads/chatgpt_conversations.json identity/
```

**Supported formats:**
- **PDF**: Resume, certificates, reports
- **DOCX**: Project descriptions, cover letters, notes
- **JSON**: ChatGPT conversation exports

**What to include:**
- Resume/CV
- Project descriptions
- Work accomplishments
- Technical blog posts
- ChatGPT conversations about your work
- Cover letters
- Performance reviews
- Presentations

**Don't include:**
- Personal sensitive info
- Passwords or credentials
- Private conversations
- Copyrighted material

### Step 5: Build RAG Index (3 minutes)

```bash
python rag_pipeline.py build
```

**Expected output:**
```
============================================================
                     RAG INDEX BUILD
============================================================

Initializing RAG Pipeline Components
✓ OpenAI Embeddings initialized
✓ Text splitter initialized

Data Ingestion: Loading Documents
✓ Loaded PDF: resume.pdf (2 pages)
✓ Loaded DOCX: projects.docx
✓ Loaded ChatGPT JSON: conversations.json (127 messages)

Chunking Documents
✓ Split 130 documents into 456 chunks

Creating Vector Store
✓ Vector store created with 456 vectors

Saving Vector Store
✓ FAISS index saved

✓ RAG INDEX BUILD COMPLETE
```

**Costs:**
- Typically $0.001 - $0.01
- One-time cost
- Rebuild only when adding documents

### Step 6: Test the System (5 minutes)

#### Test 1: Prerequisites Check

```bash
python live_interview_assistant.py check
```

Should show all green checkmarks.

#### Test 2: RAG Search

```bash
python rag_pipeline.py search
```

Try queries like:
- "Python experience"
- "leadership examples"
- "challenging projects"

#### Test 3: Transcription (Optional)

```bash
python realtime_transcription.py
```

Play audio or speak. Should see transcription appear.

#### Test 4: Full System

```bash
python live_interview_assistant.py
```

The overlay window should appear with:
- ✓ Stealth mode active
- ✓ Audio capture ready
- ✓ Transcription initialized
- ✓ RAG loaded
- ✓ Response generator ready

## Quick Test Checklist

- [ ] All dependencies installed (`test_setup.py`)
- [ ] API keys set in `.env`
- [ ] Documents added to `identity/`
- [ ] RAG index built successfully
- [ ] RAG search returns results
- [ ] Overlay window appears
- [ ] Audio indicators turn green
- [ ] System is ready for use

## Directory Structure

After setup, you should have:

```
Question Assister/
├── .env                        # Your API keys (gitignored)
├── identity/                   # Your documents (gitignored)
│   ├── resume.pdf
│   ├── projects.docx
│   └── conversations.json
├── vector_store/               # RAG index (gitignored)
│   ├── faiss_index/
│   │   ├── index.faiss
│   │   └── index.pkl
│   └── metadata.json
├── requirements.txt            # Python dependencies
├── live_interview_assistant.py # Main application
└── [other Python files]
```

## Common Setup Issues

### Issue: "ModuleNotFoundError"

**Fix:**
```bash
pip install -r requirements.txt
```

### Issue: "OPENAI_API_KEY not set"

**Fix:**
1. Create `.env` file from `.env.example`
2. Add your key: `OPENAI_API_KEY=sk-...`
3. Restart application

### Issue: "No documents found"

**Fix:**
```bash
# Check directory
ls identity/

# Add documents
cp your_resume.pdf identity/

# Rebuild index
python rag_pipeline.py build --force
```

### Issue: "Deepgram connection failed"

**Fix:**
1. Check internet connection
2. Verify Deepgram API key in `.env`
3. Check firewall isn't blocking WebSocket
4. Test at console.deepgram.com

### Issue: "No audio captured"

**Fix:**
```bash
# List devices
python main.py devices

# Test monitor mode
python main.py monitor

# Check Windows permissions:
# Settings → Privacy → Microphone
# Settings → Privacy → App permissions
```

### Issue: "Poor transcription quality"

**Fix:**
- Use speakers instead of headphones
- Increase system volume
- Reduce background noise
- Check audio device in `python main.py devices`

## Updating the System

### Adding New Documents

```bash
# Add files to identity/
cp new_document.pdf identity/

# Rebuild index
python rag_pipeline.py build --force
```

### Updating Dependencies

```bash
pip install -r requirements.txt --upgrade
```

### Changing Configuration

Edit `.env` file and restart application.

## Usage

### Starting the Application

```bash
python live_interview_assistant.py
```

### Before Each Interview

1. Start application
2. Position overlay window
3. Join interview call
4. Verify audio capture (green indicator)
5. Test with a sample question

### During Interview

- Interviewer speaks → transcription appears
- Interviewer stops (1.5s) → question detected
- System retrieves context and generates suggestions
- Use suggestions to formulate your response

### Stopping the Application

- Close overlay window, or
- Press Ctrl+C in terminal

## Best Practices

1. **Test Before Real Interview:**
   - Do a mock interview
   - Practice with friends
   - Verify all features work

2. **Keep Documents Updated:**
   - Add new projects regularly
   - Update resume
   - Rebuild index periodically

3. **Monitor Costs:**
   - Check OpenAI usage dashboard
   - Check Deepgram usage
   - Both platforms have alerts

4. **Backup Important Files:**
   - Save `.env` securely
   - Backup `identity/` folder
   - Export `vector_store/` if needed

5. **Position Overlay Strategically:**
   - Second monitor if available
   - Corner of screen
   - Where you can see without looking obvious

## Cost Summary

### One-Time Costs

| Item | Cost |
|------|------|
| RAG index build | $0.001 - $0.01 |
| **Total** | **~$0.01** |

### Per-Interview Costs (60 min)

| Service | Usage | Cost |
|---------|-------|------|
| Deepgram | 60 minutes | $0.26 |
| GPT-4o-mini | ~10 responses | $0.01 |
| RAG queries | Free | $0.00 |
| **Total** | | **~$0.27** |

### Free Tiers

- **Deepgram**: $200 free credit = ~770 hours
- **OpenAI**: $5 free credit (new users) = ~18 interviews

## Next Steps

After setup:

1. **Read User Guides:**
   - [REALTIME_GUIDE.md](REALTIME_GUIDE.md) - Real-time features
   - [RAG_SETUP.md](RAG_SETUP.md) - RAG details
   - [QUICKSTART.md](QUICKSTART.md) - Audio assistant
   - [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference

2. **Practice:**
   - Run mock interviews
   - Test different question types
   - Adjust settings to preference

3. **Customize:**
   - Tune silence threshold
   - Adjust response style
   - Add more documents

4. **Use in Real Interview:**
   - Start early, test everything
   - Position overlay properly
   - Stay natural and confident

## Getting Help

If you encounter issues:

1. **Check documentation:**
   - This guide
   - REALTIME_GUIDE.md
   - Component READMEs

2. **Run diagnostics:**
   ```bash
   python live_interview_assistant.py check
   python test_setup.py
   python test_rag.py
   ```

3. **Check error messages:**
   - Read terminal output
   - Look for specific errors
   - Search error message online

4. **Verify configuration:**
   - API keys valid
   - Environment variables set
   - All files in correct locations

5. **Test components individually:**
   ```bash
   python realtime_transcription.py
   python response_generator.py
   python rag_pipeline.py search
   ```

## Security Notes

### What's Gitignored

These are automatically excluded from Git:

```
.env                 # API keys
identity/            # Your documents
vector_store/        # RAG index
```

### Protecting Your Data

1. **Never commit `.env`**
2. **Don't share API keys**
3. **Review documents before adding**
4. **Use separate test identity folder** for demos
5. **Rotate API keys periodically**

## Congratulations!

You've completed the setup! 🎉

Your Live Interview Assistant is ready to use.

**Quick Start:**
```bash
python live_interview_assistant.py
```

**Good luck with your interviews!** 🎯
