# HAR Analyzer <img src="./src/assets/har_analyzer.png" alt="HAR Analyzer Logo" width="28" align="absmiddle">

A fast, simple, highly modular, and strictly typed Streamlit application to parse, filter, and audit HTTP Archive (`.har`) files — with a focus on tracing how identifiers (cookies, query-param tokens, session IDs) are captured and disseminated across a capture.

---

## Setup & Use

```bash
# Initialize and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (for development: pip install -r requirements-dev.txt)
pip install -r requirements.txt

# Change to source directory
cd src

# Run the Streamlit app
streamlit run app.py
```

---

## Project Structure

```bash
./src
├── app.py                     # Streamlit orchestrator
├── assets/                    # Static files (logo, etc.)
├── core/                      # Pure parsing/typing layer
│   ├── models.py                # Caching HAR parser + ParsedEntry / HarAnalysis data types
│   ├── analyzer.py              # Upload flow + tab orchestration
│   ├── app_version.py           # Reads the app version out of pyproject.toml
│   └── protocols.py             # Tab protocol every tab implements
├── tabs/                      # Self-contained, single-responsibility UI views
│   ├── networklog.py            # Request/response browser + filter/highlight search
│   ├── cookies.py                # Cookie registry + aggregation
│   ├── query_params.py          # Query-param registry + aggregation
│   ├── overview/                # HAR analytics: metrics, domain explorer, DNS/WHOIS
│   │   ├── overview.py            # Logic
│   │   └── overview_ui.py         # UI
│   ├── dissemination/           # Identifier dissemination tracing
│   │   ├── dissemination.py       # Logic
│   │   └── dissemination_ui.py    # UI
│   ├── identifiers/             # Stable identifier detection (entropy/cardinality scoring)
│   │   ├── identifiers.py         # Logic
│   │   └── identifiers_ui.py      # UI
│   ├── metadata/                 # Standardize & tag a HAR file with embedded metadata
│   │   ├── metadata.py            # Logic
│   │   └── metadata_ui.py         # UI
│   ├── naming/                   # Standardized filename format
│   │   └── naming.py              # Logic (used by tabs/metadata)
│   └── shared/                   # Code reused across tabs
│       ├── entry_render.py        # Shared expander UI for a HAR entry
│       ├── search.py              # Searching, tokenizing, matching engine
│       └── selectors.py           # Select box helper
```

* **`app.py`** — wires up all tabs and drives the page.
* **`core/`** — parsing and typing that nothing in the UI layer depends on stylistically; every other module builds on top of `ParsedEntry`.
* **`tabs/`** — one file (or sub-package, for anything with enough logic to warrant separating UI from core logic) per view. All tabs implement the `Tab` protocol from `core/protocols.py`: a `title` property and a `render(entries)` method.
* **`tabs/shared/`** — logic used by *more than one* tab (currently the entry expander renderer and the search/matching engine), kept out of `core/` since it's Streamlit-facing rather than pure parsing.

> `captures/` and `output/` are optional local working folders you can create under `src/` to keep `.har` test inputs and generated outputs organized while you work. They're gitignored scratch space, not part of the application code, so they're left out of the tree above.

---

## File Standardizer

Alongside HAR analysis, the app includes a standalone **file standardizer** for
renaming `.har` captures *after* you record them. Upload a capture and fill in
the required fields.

The capture time is detected automatically: the tool reads the timestamps of all
entries in the file and uses the earliest one. HAR files store timestamps in UTC,
and that UTC value is what appears in the generated filename. The time shown in
the interface is the same instant converted to your local timezone, so the two
will differ if you aren't on UTC.

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

This single format is defined in one place in code — `tabs/naming/naming.py`'s `get_har_filename` (building it) and `get_attrs_from_har_name` (parsing it back) — and used by both the standardizer and the Analyzer's own file-format check.

---

## Tabs

### Overview

High-level summary of the loaded HAR file.

### Network Log

The main request/response browser. Every entry renders as an expander (status, method, URL, badges) with tabs for Request Headers, Post data (POST only), Query & Cookies, Response Headers, and Response Body. Supports the full filter/highlight search described below.

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
* Matching entries render with the same expander UI as the Network Log tab, with an extra **Matches** tab showing exactly which field and encoding triggered the hit.

**How to use it:**

1. Open the Dissemination tab and pick a key from the dropdown (ordered by how often it appears).
2. Review the timeline to see first appearance and any value changes.
3. Optionally select encoded/hashed forms to match against (same Base64/MD5/SHA1/etc. options as the main search).
4. Click **Search dissemination** to run the scan.

The dissemination scan is a full sweep over every entry's every field, so it's gated behind that button and only runs on demand — switching keys, expanding rows, or adjusting other widgets won't silently re-trigger it. Results stay cached per key until you search again.

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

The same matching engine (`tabs/shared/search.py`) powers the Dissemination tab's scan.

---

## 🔌 How to Add a New Tab

Adding a custom tab (e.g., a "Performance" audit tab) takes less than two minutes:

### 1. Create the Tab File

Create `tabs/performance.py` implementing the `Tab` protocol:

```python
import streamlit as st
from core.models import ParsedEntry

class PerformanceTab:
    @property
    def title(self) -> str:
        return "🚀 Performance Analysis"

    def render(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Latency & Payload Audits")
        # Write your custom Streamlit UI code here!
```

For anything with enough logic to warrant separating UI from core logic (see `identifiers/`, `metadata/`, `dissemination/`, or `overview/`), make it a sub-package instead, following the `<name>.py` (logic) / `<name>_ui.py` (UI) convention:

```bash
tabs/performance/
├── __init__.py
├── performance.py      # Logic
└── performance_ui.py   # UI
```

### 2. Expose It in the Package

Open `tabs/__init__.py` to import and export your new class:

```python
from .performance import PerformanceTab

__all__ = [..., "PerformanceTab"]
```

### 3. Register It in the Main App

Add it to the `tabs_to_render` list inside `app.py`:

```python
tabs_to_render: list[Tab] = [
    NetworkLogTab(),
    OverviewTab(),
    CookiesTab(),
    QueryParamsTab(),
    IdentifiersTab(),
    DisseminationTab(),
    MetadataTab(),
    PerformanceTab(),  # Added!
]
```

If your tab needs logic shared with other tabs (not just its own), put it in `tabs/shared/` rather than duplicating it.
