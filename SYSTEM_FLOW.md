# System Flow Diagram

Visual representation of how the Live Interview Assistant works.

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LIVE INTERVIEW ASSISTANT                         │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    INTERVIEWER SPEAKS                         │   │
│  └────────────────────────┬──────────────────────────────────────┘   │
│                           │                                           │
│                           ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 1: AUDIO CAPTURE                                       │   │
│  │  ─────────────────────                                       │   │
│  │  • System audio via WASAPI loopback                         │   │
│  │  • Real-time streaming                                       │   │
│  │  • 16kHz, mono, 16-bit                                      │   │
│  └────────────────────────┬──────────────────────────────────────┘   │
│                           │                                           │
│                           ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 2: REAL-TIME TRANSCRIPTION                            │   │
│  │  ───────────────────────────────                            │   │
│  │  • Deepgram SDK (WebSocket)                                 │   │
│  │  • Nova-2 model                                             │   │
│  │  • Interim + final results                                  │   │
│  │  • Latency: 100-300ms                                       │   │
│  └────────────────────────┬──────────────────────────────────────┘   │
│                           │                                           │
│                           ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 3: SILENCE DETECTION                                  │   │
│  │  ─────────────────────                                      │   │
│  │  • Monitor speech timing                                    │   │
│  │  • Detect 1.5s silence                                      │   │
│  │  • Accumulate transcript                                    │   │
│  │  • Extract complete query                                   │   │
│  └────────────────────────┬──────────────────────────────────────┘   │
│                           │                                           │
│                           ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 4: CONTEXT RETRIEVAL (RAG)                            │   │
│  │  ───────────────────────────────                            │   │
│  │  • Query vector embedding                                   │   │
│  │  • FAISS similarity search                                  │   │
│  │  • Top 5 relevant chunks                                    │   │
│  │  • From: resume, projects, notes                            │   │
│  │  • Latency: 100-200ms                                       │   │
│  └────────────────────────┬──────────────────────────────────────┘   │
│                           │                                           │
│                           ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 5: RESPONSE GENERATION                                │   │
│  │  ──────────────────────────                                 │   │
│  │  • Send query + context to GPT-4o-mini                      │   │
│  │  • Use "Personal Twin" prompt                               │   │
│  │  • Generate 3 bullet points                                 │   │
│  │  • First-person, natural style                              │   │
│  │  • Latency: 500-1500ms                                      │   │
│  └────────────────────────┬──────────────────────────────────────┘   │
│                           │                                           │
│                           ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 6: DISPLAY IN OVERLAY                                 │   │
│  │  ──────────────────────────                                 │   │
│  │  • Show question detected                                   │   │
│  │  • Display context snippets                                 │   │
│  │  • Show 3 response suggestions                              │   │
│  │  • Stealth mode (invisible to capture)                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Total Time: ~2.2-3.5 seconds                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
INTERVIEWER AUDIO
      │
      ▼
┌──────────────┐
│ Microphone/  │ ──► System Audio Output
│   Speakers   │     (via video call)
└──────┬───────┘
       │
       ▼
┌────────────────────────┐
│  WASAPI Loopback       │ ──► Captures what you hear
│  Audio Capture         │     (not what you say)
└──────┬─────────────────┘
       │ Raw Audio (bytes)
       ▼
┌────────────────────────┐
│  Deepgram WebSocket    │ ──► Real-time streaming
│  Nova-2 STT            │     transcription
└──────┬─────────────────┘
       │ Text (interim/final)
       ▼
┌────────────────────────┐
│  Silence Detector      │ ──► Watches for pauses
│  (1.5s threshold)      │     Accumulates query
└──────┬─────────────────┘
       │ Complete Query
       ├──────────────────────┐
       │                      │
       ▼                      ▼
┌────────────────┐    ┌──────────────────┐
│  Query         │    │  RAG Pipeline    │
│  Processing    │───►│  FAISS Search    │
└────────────────┘    └────┬─────────────┘
                           │ Context Docs
                           ▼
                    ┌──────────────────┐
                    │  GPT-4o-mini     │
                    │  + Identity      │
                    │    Prompt        │
                    └────┬─────────────┘
                         │ 3 Bullets
                         ▼
                    ┌──────────────────┐
                    │  Stealth         │
                    │  Overlay         │
                    │  Display         │
                    └──────────────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                 COMPONENT ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  LiveInterviewAssistant (Main Application)                  │
│  ├─ Initialization                                          │
│  ├─ Callback setup                                          │
│  └─ UI management                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  RealtimeProcessor (Orchestrator)                           │
│  ├─ Coordinates all components                              │
│  ├─ Manages threads                                         │
│  ├─ Handles callbacks                                       │
│  └─ Collects statistics                                     │
└─┬─────────┬──────────┬────────────┬──────────────────────────┘
  │         │          │            │
  │         │          │            │
  ▼         ▼          ▼            ▼
