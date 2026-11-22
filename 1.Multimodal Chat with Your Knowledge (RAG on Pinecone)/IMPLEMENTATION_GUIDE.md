# Implementation Guide: Multimodal Chat with Your Knowledge (RAG on Pinecone)

Written for: you, building this by hand and wanting to understand the reason behind every step.

How to use this guide: do one phase at a time. Each phase has **What**, **Why**, **How**, and **Check** (how you know it works). Do not move on until the Check passes. Commit after every phase.

---

## Big picture first

Two pipelines share one database:

```
INGEST (write path)                         CHAT (read path)
file -> extract -> chunk -> embed -> Pinecone      question -> embed -> Pinecone -> chunks -> LLM -> answer
```

Why two paths? An LLM cannot read your 500-page PDF in every prompt (cost, limits, accuracy). So we do the heavy work once at ingest time (turn content into searchable vectors), and at chat time we only fetch the few relevant pieces. Every phase below is either improving what goes in, or improving what comes out.

Four stores, each with one job (do not mix them up):

| Store | Holds | Why this one |
|---|---|---|
| Pinecone `docs` namespace | Chunk vectors + metadata + chunk text | Semantic search |
| Pinecone `memory` namespace | Vectors of user facts | Semantic search over what the user told us |
| SQLite `documents` table | One row per ingested file (id, hash, chunk count) | Pinecone is bad at "list all documents" and "has this changed?" |
| SQLite `chats` + `messages` tables | Chat history | Exact ordered log, not semantic |

---

## Phase 0: Setup

**What:** Python environment, accounts, keys, folders.

**How:**
1. Install Python 3.11+. Create a venv: `python -m venv .venv` then activate it.
2. Install ffmpeg (needed in Phase 8): `winget install Gyan.FFmpeg`, then reopen the terminal and run `ffmpeg -version`.
3. Create a free Pinecone account and copy the API key. Create a free Groq account and an API key at console.groq.com. Groq's free tier has rate limits (requests and tokens per minute), so batch work and add small retries/sleeps when you hit a 429 error.
4. Create `.env` (never commit it) and `.env.example` (committed, no real values):
   ```
   PINECONE_API_KEY=
   GROQ_API_KEY=
   PINECONE_INDEX=rag-multimodal
   LLM_MODEL=llama-3.3-70b-versatile
   VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
   STT_MODEL=whisper-large-v3-turbo
   ```
5. Create `.gitignore` with `.venv/`, `.env`, `*.db`, `data/uploads/`.
6. `requirements.txt`: `pinecone`, `groq`, `python-dotenv`, `pymupdf`, `pdfplumber`, `faster-whisper`, `streamlit`.
   Then `pip install -r requirements.txt`.

**Why:** Secrets in code get leaked; `.env` keeps them out of git. A venv keeps dependency versions reproducible. ffmpeg is the standard tool for pulling audio out of video, and Whisper-style models need it.

**Check:** `python -c "import pinecone, groq, fitz"` runs without error.

---

## Phase 1: Pinecone index and embeddings (`index_store.py`)

**What:** A small module that creates the index and turns text into vectors.

**Why:** An *embedding* is a list of numbers that captures meaning, so "car" and "automobile" land near each other. Vector search finds the nearest vectors to your question. This is what makes search work on meaning instead of exact keywords. Everything later depends on this module, so build it first and test it alone.

**How:**
1. Pick an embedding model. Groq does not provide embeddings (it only serves chat, vision and speech models), so use Pinecone's hosted one: `pc.inference.embed(model="multilingual-e5-large", inputs=[...], parameters={"input_type": "passage"})`. Its dimension is **1024**. (Alternative: local `sentence-transformers`, dimension 384. Whatever you choose, the index dimension must match exactly.)
2. Create the index once, if it does not exist: `pc.create_index(name=..., dimension=1024, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))`.
3. Write helper functions: `embed_passages(texts)`, `embed_query(text)` (note `input_type="query"` here), `upsert(vectors, namespace)`, `query(vector, top_k, namespace, filter)`.
4. Batch embeds and upserts (around 50-100 items per call) because APIs have request size limits.

**Why two input types?** E5-style models are trained with different prefixes for stored text vs. questions. Using the right one noticeably improves retrieval.

