import yfinance as yf
import pandas as pd
import streamlit as st
import numpy as np
from datetime import date


def format_millions(value):
    """Formats a number in millions with appropriate color."""
    if isinstance(value, (int, float)):
        if value >= 0:
             return f"{int(round(value / 1e6)):,.0f} M"  # Millions
        else:
            return f"<span style='color:red'>{value / 1e6:,.2f} M</span>"  # Red for negative
    else:
        return value  # Return as is if not a number

def style_negative_red(value):
    """Applies red color to negative numbers in a Pandas DataFrame."""
    if isinstance(value, (int, float)):
        if value < 0:
            return 'color: red'
        else:
            return '' # No style for non-neg
    else:
        return '' # No style

def style_comparison(value, current_price, safety_factor):
    """Styles sensitivity analysis results based on comparison to current price."""
    if isinstance(value, (int, float)) and isinstance(current_price, (int, float)):
        if value < current_price:
            return 'background-color: red'
        elif value > current_price*(1 + safety_factor):
            return 'background-color: green'
        else:
            return ''  # No style otherwise
    return '' # No style for non-numeric or missing current_price


def style_up_downside(value):
    """Styles Upside and downside  results."""
    if isinstance(value, (int, float)) and isinstance(current_price, (int, float)):
        if value < 0:
            return 'background-color: red'
        elif value > safety_factor:
            return 'background-color: green'
        else:
            return ''  # No style otherwise
    return '' # No style for non-numeric or missing current_price

def discounted_cash_flow(ticker, number_of_years, discount_rate, growth_rate_1_5, growth_rate_6_20, terminal_growth_rate):
    """
    (Same docstring as before - keep it!)
    """
    # Input Type Validation
    if not isinstance(ticker, str):
        raise TypeError("Ticker must be a string.")
    if not all(isinstance(rate, (int, float)) for rate in [discount_rate, growth_rate_1_5, growth_rate_6_20, terminal_growth_rate]):
        raise TypeError("Discount rate and growth rates must be numbers.")

    # Input Value Validation
    if not 0 <= discount_rate <= 1:
        raise ValueError("Discount rate must be between 0 and 1.")
    if not -1 <= growth_rate_1_5 <= 2:
        raise ValueError("Growth rate (1-5) is outside a reasonable range (-1 to 2).")
    if not -1 <= growth_rate_6_20 <= 2:
        raise ValueError("Growth rate (6-20) is outside a reasonable range (-1 to 2).")
    if not -1 <= terminal_growth_rate <= 1:
        raise ValueError("Terminal growth rate is outside a reasonable range (-1 to 1).")
    if discount_rate <= terminal_growth_rate:
        raise ValueError("Discount rate must be greater than terminal growth rate.")


    try:
        # --- Data Retrieval ---
        stock = yf.Ticker(ticker)

        if stock.info is None or stock.info == {}:
                return {'Error Message': f"Invalid ticker symbol: {ticker}"}

        cashflow_statement = stock.cashflow
        balance_sheet = stock.balance_sheet
        info = stock.info

        if cashflow_statement is None or cashflow_statement.empty:
             return {'Error Message': "Cash flow statement data unavailable."}
        if balance_sheet is None or balance_sheet.empty:
            return {'Error Message': "Balance sheet data unavailable."}
        if info is None:
            return {'Error Message': "Stock info unavailable."}

        free_cash_flow = cashflow_statement.loc['Free Cash Flow'].iloc[0]
        if pd.isna(free_cash_flow):
            return {'Error Message': "Free Cash Flow data unavailable."}

        market_cap = info.get('marketCap')
        if market_cap is None:
            return {'Error Message': "Market capitalization data unavailable."}

        current_price = info.get("currentPrice")
        if current_price is None:
             return {'Error Message': "Current price data unavailable."}

        total_liabilities = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0] if 'Total Liabilities Net Minority Interest' in balance_sheet.index else balance_sheet.loc['Total Liabilities'].iloc[0]
        cash_and_equivalents = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
        net_debt = total_liabilities - cash_and_equivalents
        if pd.isna(total_liabilities) or pd.isna(cash_and_equivalents):
                return {'Error Message':"Net Debt data unavailable"}

        shares_outstanding = info.get('sharesOutstanding')
        if shares_outstanding is None:
            return {'Error Message':"Shares outstanding unavailable."}


        # --- Calculations ---
        projected_fcfs = []
        present_values = []

        for year in range(1, number_of_years+1):
            if year <= 5:
                growth_rate = growth_rate_1_5
            else:
                growth_rate = growth_rate_6_20
            projected_fcf = free_cash_flow * ((1 + growth_rate) ** year)
            projected_fcfs.append(projected_fcf)
            present_value = projected_fcf / ((1 + discount_rate) ** year)
            present_values.append(present_value)

        terminal_value = (projected_fcfs[-1] * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)               
        present_value_terminal_value = terminal_value / ((1 + discount_rate) ** number_of_years)

        sum_of_pvs = sum(present_values) + present_value_terminal_value
        enterprise_value = sum_of_pvs
        equity_value = enterprise_value - net_debt
        intrinsic_value_per_share = equity_value / shares_outstanding
        upside_downside = (intrinsic_value_per_share - current_price) / current_price
        implied_growth_rate=(discount_rate-free_cash_flow/terminal_value)/(1+free_cash_flow/terminal_value)

        return {
            'Intrinsic Value per Share': intrinsic_value_per_share,
            'Current Share Price': current_price,
            'Upside/Downside': upside_downside,
            'Free Cash Flow': free_cash_flow,
            'Market Cap': market_cap,
            'Net Debt': net_debt,
            'Projected FCFs': projected_fcfs,
            'Present Values': present_values,
            'Terminal Value': terminal_value,
            'Implied Growth Rate': implied_growth_rate,
            'Present Value of Terminal Value': present_value_terminal_value,
            'Enterprise Value': enterprise_value,
            'Equity Value': equity_value,
            'Shares Outstanding': shares_outstanding,
            'Price to FCF (YoY)': market_cap/free_cash_flow,
            'Error Message': None,
        }

    except Exception as e:
        return {'Error Message': f"An unexpected error occurred: {str(e)}"}



