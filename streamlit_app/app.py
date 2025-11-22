"""Streamlit UI for document upload."""

import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api/v1")


def safe_rerun():
    """Safely rerun the app, using st.rerun() if available, falling back to experimental_rerun()."""
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()


def normalize_value(value):
    """Normalize a value for comparison (handle None, empty strings, dates)."""
    if value is None:
        return None
    # Handle date objects - convert to string for comparison
    if hasattr(value, 'isoformat'):  # date or datetime objects
        return value.isoformat()
    if isinstance(value, str):
        return value.strip() if value.strip() else None
    return str(value) if value else None


def compare_values(original, current):
    """Compare two values and return True if they're different."""
    orig_norm = normalize_value(original)
    curr_norm = normalize_value(current)
    return orig_norm != curr_norm


def get_corrections_made(original_fields, reviewed_fields):
    """Compare original and reviewed fields, return dict of corrections made."""
    corrections = {}
    # Check all fields in original_fields
    for field_name, original_value in original_fields.items():
        current_value = reviewed_fields.get(field_name)
        if compare_values(original_value, current_value):
            corrections[field_name] = {
                "original": original_value,
                "corrected": current_value
            }
    # Also check for new fields in reviewed_fields that weren't in original
    for field_name, current_value in reviewed_fields.items():
        if field_name not in original_fields and current_value is not None:
            # New field was added
            corrections[field_name] = {
                "original": None,
                "corrected": current_value
            }
    return corrections


st.set_page_config(page_title="Logistics Document Processor", layout="wide", page_icon="📦")
st.title("📦 Logistics Document Automation")

# Check API and database connection
if "api_status" not in st.session_state:
    st.session_state.api_status = None
if "db_status" not in st.session_state:
    st.session_state.db_status = None

# Check API health on load
try:
    health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
    if health_response.status_code == 200:
        health_data = health_response.json()
        st.session_state.api_status = "connected"
        st.session_state.db_status = health_data.get("database", "unknown")
    else:
        st.session_state.api_status = "error"
except:
    st.session_state.api_status = "disconnected"

# Display status
col1, col2 = st.columns(2)
with col1:
    if st.session_state.api_status == "connected":
        st.success("✅ API Connected")
    else:
        st.error("❌ API Disconnected")
with col2:
    if st.session_state.db_status == "connected":
        st.success("✅ Database Connected")
    else:
        st.warning("⚠️ Database Disconnected")

if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "document_hash" not in st.session_state:
    st.session_state.document_hash = None
if "filename" not in st.session_state:
    st.session_state.filename = None

# Show save success message if it exists
if st.session_state.get("save_success", False):
    st.success("✅ Document saved")
    st.session_state.save_success = False  # Clear after showing

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

