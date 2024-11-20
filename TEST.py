import streamlit as st
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd  # เพิ่มการนำเข้า pandas

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Decision Making with Lagrangian", page_icon="🎲", layout="wide")

st.title("🎲 Decision Making with Lagrangian")
st.subheader("Optimize Your Decision Considering Others")

st.markdown("""
Welcome to the **Decision Making Tool using Lagrangian Method**! You can input your own functions and constraints to find the optimal decision under the uncertainty of others.

Please define your problem below.
""")

# Sidebar for input
st.sidebar.title("🔢 Define Your Problem")

# Input decision variable for the main player
st.sidebar.markdown("### Main Player")
decision_var = st.sidebar.text_input("Variable xA ", value="xA")

# Objective Function
# สำหรับ Lagrangian ตามที่คุณต้องการ: LA(xA,xB,λ ) = -10 + λ (20-xA -xB)
obj_function = st.sidebar.text_input(f"Objective Function u({decision_var}, other_decision)", value=f"-10")

# Other Player's Decision
st.sidebar.markdown("### Other Player")
other_decision_var = st.sidebar.text_input("Variable xB ", value="xB")
other_decision_values = st.sidebar.text_input(f"Possible Values for {other_decision_var} (comma-separated)", value="10,20,0,5")
other_decision_probs = st.sidebar.text_input(f"Probabilities for {other_decision_var} (comma-separated)", value="0.25,0.25,0.25,0.25")  # ความน่าจะเป็นเท่าๆ กันสำหรับสี่กรณี

# Constraints
st.sidebar.markdown("### Constraints")
num_constraints = st.sidebar.number_input("Number of Constraints", min_value=1, max_value=5, value=1, step=1)
constraints = []
for j in range(int(num_constraints)):
    constraint = st.sidebar.text_input(f"Constraint {j+1} (e.g., 20 - {decision_var} - {other_decision_var})", value=f"20 - {decision_var} - {other_decision_var}")
    constraints.append(constraint)

# Main content
st.markdown("## 📋 Problem Definition")

st.markdown("### Variables:")
st.write(f"- **{decision_var}** ")
st.write(f"- **{other_decision_var}** ")

st.markdown("### Objective Function:")
obj_expr = parse_expr(obj_function)
st.latex(r"u(" + f"{decision_var}, {other_decision_var}" + r") = " + sp.latex(obj_expr))

st.markdown("### Other Player's Possible Decisions:")
other_decision_vals = [val.strip() for val in other_decision_values.split(',')]
try:
    other_decision_probs_list = [float(p.strip()) for p in other_decision_probs.split(',')]
except ValueError:
    st.error("Please enter valid numerical probabilities for the other player's decisions.")
    st.stop()

if len(other_decision_vals) != len(other_decision_probs_list):
    st.error("The number of possible values and probabilities for the other player's decision must be the same.")
    st.stop()
if not np.isclose(sum(other_decision_probs_list), 1.0):
    st.error("The probabilities for the other player's decision must sum to 1.")
    st.stop()
st.write(f"- **Possible Values for {other_decision_var}**: {other_decision_vals}")
st.write(f"- **Probabilities**: {other_decision_probs_list}")

st.markdown("### Constraints:")
for j, constraint in enumerate(constraints):
    st.latex(rf"{constraint} = 0")

st.markdown("## 🔍 Calculating Optimal Decision")

# Define the four cases as per user
cases = [
    {"xA": 10, "xB": 10, "Description": "Case 1: Both A and B confess"},
    {"xA": 0, "xB": 20, "Description": "Case 2: A does not confess, B confesses"},
    {"xA": 20, "xB": 0, "Description": "Case 3: A confesses, B does not confess"},
    {"xA": 5, "xB": 5, "Description": "Case 4: Both A and B do not confess"}
]

# Prepare the constraint expression
try:
    # Assuming only one constraint; if multiple, handle accordingly
    constraint_expr = parse_expr(constraints[0], evaluate=False)
except Exception as e:
    st.error(f"Error parsing constraint equation: {e}")
    st.stop()

# Symbols for variables
xA_sym = sp.Symbol(decision_var)
xB_sym = sp.Symbol(other_decision_var)
lambda_sym = sp.Symbol('λ')  # ใช้สัญลักษณ์ลัมบ์ดา

# Define the Lagrangian function
try:
    # Parse the objective function
    lagrangian = obj_expr + lambda_sym * constraint_expr
except Exception as e:
    st.error(f"Error parsing Lagrangian: {e}")
    st.stop()

st.markdown("### Lagrangian Function:")
st.latex(r"L(" + f"{decision_var}, {other_decision_var}, \lambda" + r") = " + sp.latex(lagrangian))

# Calculate partial derivative w.r.t xA
partial_derivative = sp.diff(lagrangian, xA_sym)
st.markdown("### Partial Derivative w.r.t Decision Variable:")
st.latex(r"\frac{\partial L}{\partial " + f"{decision_var}" + r"} = " + sp.latex(partial_derivative) + r" = 0")

# Function to evaluate constraint using sympy.lambdify
constraint_func = sp.lambdify((xA_sym, xB_sym), constraint_expr, 'numpy')

# Create a DataFrame-like list to store results
results = []

for case in cases:
    xA_value = case["xA"]
    xB_value = case["xB"]
    description = case["Description"]
    try:
        result = constraint_func(xA_value, xB_value)
        is_satisfied = abs(result) < 1e-6
        results.append({
            "Description": description,
            "xA ": xA_value,
            "xB ": xB_value,
            "Constraint Result": result,
            "Satisfied": is_satisfied
        })
    except Exception as e:
        st.error(f"Error evaluating constraint for {description}: {e}")
        st.stop()

# Display the results in a table
st.markdown("### Results:")
result_df = pd.DataFrame(results)
result_df["Satisfied"] = result_df["Satisfied"].apply(lambda x: "✅ Yes" if x else "❌ No")
st.table(result_df.style.applymap(lambda x: 'background-color: lightgreen' if x == "✅ Yes" else 'background-color: salmon', subset=["Satisfied"]))

# Visualization


st.markdown("""
---
Built with **Python**, **SymPy**, **Streamlit**, **Matplotlib**, and **Pandas** for a comprehensive and interactive experience 🎉
""")
