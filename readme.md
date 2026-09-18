# HAR Analyzer

A fast, strictly typed tool to parse, filter, and audit HTTP Archive (`.har`) files — with a focus on tracing how identifiers (cookies, query-param tokens, session IDs) are captured and disseminated across a capture.

A FastAPI backend (Python) does the parsing/analysis; a React + TypeScript frontend renders it. Originally a single Streamlit app — rewritten for performance on large captures and richer interactive graphs. Feature-for-feature parity with the original: same 7 tabs, same search syntax, same naming convention.

---

## Setup & Use

Backend and frontend run as two separate local processes.

```bash
# Backend (FastAPI)
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt   # or requirements-dev.txt for dev (adds pytest, black, isort, pylint)
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend (React + Vite), in a second terminal
cd frontend
npm install
npm run dev   # http://localhost:5173 -- proxies /api/* to the backend on :8000
```

Open http://localhost:5173 and upload a `.har` file.

---

## Project Structure

```bash
./backend
├── app/
│   ├── main.py                  # FastAPI app + router registration
│   ├── store.py                 # In-memory upload registry (parse once, look up by id)
│   ├── schemas.py                # Pydantic response/request models
│   ├── core/
│   │   ├── models.py               # ParsedEntry / HarAnalysis data types + HAR parsing
│   │   ├── har_time.py             # HAR ISO-8601 timestamp parsing (stdlib only)
│   │   └── app_version.py          # Reads the app version out of pyproject.toml
│   ├── shared/                    # Logic reused across more than one router
│   │   ├── search.py                # Searching, tokenizing, matching engine
│   │   ├── naming.py                 # Standardized filename format
│   │   ├── aggregation.py            # Group-by-name helpers (Cookies/Query Params)
│   │   └── entry_summary.py          # ParsedEntry -> EntrySummary (Network Log + Dissemination)
│   ├── features/                  # Pure per-tab logic, no FastAPI imports
│   │   ├── overview.py, cookies.py, query_params.py, identifiers.py,
│   │   └── dissemination.py, metadata.py
│   └── routers/                   # Thin HTTP layer: parse request, call features/, shape response
│       └── har.py, overview.py, cookies.py, query_params.py, identifiers.py,
│           dissemination.py, metadata.py, naming.py
└── tests/                        # pytest -- unit tests per feature module + API integration tests

./frontend
├── src/
│   ├── App.tsx                   # Upload gate, SessionBar, tab registration
│   ├── api/                      # Typed fetch wrappers, one file per backend router
│   ├── components/                # Shared UI: TabShell, DataTable, EntryDetailPanel, Select, ...
│   ├── features/                  # One folder per tab (networkLog, overview, cookies, ...)
│   ├── hooks/                     # useDebouncedValue
│   └── lib/                       # formatBytes and other presentation-only helpers
```

* **`backend/app/core/`** — parsing and typing nothing else depends on stylistically; every other module builds on `ParsedEntry`.
* **`backend/app/shared/`** — logic used by more than one router (the search/matching engine, filename convention, aggregation helpers).
* **`backend/app/features/`** — one module per tab's business logic, pure Python, unit-tested without spinning up the API.
* **`backend/app/routers/`** — FastAPI endpoints; stay thin, delegate to `features/`.
* **`frontend/src/features/`** — one folder per tab; each view takes an explicit `uploadId` prop rather than reading global state.

> `captures/` (repo root) is an optional local working folder for `.har` test inputs. Gitignored scratch space, not part of the application.

---

## File Standardizer

Alongside HAR analysis, the app includes a standalone **file standardizer** for
renaming `.har` captures *after* you record them. Upload a capture and fill in
the required fields on the **Metadata** tab.

The capture time is detected automatically: the tool reads the timestamps of all
entries in the file and uses the earliest one. HAR files store timestamps in UTC,
and that UTC value is what appears in the generated filename. The time shown in
the interface is the same instant converted to your local timezone, so the two
will differ if you aren't on UTC. If no timestamp can be derived from the traffic,
you're prompted to enter the capture date manually.

### Naming convention

The standardizer generates (and the app parses) filenames of the form:

```
<domain>-interact-(LOA|NAV|EMA|SIG|LOG)-cookies-(ACC|DEN|IGN)-visit-(FIR|SEC|DEL)-extra-(3 LETTERS or 000)-yy-mm-dd-hh.har
```

| Segment    | Meaning                                                                                          | Codes                                                          |
| ---------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `interact` | load / navigate / enter email / sign up / login                                                   | `LOA` / `NAV` / `EMA` / `SIG` / `LOG`                          |
| `cookies`  | accept / deny / ignore                                                                             | `ACC` / `DEN` / `IGN`                                          |
| `visit`    | first visit (fresh) / second visit (reuse existing cookies or state) / delete cookies and reload  | `FIR` / `SEC` / `DEL`                                          |
| `extra`    | free-text context, first 3 letters uppercased, or `000` if omitted                                 | any 3 letters, or `000`                                        |

