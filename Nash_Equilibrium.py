import streamlit as st
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
import numpy as np

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
decision_var = st.sidebar.text_input("Decision Variable", value="xA")

# Objective Function
obj_function = st.sidebar.text_input(f"Objective Function u({decision_var}, other_decision)", value=f"-10*{decision_var}")

# Other Player's Decision
st.sidebar.markdown("### Other Player")
other_decision_var = st.sidebar.text_input("Other Player's Decision Variable", value="xB")
other_decision_values = st.sidebar.text_input(f"Possible Values for {other_decision_var} (comma-separated)", value="0,10")
other_decision_probs = st.sidebar.text_input(f"Probabilities for {other_decision_var} (comma-separated)", value="0.5,0.5")

# Constraints
st.sidebar.markdown("### Constraints")
num_constraints = st.sidebar.number_input("Number of Constraints", min_value=0, max_value=5, value=1, step=1)
constraints = []
for j in range(int(num_constraints)):
    constraint = st.sidebar.text_input(f"Constraint {j+1} (e.g., {decision_var} + {other_decision_var} - 20)", value=f"20 - {decision_var} - {other_decision_var}")
    constraints.append(constraint)

# Main content
st.markdown("## 📋 Problem Definition")

st.markdown("### Variables:")
st.write(f"Decision Variable: {decision_var}")
st.write(f"Other Player's Decision Variable: {other_decision_var}")

st.markdown("### Objective Function:")
st.write(f"u({decision_var}, {other_decision_var}) = {obj_function}")

st.markdown("### Other Player's Possible Decisions:")
other_decision_vals = [val.strip() for val in other_decision_values.split(',')]
other_decision_probs_list = [float(p.strip()) for p in other_decision_probs.split(',')]
if len(other_decision_vals) != len(other_decision_probs_list):
    st.error("The number of possible values and probabilities for the other player's decision must be the same.")
    st.stop()
if not np.isclose(sum(other_decision_probs_list), 1.0):
    st.error("The probabilities for the other player's decision must sum to 1.")
    st.stop()
st.write(f"Possible Values: {other_decision_vals}")
st.write(f"Probabilities: {other_decision_probs_list}")

st.markdown("### Constraints:")
for j, constraint in enumerate(constraints):
    st.write(f"{constraint} = 0")

st.markdown("## 🔍 Calculating Optimal Decision")

# Convert strings to sympy expressions
decision_sym = sp.Symbol(decision_var)
other_decision_sym = sp.Symbol(other_decision_var)
lambdas = sp.symbols(f"lambda1:{num_constraints+1}")

# Define 'od' as a Sympy symbol
od_sym = sp.Symbol('od')

# Expected Utility Calculation
expected_utility = 0
for val, prob in zip(other_decision_vals, other_decision_probs_list):
    local_dict = {decision_var: decision_sym, other_decision_var: float(val)}
    try:
        util_expr = parse_expr(obj_function, local_dict=local_dict)
        expected_utility += prob * util_expr
    except Exception as e:
        st.error(f"Error parsing objective function: {e}")
        st.stop()

st.markdown("### Expected Utility Function:")
st.latex(f"E[u({decision_var})] = {sp.latex(expected_utility)}")

# Build Lagrangian
lagrangian = expected_utility
for i in range(len(constraints)):
    local_dict = {decision_var: decision_sym, other_decision_var: od_sym}
    try:
        # Replace other_decision_var with 'od' in the constraint string
        constraint_str = constraints[i].replace(other_decision_var, 'od')
        # Parse the constraint expression
        constraint_expr = parse_expr(constraint_str, local_dict=local_dict)
        lagrangian += lambdas[i] * constraint_expr
    except Exception as e:
        st.error(f"Error parsing constraint: {e}")
        st.stop()

st.markdown("### Lagrangian Function:")
st.latex(f"L({decision_var}, {', '.join([str(l) for l in lambdas])}) = {sp.latex(lagrangian)}")

# Calculate derivative w.r.t decision variable
partial_derivative = sp.diff(lagrangian, decision_sym)
st.markdown("### Partial Derivative w.r.t Decision Variable:")
st.latex(f"\\frac{{\\partial L}}{{\\partial {decision_var}}} = {sp.latex(partial_derivative)} = 0")

# Solve for the decision variable
equations = [sp.Eq(partial_derivative, 0)]
for i in range(len(constraints)):
    # Replace other_decision_var with 'od' in the constraint string
    constraint_str = constraints[i].replace(other_decision_var, 'od')
    local_dict = {decision_var: decision_sym, 'od': od_sym}
    try:
        constraint_expr = parse_expr(constraint_str, local_dict=local_dict)
        equations.append(sp.Eq(constraint_expr, 0))
    except Exception as e:
        st.error(f"Error parsing constraint: {e}")
        st.stop()

# Flatten the equations by considering possible values of other_decision_var
solutions = []
for val in other_decision_vals:
    local_subs = {'od': float(val)}
    eqs = [eq.subs(local_subs) for eq in equations]
    try:
        sol = sp.solve(eqs, [decision_sym] + list(lambdas), dict=True)
        if sol:
            for s in sol:
                s['od'] = val  # Add the value of other_decision_var to the solution
                solutions.append(s)
    except Exception as e:
        st.error(f"An error occurred during solving: {e}")
        st.stop()

if solutions:
    st.success("### 🎯 Optimal Decision Found:")
    for sol in solutions:
        st.write(f"Considering {other_decision_var} = {sol.get('od', 'unknown')}")
        st.write(f"{decision_var} = {sol[decision_sym]}")
        st.write("---")
    # Simplified verification
    st.markdown("## ✅ Verifying the Constraints")
    for sol in solutions:
        st.write(f"**For {other_decision_var} = {sol.get('od', 'unknown')}:**")
        xA_value = float(sol[decision_sym])
        xB_value = float(sol['od'])
        verified = True
        for idx, constraint in enumerate(constraints):
            # Substitute xA and xB into the constraint equation
            constraint_expr = constraint
            try:
                # Replace variables with their values
                constraint_evaluated = constraint_expr.replace(decision_var, str(xA_value)).replace(other_decision_var, str(xB_value))
                # Evaluate the expression
                result = eval(constraint_evaluated)
                # Check if the result equals zero
                if abs(result) < 1e-6:
                    st.write(f"- Constraint {idx+1} is satisfied: {constraint_evaluated} = 0")
                else:
                    st.write(f"- Constraint {idx+1} is **not satisfied**: {constraint_evaluated} ≠ 0 (Value: {result})")
                    verified = False
            except Exception as e:
                st.error(f"Error evaluating constraint: {e}")
                verified = False
        if verified:
            st.write("All constraints are satisfied for this solution.")
        else:
            st.write("Not all constraints are satisfied for this solution.")
        st.write("---")
else:
    st.warning("No solution found for the given inputs.")

st.markdown("""

---

Built with **Python**, **SymPy**, and **Streamlit** for a comprehensive and interactive experience 🎉
""")
