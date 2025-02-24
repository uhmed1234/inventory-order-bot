# Compute yearly purchase and consumption
purchase_columns = ["Purchase 1st year", "Purchase 2nd year", "Purchase 3rd year", "Purchase 4th year", "Purchase 5th year"]
consumption_columns = ["Consumption 1st year", "Consumption 2nd year", "Consumption 3rd year", "Consumption 4th year", "Consumption 5th year"]

on_hand_df["Annual Avg Purchase"] = on_hand_df[purchase_columns].sum(axis=1) / 5
on_hand_df["Annual Avg Consumption"] = on_hand_df[consumption_columns].sum(axis=1) / 5
on_hand_df["Annual Max Consumption"] = on_hand_df[consumption_columns].max(axis=1)

# Calculate 3-month safety stock
on_hand_df["Safety Stock"] = (on_hand_df["Annual Max Consumption"] / 12) * 3

# Final Order Quantity Calculation
on_hand_df["Final Order Qty"] = (on_hand_df["Safety Stock"] - on_hand_df["Available physical"]).apply(lambda x: max(0, round(x)))

# Apply rounding rules
on_hand_df["Final Order Qty Rounded"] = on_hand_df["Final Order Qty"].apply(lambda x: max(5, x) if x > 0 else 0)
