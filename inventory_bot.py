import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Convert Physical date to datetime and filter last 3 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    three_years_ago = pd.Timestamp.today() - pd.DateOffset(years=3)
    filtered_transactions = transaction_df[transaction_df["Physical date"] >= three_years_ago]
    
    # Aggregate issued quantity per item
    issued_per_item = (
        filtered_transactions.groupby("Item number")["Quantity"]
        .sum()
        .abs()
        .div(36)  # Convert to average monthly issued quantity over 3 years
    )
    
    # Merge with on-hand data
    order_suggestions = on_hand_df[["Item number", "Product name", "Available physical"]].merge(
        issued_per_item.rename("Avg Monthly Issued"), on="Item number", how="left"
    )
    
    # Fill NaN values for Avg Monthly Issued with 0 before calculations
    order_suggestions["Avg Monthly Issued"] = order_suggestions["Avg Monthly Issued"].fillna(0)
    
    # Calculate safety stock (3 months of average issued quantity)
    order_suggestions["Safety Stock"] = order_suggestions["Avg Monthly Issued"] * 3
    
    # Calculate suggested order quantity only if on-hand is below safety stock
    order_suggestions["Suggested Order Qty"] = (
        order_suggestions["Safety Stock"] - order_suggestions["Available physical"]
    ).apply(lambda x: max(0, round(x)))
    
    # Apply minimum order quantity (at least 5 units if needed)
    order_suggestions["Suggested Order Qty"] = order_suggestions["Suggested Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)
    
    # Flag items with zero usage for manual review
    order_suggestions["Flag for Review"] = order_suggestions["Avg Monthly Issued"] == 0
    
    # Keep only items that need ordering
    final_order_list = order_suggestions[order_suggestions["Suggested Order Qty"] > 0]
    
    # Remove duplicates based on Item number
    final_order_list = final_order_list.drop_duplicates(subset=["Item number"], keep="first")
    
    return final_order_list

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