def sensitivity_analysis(ticker, discount_rate, growth_rate_1_5_range, growth_rate_6_20_range, terminal_growth_rate):
    """
    (Same docstring as before - keep it!)
    """
    results = {}
    for g1_5 in growth_rate_1_5_range:
        results[g1_5] = {}
        for g6_20 in growth_rate_6_20_range:
            try:
                if g1_5<g6_20:
                    dcf_result="-"
                else:                
                    dcf_result = discounted_cash_flow(ticker, number_of_years, discount_rate, g1_5, g6_20, terminal_growth_rate)
                    if dcf_result and 'Intrinsic Value per Share' in dcf_result:
                        results[g1_5][g6_20] = dcf_result['Intrinsic Value per Share']
                    else:
                        results[g1_5][g6_20] = None
            except ValueError:
                results[g1_5][g6_20] = None
            except Exception as e: # Catch any other errors.
                results[g1_5][g6_20] = None
                

# Intrinsic Value
                if dcf_results['Intrinsic Value per Share'] < dcf_results['Current Share Price']:
                    intrinsic_value_color = "red"  # Red if lower
                else:
                    intrinsic_value_color = "green" # Green if higher or equal
                st.metric("Intrinsic Value per Share", f"{dcf_results['Intrinsic Value per Share']:,.2f}", delta_color='off') #remove delta
                # Use markdown to apply color *within* the metric
                st.markdown(f"<p style='color:{intrinsic_value_color};font-size:1.1em;'>Value: {dcf_results['Intrinsic Value per Share']:,.2f}</p>", unsafe_allow_html=True)

    return pd.DataFrame(results)


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Discounted Cash Flow Calculator")

with st.sidebar:
    st.header("Inputs")
    ticker_symbol = st.text_input("Enter Stock Ticker (e.g., AAPL)", "AAPL").upper()
    discount_rate = st.number_input("Discount Rate (%)", min_value=0.0, max_value=100.0, value=9.0, step=0.25) / 100
    number_of_years = st.number_input("Number of years for the calculation", min_value=-1, max_value=20, value=6, step=1)
    growth_rate_1_5 = st.number_input("Growth Rate (Years 1-5) (%)", min_value=-100.0, max_value=200.0, value=12.5, step=0.25) / 100
    growth_rate_6_20 = st.number_input("Growth Rate (Years 6-20) (%)", min_value=-100.0, max_value=200.0, value=9.0, step=0.25) / 100
    terminal_growth_rate = st.number_input("Terminal Growth Rate (%)", min_value=-100.0, max_value=100.0, value=3.0, step=0.25) / 100
    safety_factor = st.number_input("Safety Factor (%)", min_value=0.0, max_value=100.0, value=20.0, step=0.1) / 100
    show_projected_fcf = st.checkbox("Show Projected Free Cash Flows",value=True)

    st.subheader("Perform Sensitivity Analysis")
    show_sensitivity = st.checkbox("Perform Sensitivity Analysis",value=False)
    

    if show_sensitivity:
        growth_rate_1_5_min = st.number_input("Growth Rate (1-5) Min (%)", min_value=-100.0, max_value=200.0, value=0.0, step=0.25) / 100
        growth_rate_1_5_max = st.number_input("Growth Rate (1-5) Max (%)", min_value=-100.0, max_value=200.0, value=20.0, step=0.25) / 100
        growth_rate_1_5_step = st.number_input("Growth Rate (1-5) Step (%)", min_value=0.1, max_value=20.0, value=2.0, step=0.25) / 100

        growth_rate_6_20_min = st.number_input("Growth Rate (6-20) Min (%)", min_value=-100.0, max_value=200.0, value=0.0, step=0.25) / 100
        growth_rate_6_20_max = st.number_input("Growth Rate (6-20) Max (%)", min_value=-100.0, max_value=200.0, value=20.0, step=0.25) / 100
        growth_rate_6_20_step = st.number_input("Growth Rate (6-20) Step (%)", min_value=0.1, max_value=20.0, value=2.0, step=0.25) / 100

