import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Standardize column names to avoid merge issues
    on_hand_df.rename(columns=lambda x: x.strip(), inplace=True)
    transaction_df.rename(columns=lambda x: x.strip(), inplace=True)
    
    # Ensure "Item number" is string type for accurate merging
    on_hand_df["Item number"] = on_hand_df["Item number"].astype(str)
    transaction_df["Item number"] = transaction_df["Item number"].astype(str)
    
    # Aggregate duplicate items by summing "Available physical"
    on_hand_df = on_hand_df.groupby("Item number", as_index=False).agg(
        {"Product name": "first", "Available physical": "sum"}
    )
    
    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today() - pd.DateOffset(years=5)
    filtered_transactions = transaction_df[transaction_df["Physical date"] >= five_years_ago]
    
    # Calculate annual purchases and consumption
    transaction_summary = filtered_transactions.groupby(["Item number", "Physical date"])["Quantity"].sum().unstack(fill_value=0)
    annual_purchases = transaction_summary.where(transaction_summary > 0, 0).sum(axis=1) / 5  # Last 5 years avg
    annual_consumption = transaction_summary.where(transaction_summary < 0, 0).abs().sum(axis=1) / 5
    
    # Merge all calculations into order suggestions
    order_suggestions = on_hand_df.merge(annual_purchases.rename("Annual Avg Purchase"), on="Item number", how="left")
    order_suggestions = order_suggestions.merge(annual_consumption.rename("Annual Avg Consumption"), on="Item number", how="left")
    
    # Fill NaN values
    order_suggestions.fillna({"Annual Avg Purchase": 0, "Annual Avg Consumption": 0, "Available physical": 0}, inplace=True)
    
    # Calculate safety stock (6 months of avg consumption)
    order_suggestions["Safety Stock"] = order_suggestions["Annual Avg Consumption"] / 2
    
    # Calculate final order quantity
    order_suggestions["Final Order Qty"] = (
        order_suggestions["Safety Stock"] - order_suggestions["Available physical"]
    ).apply(lambda x: max(0, round(x)))
    
    # Apply minimum order quantity (at least 5 units if needed)
    order_suggestions["Final Order Qty"] = order_suggestions["Final Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)
    
    # Identify most used items (top 10 by consumption)
    most_used_items = order_suggestions.sort_values(by="Annual Avg Consumption", ascending=False).head(10)
    
    return order_suggestions, most_used_items

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
