import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)

    # Print available columns for debugging
    print("On-Hand Data Columns:", on_hand_df.columns.tolist())
    print("Transaction Data Columns:", transaction_df.columns.tolist())

    # Ensure required columns exist before processing
    required_on_hand_cols = ["Item number", "Product name", "Unit", "Available physical", "On ordered Qty"]
    missing_on_hand_cols = [col for col in required_on_hand_cols if col not in on_hand_df.columns]

    if missing_on_hand_cols:
        raise KeyError(f"Missing columns in On-Hand file: {missing_on_hand_cols}")

    # Sum "Available physical" for duplicate items in on-hand list
    on_hand_df = on_hand_df.groupby(["Item number", "Product name", "Unit"], as_index=False).agg({
        "Available physical": "sum",
        "On ordered Qty": "sum"
    }).rename(columns={"Available physical": "On Hand Qty"})

    # Ensure "Physical date" column exists in transaction data
    if "Physical date" not in transaction_df.columns:
        raise KeyError("Missing 'Physical date' column in Transaction file.")

    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today().year - 5
    transaction_df = transaction_df[transaction_df["Physical date"].dt.year >= five_years_ago]

    return on_hand_df  # Returning only on-hand data for now to verify the fix

st.title("Inventory Order Suggestion Bot")

on_hand_file = st.file_uploader("Upload On-Hand File", type=["xlsx"])
transaction_file = st.file_uploader("Upload Transaction File", type=["xlsx"])

if on_hand_file and transaction_file:
    with tempfile.NamedTemporaryFile(delete=False) as on_hand_temp, tempfile.NamedTemporaryFile(delete=False) as transaction_temp:
        on_hand_temp.write(on_hand_file.read())
        transaction_temp.write(transaction_file.read())

        try:
            df_result = process_inventory(on_hand_temp.name, transaction_temp.name)
            st.write("### Order Suggestions")
            st.dataframe(df_result)
        except KeyError as e:
            st.error(f"Error: {e}")