**Why cosine?** It compares direction (meaning) not length, which is the standard for text embeddings.

**Check:** Embed "hello world", upsert one vector with id `test#0` and metadata `{"text": "hello world"}`, query "greeting", and get it back. Delete the test vector.

---

## Phase 2: Extract text from a PDF (`ingest/pdf.py`)

**What:** A function `extract_pages(path)` returning `[{"page": 1, "text": "..."}, ...]`.

**Why:** Page numbers are what make citations possible later. If you throw away page info now, you cannot get it back. PyMuPDF (`fitz`) is fast and handles most PDFs.

**How:** `doc = fitz.open(path)`, loop `for i, page in enumerate(doc, start=1)`, `page.get_text()`. Skip empty pages but remember them (they may be scanned images, handled in Phase 6).

**Check:** Print the text of page 3 of a sample PDF and compare with the real PDF.

---

## Phase 3: Chunking (`ingest/chunking.py`)

**What:** Split page text into overlapping pieces, e.g. 800 characters with 100 overlap.

**Why:**
- A whole page is too big and mixes topics, so its vector is "blurry" and retrieves poorly.
- A single sentence is too small and loses context.
- **Overlap** prevents an answer that straddles a boundary from being cut in half.
- Chunk per page (not across pages) so each chunk has one clean page number.

**How:** Write `chunk_text(text, size=800, overlap=100)`. Better: try to cut at paragraph or sentence boundaries (split on `\n\n`, then pack paragraphs until the size limit). Return chunks plus their `chunk_index`.

**Check:** Print chunk lengths and the first/last 50 characters of consecutive chunks to see the overlap. No chunk should be empty.

---

## Phase 4: Ingest pipeline (`ingest/pipeline.py`)

**What:** Glue Phases 1-3: file -> chunks -> vectors -> Pinecone, with the right IDs and metadata.

**Why each decision matters:**
- **`doc_id`**: a stable identifier for the document (e.g. hash of file name, or a UUID stored in SQLite). All chunks of one document share it.
- **Deterministic vector ID `{doc_id}#{chunk_index}`**: re-ingesting the same document overwrites the same IDs instead of creating duplicates. Pinecone `upsert` = insert-or-replace by ID. This one choice makes updates and deletes possible in Phase 9.
- **`content_hash`** (SHA-256 of the file bytes): lets you detect "same file uploaded again" or "file changed".
- **Metadata**: `doc_id, source_name, source_type, content_type, page, chunk_index, created_at, text`. Store the chunk `text` in metadata so retrieval returns readable text without a second lookup. (Pinecone allows about 40KB metadata per vector, so chunks of 800 characters are fine.) Metadata can also be used as a *filter* ("only search report.pdf").
- **SQLite `documents` table**: `doc_id, name, type, content_hash, chunk_count, created_at, updated_at`. Pinecone cannot cheaply list documents, so we keep a registry.

**How:**
1. Create `db.py` with SQLite connection and the `documents` table.
2. `ingest_pdf(path, namespace="docs")`: hash file -> if hash exists in registry, return "already ingested" -> extract -> chunk -> embed in batches -> upsert -> insert registry row.

**Check:** Ingest a PDF. In the Pinecone console you see the vectors; `index.describe_index_stats()` shows the count. Ingest the same file again: nothing new is added.

---

## Phase 5: Retrieval and grounded answer in the CLI (`retriever.py`, `chain.py`)

**What:** Ask a question in the terminal and get an answer with citations.

**Why:** This is the core of RAG. Prove it works in the simplest interface before building a UI. Bugs are far easier to find in a CLI.

**How:**
1. `retrieve(question, k=5)`: `embed_query` -> `index.query(top_k=k, include_metadata=True)` -> list of chunks with score and metadata.
2. Build the prompt. Put instructions in the **system** prompt: "Answer only using the provided context. If the answer is not in the context, say 'I don't know'. Cite sources like [file, p.3]." Put numbered context chunks in the user message, each labeled with its source.
3. Call Groq with the `groq` SDK: `client = Groq()` (reads `GROQ_API_KEY`), then `client.chat.completions.create(model=LLM_MODEL, messages=[{"role": "system", ...}, {"role": "user", ...}], temperature=0)`. Read the answer from `response.choices[0].message.content`. The API is OpenAI-style: the system prompt is a message with role `system`, not a separate parameter. Use `temperature=0` (or very low) for grounded answers, since you want faithfulness, not creativity. Model names change over time, so check console.groq.com/docs/models if one is rejected.
4. Add a **score threshold**: if the best score is below a cutoff (tune it, start around 0.7 for cosine with E5), skip the LLM and answer "I don't know". Do not trust the prompt alone.
5. Return the citations from metadata (not from what the LLM says), so they cannot be hallucinated.

