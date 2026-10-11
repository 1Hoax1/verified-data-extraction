"""Persistence health and P2 local input preview for existing Orders."""
import logging
import streamlit as st
from vde.bootstrap import bootstrap

st.set_page_config(page_title="Verified Data Extraction")
st.title("Verified Data Extraction")
result = bootstrap()
st.write(f"Storage: {result.health}")
if result.health == "blocked":
    st.error("Local storage is blocked. Review the storage errors before continuing.")
    for error in result.recovery.errors:
        logging.getLogger(__name__).error("Storage bootstrap failed: %s", error["details"])
        st.json(error)
elif result.health == "degraded":
    st.warning("Recovery detected incomplete local storage or stale runs. Business state was retained.")
    st.json({"staging": result.recovery.staging, "orphans": result.recovery.orphans, "stale_runs": result.recovery.stale_runs})
else:
    st.success("Local persistence is ready.")
from vde.ingestion.ui import panel
panel(result)
