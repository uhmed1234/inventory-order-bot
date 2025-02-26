import pandas as pd
import streamlit as st
import tempfile

def process_inventory(on_hand_path, transaction_path):
    # Load data
    on_hand_df = pd.read_excel(on_hand_path)
    transaction_df = pd.read_excel(transaction_path)
    
    # Sum "Available physical" for duplicate items in on-hand list
    on_hand_df = on_hand_df.groupby(["Item number", "Product name", "Unit"], as_index=False).agg({
        "Available physical": "sum",
        "On ordered Qty": "sum"
    }).rename(columns={"Available physical": "On Hand Qty"})
    
    # Convert Physical date to datetime and filter last 5 years
    transaction_df["Physical date"] = pd.to_datetime(transaction_df["Physical date"], errors="coerce")
    five_years_ago = pd.Timestamp.today().year - 5
    transaction_df = transaction_df[transaction_df["Physical date"].dt.year >= five_years_ago]
    
    # Extract purchase and consumption data by year
    transaction_df["Year"] = transaction_df["Physical date"].dt.year
    annual_data = transaction_df.groupby(["Item number", "Year", "Transaction Type"]).agg({"Quantity": "sum"}).reset_index()
    
    # Pivot to get purchase and consumption data separately
    purchase_pivot = annual_data[annual_data["Transaction Type"] == "Purchase"].pivot(index="Item number", columns="Year", values="Quantity").fillna(0)
    consumption_pivot = annual_data[annual_data["Transaction Type"] == "Consumption"].pivot(index="Item number", columns="Year", values="Quantity").fillna(0)
    
    # Calculate annual averages and max consumption
    purchase_pivot["Annual Average Purchase"] = purchase_pivot.mean(axis=1)
    consumption_pivot["Annual Average Consumption"] = consumption_pivot.mean(axis=1)
    consumption_pivot["Annual Maximum Consumption"] = consumption_pivot.max(axis=1)
    
    # Merge with on-hand data
    result_df = on_hand_df.merge(purchase_pivot, on="Item number", how="left")
    result_df = result_df.merge(consumption_pivot, on="Item number", how="left")
    
    # Fill NaN values with 0
    result_df.fillna(0, inplace=True)
    
    # Order calculations
    result_df["Order Delivery Period (Months)"] = 2  # Example fixed period
    result_df["Order Interval per year"] = 12 / result_df["Order Delivery Period (Months)"]
    result_df["Order Level"] = result_df["Annual Average Consumption"] * (result_df["Order Delivery Period (Months)"] / 12)
    result_df["Safety Stock"] = result_df["Annual Maximum Consumption"] * 0.5  # Example safety stock formula
    result_df["Maximum Order"] = result_df["Safety Stock"] + result_df["Order Level"]
    result_df["EOQ"] = result_df["Maximum Order"] - result_df["On Hand Qty"]
    result_df["Final Order Qty"] = result_df["EOQ"].apply(lambda x: max(0, round(x)))
    
    return result_df

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
