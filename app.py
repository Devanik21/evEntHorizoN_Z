import streamlit as st
from PIL import Image

# Page Config
st.set_page_config(page_title="Understand the Universe", page_icon="🌌", layout="centered")

# Background and Style
def local_css(css_text):
    st.markdown(f'<style>{css_text}</style>', unsafe_allow_html=True)

local_css('''
body {
    background: radial-gradient(circle at 50% 20%, #0a0a0f 0%, #000000 80%);
    color: white;
    font-family: 'Inter', sans-serif;
    text-align: center;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
}

.subtitle {
    color: rgba(255,255,255,0.8);
    font-size: 1.3rem;
    margin-top: -10px;
    letter-spacing: 0.5px;
}

.mystic {
    text-shadow: 0 0 20px rgba(255,255,255,0.4);
    letter-spacing: 1.2px;
}

img {
    border-radius: 16px;
    box-shadow: 0px 0px 40px rgba(255,255,255,0.05);
}
''')

# Title
st.markdown("""
<h1 class='mystic'>Grok</h1>
<h2 class='subtitle'>Understand the universe</h2>
""", unsafe_allow_html=True)

# Display the mysterious cosmic image
image = Image.open('black_hole.png')
st.image(image, caption=None, use_column_width=True)

# Add a faint footer
st.markdown("""
<hr style='opacity:0.1;'>
<p style='font-size:0.9rem; color:rgba(255,255,255,0.4);'>A voyage into cosmic intelligence ⚫</p>
""", unsafe_allow_html=True)
