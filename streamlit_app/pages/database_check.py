"""Streamlit page for viewing database content."""

import streamlit as st
import requests
import os
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

st.set_page_config(page_title="Database View", layout="wide")
st.title("Database Content")

# Get documents
if st.button("Refresh"):
    safe_rerun()

try:
    response = requests.get(f"{API_BASE_URL}/documents", timeout=10)

    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        documents = data.get("documents", [])

        st.info(f"Total documents: {total}")

        if documents:
            for doc in documents:
                with st.expander(f"ID: {doc['id']} - {doc.get('filename', 'N/A')}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Tracking Number:** {doc.get('tracking_number') or 'N/A'}")
                        st.write(f"**Shipper:** {doc.get('shipper_name') or 'N/A'}")
                        st.write(f"**Receiver:** {doc.get('receiver_name') or 'N/A'}")
                        st.write(f"**Carrier:** {doc.get('carrier') or 'N/A'}")

                    with col2:
                        st.write(f"**Status:** {doc.get('status') or 'N/A'}")
                        st.write(f"**Shipment Date:** {doc.get('shipment_date') or 'N/A'}")
                        st.write(f"**Created:** {doc.get('created_at', 'N/A')}")
                        if doc.get('storage_url'):
                            st.write(f"**Storage:** {doc['storage_url']}")

                    # Display more details
                    if doc.get('shipper_address'):
                        st.write(f"**Shipper Address:** {doc['shipper_address']}")
                    if doc.get('receiver_address'):
                        st.write(f"**Receiver Address:** {doc['receiver_address']}")
                    if doc.get('weight'):
                        st.write(f"**Weight:** {doc['weight']}")
                    if doc.get('dimensions'):
                        st.write(f"**Dimensions:** {doc['dimensions']}")

                    # View full details and delete buttons
                    col_btn1, col_btn2 = st.columns(2)

                    with col_btn1:
                        if f"show_details_{doc['id']}" not in st.session_state:
                            st.session_state[f"show_details_{doc['id']}"] = False

                        if st.button(f"View Full Details", key=f"view_{doc['id']}"):
                            st.session_state[f"show_details_{doc['id']}"] = not st.session_state[f"show_details_{doc['id']}"]

                    with col_btn2:
                        if f"confirm_delete_{doc['id']}" not in st.session_state:
                            st.session_state[f"confirm_delete_{doc['id']}"] = False

                        if st.session_state[f"confirm_delete_{doc['id']}"]:
                            st.warning(f"⚠️ Are you sure you want to delete document {doc['id']}?")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("Yes, Delete", key=f"yes_delete_{doc['id']}", type="primary"):
                                    try:
                                        delete_response = requests.delete(f"{API_BASE_URL}/documents/{doc['id']}", timeout=10)
                                        if delete_response.status_code == 200:
                                            st.success(f"✅ Document {doc['id']} deleted successfully")
                                            st.session_state[f"confirm_delete_{doc['id']}"] = False
                                            safe_rerun()
                                        else:
                                            error_detail = delete_response.json().get("detail", "Unknown error") if delete_response.status_code != 200 else delete_response.text
                                            st.error(f"❌ Error: {error_detail}")
                                            st.session_state[f"confirm_delete_{doc['id']}"] = False
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                                        st.session_state[f"confirm_delete_{doc['id']}"] = False
                            with col_no:
                                if st.button("Cancel", key=f"no_delete_{doc['id']}"):
                                    st.session_state[f"confirm_delete_{doc['id']}"] = False
                                    safe_rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"delete_{doc['id']}"):
                                st.session_state[f"confirm_delete_{doc['id']}"] = True
                                safe_rerun()

                    if st.session_state[f"show_details_{doc['id']}"]:
                        try:
                            detail_response = requests.get(f"{API_BASE_URL}/documents/{doc['id']}", timeout=10)
                            if detail_response.status_code == 200:
                                detail = detail_response.json()
                                st.markdown("---")
                                st.subheader(f"Full Details - Document {doc['id']}")
                                st.json(detail)
                            else:
                                st.error("Could not fetch details")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.info("No documents in database")

    else:
        st.error(f"Error: {response.text or 'Unknown error'}")

except Exception as e:
    st.error(f"Error: {str(e)}")
