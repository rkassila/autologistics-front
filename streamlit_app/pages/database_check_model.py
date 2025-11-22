"""Streamlit page for viewing model log database content."""

import streamlit as st
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

st.set_page_config(page_title="Model Log View", layout="wide")
st.title("Model Log Database Content")

# Database connection settings
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "")
db_name = os.getenv("DB_NAME", "logistics_db")
table_name = os.getenv("DB_MODEL_NAME", "model_log")

# Get model logs directly from database
if st.button("Refresh"):
    st.rerun()

try:
    # Create database connection
    if os.getenv("INSTANCE_CONNECTION_NAME"):
        # Cloud SQL Unix socket connection
        db_url = f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{os.getenv('INSTANCE_CONNECTION_NAME')}"
    else:
        # Regular TCP connection
        db_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    engine = create_engine(db_url, pool_pre_ping=True)

    # Simple SELECT query
    with engine.connect() as conn:
        try:
            query = text(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT 100")
            result = conn.execute(query)
            rows = result.fetchall()
            columns = result.keys()

            if rows:
                # Convert to DataFrame
                df = pd.DataFrame(rows, columns=columns)

                # Display summary
                st.info(f"Total model logs: {len(df)}")

                # Summary statistics
                if 'success' in df.columns:
                    success_count = df['success'].sum()
                    failure_count = len(df) - success_count

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Logs", len(df))
                    with col2:
                        st.metric("Successful", success_count, delta=f"{success_count/len(df)*100:.1f}%" if len(df) > 0 else "0%")
                    with col3:
                        st.metric("With Corrections", failure_count, delta=f"{failure_count/len(df)*100:.1f}%" if len(df) > 0 else "0%")

                # Display table
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No model logs in database")

        except Exception as e:
            error_str = str(e)
            if "does not exist" in error_str.lower() or "undefinedtable" in error_str.lower():
                st.warning(f"⚠️ Table '{table_name}' does not exist yet.")
                st.info(f"To create the table, run the SQL file: `infra/model_log.sql`")
            else:
                st.error(f"Database error: {str(e)}")

except Exception as e:
    st.error(f"Connection error: {str(e)}")
