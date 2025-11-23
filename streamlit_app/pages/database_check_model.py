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
        total = data.get("total", 0)
        logs = data.get("logs", [])

        # Check if there's a message about table not existing
        if "message" in data and "does not exist" in data.get("message", "").lower():
            st.warning("⚠️ Model log table does not exist yet.")
            st.info("To create the table, run the SQL file: `infra/model_log.sql`")
        else:
            st.info(f"Total model logs: {total}")

            if logs:
                # Convert to DataFrame for easier display
                df = pd.DataFrame(logs)

                # Summary statistics
                if 'success' in df.columns:
                    success_count = df['success'].sum()
                    failure_count = len(df) - success_count

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Logs", total)
                    with col2:
                        st.metric("Successful", success_count, delta=f"{success_count/len(df)*100:.1f}%" if len(df) > 0 else "0%")
                    with col3:
                        st.metric("With Corrections", failure_count, delta=f"{failure_count/len(df)*100:.1f}%" if len(df) > 0 else "0%")

                # Display logs in expandable sections
                for log in logs:
                    log_id = log.get('id', 'N/A')
                    success = log.get('success', False)
                    success_icon = "✅" if success else "❌"
                    success_text = "Success" if success else "Failure"

                    with st.expander(f"{success_icon} ID: {log_id} - {success_text}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Document ID:** {log.get('document_id') or 'N/A'}")
                            st.write(f"**Document Hash:** {log.get('document_hash') or 'N/A'}")
                            st.write(f"**Success:** {success}")
                            if log.get('document_link'):
                                st.write(f"**Document Link:** {log['document_link']}")

                        with col2:
                            st.write(f"**Created:** {log.get('created_at', 'N/A')}")
                            if log.get('corrections_made'):
                                st.write(f"**Corrections Made:** {log['corrections_made']}")
                            if log.get('failure_reason'):
                                st.write(f"**Failure Reason:** {log['failure_reason']}")

                        # View full details button
                        if f"show_details_{log_id}" not in st.session_state:
                            st.session_state[f"show_details_{log_id}"] = False

                        if st.button(f"View Full Details", key=f"view_{log_id}"):
                            st.session_state[f"show_details_{log_id}"] = not st.session_state[f"show_details_{log_id}"]

                        if st.session_state[f"show_details_{log_id}"]:
                            try:
                                detail_response = requests.get(f"{API_BASE_URL}/model-logs/{log_id}", timeout=10)
                                if detail_response.status_code == 200:
                                    detail = detail_response.json()
                                    st.markdown("---")
                                    st.subheader(f"Full Details - Model Log {log_id}")
                                    st.json(detail)
                                else:
                                    st.error("Could not fetch details")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                # Also show as a table for quick overview
                st.markdown("---")
                st.subheader("Table View")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No model logs in database")

    elif response.status_code == 404:
        error_data = response.json()
        error_detail = error_data.get("detail", "")
        if "does not exist" in error_detail.lower():
            st.warning("⚠️ Model log table does not exist yet.")
            st.info("To create the table, run the SQL file: `infra/model_log.sql`")
        else:
            st.error(f"Error: {error_detail}")
    else:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", response.text or "Unknown error")
        except:
            error_detail = response.text or "Unknown error"
        st.error(f"Error: {error_detail}")

except Exception as e:
    st.error(f"Error: {str(e)}")
