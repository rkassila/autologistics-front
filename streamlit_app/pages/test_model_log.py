"""Streamlit page for testing model log creation."""

import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load .env file (for local development)
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api/v1")


def safe_rerun():
    """Safely rerun the app, using st.rerun() if available, falling back to experimental_rerun()."""
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()


st.set_page_config(page_title="Test Model Log", layout="wide")
st.title("🧪 Test Model Log Creation")

st.info("This page allows you to test writing entries to the model_log table directly.")

# Form to create test log entry
with st.form("test_model_log_form"):
    st.subheader("Create Test Model Log Entry")

    col1, col2 = st.columns(2)

    with col1:
        success = st.selectbox("Success", [True, False], index=0, help="True if no corrections needed, False if corrections were made")
        document_id = st.number_input("Document ID", min_value=1, value=1, help="ID of the document in logistics_documents table")
        document_hash = st.text_input("Document Hash", value="test_hash_12345", help="Hash of the document")
        document_link = st.text_input("Document Link", value="https://example.com/test.pdf", help="Link to the document")

    with col2:
        failure_reason = st.text_input("Failure Reason", value="", help="Reason for failure (if success=False)")
        corrections_count = st.number_input("Number of Corrections", min_value=0, value=0, help="Number of fields that were corrected")

    # Sample data
    extraction_result = {
        "model": "gpt-4o-mini",
        "timestamp": datetime.now().isoformat(),
        "raw_response": "Test extraction result"
    }

    original_values = {
        "tracking_number": "TRACK123",
        "shipper_name": "Original Shipper",
        "receiver_name": "Original Receiver"
    }

    corrected_values = {
        "tracking_number": "TRACK123",
        "shipper_name": "Corrected Shipper" if not success else "Original Shipper",
        "receiver_name": "Original Receiver"
    }

    corrections_made = {}
    if not success and corrections_count > 0:
        corrections_made = {
            "shipper_name": {
                "original": "Original Shipper",
                "corrected": "Corrected Shipper"
            }
        }

    st.markdown("---")
    st.subheader("Preview Data")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.json({"extraction_result": extraction_result})
    with col2:
        st.json({"original_values": original_values})
    with col3:
        st.json({"corrected_values": corrected_values})

    if corrections_made:
        st.json({"corrections_made": corrections_made})

    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button("📝 Create Test Model Log Entry", use_container_width=True)
    with col2:
        test_save_button = st.form_submit_button("🧪 Test Save Endpoint Logic", use_container_width=True)

    if submit_button:
        with st.spinner("Creating test model log entry..."):
            try:
                # Prepare request data
                request_data = {
                    "success": success,
                    "document_id": document_id,
                    "document_hash": document_hash,
                    "document_link": document_link,
                    "extraction_result": extraction_result,
                    "original_values": original_values,
                    "corrected_values": corrected_values,
                    "corrections_made": corrections_made if corrections_made else None,
                    "failure_reason": failure_reason if not success else None
                }

                # Make API call
                response = requests.post(
                    f"{API_BASE_URL}/model-log",
                    json=request_data,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Model log created successfully!")
                    st.json(result)
                    st.balloons()
                else:
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", "Unknown error")
                        st.error(f"❌ Error: {error_detail}")
                    except:
                        st.error(f"❌ Error: {response.text or 'Unknown error'}")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    if test_save_button:
        with st.spinner("Testing save endpoint logic (direct DB write)..."):
            try:
                # Call the new test endpoint that uses the same code as save endpoint
                response = requests.post(
                    f"{API_BASE_URL}/test-model-log-save",
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Test save endpoint worked! Model log created successfully!")
                    st.json(result)
                    st.balloons()
                else:
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", "Unknown error")
                        st.error(f"❌ Error: {error_detail}")
                    except:
                        st.error(f"❌ Error: {response.text or 'Unknown error'}")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Show recent model logs
st.markdown("---")
st.subheader("Recent Model Logs")

if st.button("🔄 Refresh Logs"):
    safe_rerun()

try:
    response = requests.get(f"{API_BASE_URL}/model-logs", params={"limit": 10}, timeout=10)

    if response.status_code == 200:
        data = response.json()
        logs = data.get("logs", [])

        if logs:
            st.info(f"Showing {len(logs)} most recent logs (Total: {data.get('total', 0)})")

            for log in logs:
                success_icon = "✅" if log.get('success') else "❌"
                with st.expander(f"{success_icon} Log ID: {log.get('id')} - Document ID: {log.get('document_id')}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Success:** {log.get('success')}")
                        st.write(f"**Document ID:** {log.get('document_id')}")
                        st.write(f"**Document Hash:** {log.get('document_hash')}")
                        if log.get('document_link'):
                            st.write(f"**Document Link:** {log.get('document_link')}")

                    with col2:
                        st.write(f"**Created:** {log.get('created_at')}")
                        if log.get('corrections_made'):
                            st.write(f"**Corrections Made:** {log.get('corrections_made')}")
                        if log.get('failure_reason'):
                            st.write(f"**Failure Reason:** {log.get('failure_reason')}")
        else:
            st.info("No model logs found. Create one using the form above!")
    else:
        try:
            error_data = response.json()
            if "message" in error_data and "does not exist" in error_data.get("message", "").lower():
                st.warning("⚠️ Model log table does not exist yet.")
            else:
                st.error(f"Error: {error_data.get('detail', 'Unknown error')}")
        except:
            st.error(f"Error: {response.text or 'Unknown error'}")

except Exception as e:
    st.error(f"Error: {str(e)}")
