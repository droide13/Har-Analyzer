# HAR Analyzer <img src="./src/assets/har_analyzer.png" alt="HAR Analyzer Logo" width="28" align="absmiddle">

A fast, simple, highly modular, and strictly typed Streamlit application to parse, filter, and audit HTTP Archive (`.har`) files.

---

## Setup & Use

```bash
# Initialize and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies and run
pip install streamlit
streamlit run app.py

```

---

## Project Structure

* **`app.py`** — Streamlit orchestrator.
* **`models.py` & `search.py**` — Caching parser, data types, and filtering engine.
* **`tabs/`** — Subdirectory containing self-contained, single-responsibility UI views.

---

---

## Filename Generator

Alongside HAR analysis, the app includes a standalone **filename generator**
for standardizing `.har` captures *before* you record them. Switch to it via
the mode control at the top of the page — no file upload required.

Given a domain and a few dropdown selections (interaction type, cookie
handling, visit type, and optional free-text context), it produces a
filename in the form:

## Search Functionality

The Network Log tab supports two independent query fields: a **Filter** query
(discards non-matching entries) and a **Highlight** query (flags matches
without removing anything). Both share the same syntax.

* **Free text** — matches against the field selected in the scope dropdown.
* **Field prefixes** — target a specific field regardless of scope:
  `url:`, `status:`, `method:`, `header:`, `cookies:`, `body:`
* **Negation** — prefix any term with `-` to exclude matches (e.g. `-status:200`).
* **Status classes** — `status:4xx` matches any 4xx code.
* **Multiple terms** — space-separated terms are combined with AND logic;
  quote terms containing spaces (`"foo bar"`).

Additionally, each search term can be checked against **encoded or hashed
forms** of itself (Base64, Base32, MD5, SHA1, SHA256, SHA512) via the
checkboxes above the query fields. This surfaces matches even when the
plaintext only appears in encoded form somewhere in the traffic (e.g. a
token that shows up Base64-encoded in a cookie). Matched entries display a
badge indicating which field and encoding produced the match.

---

## 🔌 How to Add a New Tab

Adding custom tabs (e.g., a "Performance" audit tab) takes less than two minutes:

### 1. Create the Tab File

Create `tabs/performance.py` implementing the `Tab` protocol:

```python
import streamlit as st
from models import ParsedEntry

class PerformanceTab:
    @property
    def title(self) -> str:
        return "🚀 Performance Analysis"

    def render(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Latency & Payload Audits")
        # Write your custom Streamlit UI code here!

```

### 2. Expose It in the Package

Open `tabs/__init__.py` to import and export your new class:

```python
from .performance import PerformanceTab

__all__ = ["Tab", "RequestsTab", "OverviewTab", "SecurityTab", "PerformanceTab"]

```

### 3. Register It in the Main App

Add it to the `tabs_to_render` list inside `app.py`:

```python
tabs_to_render: list[Tab] = [
    RequestsTab(),
    OverviewTab(),
    SecurityTab(),
    PerformanceTab()  # 💡 Added!
]

```
