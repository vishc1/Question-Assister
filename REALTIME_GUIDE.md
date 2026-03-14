# Real-time Processing Guide

Complete guide for the live interview assistant with real-time transcription, silence detection, and AI-powered response generation.

## Overview

The real-time processing system provides:

1. **Live Transcription** - Deepgram SDK for real-time speech-to-text
2. **Silence Detection** - Automatic query extraction after 1.5s silence
3. **Context Retrieval** - RAG-powered personal context from your documents
4. **Response Generation** - GPT-4o-mini generates personalized suggestions
5. **Stealth Overlay** - Displays everything invisibly to screen capture

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   LIVE INTERVIEW ASSISTANT                   │
└─────────────────────────────────────────────────────────────┘

System Audio (Interviewer)
        │
        ▼
┌─────────────────────┐
│ Audio Capture       │ ──► Captures system audio via
│ (WASAPI Loopback)   │     WASAPI loopback
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Deepgram SDK        │ ──► Real-time transcription
│ (WebSocket)         │     Nova-2 model
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Silence Detector    │ ──► Detects 1.5s silence
│                     │     Extracts complete query
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ RAG Pipeline        │ ──► Retrieves relevant context
│ (FAISS + OpenAI)    │     from your documents
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Response Generator  │ ──► GPT-4o-mini generates
│ (GPT-4o-mini)       │     3 bullet point suggestions
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Stealth Overlay     │ ──► Displays transcripts,
│ (CustomTkinter)     │     context, and suggestions
└─────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys

Create `.env` file:

```env
OPENAI_API_KEY=sk-your-openai-key-here
DEEPGRAM_API_KEY=your-deepgram-key-here
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Deepgram: https://console.deepgram.com/ (free tier available)

### 3. Build RAG Index

```bash
# Add your documents to identity/
mkdir identity
cp ~/resume.pdf identity/

# Build the index
python rag_pipeline.py build
```

### 4. Check Prerequisites

```bash
python live_interview_assistant.py check
```

### 5. Run the Application

```bash
python live_interview_assistant.py
```

## Components

### 1. Real-time Transcription ([realtime_transcription.py](realtime_transcription.py))

**Features:**
- WebSocket connection to Deepgram
- Nova-2 model (most accurate)
- Interim and final results
- VAD (Voice Activity Detection)
- Smart formatting and punctuation

**Configuration:**
```python
from realtime_transcription import RealtimeTranscription

transcription = RealtimeTranscription(
    api_key="your-key",
    silence_threshold=1.5,  # seconds
    min_query_length=10     # characters
)
```

**Usage:**
```python
# Set up callbacks
transcription.on_transcript = lambda text, is_final: print(text)
transcription.on_query_detected = lambda query: handle_query(query)

# Start
transcription.start_transcription()

# Send audio
transcription.send_audio(audio_data)

# Stop
transcription.stop_transcription()
```

### 2. Silence Detector

**How It Works:**
1. Monitors transcription stream
2. Tracks time since last speech
3. When silence ≥ 1.5 seconds:
   - Accumulates transcript into single query
   - Validates minimum length
   - Triggers callback with complete question

**Configuration:**
```env
SILENCE_THRESHOLD=1.5      # seconds of silence
MIN_QUERY_LENGTH=10        # minimum characters
```

**Tuning:**
- **Lower threshold** (1.0s): Faster response, may cut off questions
- **Higher threshold** (2.0s): More complete questions, slower response
- **Recommended**: 1.5s is optimal for most interviews

### 3. Response Generator ([response_generator.py](response_generator.py))

**System Prompt:**
```
You are the user's personal twin. Based ONLY on the provided history,
suggest 3 short bullet points for a response.

Guidelines:
- Use "I" and "Me" (speak as the user)
- Do not sound like an AI
- Be natural and conversational
- Each bullet point: 1-2 sentences max
- Focus on specific details from history
- If no direct answer, provide professional tip
```

**Configuration:**
```env
GPT_MODEL=gpt-4o-mini       # model to use
MAX_BULLET_POINTS=3         # number of suggestions
```

**Example Output:**
```
Question: "Tell me about a challenging Python project"

Suggestions:
1. I built a real-time analytics dashboard that handled 100K+
   daily users. The main challenge was optimizing database
   queries and implementing efficient caching.

2. I led the development of a microservices architecture using
   FastAPI. We faced issues with service discovery which I
   solved using a circuit breaker pattern.

3. I developed a machine learning recommendation system that
   improved engagement by 35%. The tricky part was handling
   sparse data and cold start problems.
```

### 4. Real-time Processor ([realtime_processor.py](realtime_processor.py))

**Orchestrates:**
- Audio capture
- Transcription
- Silence detection
- RAG retrieval
- Response generation

**Usage:**
```python
from realtime_processor import RealtimeProcessor

processor = RealtimeProcessor()

# Set callbacks
processor.on_transcript_update = handle_transcript
processor.on_query_detected = handle_query
processor.on_response_generated = handle_response

