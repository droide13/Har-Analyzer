# HAR Analyzer <img src="./assets/har_analyzer.png" alt="HAR Analyzer Logo" width="28" align="absmiddle">

A fast, strictly typed tool to parse, filter, and audit HTTP Archive (`.har`) files — with a focus on tracing how identifiers (cookies, query-param tokens, session IDs) are captured and disseminated across a capture.

The app has been written from manually created python scripts to a visual browser tool using Claude.

A FastAPI backend (Python) does the parsing/analysis; a React + TypeScript frontend renders it. Feature-for-feature parity with the original: same 7 tabs, same search syntax, same naming convention.

---

## Setup & Use

Requires Python 3 and Node.js already installed.

```bash
./dev.sh
```

Sets up the backend virtual environment and installs frontend dependencies
on first run, then starts both dev servers together. Ctrl+C stops both.

<details>
<summary>Manual setup (two separate terminals)</summary>

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

</details>

Open http://localhost:5173 and upload a `.har` file.

### Vendor tracker/known-ID data (optional)

Two generated data files back two separate features -- kept conceptually
separate since they answer different questions:

- **`backend/app/data/trackers.csv`** -- domain -> tracker service/category,
  a broad list (tens of thousands of domains, domain-exploded from Ghostery +
  Tracker Radar) used by Network Log's **Party** column and "Hide
  first-party domains" filter (see **Network Log** below). Answers "is this
  domain a known tracker, and roughly what kind?"
- **`backend/app/data/known_ids/*.json`** -- identity/ad-tech vendors'
  documented cookie/query-param/body-field *names* (e.g. `id5id` -> ID5),
  used by the Identifiers tab's **Known IDs** source (see **Identifiers**
  below). Answers "does this exact field name match something a specific
  vendor documents?" -- a narrower, curated subset (the `ID-Graph-Tables`
  submodule's *studied-services* list) rather than its full, less-reviewed
  research set.

Both are committed, so the app works out of the box with whatever was last
generated. They're regenerated from the `ID-Graph-Tables` git submodule at
repo root -- pull it in with:

```bash
git submodule update --init
```

**Note:** `.gitmodules` points at `git@github-work:droide13/ID-Graph-Tables.git` -- `github-work` is a personal SSH host alias (`~/.ssh/config`), not a public hostname. Without that alias (or without access to that private repo), this command fails; that's expected for anyone other than the primary maintainer, and harmless -- `backend/scripts/sync_tracker_data.py` (run automatically by `dev.sh`) silently skips regeneration and keeps using the already-committed data files when the submodule isn't initialized.

If you do have access, re-run `python backend/scripts/sync_tracker_data.py` after updating the submodule to a newer commit to refresh the committed data files.

---

## Deployment

Build the frontend to static files, then run the backend without `--reload` --
it serves both the API and the built frontend from one process/port:

