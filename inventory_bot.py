import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Aggregate duplicate items in on-hand list by summing "Available physical"
    on_hand_df = on_hand_df.groupby("Item number", as_index=False).agg({
        "Product name": "first",
        "Available physical": "sum"
    })
    
    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today() - pd.DateOffset(years=5)
    filtered_transactions = transaction_df[transaction_df["Physical date"] >= five_years_ago]
    
    # Aggregate annual purchase and consumption per item
    annual_data = filtered_transactions.groupby(["Item number", filtered_transactions["Physical date"].dt.year])
    annual_purchase = annual_data["Purchase Quantity"].sum().unstack(fill_value=0)
    annual_consumption = annual_data["Issued Quantity"].sum().unstack(fill_value=0)
    
    # Calculate averages
    avg_purchase = annual_purchase.mean(axis=1)
    avg_consumption = annual_consumption.mean(axis=1)
    
    # Merge data
    order_suggestions = on_hand_df.merge(avg_purchase.rename("Annual Avg Purchase"), on="Item number", how="left")
    order_suggestions = order_suggestions.merge(avg_consumption.rename("Annual Avg Consumption"), on="Item number", how="left")
    
    # Fill NaN values with 0
    order_suggestions.fillna(0, inplace=True)
    
    # Calculate safety stock (6 months of average consumption)
    order_suggestions["Safety Stock"] = order_suggestions["Annual Avg Consumption"] / 2
    
    # Calculate suggested order quantity
    order_suggestions["Final Order Qty"] = (
        order_suggestions["Safety Stock"] - order_suggestions["Available physical"]
    ).apply(lambda x: max(0, round(x)))
    
    # Apply minimum order quantity (at least 5 units if needed)
    order_suggestions["Final Order Qty"] = order_suggestions["Final Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)
    
    # Identify most used items
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
