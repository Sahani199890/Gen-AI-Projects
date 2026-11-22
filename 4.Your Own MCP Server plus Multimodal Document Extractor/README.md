# Project 4: Your Own MCP Server plus Multimodal Document Extractor

**Level:** Intermediate

## What we are building
An MCP (Model Context Protocol) server that exposes a document-extraction tool. The tool takes invoice or receipt images and PDFs, uses a vision model to extract structured fields, and validates them. Any MCP client, including the agent from Project 3, can then use it.

## Why
MCP is the emerging standard for connecting LLMs to tools. This project also teaches vision models and reliable structured extraction.

## How it works
```
MCP client (Claude Desktop / your agent)
    <-> MCP server (tools + resources)
          -> extract_document(file) -> vision LLM -> JSON
          -> validate against schema + business rules -> retry if invalid
          -> save to SQLite / JSON
```

## What we will implement
1. **MCP server** built with the official Python SDK (FastMCP).
2. **Tools:**
   - `extract_invoice(path)`: returns structured fields (vendor, date, line items, tax, total, currency)
   - `validate_invoice(data)`: runs the checks
   - `search_invoices(query)`: queries stored results
3. **Resources:** expose stored documents and a schema description.
4. **Vision extraction:** send the image or PDF pages to a vision-capable LLM with a Pydantic schema.
5. **Validation:** schema checks plus rules such as line items summing to the subtotal, a valid date, and tax calculated correctly.
6. **Retry loop:** on validation failure, feed the errors back to the model and retry up to N times.
7. **Storage:** persist results to SQLite.
8. **Client integration:** connect to Claude Desktop or an MCP inspector, then call the tools from your Project 3 agent.
9. **Comparison:** compare the vision LLM against classic OCR (Tesseract) on accuracy.

## Concepts learned
Model Context Protocol, tool and resource design, vision models, schema validation, retry on invalid output, how agents discover and call tools.

## Suggested tech stack
Python, `mcp` SDK, Pydantic, SQLite, a vision-capable LLM API, pdf2image or PyMuPDF, MCP Inspector for testing.

## Suggested structure
```
server.py         # MCP server and tool registration
extractor.py      # vision call + schema
validator.py      # business rules
store.py          # SQLite
samples/          # test invoices
tests/
```

## Milestones
- [ ] Hello-world MCP server with one tool, tested in the Inspector
- [ ] Vision extraction on one image
- [ ] Schema and business-rule validation
- [ ] Retry loop
- [ ] Storage and a search tool
- [ ] Connect to an MCP client
- [ ] Measure accuracy on 20+ sample documents

## Stretch goals
Authentication, batch processing, an HTTP transport, human review queue for low-confidence extractions.

## Done when
An MCP client can call your tool on a new invoice and get validated JSON back, and you know your extraction accuracy.