# Initialize and start
processor.initialize()
processor.start()

# Stop
processor.stop()
```

### 5. Live Interview Assistant ([live_interview_assistant.py](live_interview_assistant.py))

**Complete Application:**
- Integrates all components
- Displays in stealth overlay
- Handles errors gracefully
- Provides statistics

## Usage During Interview

### Before Interview

1. **Test everything:**
   ```bash
   python live_interview_assistant.py check
   ```

2. **Start application:**
   ```bash
   python live_interview_assistant.py
   ```

3. **Position overlay:**
   - Drag to second monitor if available
   - Place in corner where you can easily see
   - Ensure interviewer can't see it on camera

4. **Verify audio:**
   - Check speaker status indicator (green)
   - Speak or play audio to test transcription

### During Interview

**What You'll See:**

1. **Live Transcription:**
   ```
   [INTERVIEWER] How did you handle that challenge?
   ```

2. **Question Detection:**
   ```
   ═══════════════════════════════════
   🔍 QUESTION DETECTED
   ═══════════════════════════════════
   Q: How did you handle that challenge?
   ```

3. **Context Retrieval:**
   ```
   📚 Retrieved 5 relevant items:
   [1] resume.pdf: Led team through technical migration...
   [2] projects.docx: Implemented gradual rollout strategy...
   [3] chatgpt.json: Used clear communication and...
   ```

4. **Response Suggestions:**
   ```
   ═══════════════════════════════════
   💡 SUGGESTED RESPONSES
   ═══════════════════════════════════
   1. I approached it by breaking down the problem into
      smaller tasks and prioritizing based on impact.

   2. I maintained clear communication with stakeholders
      throughout the process, providing regular updates.

   3. I documented everything and created a rollback plan
      to mitigate risks.
   ═══════════════════════════════════
   ```

**Best Practices:**

1. **Use Suggestions as Guides:**
   - Don't read verbatim
   - Use as talking points
   - Add your own examples

2. **Stay Natural:**
   - Make eye contact
   - Use your own words
   - Show genuine enthusiasm

3. **Have Backup:**
   - Know your stories well
   - Don't rely 100% on system
   - Be ready if it fails

## Configuration

### Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...

# Optional (defaults shown)
SILENCE_THRESHOLD=1.5
MIN_QUERY_LENGTH=10
GPT_MODEL=gpt-4o-mini
MAX_BULLET_POINTS=3
TOP_K_RESULTS=5
```

### Customization

#### Adjust Silence Threshold

```python
# In .env
SILENCE_THRESHOLD=2.0  # Wait 2 seconds instead of 1.5
```

#### Change Response Style

Edit the system prompt in [response_generator.py](response_generator.py:15):

```python
IDENTITY_PROMPT = """Your custom prompt here..."""
```

#### Adjust Context Amount

```python
# In .env
TOP_K_RESULTS=10  # Retrieve 10 items instead of 5
```

## Performance

### Latency Breakdown

| Step | Time |
|------|------|
| Audio capture | 0ms (real-time) |
| Transcription | 100-300ms |
| Silence detection | 1500ms (configurable) |
| RAG retrieval | 100-200ms |
| GPT response | 500-1500ms |
| **Total** | **~2-3.5 seconds** |

### Costs

**Per Interview (60 minutes):**

1. **Deepgram Transcription:**
   - $0.0043 per minute
   - Total: ~$0.26

2. **OpenAI Embeddings:**
   - $0 (index already built)

3. **GPT-4o-mini:**
   - ~10 questions per interview
   - ~500 tokens per response
   - $0.15 per 1M input tokens
   - $0.60 per 1M output tokens
   - Total: ~$0.005

**Total Cost: ~$0.27 per 60-minute interview**

Very affordable!

### Optimization Tips

1. **Reduce Latency:**
   - Lower silence threshold (1.0s)
   - Use fewer RAG results (TOP_K=3)
   - Use shorter max_tokens for GPT

2. **Reduce Costs:**
   - Use longer silence threshold (fewer queries)
   - Cache common questions/responses
   - Use smaller embedding model

3. **Improve Accuracy:**
   - Add more documents to identity/
   - Use text-embedding-3-large for RAG
   - Increase TOP_K_RESULTS
   - Fine-tune system prompt

## Troubleshooting

### No Transcription

**Symptoms:**
- Overlay shows no text
- Speaker indicator stays gray

**Causes & Fixes:**

1. **Wrong audio device:**
   ```bash
   python main.py devices  # Check available devices
   ```

2. **No system audio:**
   - Play audio/video to test
   - Check volume isn't muted
   - Use speakers instead of headphones

3. **Deepgram API key invalid:**
   - Check .env file
   - Verify key at console.deepgram.com

### Questions Not Detected

**Symptoms:**
- Transcription works
- But no "QUESTION DETECTED" appears

**Causes & Fixes:**

