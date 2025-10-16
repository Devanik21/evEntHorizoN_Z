import streamlit as st
from PIL import Image
import base64
import os
import google.generativeai as genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="Understand the Universe", page_icon="🌌", layout="centered")

# --- CONFIGURE GEMINI API ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemma-3n-e2b-it')
except Exception as e:
    st.error(f"⚠️ API Configuration Error: {str(e)}")

# --- FUNCTIONS ---
def get_base64_of_bin_file(bin_file):
    """
    Encodes a binary file to a base64 string.
    Args:
        bin_file (str): The path to the binary file.
    Returns:
        str: The base64 encoded string.
    """
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_page_background_and_style(file_path):
    """
    Sets the background image and applies custom CSS styles.
    Args:
        file_path (str): The path to the background image file.
    """
    # Check if the file exists to avoid errors
    if not os.path.exists(file_path):
        st.error(f"Error: Background image not found at '{file_path}'. Please ensure the image is in the same directory as your script.")
        return
    
    # Encode the image to base64
    base64_img = get_base64_of_bin_file(file_path)
    
    # Custom CSS with the base64 image as background
    css_text = f'''
    <style>
    /* --- Main App Background --- */
    .stApp {{
        background-image: url("data:image/png;base64,{base64_img}");
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* --- Make Streamlit header transparent --- */
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}
    
    /* --- General Text and Font Styles --- */
    body, h1, h2, h3, h4, h5, h6 {{
        color: white;
        font-family: 'Inter', sans-serif;
        text-align: center;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-weight: 700;
    }}
    
    /* --- Custom Class Styles --- */
    .subtitle {{
        color: rgba(255,255,255,0.8);
        font-size: 1.3rem;
        margin-top: -10px;
        letter-spacing: 0.5px;
    }}
    
    .mystic {{
        text-shadow: 0 0 20px rgba(255,255,255,0.4);
        letter-spacing: 1.2px;
    }}
    
    /* --- Chat Input Styling --- */
    .stChatInput {{
        background: rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 15px;
    }}
    
    /* --- Chat Message Styling --- */
    .stChatMessage {{
        background: rgba(0,0,0,0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        color: white;
    }}
    
    /* --- Footer Style --- */
    .footer {{
        font-size: 0.9rem;
        color: rgba(255,255,255,0.4);
    }}
    
    hr {{
        opacity: 0.1;
        border-color: rgba(255,255,255,0.2);
    }}
    
    /* --- Text Area and Input Styling --- */
    textarea, input {{
        color: white !important;
        background: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }}
    </style>
    '''
    st.markdown(css_text, unsafe_allow_html=True)

def get_cosmic_response(prompt):
    """
    Generate response using Gemini API with cosmic context.
    Args:
        prompt (str): User's question
    Returns:
        str: AI-generated response
    """
    try:
        cosmic_context = "You are a cosmic intelligence exploring the mysteries of the universe. Answer questions with wonder, scientific accuracy, and philosophical depth. Keep responses insightful yet accessible."
        full_prompt = f"{cosmic_context}\n\nQuestion: {prompt}"
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"✨ The cosmic signals are unclear: {str(e)}"

# --- APP LAYOUT ---
# Set the background image and custom styles
set_page_background_and_style('black_hole.png')

# Add some vertical space from the top
st.markdown("<br>", unsafe_allow_html=True)

# Title Section
st.markdown("""
<h1 class='mystic'>♾️</h1>
<h2 class='subtitle'>Understand the universe</h2>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🌌" if message["role"] == "assistant" else "🧑‍🚀"):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask the cosmos..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user", avatar="🧑‍🚀"):
        st.markdown(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("✨ Consulting the cosmic consciousness..."):
            response = get_cosmic_response(prompt)
            st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Add more vertical space before the footer
st.markdown("<br><br>", unsafe_allow_html=True)

# Footer Section
st.markdown("""
<hr>
<p class='footer'>A voyage into cosmic intelligence ✨</p>
""", unsafe_allow_html=True)
