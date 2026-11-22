# Project 1: Multimodal Chat with Your Knowledge (RAG on Pinecone)

**Level:** Beginner to Intermediate

## What we are building
A web app where you add knowledge in many forms (PDFs, pasted text, audio, video) and chat with it. Everything is indexed in a **Pinecone** vector database. Answers use only your stored content and cite the source (file, page or timestamp). The app keeps chat history, short-term memory, and a long-term context memory of what you said across all chats.

## Why
This is the "hello world" of GenAI apps, extended to real-world needs: multiple input types, a managed vector DB, data updates, and memory. It teaches Retrieval-Augmented Generation (RAG), the pattern behind most LLM products.

## How it works
```
INGEST
PDF   -> text + tables + images (captioned/OCR) -> chunk -+
Text  -> chunk -----------------------------------------+
Audio -> speech-to-text (timestamps) -> chunk -----------+-> embed -> Pinecone (with metadata)
Video -> audio transcript + keyframe captions -> chunk --+

CHAT
Question + memory -> rewrite to standalone query -> embed -> Pinecone top-k (+ metadata filter)
  -> prompt (chunks + short-term memory + user facts) -> LLM -> streamed answer + citations
  -> save turn to chat history; extract durable facts to long-term memory
```

## Requirements

### 1. Data sources
- **PDF:** text per page, with page numbers as metadata.
- **PDF tables:** extract as structured tables (pdfplumber / PyMuPDF), convert to Markdown, and store as separate "table" chunks that also keep the page and a short summary.
- **PDF images and scanned pages:** extract embedded images; caption them with a vision-capable LLM and OCR scanned pages. Store the caption/OCR text as "image" chunks pointing to the page.
- **Plain text:** paste text or upload .txt/.md; give it a title/source name.
- **Audio (mp3, wav, m4a):** transcribe with a speech-to-text model (e.g., Whisper) with timestamps; chunk by time window.
- **Video (mp4, etc.):** extract audio with ffmpeg and transcribe; optionally sample keyframes and caption them. Cite by timestamp.

### 2. Vector database (Pinecone)
- One index; use **namespaces** to separate users/workspaces.
- Metadata per chunk: `doc_id`, `source_name`, `source_type` (pdf/text/audio/video), `content_type` (text/table/image/transcript), `page`, `start_time`, `end_time`, `chunk_index`, `created_at`, `content_hash`.
- Deterministic vector IDs (`{doc_id}#{chunk_index}`) so re-ingesting is safe.

### 3. Data management
- **Append:** add new documents or add more text to an existing document without touching the rest.
- **Update:** re-upload a changed file; detect via `content_hash`, delete old vectors for that `doc_id` (by ID prefix, since IDs are deterministic), and upsert the new chunks.
- **Delete:** remove a document and all of its vectors.
- **List:** show ingested documents with type, size, date, and chunk count.
- Skip duplicates (same hash) automatically.

### 4. Retrieval
- Embed the query, search Pinecone top-k, with optional filter by file/type/date.
- Optional: hybrid search (dense + sparse) and reranking to improve results.
- Rewrite follow-up questions into standalone ones using chat memory.

### 5. Answering
- Grounded prompt: answer only from retrieved context and say "I don't know" otherwise.
- Citations on every answer: file + page, or file + timestamp; show table/image sources.
- Streaming responses in the UI.

### 6. Memory (three layers)
| Layer | What it holds | Where | Used for |
|---|---|---|---|
| **Chat history** | Full message log of every conversation, with chat IDs, titles, timestamps | SQLite (or Postgres) | Reopen, rename, delete old chats |
| **Short-term memory** | Last N turns (and a running summary of older turns) of the current chat | In-process / session state | Follow-up questions, coherent replies |
| **Long-term context memory** | Durable facts and preferences the user stated across **all** chats (name, role, goals, preferences, ongoing projects) | Separate Pinecone namespace (`memory`) + a facts table | Personalizing answers in any chat |

- After each turn, a small LLM call extracts durable user facts; new facts are upserted, conflicting ones are updated (not duplicated).
- At query time, retrieve the top relevant memories for the question and inject them into the prompt, separate from document context.
- User can view, edit, and delete memories (privacy control) and turn memory off.

## Concepts learned
Prompting, embeddings, chunking, multimodal ingestion (OCR, vision, speech-to-text), vector databases and metadata filtering, upsert/update/delete, grounding, streaming, short-term vs long-term memory.

## Suggested tech stack
Python, Streamlit or Gradio (or FastAPI + React), Pinecone, PyMuPDF + pdfplumber, Whisper (or a hosted STT API), ffmpeg, Groq (Llama chat and vision models, hosted Whisper) plus Pinecone's hosted embedding model, SQLite, python-dotenv.

## Suggested structure
```
app.py              # UI (chat, upload, document manager, memory viewer)
ingest/
  pdf.py            # text, tables, images, OCR
  text.py           # plain text
  audio.py          # transcription
  video.py          # audio + keyframes
  chunking.py       # chunkers per content type
index_store.py      # Pinecone: upsert, update, delete, query, namespaces
retriever.py        # search, filters, rewrite, rerank
chain.py            # prompt + LLM call + citations
memory/
  history.py        # chat history (SQLite)
  short_term.py     # recent turns + summary
  long_term.py      # fact extraction + memory namespace
data/               # sample files
requirements.txt
.env.example        # PINECONE_API_KEY, GROQ_API_KEY, etc.
```

## Milestones
- [ ] Extract text from a PDF and print it with page numbers
- [ ] Chunk, embed, and upsert into Pinecone with metadata
- [ ] Retrieve top-k chunks and answer in the CLI with citations
- [ ] Extract tables and images from PDFs and index them
- [ ] Add plain-text ingestion
- [ ] Add audio and video transcription with timestamps
- [ ] Append, update (hash-based re-index), and delete documents
- [ ] Build the chat UI with streaming and a document manager
- [ ] Persist chat history; reopen and rename chats
- [ ] Add short-term memory and follow-up rewriting
- [ ] Add long-term context memory across all chats, with a memory viewer
- [ ] Write up what failed (bad chunks, table splits, noisy transcripts, memory conflicts) and how you fixed it

## Stretch goals
Hybrid search and reranking, per-user namespaces with login, speaker labels in audio, YouTube URL ingestion, tuning chunk size and k and recording the effect, evaluation set for retrieval quality.

## Done when
You can add a PDF (with tables/images), text, audio, and video; update or append to any of them; chat with streamed, cited answers; reopen past chats; and the assistant remembers facts you told it in earlier chats. Out-of-scope questions get "I don't know".