1. **Silence threshold too high:**
   ```env
   SILENCE_THRESHOLD=1.0  # Lower to 1 second
   ```

2. **Query too short:**
   ```env
   MIN_QUERY_LENGTH=5  # Lower minimum
   ```

3. **Continuous speech:**
   - Interviewer doesn't pause
   - Manually force detection (future feature)

### No Response Suggestions

**Symptoms:**
- Question detected
- Context retrieved
- But no suggestions appear

**Causes & Fixes:**

1. **OpenAI API key issue:**
   - Check .env file
   - Verify API key valid
   - Check account has credits

2. **GPT API error:**
   - Check error messages
   - Try different model:
     ```env
     GPT_MODEL=gpt-3.5-turbo
     ```

3. **Rate limit hit:**
   - Wait a moment
   - Upgrade OpenAI plan

### Poor Response Quality

**Symptoms:**
- Suggestions are generic
- Don't match your style
- Miss important details

**Fixes:**

1. **Add more documents:**
   ```bash
   cp more_docs/* identity/
   python rag_pipeline.py build --force
   ```

2. **Increase context:**
   ```env
   TOP_K_RESULTS=10
   ```

3. **Adjust prompt:**
   - Edit system prompt in response_generator.py
   - Add style guidelines
   - Include examples

### High Latency

**Symptoms:**
- Long delay between question and suggestion
- Feels sluggish

**Fixes:**

1. **Reduce silence threshold:**
   ```env
   SILENCE_THRESHOLD=1.0
   ```

2. **Use fewer RAG results:**
   ```env
   TOP_K_RESULTS=3
   ```

3. **Faster GPT model:**
   ```env
   GPT_MODEL=gpt-4o-mini  # Already fastest
   ```

4. **Check internet speed:**
   - API calls require good connection
   - Test speed at speedtest.net
   - Use wired connection if possible

## Testing

### Test Individual Components

**1. Test Transcription:**
```bash
python realtime_transcription.py
```

**2. Test Response Generator:**
```bash
python response_generator.py
```

**3. Test Real-time Processor:**
```bash
python realtime_processor.py
```

**4. Test Complete App:**
```bash
python live_interview_assistant.py
```

### Mock Interview Practice

```bash
# Start the app
python live_interview_assistant.py

# Have friend ask questions via call
# Or use recorded interview questions
```

## Advanced Features

### Custom Question Detection

Add keyword-based detection in addition to silence:

```python
# In realtime_transcription.py
def is_question(text):
    question_words = ['what', 'how', 'why', 'when', 'where', 'tell me']
    return any(word in text.lower() for word in question_words)
```

### Response Caching

Cache common questions:

```python
response_cache = {}

def get_cached_response(query):
    # Simple similarity check
    for cached_query, response in response_cache.items():
        if similarity(query, cached_query) > 0.9:
            return response
    return None
```

### Multi-Language Support

Change Deepgram language:

```python
options = LiveOptions(
    model="nova-2",
    language="es",  # Spanish
    # ... other options
)
```

### Recording Sessions

Save transcripts for later review:

```python
transcript_file = open("interview_transcript.txt", "a")

def on_transcript(text, is_final):
    if is_final:
        transcript_file.write(f"{datetime.now()}: {text}\n")
```

## Best Practices

### Before Interview

- [ ] Test all components
- [ ] Build/update RAG index with latest docs
- [ ] Check API keys and credits
- [ ] Position overlay on second monitor
- [ ] Test with sample questions
- [ ] Verify audio capture works
- [ ] Close unnecessary applications
- [ ] Ensure stable internet connection

### During Interview

- [ ] Keep responses natural
- [ ] Use suggestions as guides, not scripts
- [ ] Maintain eye contact
- [ ] Show genuine interest
- [ ] Have backup stories ready
- [ ] Don't panic if system fails

### After Interview

- [ ] Review transcripts
- [ ] Analyze response quality
- [ ] Update documents with new experiences
- [ ] Rebuild RAG index
- [ ] Note improvements for next time

## Ethical Considerations

**Important:**

1. **Recording Laws:**
   - Know your local laws
   - Some jurisdictions require consent
   - Company policy may prohibit

2. **Interview Ethics:**
   - System is an aid, not a cheat
   - You still need genuine knowledge
   - Use as backup/confidence booster
   - Don't misrepresent abilities

3. **Transparency:**
   - Consider if disclosure is appropriate
   - Some companies may allow it
   - Others may not
   - Use your judgment

## Support

### Get Help

1. Check this guide
2. Review error messages
3. Run diagnostic: `python live_interview_assistant.py check`
4. Check API status pages
5. Review component docs

### Common Issues

See **Troubleshooting** section above.

## Next Steps

1. ✅ Install dependencies
2. ✅ Set up API keys
3. ✅ Build RAG index
4. ✅ Test components
5. ✅ Run practice interview
6. ✅ Optimize settings
7. ✅ Use in real interview

Good luck with your interview! 🎯