**Why grounding?** Without it the LLM answers from its training memory and may invent things. Grounding plus a refusal rule is what turns a chatbot into a trustworthy document assistant.

**Check:** Ask a question the PDF answers (should cite the right page). Ask "Who won the 1998 World Cup?" (should say "I don't know").

---

## Phase 6: Tables and images inside PDFs (`ingest/pdf.py`)

**What:** Treat tables and pictures as first-class content, not garbage text.

**Why:** Plain `get_text()` flattens a table into a jumble of numbers with no row/column meaning, and ignores images completely. Questions like "what was Q3 revenue?" often live in a table or chart.

**How, tables:**
1. With `pdfplumber`: `page.extract_tables()` returns rows of cells.
2. Convert each table to Markdown (`| col | col |` rows). LLMs read Markdown tables well.
3. Store each table as **one chunk** (do not split it across chunks), with `content_type="table"` and the page. Optionally ask the LLM for a one-line summary and prepend it to the chunk, because the summary embeds much better than raw numbers do.

**How, images:**
1. With PyMuPDF: `page.get_images()` and `doc.extract_image(xref)` to get the bytes. Skip tiny images (logos, icons) by size.
2. Send the image to a Groq vision model (`VISION_MODEL`, a Llama 4 model) through the same chat endpoint. The image goes inside the user message content as a list: `[{"type": "text", "text": "Describe this image/chart in detail, including any numbers and labels."}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]`. Base64-encode the bytes first. Note that vision models accept limited image sizes (resize large images) and the free tier is rate-limited, so caption only images above a minimum size and sleep/retry on 429.
3. Store the description as a chunk with `content_type="image"` and the page.

**How, scanned pages:** If a page has almost no text but has a full-page image, render it (`page.get_pixmap()`) and ask the vision model to transcribe it (that is OCR). Mark `content_type="text"` with a metadata flag `ocr=True`.

**Why store a text description of an image?** Vectors are made from text here. Converting images to text lets the same search and the same embedding model handle everything.

**Check:** Ingest a PDF containing a table. Ask a question whose answer is in that table; the citation should show the table chunk.

---

## Phase 7: Plain text ingestion (`ingest/text.py`)

**What:** Add pasted text or `.txt`/`.md` files.

**Why:** Simplest source; shows that the pipeline is really "anything -> list of chunks with metadata". After this, adding a new source type means writing only an extractor.

**How:** Reuse `chunk_text` and the pipeline. Let the user give a title (becomes `source_name`). `source_type="text"`, `page=None`. For pasted text, hash the text itself.

**Refactor now:** Make the pipeline accept a generic list of `{"text", "metadata"}` records so PDF, text, audio, and video all call the same `ingest_records(...)`.

**Check:** Paste a paragraph, ask about it, see it cited by title.

---

## Phase 8: Audio and video (`ingest/audio.py`, `ingest/video.py`)

**What:** Speech to text with timestamps, then the same pipeline.

**Why timestamps:** A citation like "meeting.mp3 at 12:30-13:05" is useful; "somewhere in the audio" is not. Keeping `start_time`/`end_time` in metadata also lets the UI jump to that point.

**How, audio:**
1. Two options, same output shape (segments with `start`, `end`, `text`):
   - **Groq-hosted Whisper (fast, no local setup):** `client.audio.transcriptions.create(file=(filename, bytes), model=STT_MODEL, response_format="verbose_json", timestamp_granularities=["segment"])`, then read `result.segments`. Limitation: uploads have a size cap (about 25MB on the free tier), so for long files split the audio into 10-minute pieces with ffmpeg and add each piece's offset to its timestamps.
   - **Local `faster-whisper` (free, no size cap, slower on CPU):** `model = WhisperModel("small")` then `segments, _ = model.transcribe(path)`. Start with `base` or `small`.
   Start with Groq since you already have the key; keep faster-whisper as the fallback for big files.
