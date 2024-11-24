import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(page_title="Portfolio Analysis and Benchmark Comparison", layout="wide")

# Title and Description
st.title("Portfolio Analysis and Benchmark Comparison")
st.markdown("""
This app allows you to create a stock portfolio, compare it with a benchmark index, 
and analyze important portfolio metrics, including Value at Risk (VaR), Sharpe Ratio, and Sortino Ratio.
""")

# Sidebar for Portfolio Inputs
st.sidebar.header("Portfolio Inputs")
if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = []

# Stock Input Form
with st.sidebar.form("portfolio_form"):
    st.subheader("Add Stock to Portfolio")
    stock_ticker = st.text_input("Stock Ticker (e.g., AAPL)", value="AAPL")
    avg_price = st.number_input("Average Price Bought ($)", min_value=0.0, value=100.0)
    quantity = st.number_input("Quantity Bought", min_value=1, value=10)
    add_stock = st.form_submit_button("Add Stock")

    if add_stock:
        st.session_state["portfolio"].append({
            "Ticker": stock_ticker.upper(),
            "Avg Price": avg_price,
            "Quantity": quantity
        })
        st.success(f"Added {stock_ticker.upper()} to your portfolio!")

# Display the Portfolio
portfolio_df = pd.DataFrame(st.session_state["portfolio"])
if not portfolio_df.empty:
    portfolio_df["Total Investment"] = portfolio_df["Avg Price"] * portfolio_df["Quantity"]
    total_portfolio_value = portfolio_df["Total Investment"].sum()
    portfolio_df["Weight"] = portfolio_df["Total Investment"] / total_portfolio_value

    st.subheader("Portfolio Details")
    st.metric("Total Portfolio Value ($)", f"{total_portfolio_value:,.2f}")
    portfolio_pie = px.pie(
        portfolio_df,
        names="Ticker",
        values="Total Investment",
        title="Portfolio Allocation by Investment",
        hole=0.4
    )
    st.plotly_chart(portfolio_pie, use_container_width=True)
    st.dataframe(portfolio_df)
else:
    st.info("Your portfolio is empty. Add stocks to begin.")

# Dropdown for Benchmark and Lookback Period
benchmark_options = {
    "S&P 500 (SPY)": "^GSPC",
    "Dow Jones (DIA)": "^DJI",
    "FTSE 100 (FTSE)": "^FTSE",
    "Nikkei 225 (NIKKEI)": "^N225",
    "Euro Stoxx 50 (STOXX50E)": "^STOXX50E",
    "India Nifty 50 (NSEI)": "^NSEI"
}
benchmark_index = st.sidebar.selectbox("Choose Benchmark Index", options=list(benchmark_options.keys()))
benchmark_ticker = benchmark_options[benchmark_index]

lookback_period = st.sidebar.selectbox(
    "Select Lookback Period",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=1
)

var_level = st.sidebar.slider("Select VaR Level (%)", min_value=90, max_value=99, value=95)

