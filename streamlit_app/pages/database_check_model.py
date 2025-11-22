"""Streamlit page for viewing model log database content."""

import streamlit as st
import requests
import os
import pandas as pd
from dotenv import load_dotenv

# Load .env file (for local development)
# For Cloud Run, set API_BASE_URL as an environment variable
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api/v1")


def safe_rerun():
    """Safely rerun the app, using st.rerun() if available, falling back to experimental_rerun()."""
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()


st.set_page_config(page_title="Model Log View", layout="wide")
st.title("Model Log Database Content")

# Get model logs
if st.button("Refresh"):
    safe_rerun()

try:
    response = requests.get(f"{API_BASE_URL}/model-logs", timeout=10)

    if response.status_code == 200:
        data = response.json()

        # Check if table doesn't exist
        if "message" in data:
            st.warning(data["message"])
            st.info("To create the table, run the SQL file: `infra/model_log.sql`")
            return

        total = data.get("total", 0)
        logs = data.get("logs", [])

        st.info(f"Total model logs: {total}")

        # Summary statistics
        if logs:
            success_count = sum(1 for log in logs if log.get("success"))
            failure_count = total - success_count

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Logs", total)
            with col2:
                st.metric("Successful", success_count, delta=f"{success_count/total*100:.1f}%" if total > 0 else "0%")
            with col3:
                st.metric("With Corrections", failure_count, delta=f"{failure_count/total*100:.1f}%" if total > 0 else "0%")

        if logs:
            # Display as a table
            import pandas as pd

            # Prepare data for table display
            table_data = []
            for log in logs:
                corrections_count = len(log.get('corrections_made', {})) if log.get('corrections_made') else 0
                table_data.append({
                    "ID": log.get("id"),
                    "Status": "✅ Success" if log.get("success") else "❌ Corrections",
                    "Document ID": log.get("document_id") or "N/A",
                    "Document Hash": log.get("document_hash", "N/A")[:16] + "..." if log.get("document_hash") else "N/A",
                    "Corrections": corrections_count,
                    "Created": log.get("created_at", "N/A")[:19] if log.get("created_at") else "N/A"  # Truncate to date/time
                })

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Show details in expanders below the table
            st.markdown("---")
            st.subheader("Detailed View")
            for log in logs:
                success_icon = "✅" if log.get("success") else "❌"
                with st.expander(f"{success_icon} Log ID: {log['id']} - {log.get('document_hash', 'N/A')[:16]}..."):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Success:** {'Yes' if log.get('success') else 'No'}")
                        st.write(f"**Document ID:** {log.get('document_id') or 'N/A'}")
                        st.write(f"**Document Hash:** {log.get('document_hash') or 'N/A'}")
                        if log.get('document_link'):
                            st.write(f"**Document Link:** {log['document_link']}")

                    with col2:
                        st.write(f"**Created:** {log.get('created_at', 'N/A')}")
                        if log.get('failure_reason'):
                            st.write(f"**Failure Reason:** {log['failure_reason']}")

                    # Show corrections if any
                    corrections = log.get('corrections_made', {})
                    if corrections:
                        st.markdown("**Corrections Made:**")
                        for field, change in corrections.items():
                            st.write(f"- **{field}:** `{change.get('original')}` → `{change.get('corrected')}`")
        else:
            st.info("No model logs in database")

    else:
        st.error(f"Error: {response.text or 'Unknown error'}")

except Exception as e:
    error_str = str(e)
    if "does not exist" in error_str.lower() or "undefinedtable" in error_str.lower():
        st.warning("⚠️ Model log table does not exist yet.")
        st.info("To create the table, run the SQL file: `infra/model_log.sql`")
    else:
        st.error(f"Error: {str(e)}")