2. Merge consecutive segments into chunks of about 30-60 seconds or about 800 characters. Keep the first `start` and last `end`.
3. Metadata: `source_type="audio"`, `content_type="transcript"`, `start_time`, `end_time`.

**How, video:**
1. Extract audio: `ffmpeg -i input.mp4 -vn -ac 1 -ar 16000 audio.wav` (via `subprocess.run`). Then use the audio path above with `source_type="video"`.
2. Optional: grab a keyframe every N seconds (`ffmpeg -vf fps=1/30`), caption with the vision model like Phase 6, store as `content_type="image"` with a `start_time`.

**Why mono 16kHz?** That is what speech models expect; it also makes files small and processing fast.

**Check:** Ingest a 2-minute audio clip. Ask about something said; the citation shows a timestamp range.

---

## Phase 9: Append, update, delete, list (`index_store.py`, `ingest/manage.py`)

**What:** Manage data after it is ingested.

**Why:** Real knowledge changes. Without these, users must wipe the index and start over.

**How:**
- **List:** read the SQLite `documents` table.
- **Delete a document:** vector IDs are `{doc_id}#0 ... {doc_id}#{chunk_count-1}`. Build that list from the registry and call `index.delete(ids=[...], namespace=...)` in batches (up to 1000 IDs per call). Then delete the registry row. Alternative: `index.list(prefix=f"{doc_id}#")` to discover IDs. (Do not rely on delete-by-metadata-filter: serverless indexes have not supported it historically, so ID-based delete is the portable approach. This is another reason for deterministic IDs.)
- **Update (file changed):** compute the new hash; if different from the stored one: **delete all old vectors first, then ingest the new version** under the same `doc_id`. Why delete first? If the new file has fewer chunks, upsert alone would leave old high-index chunks behind as stale "ghost" data that still gets retrieved.
- **Append:** new chunks continue numbering from the registry's `chunk_count` (`{doc_id}#{chunk_count}`, ...), so they never overwrite existing ones. Update `chunk_count` and `updated_at`. For pasted text: "add more to this document" is exactly this.
- **Duplicates:** same hash under another name -> warn and skip.

**Check:**
1. Ingest, then delete: `describe_index_stats()` count drops back and questions about it now return "I don't know".
2. Edit a text doc, re-ingest: old content no longer retrievable, new content is.
3. Append: both old and new content are retrievable.

---

## Phase 10: Chat history (`memory/history.py`)

**What:** Persist every conversation.

**Why:** Users expect to close the app and reopen yesterday's chat. History is an *exact ordered log*, so a normal database is the right tool; vectors are not.

**How:** SQLite tables:
- `chats(id, title, created_at, updated_at)`
- `messages(id, chat_id, role, content, sources_json, created_at)`

Functions: `create_chat()`, `add_message(chat_id, role, content, sources)`, `get_messages(chat_id)`, `list_chats()`, `rename_chat()`, `delete_chat()`. Auto-title a chat from its first question (one cheap LLM call or first 6 words). Store `sources_json` so old answers keep their citations.

**Check:** Create a chat, add messages, restart Python, load them back in order.

---

## Phase 11: Short-term memory and follow-up rewriting (`memory/short_term.py`)

**What:** Give the model the recent conversation, and make follow-up questions searchable.

**Why two separate problems:**
1. **Coherent replies:** to answer "and what about its price?", the LLM must see earlier turns. Send the last N turns (e.g. 6 messages) in the messages list.
2. **Retrieval:** the vector search sees only the string you embed. "What about its price?" embeds to nothing useful. So first **rewrite** it into a standalone question ("What is the price of the Model X laptop?") using the recent turns, and embed *that*.

**Why a running summary:** Chats grow past the context window and cost more every turn. Keep the last N turns verbatim; when older turns fall out, fold them into a short summary (LLM call) and prepend it. You keep the gist cheaply.

**How:**
1. `rewrite_query(history, question)`: small LLM call, instruction "Rewrite the last question to be fully standalone. Output only the question." If there is no history, skip it (saves a call).
2. `build_messages(summary, recent_turns, context, question)`.
3. Trigger summarization when the history exceeds a token or turn budget.