┌────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐
│ Audio  │ │Transcri-│ │   RAG   │ │  Response    │
│Capture │ │  ption  │ │Pipeline │ │  Generator   │
└────────┘ └─────────┘ └─────────┘ └──────────────┘
    │          │           │              │
    │          │           │              │
    ▼          ▼           ▼              ▼
┌────────────────────────────────────────────────┐
│              Stealth Overlay                    │
│  ┌──────────────────────────────────────────┐  │
│  │  Transcript Display                      │  │
│  ├──────────────────────────────────────────┤  │
│  │  Context Snippets                        │  │
│  ├──────────────────────────────────────────┤  │
│  │  Response Suggestions                    │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

## RAG Pipeline Detail

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG PIPELINE FLOW                         │
└─────────────────────────────────────────────────────────────┘

OFFLINE (One-time setup):
─────────────────────────

identity/
├── resume.pdf        ┐
├── projects.docx     │
└── chatgpt.json      │
                      │
                      ▼
         ┌──────────────────────┐
         │  Document Loaders    │
         │  • PyPDF             │
         │  • python-docx       │
         │  • JSON parser       │
         └──────┬───────────────┘
                │ Documents
                ▼
         ┌──────────────────────┐
         │  Text Chunking       │
         │  • 500 chars         │
         │  • 50 overlap        │
         │  • Smart separators  │
         └──────┬───────────────┘
                │ Chunks
                ▼
         ┌──────────────────────┐
         │  OpenAI Embeddings   │
         │  • text-embedding-   │
         │    3-small           │
         └──────┬───────────────┘
                │ Vectors
                ▼
         ┌──────────────────────┐
         │  FAISS Index         │
         │  • Build index       │
         │  • Save to disk      │
         └──────────────────────┘
                │
                ▼
         vector_store/
         └── faiss_index/


ONLINE (Real-time):
──────────────────

Query: "Tell me about Python"
         │
         ▼
┌──────────────────────┐
│  Query Embedding     │
│  (same model)        │
└──────┬───────────────┘
       │ Query Vector
       ▼
┌──────────────────────┐
│  FAISS Similarity    │
│  Search              │
│  • Cosine distance   │
│  • Top K results     │
└──────┬───────────────┘
       │ Top 5 Chunks
       ▼
┌──────────────────────┐
│  Ranked Results      │
│  with metadata       │
└──────────────────────┘
```

## Silence Detection Flow

```
┌─────────────────────────────────────────────────────────────┐
│              SILENCE DETECTION STATE MACHINE                 │
└─────────────────────────────────────────────────────────────┘

     ┌───────────────┐
     │  Listening    │ ◄─────────────────────┐
     │  (idle)       │                        │
     └───────┬───────┘                        │
             │ Speech detected                │
             ▼                                 │
     ┌───────────────┐                        │
     │  Speaking     │                        │
     │  (accumulate) │                        │
     └───────┬───────┘                        │
             │                                 │
             │ No speech for                   │
             │ 1.5 seconds                     │
             ▼                                 │
     ┌───────────────┐                        │
     │  Silence      │                        │
     │  Detected     │                        │
     └───────┬───────┘                        │
             │                                 │
             │ Check length                    │
             ▼                                 │
     ┌───────────────┐                        │
     │  >= 10 chars? │                        │
     └───────┬───────┘                        │
             │                                 │
         Yes │      No (discard)               │
             ▼         └─────────────────────►┘
     ┌───────────────┐
     │  Emit Query   │
     └───────┬───────┘
             │
             ▼
     ┌───────────────┐
     │  Process      │
     │  Query        │
     └───────┬───────┘
             │
             └─────────────────────────────────┘


Timeline Example:
────────────────

Time:  0s    1s    2s    3s    4s    5s
       │     │     │     │     │     │
Speech:█████████████     ░░░░░       █████
       │   Speaking   │ Silence │  Next
       │              │ 1.5s    │
       │              ▼         │
       │         Query Detected │
       │              │         │
       │              ▼         │
       │         Process        │
       │         (2-3s)         │
       │              │         │
       │              ▼         │
       │         Display        │
```

## Response Generation Flow

```
┌─────────────────────────────────────────────────────────────┐
│            RESPONSE GENERATION PIPELINE                      │
└─────────────────────────────────────────────────────────────┘

Query: "Tell me about leadership experience"
  │
  ▼