# Extract
if uploaded_file and st.session_state.extracted_data is None:
    if st.button("Extract Document"):
        with st.spinner("Processing..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                response = requests.post(f"{API_BASE_URL}/extract", files=files, timeout=90)

                # Check status code first
                if response.status_code == 200:
                    response_data = response.json()
                    st.session_state.extracted_data = response_data
                    st.session_state.document_hash = response_data.get("document_hash")
                    st.session_state.filename = uploaded_file.name
                    # Store original values for comparison
                    original_fields = response_data.get("structured_fields", {})
                    st.session_state.original_fields = original_fields.copy()
                    safe_rerun()
                else:
                    # Parse error response
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", "")
                    except:
                        error_detail = response.text or "Error"

                    st.error(f"❌ {error_detail}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Review and save
if st.session_state.extracted_data:
    result = st.session_state.extracted_data
    already_exists = result.get("already_exists", False)

    if not result.get("is_valid"):
        st.error(result.get("validation_message", "Not a valid logistics document"))
        if st.button("Try Again"):
            st.session_state.extracted_data = None
            safe_rerun()
    else:
        fields = result.get("structured_fields", {})

        # Initialize original_fields if not set (for backward compatibility)
        if "original_fields" not in st.session_state:
            st.session_state.original_fields = fields.copy()

        # Show message if document already exists in DB - display BEFORE form
        if already_exists:
            st.warning("⚠️ document already in db", icon="⚠️")

        with st.form("review_form"):
            st.subheader("Review Extracted Fields")

            # Track modifications in real-time by comparing with original
            original_fields = st.session_state.original_fields

            col1, col2 = st.columns(2)

            with col1:
                # Create inputs and check for modifications
                shipper_name_val = st.text_input("Shipper Name", value=fields.get("shipper_name") or "", key="shipper_name_input")
                if compare_values(original_fields.get("shipper_name"), shipper_name_val):
                    st.caption("✏️ Modified")

                shipper_address_val = st.text_area("Shipper Address", value=fields.get("shipper_address") or "", key="shipper_address_input")
                if compare_values(original_fields.get("shipper_address"), shipper_address_val):
                    st.caption("✏️ Modified")

                receiver_name_val = st.text_input("Receiver Name", value=fields.get("receiver_name") or "", key="receiver_name_input")
                if compare_values(original_fields.get("receiver_name"), receiver_name_val):
                    st.caption("✏️ Modified")

                receiver_address_val = st.text_area("Receiver Address", value=fields.get("receiver_address") or "", key="receiver_address_input")
                if compare_values(original_fields.get("receiver_address"), receiver_address_val):
                    st.caption("✏️ Modified")

                reviewed_fields = {
                    "shipper_name": shipper_name_val,
                    "shipper_address": shipper_address_val,
                    "receiver_name": receiver_name_val,
                    "receiver_address": receiver_address_val,
                }

            with col2:
                tracking_number_val = st.text_input("Tracking Number", value=fields.get("tracking_number") or "", key="tracking_number_input")
                if compare_values(original_fields.get("tracking_number"), tracking_number_val):
                    st.caption("✏️ Modified")

                carrier_val = st.text_input("Carrier", value=fields.get("carrier") or "", key="carrier_input")
                if compare_values(original_fields.get("carrier"), carrier_val):
                    st.caption("✏️ Modified")

                weight_val = st.text_input("Weight", value=fields.get("weight") or "", key="weight_input")
                if compare_values(original_fields.get("weight"), weight_val):
                    st.caption("✏️ Modified")

                dimensions_val = st.text_input("Dimensions", value=fields.get("dimensions") or "", key="dimensions_input")
                if compare_values(original_fields.get("dimensions"), dimensions_val):
                    st.caption("✏️ Modified")

                status_val = st.text_input("Status", value=fields.get("status") or "", key="status_input")
                if compare_values(original_fields.get("status"), status_val):
                    st.caption("✏️ Modified")

                shipment_date_val = st.text_input("Shipment Date", value=str(fields.get("shipment_date")) if fields.get("shipment_date") else "", key="shipment_date_input")
                if compare_values(original_fields.get("shipment_date"), shipment_date_val):
                    st.caption("✏️ Modified")

                delivery_date_val = st.text_input("Delivery Date", value=str(fields.get("delivery_date")) if fields.get("delivery_date") else "", key="delivery_date_input")
                if compare_values(original_fields.get("delivery_date"), delivery_date_val):
                    st.caption("✏️ Modified")

                reviewed_fields.update({
                    "tracking_number": tracking_number_val,
                    "carrier": carrier_val,
                    "weight": weight_val,
                    "dimensions": dimensions_val,
                    "status": status_val,
                    "shipment_date": shipment_date_val,
                    "delivery_date": delivery_date_val,
                })

            special_instructions_val = st.text_area("Special Instructions", value=fields.get("special_instructions") or "", key="special_instructions_input")
            if compare_values(original_fields.get("special_instructions"), special_instructions_val):
                st.caption("✏️ Modified")

            reviewed_fields["special_instructions"] = special_instructions_val

            # Check for modifications and show summary (using original_fields already defined above)
            modifications = get_corrections_made(original_fields, reviewed_fields)

            if modifications:
                st.info(f"⚠️ **{len(modifications)} field(s) modified:** {', '.join(modifications.keys())}")

            col1, col2 = st.columns(2)
            with col1:
                # Disable save button if document already exists in DB
                save_btn = st.form_submit_button("Save", disabled=already_exists)
            with col2:
                cancel_btn = st.form_submit_button("Cancel")

            if save_btn:
                with st.spinner("Saving..."):
                    clean_fields = {k: (None if v == "" or (isinstance(v, str) and not v.strip()) else v)
                                  for k, v in reviewed_fields.items()}

                    # Compare original vs reviewed to determine if corrections were made
                    original_fields = st.session_state.original_fields
                    corrections_made = get_corrections_made(original_fields, clean_fields)
                    has_modifications = len(corrections_made) > 0

                    save_request = {
                        "document_hash": st.session_state.document_hash,
                        "filename": st.session_state.filename or "unknown.pdf",
                        "structured_fields": clean_fields
                    }

                    try:
                        response = requests.post(f"{API_BASE_URL}/save", json=save_request, timeout=30)

                        # Check response status
                        if response.status_code == 200:
                            response_data = response.json()
                            document_id = response_data.get("document_id")
                            storage_url = response_data.get("storage_url") or result.get("storage_url")

                            # Log extraction quality
                            quality_log_data = {
                                "success": not has_modifications,
                                "document_id": document_id,
                                "document_hash": st.session_state.document_hash,
                                "document_link": storage_url,
                                "extraction_result": result,
                                "original_values": original_fields,
                                "corrected_values": clean_fields,
                                "corrections_made": corrections_made if has_modifications else {},
                                "failure_reason": f"Manual corrections made to {len(corrections_made)} field(s): {', '.join(corrections_made.keys())}" if has_modifications else None
                            }

                            # Send model log to backend
                            try:
                                log_response = requests.post(
                                    f"{API_BASE_URL}/model-log",
                                    json=quality_log_data,
                                    timeout=10
                                )
                                if log_response.status_code != 200:
                                    print(f"Warning: Failed to log model quality: {log_response.text}")
                            except Exception as e:
                                print(f"Warning: Error logging model quality: {str(e)}")

                            # Successfully saved - clear all displayed values
                            st.session_state.extracted_data = None
                            st.session_state.document_hash = None
                            st.session_state.filename = None
                            st.session_state.original_fields = None
                            st.session_state.save_success = True
                            safe_rerun()
                        elif response.status_code == 400:
                            try:
                                error_detail = response.json().get("detail", "")
                                st.error(f"❌ Error: {error_detail}")
                            except:
                                st.error("❌ Error saving document")
                        else:
                            # For 500 or other errors - might still be saved, so check error message
                            try:
                                error_detail = response.json().get("detail", "")
                                print(f"Backend error (status {response.status_code}): {error_detail}")
                                # If error mentions save succeeded or document exists, treat as success
                                if "saved" in error_detail.lower() or "already exists" in error_detail.lower():
                                    st.session_state.extracted_data = None
                                    st.session_state.document_hash = None
                                    st.session_state.filename = None
                                    st.session_state.original_fields = None
                                    st.session_state.save_success = True
                                    safe_rerun()
                                else:
                                    # Unknown error - show warning but don't block
                                    st.warning(f"⚠️ Warning: {error_detail} - Please check if document was saved")
                            except:
                                # Can't parse error - assume it might have worked
                                print(f"Unknown error with status {response.status_code}")
                                st.warning("⚠️ Warning: Unknown error - Please check if document was saved")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            if cancel_btn:
                st.session_state.extracted_data = None
                st.session_state.document_hash = None
                st.session_state.filename = None
                st.session_state.original_fields = None
                safe_rerun()