**Check:** Ask "Who wrote the report?" then "When was it published?". Print the rewritten query to confirm it names the report. Retrieval should now succeed.

---

## Phase 12: Long-term context memory (`memory/long_term.py`)

**What:** Remember durable facts about the user across **all** chats ("I'm a backend engineer", "I prefer short answers", "I'm studying for the AWS exam").

**Why this is different from history:** History is per-chat and replaying all of it is impossible. Long-term memory is a small distilled set of *facts*, retrievable by relevance, available in every new chat.

**How:**
1. **Extract:** after each assistant reply, make a small LLM call with the last exchange: "List any durable facts or preferences the user stated about themselves. Return JSON array of short statements, or []." Ignore anything that is only a question about documents. Run it in the background or batch every few turns to save cost.
2. **Store:** table `memories(id, text, created_at, updated_at, source_chat_id)` in SQLite, and the same text embedded into Pinecone namespace `memory` with ID `mem#{id}`.
3. **Dedupe/update:** before inserting a new fact, query the `memory` namespace for similar ones (cosine above about 0.85). If found, ask the LLM "same, contradictory, or new?" -> skip / replace / add. This stops "I live in Pune" and later "I moved to Delhi" from both living forever.
4. **Recall:** at chat time embed the question, fetch the top 3-5 memories, and put them in a **separate** prompt section: "Known facts about the user (use only if relevant)". Keep them apart from document context so the LLM never cites a memory as if it were a document.
5. **Privacy controls:** UI page to list, edit, delete memories, plus a toggle to turn memory off. Deleting must remove both the SQLite row and the Pinecone vector.

**Check:** In chat A say "I'm a data engineer and I like concise answers". Open a brand-new chat B and ask "What do I do for work?". It should answer from memory. Then delete the memory and confirm it no longer knows.

---

## Phase 13: Streamlit UI with streaming (`app.py`)

**What:** Put everything behind a chat interface.

**Why:** Streaming shows tokens as they arrive; perceived speed improves massively even though total time is the same.

**How:**
1. Sidebar: chat list (select/new/rename/delete), file uploader (pdf/txt/md/mp3/wav/mp4), pasted-text box, "Documents" manager (list + delete + re-upload to update + append text), "Memory" viewer.
2. Main: `st.chat_message` for history, `st.chat_input` for questions.
3. Streaming: call `client.chat.completions.create(..., stream=True)`, then write a generator that loops over the chunks and yields `chunk.choices[0].delta.content` (skip `None`). Pass that generator to `st.write_stream(...)`.
4. After the answer, show a "Sources" expander built from the retrieved metadata (file, page or timestamp, table/image tag).
5. Use `st.session_state` for current chat id and in-memory recent turns (Streamlit reruns the script on every interaction, so anything not in session state or the DB is lost).
6. Show a spinner during ingestion (audio and video take a while) and show errors clearly.

**Check:** Full run-through of the "Done when" list in the README.

---

## Phase 14: Test, tune, and write up

**What:** Make it reliable, and record what you learned.

**How:**
1. Build a small test set: about 15 questions with the expected source and page (include table, image, audio, and out-of-scope questions).
2. Measure: did the right chunk appear in the top-k? Try chunk sizes 500/800/1200 and k = 3/5/8 and record the results in a table. This is the real learning of RAG.
3. Common failures to look for: table split across chunks, headers/footers polluting text, noisy transcripts, memory facts stored wrongly, stale vectors after updates.
4. Optional upgrades: reranking, hybrid search, per-user namespaces.
5. Write `NOTES.md`: what failed, why, and how you fixed it. This is what makes the project valuable in an interview.

---

## Order of risk (where people get stuck)

1. Embedding dimension not matching the index dimension. Fix: they must be equal, recreate the index if you change models.
2. Forgetting `input_type` query vs passage.
3. Search returns nothing: you queried a different namespace than you upserted to.
4. Stale chunks after update: you did not delete before re-ingest.
5. Memory facts leaking into document citations: keep the two context blocks separate.
6. Windows: ffmpeg not on PATH. Reopen the terminal after installing.

Build slowly, test each phase alone, and print intermediate values (chunks, scores, rewritten queries). Most RAG problems are visible if you print what the model actually received.
