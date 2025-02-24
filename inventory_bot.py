import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today() - pd.DateOffset(years=5)
    filtered_transactions = transaction_df[transaction_df["Physical date"] >= five_years_ago]
    
    # Aggregate yearly purchase and consumption per item
    filtered_transactions["Year"] = filtered_transactions["Physical date"].dt.year
    purchase_per_year = filtered_transactions[filtered_transactions["Quantity"] > 0].groupby(["Item number", "Year"])["Quantity"].sum().unstack().fillna(0)
    consumption_per_year = filtered_transactions[filtered_transactions["Quantity"] < 0].groupby(["Item number", "Year"])["Quantity"].sum().abs().unstack().fillna(0)
    
    # Merge with on-hand data
    order_suggestions = on_hand_df[["Item number", "Product name", "Available physical", "On order quantity"]].merge(
        purchase_per_year, on="Item number", how="left"
    ).merge(
        consumption_per_year, on="Item number", how="left", suffixes=("_Purchase", "_Consumption")
    ).fillna(0)
    
    # Calculate annual averages
    order_suggestions["Annual Avg Purchase"] = purchase_per_year.mean(axis=1)
    order_suggestions["Annual Avg Consumption"] = consumption_per_year.mean(axis=1)
    
    # Calculate Annual Maximum Consumption
    order_suggestions["Annual Max Consumption"] = consumption_per_year.max(axis=1)
    
    # Set Order Delivery Period (Months) and Order Interval per Year (assumed to be 12 months / period)
    order_suggestions["Order Delivery Period (Months)"] = 3  # Assuming a default value of 3 months
    order_suggestions["Order Interval per Year"] = 12 / order_suggestions["Order Delivery Period (Months)"]
    
    # Calculate Order Level
    order_suggestions["Order Level"] = order_suggestions["Annual Max Consumption"] / order_suggestions["Order Interval per Year"]
    
    # Calculate Safety Stock
    order_suggestions["Safety Stock"] = (order_suggestions["Annual Max Consumption"] / 12) * order_suggestions["Order Delivery Period (Months)"]
    
    # Calculate Maximum Order
    order_suggestions["Maximum Order"] = order_suggestions["Annual Max Consumption"] * 1.5  # Assuming a factor
    
    # Calculate EOQ
    order_suggestions["EOQ"] = (order_suggestions["Maximum Order"] + order_suggestions["Safety Stock"] - order_suggestions["Available physical"] - order_suggestions["On order quantity"]).apply(lambda x: max(0, x))
    
    # Apply Adjustments (New Forecasts, set to 0 for now)
    order_suggestions["Adjustments (New Forecasts)"] = 0
    
    # Calculate Optimum Order
    order_suggestions["Optimum Order"] = order_suggestions[["EOQ", "Adjustments (New Forecasts)"]].sum(axis=1)
    
    # Set Minimum Order (Supplier Requirement)
    order_suggestions["Minimum Order"] = 5  # Default minimum order quantity
    
    # Calculate Final Order Qty
    order_suggestions["Final Order Qty"] = order_suggestions[["Optimum Order", "Minimum Order"]].max(axis=1)
    
    # Round Up Final Order Qty
    order_suggestions["Final Order Qty (Rounded)"] = order_suggestions["Final Order Qty"].apply(lambda x: max(5, round(x)))
    
    # Keep only items that need ordering
    final_order_list = order_suggestions[order_suggestions["Final Order Qty (Rounded)"] > 0]
    # Compute yearly purchase and consumption
   
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
       


