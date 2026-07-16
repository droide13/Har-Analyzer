"""Tab class for showing stored HAR cookies."""

from typing import Any
import streamlit as st
from models import ParsedEntry

class CookiesTab:
    @property
    def title(self) -> str:
        return "Cookies"

    def render(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Cookies list")
        
        records: list[dict[str, Any]] = []
        for e in entries:
            for c in e.req_cookies:
                records.append({
                    "Name": c.get("name", "Unnamed"), "Scope": "Sent Cookie", 
                    "Secure": c.get("secure", False), "HttpOnly": c.get("httpOnly", False), "Host": e.domain
                })
            for c in e.res_cookies:
                records.append({
                    "Name": c.get("name", "Unnamed"), "Scope": "Set-Cookie Received", 
                    "Secure": c.get("secure", False), "HttpOnly": c.get("httpOnly", False), "Host": e.domain
                })

        if not records:
            st.success("No active authentication headers or session tokens found.")
            return

        missing_secure = sum(1 for r in records if not r["Secure"])
        missing_httponly = sum(1 for r in records if not r["HttpOnly"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Cookies", len(records))
        c2.metric("Insecure SSL Cookies", missing_secure, delta_color="inverse")
        c3.metric("Missing HttpOnly Protection", missing_httponly, delta_color="inverse")

        st.markdown("#### Complete Cookie Registry Matrix")
        st.dataframe(records, height=700)