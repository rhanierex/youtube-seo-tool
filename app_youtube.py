import pandas as pd
import streamlit as st

def draw_competitor_chart(df):
    """Visualize competitor data using Streamlit's built-in chart functions"""
    if df is None or df.empty:
        st.warning("No data available")
        return
    
    st.markdown("### 📊 Top Competitor Videos")
    
    # Use Streamlit's built-in bar chart function
    chart_data = pd.DataFrame({
        'Title': df['Title'],
        'Views': df['Views']
    })

    st.bar_chart(chart_data.set_index('Title'))

# Example usage with a dummy DataFrame
data = {
    'Title': ['Video 1', 'Video 2', 'Video 3'],
    'Views': [1000, 5000, 3000]
}

df = pd.DataFrame(data)

draw_competitor_chart(df)