if st.button("Calculate DCF"):
    try:
        dcf_results = discounted_cash_flow(
            ticker_symbol,number_of_years, discount_rate, growth_rate_1_5, growth_rate_6_20, terminal_growth_rate
        )

        if dcf_results and dcf_results['Error Message'] is None:
            st.subheader(f"DCF Results for {ticker_symbol}")

            # --- Conditional Formatting for Metrics ---
            col1, col2, col3 = st.columns(3)

            with col1:
                # Intrinsic Value
                if dcf_results['Intrinsic Value per Share'] < dcf_results['Current Share Price']:
                    intrinsic_value_color = "red"  # Red if lower
                else:
                    intrinsic_value_color = "green" # Green if higher or equal
                st.metric("Intrinsic Value per Share", f"{dcf_results['Intrinsic Value per Share']:,.2f}", delta=round(dcf_results['Intrinsic Value per Share']-dcf_results['Current Share Price'],2), delta_color='normal')
                st.markdown(f"<p style='color:{intrinsic_value_color};font-size:1.5em;'>Upside/Downside:{dcf_results['Upside/Downside']:,.2%}</p>", unsafe_allow_html=True)

            with col2:
                # Upside/Downside - already a percentage
                st.metric("Current Share Price", f"{dcf_results['Current Share Price']:,.2f}")
                st.metric("Free Cash Flow", format_millions(dcf_results['Free Cash Flow']))

            with col3:
                st.metric("Price to Free Cash Flow", round(dcf_results['Price to FCF (YoY)'],1))
                st.metric("Annual Yield", f"{1/dcf_results['Price to FCF (YoY)']:.2%}")
            

            st.subheader(f"Projections")
            col4, col5, col6= st.columns(3)
            with col4:
                
                st.metric("Projected Terminal Value", format_millions(dcf_results['Terminal Value']))
                st.metric("Actual Market Cap", format_millions(dcf_results['Market Cap']))
                
            with col5:
                st.metric("Present Value of Projected Terminal Value", format_millions(dcf_results['Present Value of Terminal Value']))
                st.metric("Projected Enterprise Value", format_millions(dcf_results['Enterprise Value']))
            with col6:
                st.metric("Shares Outstanding", format_millions(dcf_results['Shares Outstanding']))
                st.metric("Actual Net Debt", format_millions(dcf_results['Net Debt']))
                
                     
        elif dcf_results:
            st.error(dcf_results['Error Message'])
            
            
            


        # --- Sensitivity Analysis ---
        if show_sensitivity:
            st.subheader("Sensitivity Analysis")
            st.write("Intrinsic Value per Share based on different growth rate assumptions:")

            growth_rate_1_5_range = np.arange(growth_rate_1_5_min, growth_rate_1_5_max + growth_rate_1_5_step, growth_rate_1_5_step)
            growth_rate_6_20_range = np.arange(growth_rate_6_20_min, growth_rate_6_20_max + growth_rate_6_20_step, growth_rate_6_20_step)
            growth_rate_1_5_range = np.round(growth_rate_1_5_range, 4)
            growth_rate_6_20_range = np.round(growth_rate_6_20_range, 4)

            sensitivity_df = sensitivity_analysis(
                ticker_symbol, discount_rate, growth_rate_1_5_range, growth_rate_6_20_range, terminal_growth_rate
            )
                        
           # Apply styling to the sensitivity analysis dataframe based on current_price
            st.dataframe(sensitivity_df.style.applymap(lambda x: style_comparison(x, dcf_results['Current Share Price'],safety_factor)).format("{:.2f}"), height=600) # Use style_comparison

        if show_projected_fcf:
            st.subheader("Projected Free Cash Flows and Present Values")
            df_projections = pd.DataFrame({
                'Year': range(1, number_of_years+1),
                'Projected FCF (M)': [round(fcf / 1e6) for fcf in dcf_results['Projected FCFs']],  # Millions
                'Present Value (M)': [round(pv / 1e6) for pv in dcf_results['Present Values']]     # Millions
            })
            # Apply styling for negative numbers
            st.dataframe(df_projections.set_index('Year').style.applymap(style_negative_red), height=600)

    except (TypeError, ValueError) as e:
        st.error(f"Input Error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")