┌─────────────────────────────────┐
│ RAG Retrieval                   │
│ ────────────                    │
│ Top 5 contexts:                 │
│ 1. "Led team of 5..."          │
│ 2. "Mentored junior devs..."   │
│ 3. "Organized workshops..."    │
│ 4. "Resolved team conflict..." │
│ 5. "Improved processes..."     │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Build Prompt                    │
│ ────────────                    │
│                                 │
│ System: "You are the user's    │
│          personal twin..."      │
│                                 │
│ User: "Question: [query]       │
│        Context: [contexts]"    │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ GPT-4o-mini API Call            │
│ ───────────────────             │
│ • Temperature: 0.7              │
│ • Max tokens: 300               │
│ • Top-p: 0.9                    │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Parse Response                  │
│ ──────────────                  │
│ Extract bullet points:          │
│ • Point 1                       │
│ • Point 2                       │
│ • Point 3                       │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Display in Overlay              │
│ ──────────────────              │
│                                 │
│ 💡 SUGGESTED RESPONSES          │
│                                 │
│ 1. I led a team of 5           │
│    developers on a             │
│    microservices project...    │
│                                 │
│ 2. I mentored several junior   │
│    developers, helping them    │
│    grow their skills...        │
│                                 │
│ 3. I organized weekly tech     │
│    talks to share knowledge    │
│    across the team...          │
└─────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  ERROR HANDLING FLOW                         │
└─────────────────────────────────────────────────────────────┘

At each step:

┌────────────────┐
│  Operation     │
└────┬───────────┘
     │
     ├─► Success ──────► Continue
     │
     └─► Error ────► ┌──────────────────┐
                     │  Error Handler   │
                     └────┬─────────────┘
                          │
                          ├─► Log error
                          │
                          ├─► Update UI
                          │   ("Error: ...")
                          │
                          ├─► Increment stats
                          │
                          └─► Try graceful
                              degradation

Examples:

1. Transcription Error:
   ┌──────────────────┐
   │ Deepgram fails   │
   └────┬─────────────┘
        │
        ├─► Show: "Transcription error"
        ├─► Log: "Deepgram connection lost"
        └─► Continue: Other features work

2. RAG Error:
   ┌──────────────────┐
   │ Index not found  │
   └────┬─────────────┘
        │
        ├─► Show: "Context unavailable"
        ├─► Continue: Generate without context
        └─► Graceful degradation

3. GPT Error:
   ┌──────────────────┐
   │ API rate limit   │
   └────┬─────────────┘
        │
        ├─► Show: "Rate limit reached"
        ├─► Log: "Wait and retry"
        └─► Cache previous responses
```

## User Interaction Flow

```
┌─────────────────────────────────────────────────────────────┐
│                USER INTERACTION TIMELINE                     │
└─────────────────────────────────────────────────────────────┘

Interview Start
│
├─ User: Start application
│  python live_interview_assistant.py
│
├─ System: Initialize
│  ✓ Load overlay
│  ✓ Start audio capture
│  ✓ Connect to Deepgram
│  ✓ Load RAG index
│  ✓ Ready
│
├─ User: Position overlay
│  Drag to second monitor
│
├─ User: Join interview call
│  Zoom / Teams / Meet
│
└─ System: Status = "Ready"

Interview in Progress
│
├─ Interviewer asks question
│  "Tell me about your Python experience"
│
├─ System: Transcribe
│  [INTERVIEWER] Tell me about your Python experience
│
├─ System: Detect silence (1.5s)
│  🔍 QUESTION DETECTED
│
├─ System: Retrieve context (0.2s)
│  📚 Retrieved 5 items
│
├─ System: Generate response (1.5s)
│  💡 3 suggestions displayed
│
├─ User: Read suggestions
│  Glance at overlay
│
├─ User: Formulate answer
│  Using suggestions as guide
│
└─ User: Respond naturally
   "Well, I've been working with Python for..."

Interview End
│
├─ User: Close overlay
│  Click X button
│
├─ System: Cleanup
│  Stop transcription
│  Stop audio capture
│  Show statistics
│
└─ Done!
```

## Quick Reference

```
SYSTEM COMPONENTS
────────────────
1. Audio Capture      →  WASAPI Loopback
2. Transcription      →  Deepgram Nova-2
3. Silence Detection  →  1.5s threshold
4. Context Retrieval  →  RAG + FAISS
5. Response Gen       →  GPT-4o-mini
6. Display            →  Stealth Overlay

LATENCY BREAKDOWN
────────────────
Audio Capture        :     0ms (real-time)
Transcription        : 100-300ms
Silence Detection    :  1500ms
RAG Retrieval        : 100-200ms
GPT Response         : 500-1500ms
──────────────────────────────────
Total                : 2.2-3.5s

COST PER INTERVIEW
─────────────────
Deepgram (60 min)    : $0.26
GPT-4o-mini (~10q)   : $0.01
RAG queries          : $0.00
──────────────────────────────────
Total                : ~$0.27

CONFIGURATION
────────────
Silence threshold    : 1.5s (tunable)
Min query length     : 10 chars
Top-K results        : 5 contexts
Chunk size           : 500 chars
Bullet points        : 3 suggestions
```

This visual guide helps understand how all components work together!