# Button to Run Simulation
if st.sidebar.button("Run Simulation"):
    tickers = portfolio_df["Ticker"].tolist()
    try:
        historical_data = yf.download(tickers, period=f"{lookback_period}")["Adj Close"]
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.stop()

    # Calculate daily returns
    daily_returns = historical_data.pct_change().dropna()

    # Portfolio metrics
    weights = portfolio_df["Weight"].values
    portfolio_returns = daily_returns.dot(weights)
    portfolio_std = portfolio_returns.std()
    portfolio_mean = portfolio_returns.mean()



    # Fetch Benchmark Data
    try:
        benchmark_data = yf.download(benchmark_ticker, period=f"{lookback_period}")["Adj Close"]


        # Ensure benchmark_data is a single column
        if isinstance(benchmark_data, pd.DataFrame):
            benchmark_data = benchmark_data.squeeze()  # Convert to Series if necessary

        # Calculate benchmark returns
        benchmark_returns = benchmark_data.pct_change().dropna()

        # Calculate mean and standard deviation
        benchmark_mean = float(benchmark_returns.mean())  # Convert to scalar
        benchmark_std = float(benchmark_returns.std())  # Convert to scalar

        # Sharpe Ratio
        risk_free_rate = 0.02 / 252
        portfolio_sharpe = (portfolio_mean - risk_free_rate) / portfolio_std
        benchmark_sharpe = (benchmark_mean - risk_free_rate) / benchmark_std

        # Sortino Ratio
        portfolio_sortino = (portfolio_mean - risk_free_rate) / portfolio_returns[portfolio_returns < 0].std()
        benchmark_sortino = (benchmark_returns.mean() - risk_free_rate) / benchmark_returns[benchmark_returns < 0].std()

        # Value at Risk (VaR)
        z_score = {90: 1.28, 95: 1.645, 99: 2.33}[var_level]
        portfolio_var = z_score * portfolio_std * total_portfolio_value
        benchmark_var = z_score * benchmark_returns.std() * total_portfolio_value

        # Display Metrics
        st.subheader("Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Portfolio Metrics")
            # Metrics with Descriptions
            st.metric("Average Daily Return", f"{portfolio_mean * 100:.2f} % ", "Represents expected daily return")
            st.metric("Portfolio Volatility (Std Dev)", f"{portfolio_std * 100:.2f} %", "Indicates riskiness of the portfolio")
            st.metric("Sharpe Ratio", f"{portfolio_sharpe:.2f}", "A Higher Sharpe Ratio indicates better risk-adjusted returns")
            st.metric("Sortino Ratio", f"{portfolio_sortino:.2f}")

        with col2:
            st.markdown("### Benchmark Metrices")
            st.metric("Average Daily Return", f"{benchmark_mean * 100:.2f} % ", "Represents expected daily return")
            st.metric("Benchmark Volatility (Std Dev)", f"{benchmark_std * 100:.2f} % ", "Indicates riskiness of the benchmark ")
            st.metric("Sharpe Ratio", f"{benchmark_sharpe:.2f}","A Higher Sharpe Ratio indicates better risk-adjusted returns")
            st.metric("Sortino Ratio", f"{benchmark_sortino:.2f}")
            #st.metric("cumreturn", (1+benchmark_returns).cumprod())

        # Cumulative Returns Comparison
        st.subheader("Cumulative Returns Comparison")
        cumulative_portfolio = (1 + portfolio_returns).cumprod()
        cumulative_benchmark = (1 + benchmark_returns).cumprod()
        comparison_fig = go.Figure()
        comparison_fig.add_trace(go.Scatter(
            x=cumulative_portfolio.index, y=cumulative_portfolio.values,
            mode="lines", name="Portfolio", line=dict(width=3, color="blue")
        ))
        comparison_fig.add_trace(go.Scatter(
            x=cumulative_benchmark.index, y=cumulative_benchmark.values,
            mode="lines", name=benchmark_index, line=dict(width=3, color="orange")
        ))
        comparison_fig.update_layout(
            title="Portfolio vs Benchmark Cumulative Returns",
            xaxis_title="Date",
            yaxis_title="Cumulative Returns",
            template="plotly_white"
        )
        st.plotly_chart(comparison_fig, use_container_width=True)

        # Value at Risk (VaR) Display
        st.subheader("Value at Risk (VaR)")
        st.metric(f"Portfolio VaR ({var_level}% Confidence)", f"${portfolio_var:,.2f}")
        st.metric(f"Benchmark VaR ({var_level}% Confidence)", f"${benchmark_var:,.2f}")
        st.markdown("""**Interpretation:** VaR represents the maximum potential loss at a certain confidence level
        over a specified time horizon. For example, a 95% VaR of $10,000 means there is a 95% chance
        you will not lose more than $10,000 in a day.""")

    except Exception as e:
        st.error(f"Error in simulation: {e}")
