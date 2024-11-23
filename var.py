import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(page_title="Value at Risk (VaR) Calculator", layout="wide")

# Title and Description
st.title("Value at Risk (VaR) Calculator")
st.markdown("""
This application calculates the **Value at Risk (VaR)** for a portfolio of stocks. 
Define your portfolio, fetch historical data, and analyze relevant metrics with interactive visualizations.
""")

# Sidebar for Inputs
st.sidebar.header("Portfolio Inputs")

# Initialize session state for the portfolio
if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = []

# Stock Input Form
st.sidebar.subheader("Add Stock to Portfolio")
with st.sidebar.form("stock_form"):
    stock_symbol = st.text_input("Ticker Symbol", value="AAPL")
    avg_price = st.number_input("Average Price Bought ($)", min_value=0.0, value=100.0)
    quantity = st.number_input("Quantity Bought", min_value=1, value=10)
    add_stock = st.form_submit_button("Add Stock to Basket")

    if add_stock:
        st.session_state["portfolio"].append({
            "Ticker": stock_symbol,
            "Avg Price": avg_price,
            "Quantity": quantity
        })
        st.success(f"Added {stock_symbol} to your portfolio!")

# Display the Portfolio
portfolio_df = pd.DataFrame(st.session_state["portfolio"])
if not portfolio_df.empty:
    portfolio_df["Total Investment"] = portfolio_df["Avg Price"] * portfolio_df["Quantity"]
    total_portfolio_value = portfolio_df["Total Investment"].sum()
    portfolio_df["Weight"] = portfolio_df["Total Investment"] / total_portfolio_value

    st.subheader("Portfolio Details")
    portfolio_pie = px.pie(
        portfolio_df,
        names="Ticker",
        values="Total Investment",
        title="Portfolio Allocation by Investment",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Plasma
    )
    st.plotly_chart(portfolio_pie, use_container_width=True)
    st.dataframe(portfolio_df)
    st.metric("Total Portfolio Value ($)", f"{total_portfolio_value:,.2f}")
else:
    st.info("Your portfolio is empty. Add stocks to calculate metrics.")

# Lookback Period Input
lookback_period_options = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
lookback_period = st.sidebar.selectbox(
    "Select Lookback Period",
    options=lookback_period_options,
    index=3  # Default to '3mo'
)

# Fetch Historical Data
if not portfolio_df.empty:
    st.subheader("Fetching Historical Data")
    tickers = portfolio_df["Ticker"].tolist()
    try:
        historical_data = yf.download(tickers, period=f"{lookback_period}")["Adj Close"]
        st.write("Historical Adjusted Close Prices")
        st.dataframe(historical_data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.stop()

    # Calculate daily returns
    daily_returns = historical_data.pct_change().dropna()
    st.write("Daily Returns")
    st.dataframe(daily_returns)

    # Portfolio metrics
    weights = portfolio_df["Weight"].values
    portfolio_returns = daily_returns.dot(weights)
    portfolio_std = portfolio_returns.std()
    portfolio_mean = portfolio_returns.mean()

    # Metrics with Descriptions
    st.subheader("Portfolio Metrics")
    st.metric("Average Daily Return", f"{portfolio_mean:.4f}", "Represents expected daily return")
    st.metric("Portfolio Volatility (Std Dev)", f"{portfolio_std:.4f}", "Indicates riskiness of the portfolio")

    # Visualizing Portfolio Returns Over Time
    st.subheader("Portfolio Cumulative Returns")
    cumulative_returns = (1 + portfolio_returns).cumprod()
    cumulative_returns_fig = px.line(
        x=cumulative_returns.index,
        y=cumulative_returns.values,
        title="Portfolio Cumulative Returns Over Time",
        labels={"x": "Date", "y": "Cumulative Returns"},
        template="plotly_dark",
        color_discrete_sequence=["cyan"]
    )
    cumulative_returns_fig.update_traces(line=dict(width=3))
    st.plotly_chart(cumulative_returns_fig, use_container_width=True)

    # Calculate VaR
    confidence_level = 0.95
    z_score = 1.645  # For 95% confidence
    portfolio_var = z_score * portfolio_std * total_portfolio_value

    st.subheader("Value at Risk (VaR)")
    st.metric("Portfolio VaR (95% Confidence, 1 Day)", f"${portfolio_var:,.2f}")
    st.markdown("""
    **Interpretation**: The portfolio has a 95% chance of not losing more than this amount in one day.
    """)

    # Visualization of Portfolio Returns with VaR
    st.subheader("Portfolio Returns Distribution with VaR")
    returns_histogram = go.Figure()

    # Add histogram
    returns_histogram.add_trace(
        go.Histogram(
            x=portfolio_returns,
            nbinsx=50,
            marker_color="blue",
            opacity=0.7,
            name="Portfolio Returns"
        )
    )

    # Add VaR line
    returns_histogram.add_vline(
        x=-portfolio_var / total_portfolio_value,
        line_width=3,
        line_dash="dash",
        line_color="red",
        annotation_text="VaR Threshold",
        annotation_position="top right"
    )

    returns_histogram.update_layout(
        title="Portfolio Returns Distribution",
        xaxis_title="Daily Returns",
        yaxis_title="Frequency",
        template="plotly_white",
        showlegend=False
    )
    st.plotly_chart(returns_histogram, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
**Disclaimer:** This tool is for educational purposes only and does not constitute financial advice.
""")
