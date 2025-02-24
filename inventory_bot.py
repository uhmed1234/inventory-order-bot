import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Ensure required columns exist in On-Hand File
    required_columns = ["Item number", "Product name", "Available physical", "On order quantity",
                        "Purchase 1st year", "Purchase 2nd year", "Purchase 3rd year", 
                        "Purchase 4th year", "Purchase 5th year",
                        "Consumption 1st year", "Consumption 2nd year", "Consumption 3rd year", 
                        "Consumption 4th year", "Consumption 5th year"]
    
    missing_columns = [col for col in required_columns if col not in on_hand_df.columns]
    if missing_columns:
        raise KeyError(f"Missing columns in On-Hand file: {missing_columns}")

    # Compute yearly purchase and consumption
    purchase_columns = ["Purchase 1st year", "Purchase 2nd year", "Purchase 3rd year", "Purchase 4th year", "Purchase 5th year"]
    consumption_columns = ["Consumption 1st year", "Consumption 2nd year", "Consumption 3rd year", "Consumption 4th year", "Consumption 5th year"]

    on_hand_df["Annual Avg Purchase"] = on_hand_df[purchase_columns].sum(axis=1) / 5
    on_hand_df["Annual Avg Consumption"] = on_hand_df[consumption_columns].sum(axis=1) / 5
    on_hand_df["Annual Max Consumption"] = on_hand_df[consumption_columns].max(axis=1)

    # Calculate 3-month safety stock
    on_hand_df["Safety Stock"] = (on_hand_df["Annual Max Consumption"] / 12) * 3

    # Calculate Final Order Quantity based on 3-month safety stock
    on_hand_df["Final Order Qty"] = (on_hand_df["Safety Stock"] - on_hand_df["Available physical"]).apply(lambda x: max(0, round(x)))

    # Apply rounding rules (minimum order quantity of 5 if greater than 0)
    on_hand_df["Final Order Qty Rounded"] = on_hand_df["Final Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)

    # Return the final order list
    return on_hand_df

st.title("Inventory Order Suggestion Bot")

on_hand_file = st.file_uploader("Upload On-Hand File", type=["xlsx"])
transaction_file = st.file_uploader("Upload Transaction File", type=["xlsx"])

if on_hand_file and transaction_file:
    with tempfile.NamedTemporaryFile(delete=False) as on_hand_temp, tempfile.NamedTemporaryFile(delete=False) as transaction_temp:
        on_hand_temp.write(on_hand_file.read())
        transaction_temp.write(transaction_file.read())
        
        df_result = process_inventory(on_hand_temp.name, transaction_temp.name)
        
        st.write("### Order Suggestions")
        st.dataframe(df_result)

        # Provide download option for order suggestions
        output_file = "Order_Suggestions.xlsx"
        df_result.to_excel(output_file, index=False)
        st.download_button(label="Download Order Suggestions", data=open(output_file, "rb"), file_name=output_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


