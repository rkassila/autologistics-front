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


def get_modified_fields(original_fields, current_fields):
    """Get list of field names that have been modified."""
    modified = []
    # Only compare fields that are actually in the form (current_fields)
    # Don't check fields that exist in original but aren't editable in the form
    for field_name in current_fields.keys():
        original_value = original_fields.get(field_name)
        current_value = current_fields.get(field_name)
        if compare_values(original_value, current_value):
            modified.append(field_name)
    return modified


st.set_page_config(page_title="Logistics Document Processor", layout="wide", page_icon="📦")
st.title("📦 Logistics Document Automation")

# Check API and database connection
if "api_status" not in st.session_state:
    st.session_state.api_status = None
if "db_status" not in st.session_state:
    st.session_state.db_status = None
if "bucket_status" not in st.session_state:
    st.session_state.bucket_status = None
if "model_log_db_status" not in st.session_state:
    st.session_state.model_log_db_status = None

# Check API health on load
try:
    health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
    if health_response.status_code == 200:
        health_data = health_response.json()
        st.session_state.api_status = "connected"
        st.session_state.db_status = health_data.get("database", "unknown")
        st.session_state.bucket_status = health_data.get("bucket", "unknown")
        st.session_state.model_log_db_status = health_data.get("model_log_db", "unknown")
    else:
        st.session_state.api_status = "error"
except:
    st.session_state.api_status = "disconnected"

# Display status - 4 checks in 2x2 grid
col1, col2 = st.columns(2)
with col1:
    if st.session_state.api_status == "connected":
        st.success("✅ API Connected")
    else:
        st.error("❌ API Disconnected")

    if st.session_state.db_status == "connected":
        st.success("✅ Database Connected")
    elif st.session_state.db_status == "disconnected":
        st.warning("⚠️ Database Disconnected")
    else:
        st.info("ℹ️ Database Status Unknown")

