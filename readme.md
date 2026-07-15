# HAR Visualizer

A fast, highly modular, and strictly typed Streamlit application to parse, filter, and audit HTTP Archive (`.har`) files.

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
