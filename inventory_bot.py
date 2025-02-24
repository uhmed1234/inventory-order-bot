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
    recent_transactions = transaction_df[transaction_df["Physical date"] >= five_years_ago]
    
    # Aggregate purchase and consumption data per year
    transaction_df["Year"] = transaction_df["Physical date"].dt.year
    yearly_summary = transaction_df.groupby(["Item number", "Year"])["Quantity"].sum().unstack(fill_value=0)
    
    # Ensure we have 5 years of data
    latest_year = pd.Timestamp.today().year
    for year in range(latest_year - 4, latest_year + 1):
        if year not in yearly_summary.columns:
            yearly_summary[year] = 0
    
    # Calculate annual averages
    yearly_summary["Annual Avg Purchase"] = yearly_summary.mean(axis=1)
    yearly_summary["Annual Avg Consumption"] = yearly_summary[yearly_summary.columns[-6:-1]].mean(axis=1)
    yearly_summary["Annual Max Consumption"] = yearly_summary[yearly_summary.columns[-6:-1]].max(axis=1)
    
    # Merge with on-hand data
    order_suggestions = on_hand_df[["Item number", "Product name", "Available physical", "Ordered in total"]].merge(
        yearly_summary, on="Item number", how="left"
    )
    
    # Fill NaN values with 0
    order_suggestions.fillna(0, inplace=True)
    
    # Calculate order level, safety stock, EOQ, and final order quantity
    order_suggestions["Order Level"] = order_suggestions["Annual Max Consumption"] / 12
    order_suggestions["Safety Stock"] = (order_suggestions["Order Level"] * 3)
    order_suggestions["EOQ"] = order_suggestions["Safety Stock"] - order_suggestions["Available physical"] - order_suggestions["On order quantity"]
    order_suggestions["EOQ"] = order_suggestions["EOQ"].apply(lambda x: max(0, round(x)))
    order_suggestions["Final Order Qty"] = order_suggestions["EOQ"].apply(lambda x: max(5, x) if x > 0 else 0)
    
    # Remove duplicates based on Item number
    final_order_list = order_suggestions.drop_duplicates(subset=["Item number"], keep="first")
    
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