```bash
cd frontend && npm install && npm run build   # produces frontend/dist/
cd ../backend
# python3 -m venv .venv # only if not already created
source ./.venv/bin/activate
# pip install -r requirements.txt # only if not already installed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`app/main.py` mounts `frontend/dist/` as static files (only if that directory
exists, so this is a no-op in local dev via `./dev.sh`) after all the API
routes, so `/api/*` is tried first and everything else falls through to the
built frontend. No CORS config or separate frontend server needed since it's
all same-origin.

**Important:** uploads live in an in-memory, per-process store (see
`backend/app/store.py`) -- there's no database, no shared cache, and no
persistence across restarts, by design (a local, single-user tool). This
means:
- Run a single uvicorn process, never multiple `--workers` or replicas
  behind a load balancer -- a request could land on a worker that never saw
  the upload.
- Any restart (crash, redeploy, reboot) clears every uploaded session; users
  just re-upload their `.har` file.

---

## Project Structure

```bash
./backend
├── app/
│   ├── main.py                  # FastAPI app + router registration
│   ├── store.py                 # In-memory upload registry (parse once, look up by id)
│   ├── schemas.py                # Pydantic response/request models
│   ├── data/                    # Generated: trackers.csv + known_ids/*.json (see Vendor tracker/known-ID data above)
│   ├── core/
│   │   ├── models.py               # ParsedEntry / HarAnalysis data types + HAR parsing
│   │   ├── har_time.py             # HAR ISO-8601 timestamp parsing (stdlib only)
│   │   └── app_version.py          # Reads the app version out of pyproject.toml
│   ├── shared/                    # Logic reused across more than one router
│   │   ├── search.py                # Searching, tokenizing, matching engine
│   │   ├── naming.py                 # Standardized filename format
│   │   ├── aggregation.py            # Group-by-name helpers (Cookies/Query Params)
│   │   ├── entry_summary.py          # ParsedEntry -> EntrySummary (Network Log + Dissemination)
│   │   ├── json_body.py              # JSON body parsing/flattening (Body Fields, Identifiers)
│   │   ├── trackers.py               # Domain -> tracker service/category classification
│   │   ├── known_ids.py              # Exact id-name -> documenting vendor(s)
│   │   └── data_files.py             # Shared APP_DATA_DIR constant
│   ├── features/                  # Pure per-tab logic, no FastAPI imports
│   │   ├── overview.py, cookies.py, query_params.py, identifiers.py,
│   │   └── dissemination.py, metadata.py
│   └── routers/                   # Thin HTTP layer: parse request, call features/, shape response
│       └── har.py, overview.py, cookies.py, query_params.py, identifiers.py,
│           dissemination.py, metadata.py, naming.py
├── scripts/
│   └── sync_tracker_data.py     # Regenerates app/data/* from the ID-Graph-Tables submodule
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
<domain>-platform-(WEB|MOB)-interact-(LOA|NAV|EMA|SIG|LOG)-cookies-(ACC|DEN|IGN)-visit-(FIR|SEC|DEL)-extra-(3 LETTERS or 000)-yy-mm-dd-hh.har
```

| Segment    | Meaning                                                                                          | Codes                                                          |
| ---------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `platform` | web / mobile (more device types, e.g. TV/CTV, can be added the same way)                          | `WEB` / `MOB`                                                  |
| `interact` | load / navigate / enter email / sign up / login                                                   | `LOA` / `NAV` / `EMA` / `SIG` / `LOG`                          |
| `cookies`  | accept / deny / ignore                                                                             | `ACC` / `DEN` / `IGN`                                          |
| `visit`    | first visit (fresh) / second visit (reuse existing cookies or state) / delete cookies and reload  | `FIR` / `SEC` / `DEL`                                          |
| `extra`    | free-text context, first 3 letters uppercased, or `000` if omitted                                 | any 3 letters, or `000`                                        |

This format is defined in one place — `backend/app/shared/naming.py`'s `get_har_filename` (building it) and `get_attrs_from_har_name` (parsing it back) — used by both the standardizer and the upload's file-format check. `GET /api/naming/options` serves the same code/label tables to the frontend, so they can't drift apart.

### Ground truth & experiment notes

Beyond the filename fields, the Metadata tab also records a free-text **description**, free-text **notes**, and a repeatable **ground truth** key/value list (email, name, phone, IP, etc. — pick from the canonical list or type a custom key). None of this affects the filename; all of it is written into `log._analysis` inside the file itself, so the context survives a rename or move. See **Ground Truth** below for how it's later used to scan for leaks.

### Capture notes (pre-upload)

Remembering exactly which platform/interaction/cookie choice/ground-truth values you used *after* you've already recorded and closed a capture is easy to get wrong. The upload screen has a collapsible **Capture notes** panel (below the dropzone) for jotting those down before or while recording instead. It's saved to `localStorage` in your browser — not the backend, since there's no upload yet to attach it to — and the next time you upload a `.har` that doesn't already have `log._analysis` embedded, the Metadata tab prefills itself from that draft and clears it. Domain and capture time are never part of the draft; both are always read straight out of the uploaded file's own traffic.

---

## Tabs

### HAR Analytics (Overview)

High-level summary of the loaded HAR file: request/size/domain/latency metrics, method and status-code distribution, and a domain/subdomain traffic explorer with an opt-in DNS + WHOIS resolution report.

### Network Log

The main request/response browser: a virtualized table (handles large captures without the browser choking) plus a detail panel per row with tabs for Request/Response Headers, Post data, Query & Cookies, Response Body, Initiator, Timing, Details, and (when the entry has any) **Matched Fields**. Supports the full filter/highlight search described below, plus the opt-in **ground-truth search** — see **Ground Truth** below.

Each row's **Party** column classifies the request's domain against the tracker table (see **Vendor tracker/known-ID data** above): a `1st Party` badge for same-site requests, or the matched tracker's service name (hover for its description) for a known third-party domain -- blank when the domain matches neither. A **Hide first-party domains** checkbox above the table filters the list down to third-party traffic only.

### Query Params

Lists every query-string parameter across the capture, either as a raw registry (one row per occurrence) or aggregated by name — showing whether a param's method and value stayed consistent or varied, how often it appeared, and which hosts used it.

### Cookies

Same idea as Query Params but for cookies, split by scope (sent vs. `Set-Cookie` received), and flags security posture per name: whether `Secure`/`HttpOnly` were always set, never set, or mixed.

### Body Fields

Same raw-registry-or-aggregate idea again, but for identifiers that only ever show up inside a JSON request/response body — a UID2 token, an email hash, a resolved third-party ID — never as a cookie or query param. Every JSON body in the capture is flattened into dotted field paths (e.g. `fms_params.fms_uid2`), each tracked like a cookie/query-param name would be, split by scope (POST Data vs. Response Body). Non-JSON bodies (HTML, JS, form-encoded, binary) are silently skipped.

A real identity/consent-style payload is small -- a few KB, a few dozen to low hundreds of fields. A body over 100,000 characters is skipped outright (it's a product catalog, a config dump, a translations table, not an identifier), and flattening any single body stops after 300 fields regardless of its size, as a second safety net. Both caps exist so one oversized response in a capture can't blow up this tab's response size or the browser rendering it — see `app/shared/json_body.py`.

### Dissemination

Traces a single query-param or cookie key across the whole capture — not just where it's *named*, but where its *value* shows up anywhere else in the traffic.

**What it does:**

* Groups every sighting of the selected key from query strings and both request/response cookies, ordered by the HAR entry's actual timestamp — so you can see exactly when the identifier first appeared.
* Builds a **value timeline**: one row per sighting, flagging whenever the value changes from the sighting immediately before it. Useful for spotting session rotation, token refresh, or a value that never changes when it probably should.
* Runs a **dissemination scan**: takes every distinct value ever seen under that key and searches *every* field of *every* entry — headers, URLs, request/response bodies, other cookies — not just the field the value originally came from. This is how you catch a session cookie quietly leaking into a third-party request URL or an analytics payload.
* Summarizes the scan **by domain**: which hosts received or echoed the value, in how many entries, and through which fields — a quick way to gauge third-party exposure before drilling into individual requests.
* Renders a **flow graph**: a node-link diagram of the traced value's whole story — the initiator chain that caused its first sighting, pinned in a straight line, flowing into the origin domain, then fanning out (force-directed layout) to every domain it later reached. Edge color/style encodes *why* two domains are connected (initiator, cookie, query param, URL, other); node size reflects how many entries a destination was hit in. Clicking a node narrows the Matching HAR Entries list via the same `domain:` search syntax used elsewhere.
* Matching entries share the same detail-panel UI as the Network Log tab, including its **Matched Fields** tab (see below) showing exactly which field, encoding, and literal text triggered each hit.
* Supports the same opt-in **ground-truth search** as Network Log (see **Ground Truth** below) against the "Matching HAR Entries" list, so a real tagged value's disappearance/reappearance can be checked the same way as any other traced key.

**How to use it:**

1. Open the Dissemination tab and pick a key from the dropdown (ordered by how often it appears).
2. Review the timeline to see first appearance and any value changes.
3. Optionally select encoded/hashed forms to match against (same Base64/MD5/SHA1/etc. options as the main search).
4. Click **Search dissemination** to run the scan.

The dissemination scan is a full sweep over every entry's every field, so it's gated behind that button and only runs on demand — switching keys or adjusting the encoding checkboxes won't silently re-trigger it. The narrow/highlight filters below the results *are* live once a scan has run.

### Identifiers

Detection and scoring of likely identifier values (tokens, session IDs, etc.), across four sources picked via the Source control:

* **Known IDs** (shown first, and the tab's default) — exact-name matches against identity/ad-tech vendors' documented cookie/query-param/body-field names (see **Vendor tracker/known-ID data** above), e.g. `id5id` matching ID5. This bypasses the 4-signal filter entirely -- a confirmed vendor-documented match is worth showing no matter how rarely it appears -- and has no raw "Show all" mode, since it's already the precise view by construction.
* **Cookies**, **Query Parameters**, **Body Fields** (JSON request/response body fields, flattened into dotted paths — see **Body Fields** above) — the original heuristic detector: the same 4-signal filter (appearance count, cardinality, average length, entropy), each with its own raw "Show all" listing.

Dissemination tracing (the **Trace** button) works for any matched key that is, or ever was, a cookie or query param — including a Known IDs match that happens to be one — since Dissemination itself only ever tracks cookie/query-param sightings. A match seen only inside a JSON body field (the Body Fields source, or a body-only Known IDs match) can't be traced there that way; its value can still be searched manually.

### Metadata

Confirms or overrides the domain/platform/interaction/cookie-handling/visit classification for the loaded file, records free-text description/notes and any ground-truth values (see below), then generates a standardized copy of the `.har` with all of it embedded in `log._analysis`. See **File Standardizer** below for the full naming convention.

### Matched Fields (per entry)

Network Log and Dissemination's entry tables truncate their match badges to keep rows scannable. Opening an entry's detail panel shows a **Matched Fields** tab (only present when the entry has matches) listing every match uncut — which field, which encoding, and the literal on-the-wire text that triggered it — and clicking one jumps straight to that field's own tab with the match highlighted.

## Ground Truth

A **ground truth** entry is a real, known value used to set up a capture — the email actually registered with, a name actually typed in, the IP you captured from — tagged onto the file (via the Metadata tab, see below) so later analysis can check whether, and where, that exact value leaks into the traffic itself.

Once a file has ground truth tagged, both **Network Log** and **Dissemination** offer an opt-in **ground-truth search**: every tagged key/value is listed pre-checked, and clicking "Search ground truth values" scans every entry × every included value × every encoding, same as a manual dissemination scan. A match gets its own distinct row highlight (red, vs. the yellow used for a plain search/highlight match) and its badge names which ground-truth field matched (e.g. "E-mail match: ..."), since a real value actually leaking is a different signal from an ordinary search hit.

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