This format is defined in one place — `backend/app/shared/naming.py`'s `get_har_filename` (building it) and `get_attrs_from_har_name` (parsing it back) — used by both the standardizer and the upload's file-format check. `GET /api/naming/options` serves the same code/label tables to the frontend, so they can't drift apart.

---

## Tabs

### HAR Analytics (Overview)

High-level summary of the loaded HAR file: request/size/domain/latency metrics, method and status-code distribution, and a domain/subdomain traffic explorer with an opt-in DNS + WHOIS resolution report.

### Network Log

The main request/response browser: a virtualized table (handles large captures without the browser choking) plus a detail panel per row with tabs for Request/Response Headers, Post data, Query & Cookies, Response Body, Initiator, Timing, and Details. Supports the full filter/highlight search described below.

### Query Params

Lists every query-string parameter across the capture, either as a raw registry (one row per occurrence) or aggregated by name — showing whether a param's method and value stayed consistent or varied, how often it appeared, and which hosts used it.

### Cookies

Same idea as Query Params but for cookies, split by scope (sent vs. `Set-Cookie` received), and flags security posture per name: whether `Secure`/`HttpOnly` were always set, never set, or mixed.

### Dissemination

Traces a single query-param or cookie key across the whole capture — not just where it's *named*, but where its *value* shows up anywhere else in the traffic.

**What it does:**

* Groups every sighting of the selected key from query strings and both request/response cookies, ordered by the HAR entry's actual timestamp — so you can see exactly when the identifier first appeared.
* Builds a **value timeline**: one row per sighting, flagging whenever the value changes from the sighting immediately before it. Useful for spotting session rotation, token refresh, or a value that never changes when it probably should.
* Runs a **dissemination scan**: takes every distinct value ever seen under that key and searches *every* field of *every* entry — headers, URLs, request/response bodies, other cookies — not just the field the value originally came from. This is how you catch a session cookie quietly leaking into a third-party request URL or an analytics payload.
* Summarizes the scan **by domain**: which hosts received or echoed the value, in how many entries, and through which fields — a quick way to gauge third-party exposure before drilling into individual requests.
* Matching entries share the same detail-panel UI as the Network Log tab, with an extra **Matches** tab showing exactly which field and encoding triggered the hit.

**How to use it:**

1. Open the Dissemination tab and pick a key from the dropdown (ordered by how often it appears).
2. Review the timeline to see first appearance and any value changes.
3. Optionally select encoded/hashed forms to match against (same Base64/MD5/SHA1/etc. options as the main search).
4. Click **Search dissemination** to run the scan.

The dissemination scan is a full sweep over every entry's every field, so it's gated behind that button and only runs on demand — switching keys or adjusting the encoding checkboxes won't silently re-trigger it. The narrow/highlight filters below the results *are* live once a scan has run.

### Identifiers

Detection and scoring of likely identifier values (tokens, session IDs, etc.) found in the capture, feeding into the same value/field matching machinery used elsewhere in the app.

## Search Functionality

The Network Log tab supports two independent query fields: a **Filter** query (discards non-matching entries) and a **Highlight** query (flags matches without removing anything). Both share the same syntax.

* **Free text** — matches against the field selected in the scope dropdown.
* **Field prefixes** — target a specific field regardless of scope:
  `url:`, `status:`, `method:`, `header:`, `cookies:`, `body:`
* **Negation** — prefix any term with `-` to exclude matches (e.g. `-status:200`).
* **Status classes** — `status:4xx` matches any 4xx code.
* **Multiple terms** — space-separated terms are combined with AND logic; quote terms containing spaces (`"foo bar"`).

Additionally, each search term can be checked against **encoded or hashed forms** of itself (Base64, Base32, Hex, URL-encoding — single/double/triple pass, MD5, SHA1, SHA256, SHA512, and common hash-then-encode / encode-then-hash combinations) via the checkboxes above the query fields. This surfaces matches even when the plaintext only appears in encoded form somewhere in the traffic (e.g. a token that shows up Base64-encoded in a cookie). Matched entries display a badge indicating which field and encoding produced the match.

The same matching engine (`backend/app/shared/search.py`) powers the Dissemination tab's scan.

---

## Adding a New Tab

1. **Backend**: add `backend/app/features/<name>.py` (pure logic, unit-tested) and `backend/app/routers/<name>.py` (thin FastAPI endpoints calling into it), then register the router in `backend/app/main.py`.
2. **Frontend**: add `frontend/src/api/<name>.ts` (typed fetch wrappers) and `frontend/src/features/<name>/<Name>View.tsx`, then add it to the `tabs` array in `frontend/src/App.tsx`.

If your tab needs logic shared with other tabs (not just its own), put it in `backend/app/shared/` (backend) or `frontend/src/components/`/`frontend/src/lib/` (frontend) rather than duplicating it.
