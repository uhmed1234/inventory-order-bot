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
    
    # Aggregate total usage per item over 3 years
    usage_per_item = (
        filtered_transactions.groupby("Item number")["Quantity"]
        .sum()
        .abs()
    )
    
    # Merge with on-hand data
    order_suggestions = on_hand_df[["Item number", "Product name", "Available physical"]].merge(
        usage_per_item.rename("Total 3-Year Usage"), on="Item number", how="left"
    )
    
    # Fill NaN values for Total Usage with 0 before calculations
    order_suggestions["Total 3-Year Usage"] = order_suggestions["Total 3-Year Usage"].fillna(0)
    
    # Calculate average monthly usage
    order_suggestions["Avg Monthly Usage"] = order_suggestions["Total 3-Year Usage"] / 36
    
    # Identify most used items
    most_used_items = order_suggestions.sort_values(by="Avg Monthly Usage", ascending=False).head(10)
    
    # Calculate safety stock based on 3 years of average usage (e.g., 6 months of usage)
    order_suggestions["Safety Stock"] = order_suggestions["Avg Monthly Usage"] * 6
    
    # Calculate suggested order quantity
    order_suggestions["Suggested Order Qty"] = (
        order_suggestions["Safety Stock"] - order_suggestions["Available physical"]
    ).apply(lambda x: max(0, round(x)))
    
    # Apply minimum order quantity (at least 5 units if needed)
    order_suggestions["Suggested Order Qty"] = order_suggestions["Suggested Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)
    
    # Flag items with zero usage for manual review
    order_suggestions["Flag for Review"] = order_suggestions["Avg Monthly Usage"] == 0
    
    # Keep only items that need ordering
    final_order_list = order_suggestions[order_suggestions["Suggested Order Qty"] > 0]
    
    # Remove duplicates based on Item number
    final_order_list = final_order_list.drop_duplicates(subset=["Item number"], keep="first")
    
    return final_order_list, most_used_items

st.title("Inventory Order Suggestion Bot")

on_hand_file = st.file_uploader("Upload On-Hand File", type=["xlsx"])
transaction_file = st.file_uploader("Upload Transaction File", type=["xlsx"])

if on_hand_file and transaction_file:
    with tempfile.NamedTemporaryFile(delete=False) as on_hand_temp, tempfile.NamedTemporaryFile(delete=False) as transaction_temp:
        on_hand_temp.write(on_hand_file.read())
        transaction_temp.write(transaction_file.read())
        
        df_result, df_most_used = process_inventory(on_hand_temp.name, transaction_temp.name)
        
        st.write("### Order Suggestions")
        st.dataframe(df_result)
        
        st.write("### Most Used Items")
        st.dataframe(df_most_used)
        
        # Provide download option for order suggestions
        output_file = "Order_Suggestions.xlsx"
        df_result.to_excel(output_file, index=False)
        st.download_button(label="Download Order Suggestions", data=open(output_file, "rb"), file_name=output_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # Provide download option for most used items
        output_most_used_file = "Most_Used_Items.xlsx"
        df_most_used.to_excel(output_most_used_file, index=False)
        st.download_button(label="Download Most Used Items", data=open(output_most_used_file, "rb"), file_name=output_most_used_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