with col2:
    if st.session_state.bucket_status == "connected":
        st.success("✅ Bucket Connected")
    elif st.session_state.bucket_status == "not_configured":
        st.info("ℹ️ Bucket Not Configured")
    elif st.session_state.bucket_status == "disconnected":
        st.warning("⚠️ Bucket Disconnected")
    else:
        st.info("ℹ️ Bucket Status Unknown")

    if st.session_state.model_log_db_status == "connected":
        st.success("✅ Model Log DB Connected")
    elif st.session_state.model_log_db_status == "disconnected":
        st.warning("⚠️ Model Log DB Disconnected")
    else:
        st.info("ℹ️ Model Log DB Status Unknown")

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

        # Initialize current_fields to track form values
        if "current_fields" not in st.session_state:
            st.session_state.current_fields = fields.copy()

        # Show message if document already exists in DB - display BEFORE form
        if already_exists:
            st.warning("⚠️ document already in db", icon="⚠️")

        # Get original fields for comparison
        original_fields = st.session_state.original_fields
        current_fields = st.session_state.current_fields

        with st.form("review_form"):
            st.subheader("Review Extracted Fields")

            # Add a tip for users
            st.caption("💡 Tip: Make your changes, then click 'Check Modifications' to see what changed, or click 'Save' to save directly")

            col1, col2 = st.columns(2)

            with col1:
                # Use current_fields as default, fallback to fields
                shipper_name_val = st.text_input(
                    "Shipper Name",
                    value=current_fields.get("shipper_name") or fields.get("shipper_name") or "",
                    disabled=already_exists,
                    key="shipper_name_input"
                )
                if compare_values(original_fields.get("shipper_name"), shipper_name_val):
                    st.caption("✏️ Modified")

                shipper_address_val = st.text_area(
                    "Shipper Address",
                    value=current_fields.get("shipper_address") or fields.get("shipper_address") or "",
                    disabled=already_exists,
                    key="shipper_address_input"
                )
                if compare_values(original_fields.get("shipper_address"), shipper_address_val):
                    st.caption("✏️ Modified")

                receiver_name_val = st.text_input(
                    "Receiver Name",
                    value=current_fields.get("receiver_name") or fields.get("receiver_name") or "",
                    disabled=already_exists,
                    key="receiver_name_input"
                )
                if compare_values(original_fields.get("receiver_name"), receiver_name_val):
                    st.caption("✏️ Modified")

                receiver_address_val = st.text_area(
                    "Receiver Address",
                    value=current_fields.get("receiver_address") or fields.get("receiver_address") or "",
                    disabled=already_exists,
                    key="receiver_address_input"
                )
                if compare_values(original_fields.get("receiver_address"), receiver_address_val):
                    st.caption("✏️ Modified")

                reviewed_fields = {
                    "shipper_name": shipper_name_val,
                    "shipper_address": shipper_address_val,
                    "receiver_name": receiver_name_val,
                    "receiver_address": receiver_address_val,
                }

            with col2:
                tracking_number_val = st.text_input(
                    "Tracking Number",
                    value=current_fields.get("tracking_number") or fields.get("tracking_number") or "",
                    disabled=already_exists,
                    key="tracking_number_input"
                )
                if compare_values(original_fields.get("tracking_number"), tracking_number_val):
                    st.caption("✏️ Modified")

                carrier_val = st.text_input(
                    "Carrier",
                    value=current_fields.get("carrier") or fields.get("carrier") or "",
                    disabled=already_exists,
                    key="carrier_input"
                )
                if compare_values(original_fields.get("carrier"), carrier_val):
                    st.caption("✏️ Modified")

                weight_val = st.text_input(
                    "Weight",
                    value=current_fields.get("weight") or fields.get("weight") or "",
                    disabled=already_exists,
                    key="weight_input"
                )
                if compare_values(original_fields.get("weight"), weight_val):
                    st.caption("✏️ Modified")

                dimensions_val = st.text_input(
                    "Dimensions",
                    value=current_fields.get("dimensions") or fields.get("dimensions") or "",
                    disabled=already_exists,
                    key="dimensions_input"
                )
                if compare_values(original_fields.get("dimensions"), dimensions_val):
                    st.caption("✏️ Modified")

                status_val = st.text_input(
                    "Status",
                    value=current_fields.get("status") or fields.get("status") or "",
                    disabled=already_exists,
                    key="status_input"
                )
                if compare_values(original_fields.get("status"), status_val):
                    st.caption("✏️ Modified")

                shipment_date_val = st.text_input(
                    "Shipment Date",
                    value=current_fields.get("shipment_date") or (str(fields.get("shipment_date")) if fields.get("shipment_date") else ""),
                    disabled=already_exists,
                    key="shipment_date_input"
                )
                if compare_values(original_fields.get("shipment_date"), shipment_date_val):
                    st.caption("✏️ Modified")

                delivery_date_val = st.text_input(
                    "Delivery Date",
                    value=current_fields.get("delivery_date") or (str(fields.get("delivery_date")) if fields.get("delivery_date") else ""),
                    disabled=already_exists,
                    key="delivery_date_input"
                )
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

            special_instructions_val = st.text_area(
                "Special Instructions",
                value=current_fields.get("special_instructions") or fields.get("special_instructions") or "",
                disabled=already_exists,
                key="special_instructions_input"
            )
            if compare_values(original_fields.get("special_instructions"), special_instructions_val):
                st.caption("✏️ Modified")

            reviewed_fields["special_instructions"] = special_instructions_val

            # Update current_fields with form values
            st.session_state.current_fields = reviewed_fields.copy()

            # Check for modifications
            modified_fields = get_modified_fields(original_fields, reviewed_fields)

            # Form action buttons
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                # Button to check modifications (triggers form submission and shows summary)
                check_btn = st.form_submit_button("🔍 Check Modifications", disabled=already_exists, use_container_width=True)
            with col2:
                # Disable save button if document already exists in DB
                save_btn = st.form_submit_button("💾 Save", disabled=already_exists, use_container_width=True)
            with col3:
                # Button to save to model_log database
                save_model_log_btn = st.form_submit_button("📊 Save to Model Log", disabled=already_exists, use_container_width=True)
            with col4:
                # Button that saves model log first, then saves document
                save_both_btn = st.form_submit_button("💾📊 Save All", disabled=already_exists, use_container_width=True)
            with col5:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

            # Display modification summary after form submission
            if check_btn or save_btn:
                if modified_fields:
                    st.markdown("---")
                    st.warning(f"✏️ **{len(modified_fields)} field(s) modified:** {', '.join(modified_fields)}")
                    # Show details of what changed
                    with st.expander("View Modification Details"):
                        for field in modified_fields:
                            orig_val = original_fields.get(field, "None")
                            curr_val = reviewed_fields.get(field, "None")
                            st.write(f"**{field}:**")
                            st.write(f"  - Original: `{orig_val}`")
                            st.write(f"  - Current: `{curr_val}`")
                else:
                    st.markdown("---")
                    st.success("✅ No modifications detected - all fields match original extraction")

            if save_btn:
                with st.spinner("Saving..."):
                    clean_fields = {k: (None if v == "" or (isinstance(v, str) and not v.strip()) else v)
                                  for k, v in reviewed_fields.items()}

                    save_request = {
                        "document_hash": st.session_state.document_hash,
                        "filename": st.session_state.filename or "unknown.pdf",
                        "structured_fields": clean_fields
                    }

                    try:
                        response = requests.post(f"{API_BASE_URL}/save", json=save_request, timeout=30)

                        # Check response status
                        if response.status_code == 200:
                            # Successfully saved - clear all displayed values
                            st.session_state.extracted_data = None
                            st.session_state.document_hash = None
                            st.session_state.filename = None
                            st.session_state.original_fields = None
                            st.session_state.current_fields = None
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

            if save_model_log_btn:
                with st.spinner("Saving to model log..."):
                    try:
                        # Prepare request with real document data
                        result = st.session_state.extracted_data
                        save_model_log_request = {
                            "document_hash": st.session_state.document_hash,
                            "original_fields": original_fields,
                            "reviewed_fields": reviewed_fields,
                            "additional_data": result.get("additional_data", {}),
                            "storage_url": result.get("storage_url")
                        }

                        # Call the endpoint that saves to model_log
                        response = requests.post(f"{API_BASE_URL}/test-model-log-save", json=save_model_log_request, timeout=30)

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Saved to model log! Log ID: {result.get('log_id')}")
                        else:
                            try:
                                error_detail = response.json().get("detail", "Unknown error")
                                st.error(f"❌ Error: {error_detail}")
                            except:
                                st.error(f"❌ Error: {response.text or 'Unknown error'}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            if save_both_btn:
                with st.spinner("Saving model log and document..."):
                    try:
                        # Step 1: Save to model_log first
                        result = st.session_state.extracted_data
                        save_model_log_request = {
                            "document_hash": st.session_state.document_hash,
                            "original_fields": original_fields,
                            "reviewed_fields": reviewed_fields,
                            "additional_data": result.get("additional_data", {}),
                            "storage_url": result.get("storage_url")
                        }

                        model_log_response = requests.post(f"{API_BASE_URL}/test-model-log-save", json=save_model_log_request, timeout=30)

                        if model_log_response.status_code != 200:
                            try:
                                error_detail = model_log_response.json().get("detail", "Unknown error")
                                st.error(f"❌ Error saving model log: {error_detail}")
                            except:
                                st.error(f"❌ Error saving model log: {model_log_response.text or 'Unknown error'}")
                            # Don't continue to document save if model log failed
                        else:
                            # Step 2: Save document
                            clean_fields = {k: (None if v == "" or (isinstance(v, str) and not v.strip()) else v)
                                          for k, v in reviewed_fields.items()}

                            save_request = {
                                "document_hash": st.session_state.document_hash,
                                "filename": st.session_state.filename or "unknown.pdf",
                                "structured_fields": clean_fields
                            }

                            doc_response = requests.post(f"{API_BASE_URL}/save", json=save_request, timeout=30)

                            # Check response status
                            if doc_response.status_code == 200:
                                # Successfully saved both - clear all displayed values
                                st.session_state.extracted_data = None
                                st.session_state.document_hash = None
                                st.session_state.filename = None
                                st.session_state.original_fields = None
                                st.session_state.current_fields = None
                                st.session_state.save_success = True
                                safe_rerun()
                            elif doc_response.status_code == 400:
                                try:
                                    error_detail = doc_response.json().get("detail", "")
                                    st.error(f"❌ Error saving document: {error_detail}")
                                except:
                                    st.error("❌ Error saving document")
                            else:
                                # For 500 or other errors - might still be saved, so check error message
                                try:
                                    error_detail = doc_response.json().get("detail", "")
                                    print(f"Backend error (status {doc_response.status_code}): {error_detail}")
                                    # If error mentions save succeeded or document exists, treat as success
                                    if "saved" in error_detail.lower() or "already exists" in error_detail.lower():
                                        st.session_state.extracted_data = None
                                        st.session_state.document_hash = None
                                        st.session_state.filename = None
                                        st.session_state.save_success = True
                                        safe_rerun()
                                    else:
                                        # Unknown error - show warning but don't block
                                        st.warning(f"⚠️ Warning: {error_detail} - Please check if document was saved")
                                except:
                                    # Can't parse error - assume it might have worked
                                    print(f"Unknown error with status {doc_response.status_code}")
                                    st.warning("⚠️ Warning: Unknown error - Please check if document was saved")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            if cancel_btn:
                st.session_state.extracted_data = None
                st.session_state.document_hash = None
                st.session_state.filename = None
                st.session_state.original_fields = None
                safe_rerun()
