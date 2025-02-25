import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Sum "Available physical" for duplicate items in on-hand list
    on_hand_df = on_hand_df.groupby(["Item number", "Product name"], as_index=False).agg({"Available physical": "sum"})
    
    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today() - pd.DateOffset(years=5)
    filtered_transactions = transaction_df[transaction_df["Physical date"] >= five_years_ago]
    
    # Extract annual purchase and consumption data
    filtered_transactions["Year"] = filtered_transactions["Physical date"].dt.year
    annual_data = filtered_transactions.groupby(["Item number", "Year"]).agg({
        "Quantity": "sum"
    }).reset_index()
    
    # Pivot data to get last 5 years' purchase and consumption
    annual_pivot = annual_data.pivot(index="Item number", columns="Year", values="Quantity").fillna(0)
    
    # Calculate annual averages
    annual_pivot["Annual Avg Purchase"] = annual_pivot.mean(axis=1)
    annual_pivot["Annual Avg Consumption"] = annual_pivot.mean(axis=1)
    
    # Merge with on-hand data
    order_suggestions = on_hand_df.merge(
        annual_pivot, on="Item number", how="left"
    )
    
    # Fill NaN values with 0
    order_suggestions.fillna(0, inplace=True)
    
    # Calculate safety stock (6 months of average consumption)
    order_suggestions["Safety Stock"] = order_suggestions["Annual Avg Consumption"] * 6 / 12
    
    # Calculate EOQ and final order quantity
    order_suggestions["EOQ"] = order_suggestions["Safety Stock"] - order_suggestions["Available physical"]
    order_suggestions["Final Order Qty"] = order_suggestions["EOQ"].apply(lambda x: max(0, round(x)))
    
    return order_suggestions

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
