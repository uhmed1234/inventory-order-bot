import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Remove "Annual Max Consumption" column if it exists
    if "Annual Max Consumption" in on_hand_df.columns:
        on_hand_df = on_hand_df.drop(columns=["Annual Max Consumption"])
    
    # Handle duplicate items by summing "Available physical"
    on_hand_df = on_hand_df.groupby(["Item number", "Product name"], as_index=False).agg({"Available physical": "sum", "Ordered in total": "sum"})
    
    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today() - pd.DateOffset(years=5)
    filtered_transactions = transaction_df[transaction_df["Physical date"] >= five_years_ago]
    
    # Aggregate yearly purchase and consumption per item
    purchase_per_year = filtered_transactions[filtered_transactions["Quantity"] > 0].groupby(["Item number", filtered_transactions["Physical date"].dt.year])["Quantity"].sum().unstack(fill_value=0)
    consumption_per_year = filtered_transactions[filtered_transactions["Quantity"] < 0].groupby(["Item number", filtered_transactions["Physical date"].dt.year])["Quantity"].sum().abs().unstack(fill_value=0)
    
    # Calculate annual averages
    purchase_per_year["Annual Avg Purchase"] = purchase_per_year.mean(axis=1)
    consumption_per_year["Annual Avg Consumption"] = consumption_per_year.mean(axis=1)
    
    # Merge with on-hand data
    order_suggestions = on_hand_df.merge(purchase_per_year, on="Item number", how="left").merge(consumption_per_year, on="Item number", how="left")
    
    # Fill NaN values for missing data
    order_suggestions.fillna(0, inplace=True)
    
    # Calculate safety stock (3 months of annual average consumption)
    order_suggestions["Safety Stock"] = order_suggestions["Annual Avg Consumption"] / 4
    
    # Calculate final order quantity (ensuring at least 3 months of safety stock)
    order_suggestions["Final Order Qty"] = (order_suggestions["Safety Stock"] - order_suggestions["Available physical"]).apply(lambda x: max(0, round(x)))
    
    # Apply minimum order quantity (at least 5 units if needed)
    order_suggestions["Final Order Qty"] = order_suggestions["Final Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)
    
    # Keep only items that need ordering
    final_order_list = order_suggestions[order_suggestions["Final Order Qty"] > 0]
    
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
