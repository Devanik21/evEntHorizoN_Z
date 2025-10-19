import streamlit as st
from PIL import Image
import base64
import os
import google.generativeai as genai
import PyPDF2
import docx
from pathlib import Path
import json
from datetime import datetime
from tinydb import TinyDB, Query
import io
import pandas as pd
import numpy as np

# --- Plotly for Advanced Visualizations ---
import plotly.graph_objects as go
import plotly.express as px

# --- ADVANCED FEATURE IMPORTS ---
from gtts import gTTS
from scipy import stats

# --- CONSTANTS ---
VISUALIZATION_INSTRUCTIONS = """
When asked to create a plot or visualization, you MUST generate Python code using the `plotly` library.
The code block must be a valid Python script that creates a figure object named `fig`.
The code should be wrapped in ```python ... ```.
To make the plot match the app's theme, you MUST use one of the available cosmic themes by calling `apply_cosmic_theme(fig, 'Theme Name')` at the end of your script.
Available 'Theme Name' options are: 'Nebula Burst', 'Starlight', 'Void', 'Supernova', 'Quantum Foam'.
The final figure object in the script MUST be named `fig`.
Example of a simple plot generation:
```python
import plotly.graph_objects as go
import pandas as pd

df = pd.DataFrame({'x': [1, 2, 3, 4], 'y': [10, 11, 12, 13]})
fig = go.Figure(data=go.Scatter(x=df['x'], y=df['y'], mode='lines+markers'))
fig.update_layout(title='Sample Plot')
apply_cosmic_theme(fig, 'Nebula Burst')
```
"""

PERSONAS = {
    "Cosmic Intelligence": "You are a cosmic intelligence exploring the mysteries of the universe. Answer questions with wonder, scientific accuracy, and philosophical depth. Keep responses insightful yet accessible." + VISUALIZATION_INSTRUCTIONS,
    "Astrophysicist": "You are a brilliant and enthusiastic astrophysicist. Explain complex topics like black holes, dark matter, and stellar evolution with clarity and passion, using real-world analogies." + VISUALIZATION_INSTRUCTIONS,
    "Sci-Fi Author": "You are a creative science fiction author. Respond to prompts by weaving imaginative narratives, describing futuristic technologies, and exploring the philosophical implications of space travel and alien contact." + VISUALIZATION_INSTRUCTIONS,
    "Quantum Philosopher": "You are a philosopher specializing in the metaphysical implications of quantum mechanics. Discuss topics with a blend of scientific principles and deep philosophical inquiry, exploring concepts like consciousness, reality, and the nature of time." + VISUALIZATION_INSTRUCTIONS
}

# --- PAGE CONFIG ---
st.set_page_config(page_title="evEnt HorizoN", page_icon="♾️", layout="centered")

# --- CONFIGURE GEMINI API ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemma-3-27b-it')
except Exception as e:
    st.error(f"⚠️ API Configuration Error: {str(e)}")

# --- DATABASE FUNCTIONS ---
def init_database():
    """Initialize TinyDB database for chat history."""
    db = TinyDB('cosmic_chats.json')
    return db

def create_new_session(db, session_name=None, persona_name="Cosmic Intelligence"):
    """Create a new chat session."""
    if session_name is None:
        session_name = f"Cosmic Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    sessions_table = db.table('sessions')
    session_id = sessions_table.insert({
        'session_name': session_name,
        'persona_name': persona_name,
        'created_at': datetime.now().isoformat(),
        'messages': []
    })
    return session_id

def get_all_sessions(db):
    """Get all chat sessions."""
    sessions_table = db.table('sessions')
    sessions = sessions_table.all()
    sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return sessions

def save_message(db, session_id, role, content, files=None, suggestions=None):
    """Save a message to the database."""
    sessions_table = db.table('sessions') 
    Session = Query()
    
    session = sessions_table.get(doc_id=session_id)
    if session:
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        if files:
            message['files'] = files
        if suggestions:
            message['suggestions'] = suggestions
        
        messages = session.get('messages', [])
        messages.append(message)
        sessions_table.update({'messages': messages}, doc_ids=[session_id])
        return message

def load_session_messages(db, session_id):
    """Load all messages for a session."""
    sessions_table = db.table('sessions')
    session = sessions_table.get(doc_id=session_id)
    
    if session:
        messages = []
        for msg in session.get('messages', []):
            message = {
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': msg.get('timestamp', datetime.now().isoformat())
            }
            if 'files' in msg:
                message['files'] = msg['files']
            if 'suggestions' in msg:
                message['suggestions'] = msg['suggestions']
            messages.append(message)
        return messages
    return []

def delete_session(db, session_id):
    """Delete a chat session."""
    sessions_table = db.table('sessions')
    sessions_table.remove(doc_ids=[session_id])

def rename_session(db, session_id, new_name):
    """Rename a chat session."""
    sessions_table = db.table('sessions')
    sessions_table.update({'session_name': new_name}, doc_ids=[session_id])

def get_session_name(db, session_id):
    """Get session name by ID."""
    sessions_table = db.table('sessions')
    session = sessions_table.get(doc_id=session_id)
    return session.get('session_name', 'Unknown') if session else 'Unknown'

def get_session_persona(db, session_id):
    """Get session persona by ID."""
    sessions_table = db.table('sessions')
    session = sessions_table.get(doc_id=session_id)
    return session.get('persona_name', 'Cosmic Intelligence') if session else 'Cosmic Intelligence'

# --- VISUALIZATION THEMES ---
COSMIC_THEMES = {
    'Nebula Burst': {
        'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#E5E5E5'}, 'title_font': {'color': '#FFFFFF', 'size': 20},
        'xaxis': {'gridcolor': 'rgba(255, 255, 255, 0.1)', 'linecolor': 'rgba(255, 255, 255, 0.3)'},
        'yaxis': {'gridcolor': 'rgba(255, 255, 255, 0.1)', 'linecolor': 'rgba(255, 255, 255, 0.3)'},
        'colorway': ['#E040FB', '#7C4DFF', '#448AFF', '#00BCD4', '#FF4081']
    },
    'Starlight': {
        'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#B0C4DE'}, 'title_font': {'color': '#FFFFFF', 'size': 20},
        'xaxis': {'gridcolor': 'rgba(176, 196, 222, 0.2)', 'linecolor': 'rgba(176, 196, 222, 0.4)'},
        'yaxis': {'gridcolor': 'rgba(176, 196, 222, 0.2)', 'linecolor': 'rgba(176, 196, 222, 0.4)'},
        'colorway': ['#FFFFFF', '#ADD8E6', '#87CEEB', '#00BFFF', '#1E90FF']
    },
    'Void': {
        'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#999999'}, 'title_font': {'color': '#FFFFFF', 'size': 20},
        'xaxis': {'gridcolor': 'rgba(255, 255, 255, 0.05)', 'linecolor': 'rgba(255, 255, 255, 0.2)'},
        'yaxis': {'gridcolor': 'rgba(255, 255, 255, 0.05)', 'linecolor': 'rgba(255, 255, 255, 0.2)'},
        'colorway': ['#FFFFFF', '#D3D3D3', '#A9A9A9', '#808080', '#696969']
    },
    'Supernova': {
        'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#FFDDC1'}, 'title_font': {'color': '#FFFFFF', 'size': 20},
        'xaxis': {'gridcolor': 'rgba(255, 107, 107, 0.2)', 'linecolor': 'rgba(255, 107, 107, 0.4)'},
        'yaxis': {'gridcolor': 'rgba(255, 107, 107, 0.2)', 'linecolor': 'rgba(255, 107, 107, 0.4)'},
        'colorway': ['#FF4E50', '#FC913A', '#F9D423', '#FFD700', '#FCE38A']
    },
    'Quantum Foam': {
        'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#AFEEEE'}, 'title_font': {'color': '#FFFFFF', 'size': 20},
        'xaxis': {'gridcolor': 'rgba(64, 224, 208, 0.2)', 'linecolor': 'rgba(64, 224, 208, 0.4)'},
        'yaxis': {'gridcolor': 'rgba(64, 224, 208, 0.2)', 'linecolor': 'rgba(64, 224, 208, 0.4)'},
        'colorway': ['#00FF7F', '#7FFFD4', '#40E0D0', '#20B2AA', '#00CED1']
    }
}

def apply_cosmic_theme(fig, theme_name='Nebula Burst'):
    """Applies a futuristic, transparent theme to a Plotly figure."""
    if theme_name not in COSMIC_THEMES:
        theme_name = 'Nebula Burst'
    
    theme = COSMIC_THEMES[theme_name]
    fig.update_layout(
        paper_bgcolor=theme['paper_bgcolor'],
        plot_bgcolor=theme['plot_bgcolor'],
        font=theme['font'],
        title_font=theme['title_font'],
        xaxis=theme['xaxis'],
        yaxis=theme['yaxis'],
        colorway=theme['colorway'],
        legend=dict(bgcolor='rgba(0,0,0,0.3)', bordercolor='rgba(255,255,255,0.2)'),
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- DATA TOOL FUNCTIONS ---
def statistical_analysis(df):
    """Generate comprehensive statistical analysis"""
    stats_dict = {
        'shape': df.shape,
        'columns': df.columns.tolist(),
        'dtypes': df.dtypes.to_dict(),
        'missing': df.isnull().sum().to_dict(),
        'numeric_stats': df.describe().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {}
    }
    return stats_dict

def correlation_matrix(df):
    """Generate correlation matrix for numeric columns"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            colorscale='Viridis',
            text=corr.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 10},
            colorbar=dict(title="Correlation")
        ))
        fig.update_layout(title='Correlation Matrix')
        apply_cosmic_theme(fig, 'Quantum Foam')
        return fig
    return None

def trend_detection(df):
    """Detect trends in time series or sequential data"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        col = numeric_cols[0]
        data = df[col].dropna()
        x = np.arange(len(data))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=data, mode='markers', name='Data', marker=dict(color='#00BCD4')))
        fig.add_trace(go.Scatter(x=x, y=slope*x + intercept, mode='lines', name=f'Trend (R²={r_value**2:.3f})', line=dict(color='#E040FB', width=2)))
        fig.update_layout(title=f'Trend Analysis: {col}', xaxis_title='Index', yaxis_title=col)
        apply_cosmic_theme(fig, 'Nebula Burst')
        return fig
    return None

def distribution_analysis(df):
    """Analyze distribution of numeric columns"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        col = numeric_cols[0]
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=df[col], name='Distribution', marker=dict(color='#7C4DFF'), opacity=0.7))
        fig.update_layout(title=f'Distribution: {col}', xaxis_title=col, yaxis_title='Frequency')
        apply_cosmic_theme(fig, 'Supernova')
        return fig
    return None

# --- FUNCTIONS ---
def get_base64_of_bin_file(bin_file):
    """Encodes a binary file to a base64 string."""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_page_background_and_style(file_path):
    """Sets the background image and applies custom CSS styles."""
    if not os.path.exists(file_path):
        st.error(f"Error: Background image not found at '{file_path}'.")
        return
    
    base64_img = get_base64_of_bin_file(file_path)
    
    css_text = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{base64_img}");
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* 100% Pure Transparency - No boxes, no borders */
    [data-testid="stHeader"],
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"],
    [data-testid="stBottomBlockContainer"],
    [data-testid="stChatInputContainer"],
    [data-testid="stFileUploader"],
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploaderDropzoneInstructions"],
    .stTextArea,
    .stTextInput,
    .stChatMessage,
    [data-testid="stChatMessageContent"],
    .element-container,
    .stMarkdown,
    section[data-testid="stSidebar"],
    .stSelectbox,
    div[data-baseweb="select"],
    .stExpander,
    [data-testid="stSidebar"]::before {{
        background: transparent !important;
        backdrop-filter: none !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* Remove all borders from sidebar */
    [data-testid="stSidebar"] {{
        border-right: none !important;
    }}
    
    /* Pure transparent inputs - no borders */
    textarea, input {{
        background: transparent !important;
        border: none !important;
        color: rgba(200, 200, 200, 0.9) !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
    }}
    
    textarea:hover, input:hover,
    textarea:focus, input:focus {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: rgba(220, 220, 220, 1) !important;
    }}
    
    /* Pure transparent buttons - no borders */
    button {{
        background: transparent !important;
        border: none !important;
        color: rgba(200, 200, 200, 0.85) !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
    }}
    
    button:hover {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: rgba(240, 240, 240, 1) !important;
        transform: none !important;
    }}
    
    /* Gray-white text throughout */
    body, h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdown {{
        color: rgba(200, 200, 200, 0.9) !important;
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
    }}
    
    h1, h2, h3 {{
        font-weight: 300 !important;
        text-align: center;
        letter-spacing: 2px;
    }}
    
    h1 {{
        font-size: 3rem !important;
        color: rgba(220, 220, 220, 0.95) !important;
    }}
    
    .subtitle {{
        color: rgba(180, 180, 180, 0.8);
        font-size: 1.1rem;
        margin-top: -10px;
        letter-spacing: 3px;
        font-weight: 300;
    }}
    
    /* Transparent chat messages - no borders */
    .stChatMessage {{
        background: transparent !important;
        border: none !important;
        padding-left: 0px !important;
        margin: 8px 0 !important;
    }}
    
    .stChatMessage:hover {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* File badges - pure transparent */
    .file-badge {{
        display: inline-block;
        background: transparent;
        border: none;
        padding: 4px 10px;
        margin: 3px;
        font-size: 0.85rem;
        color: rgba(180, 180, 180, 0.8);
        transition: all 0.3s ease;
    }}
    
    .file-badge:hover {{
        background: transparent;
        border: none;
        color: rgba(220, 220, 220, 1);
    }}
    
    /* Data tool buttons - no special styling */
    .data-tool-button button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

    .data-tool-button button:hover {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* Minimal scrollbar */
    ::-webkit-scrollbar {{
        width: 6px;
        background: transparent;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: rgba(150, 150, 150, 0.3);
        border-radius: 3px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(180, 180, 180, 0.5);
    }}
    
    /* Placeholder text */
    ::placeholder {{
        color: rgba(150, 150, 150, 0.5) !important;
    }}
    
    /* Selectbox - transparent */
    div[data-baseweb="select"] > div {{
        background: transparent !important;
        border: none !important;
    }}
    
    div[data-baseweb="select"]:hover > div {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* Footer */
    .footer {{
        font-size: 0.85rem;
        color: rgba(160, 160, 160, 0.7);
        text-align: center;
        font-weight: 300;
        letter-spacing: 1px;
    }}
    
    hr {{
        opacity: 0.1;
        border-color: rgba(200, 200, 200, 0.15);
        box-shadow: none;
    }}
    
    /* Expander - transparent */
    .stExpander {{
        background: transparent !important;
        border: none !important;
    }}
    
    .stExpander:hover {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* Caption text */
    .stCaptionContainer, small {{
        color: rgba(160, 160, 160, 0.7) !important;
        font-weight: 300;
    }}
    
    /* File uploader */
    .stFileUploader label {{
        color: rgba(180, 180, 180, 0.8) !important;
    }}
    
    .stFileUploader section {{
        background: transparent !important;
        border: none !important;
    }}
    
    .stFileUploader section:hover {{
        background: transparent !important;
        border: none !important;
    }}
    </style>
    '''
    st.markdown(css_text, unsafe_allow_html=True)

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(docx_file):
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(docx_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(txt_file):
    """Extract text from TXT file."""
    try:
        return txt_file.read().decode('utf-8')
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

def process_uploaded_file(uploaded_file):
    """Process uploaded file and extract content."""
    try:
        uploaded_file.seek(0)
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        if file_extension == '.pdf':
            return extract_text_from_pdf(uploaded_file), "text"
        elif file_extension == '.docx':
            return extract_text_from_docx(uploaded_file), "text"
        elif file_extension == '.txt':
            return extract_text_from_txt(uploaded_file), "text"
        elif file_extension in ['.csv', '.xls', '.xlsx']:
            if file_extension == '.csv':
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            buffer = io.StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()
            summary = f"""The user uploaded a data file named '{uploaded_file.name}'.
This file has been pre-loaded into a pandas DataFrame named `df` which is available in the code execution scope.
When generating Python code for visualization, you MUST use this existing `df` variable directly. DO NOT try to read the file again.

Here is a summary of the `df` DataFrame:

First 5 rows:
{df.head().to_string()}

Data columns and types:
{info_str}
"""
            uploaded_file.seek(0)
            return summary, "text"
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            image = Image.open(uploaded_file)
            return image, "image"
        else:
            return f"Unsupported file type: {file_extension}", "error"
    except Exception as e:
        return f"Error processing file: {str(e)}", "error"

def get_cosmic_response(prompt, cosmic_context, parts=None):
    """Generate response using Gemini API with multi-modal context."""
    try:
        request_parts = [cosmic_context, "\n\n---", f"\n\n**User's Query:** {prompt}"]
        
        if parts:
            request_parts.append("\n\n**Attached Context:**\n")
            request_parts.extend(parts)

        response = model.generate_content(request_parts)
        return response.text
    except Exception as e:
        return f"✨ The cosmic signals are unclear: {str(e)}"

def get_follow_up_suggestions(prompt, response):
    """Generate follow-up questions using the Gemini API."""
    try:
        suggestion_prompt = f"""
        Based on the following exchange:
        User: "{prompt}"
        AI: "{response}"

        Generate three short, distinct, and relevant follow-up questions.
        Return as JSON list of strings.
        Example: ["What is a singularity?", "How do black holes evaporate?", "Are wormholes real?"]
        """
        suggestion_response = model.generate_content(suggestion_prompt)
        json_part = suggestion_response.text.strip().replace("```json", "").replace("```", "")
        suggestions = json.loads(json_part)
        if isinstance(suggestions, list) and all(isinstance(s, str) for s in suggestions):
            return suggestions[:3]
        return []
    except Exception as e:
        return []

def format_chat_as_markdown(messages, session_name):
    """Formats a list of chat messages into a Markdown string."""
    md_string = f"# Chat History: {session_name}\n\n"
    for message in messages:
        role = "🧑‍🚀 User" if message["role"] == "user" else "🌌 AI"
        md_string += f"**{role}:**\n"
        md_string += f"{message['content']}\n\n"
        md_string += "---\n\n"
    return md_string

# --- APP LAYOUT ---
set_page_background_and_style('black_hole (1).png')

# Initialize database
db = init_database()

# Initialize session state
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "audio_to_play" not in st.session_state:
    st.session_state.audio_to_play = None
if "dataframe_for_viz" not in st.session_state:
    st.session_state.dataframe_for_viz = None
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = "Cosmic Intelligence"

# Main content area
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<h1>EVENT   HORIZON</h1>
<h2 class='subtitle'></h2>
""", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# Footer in main area
st.markdown("""
<hr>
<p class='footer'>Understand The Universe</p>
""", unsafe_allow_html=True)

# Sidebar with chat interface
with st.sidebar:
    # --- Persona Selection ---
    st.markdown("### 🎓 AI PERSONA")
    st.session_state.selected_persona = st.selectbox(
        "Choose the AI's identity",
        options=list(PERSONAS.keys()),
        index=list(PERSONAS.keys()).index(st.session_state.selected_persona),
        label_visibility="collapsed"
    )

    st.markdown("### 🌌 CHAT SESSIONS")
    
    # New chat button
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("✨ New Chat", use_container_width=True):
            new_session_id = create_new_session(db, persona_name=st.session_state.selected_persona)
            st.session_state.current_session_id = new_session_id
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("🔄", use_container_width=True):
            st.rerun()
    
    # Search bar
    search_query = st.text_input("🔍 Search history...", placeholder="Filter by name...")

    # Load existing sessions
    sessions = get_all_sessions(db)
    if search_query:
        sessions = [s for s in sessions if search_query.lower() in s.get('session_name', '').lower()]
    
    if sessions:
        st.markdown("---")
        st.markdown("#### HISTORY")
        
        for session in sessions[:10]:
            session_id = session.doc_id
            session_name = session.get('session_name', 'Unnamed Chat')
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if st.button(
                    f" {session_name}",
                    key=f"load_{session_id}",
                    use_container_width=True
                ):
                    st.session_state.current_session_id = session_id
                    st.session_state.messages = load_session_messages(db, session_id)
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{session_id}"):
                    delete_session(db, session_id)
                    if st.session_state.current_session_id == session_id:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                    st.rerun()
    
    # --- Active Session Controls ---
    if st.session_state.current_session_id:
        st.markdown("---")
        st.markdown("#### ACTIVE SESSION")
        current_name = get_session_name(db, st.session_state.current_session_id)

        if st.session_state.get('renaming_session_id') == st.session_state.current_session_id:
            with st.form(key='rename_form'):
                new_name_input = st.text_input("Enter new name", value=current_name)
                if st.form_submit_button("💾 Save"):
                    rename_session(db, st.session_state.current_session_id, new_name_input)
                    del st.session_state.renaming_session_id
                    st.rerun()
        else:
            st.caption(f"📍 {current_name}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Rename", use_container_width=True):
                st.session_state.renaming_session_id = st.session_state.current_session_id
                st.rerun()
        with col2:
            markdown_export = format_chat_as_markdown(st.session_state.messages, current_name)
            st.download_button(
                label="📥 Export",
                data=markdown_export,
                file_name=f"{current_name.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )

    # --- GENESIS ENGINE: On-Demand App Generation ---
    st.markdown("---")
    with st.expander("🚀 Genesis Engine: Create an App"):
        st.markdown("<small>Describe a web tool or dashboard. The AI will generate a complete Streamlit app script for you to download.</small>", unsafe_allow_html=True)
        app_description = st.text_area(
            "Describe the app you want to build...",
            placeholder="e.g., 'An app to track stocks with a price chart and news.'",
            height=150,
            key="genesis_input"
        )

        if st.button("✨ Generate App Script", key="genesis_button", use_container_width=True):
            if app_description:
                with st.spinner("🛠️ Architecting your application... Please wait."):
                    GENESIS_ENGINE_PROMPT = f"""
You are the Genesis Engine, an expert AI software architect specializing in creating self-contained, single-file Streamlit applications.
Your task is to take a user's description of a web tool or dashboard and generate a complete, functional, and well-documented Python script for a Streamlit app.

**Instructions:**
1.  **Standalone Script:** The generated code MUST be a single, complete Python file (`.py`).
2.  **Imports:** Include all necessary imports at the top of the script.
3.  **Data Handling:** If the app requires data, use pandas DataFrames. For sample data, generate it directly within the script (e.g., `pd.DataFrame(...)`) or provide clear instructions on how the user should provide their data (e.g., a file uploader).
4.  **Visualizations:** Use Plotly for any charts or graphs.
5.  **Clarity and Comments:** The code should be clean, well-organized, and include comments to explain complex parts.
6.  **Error Handling:** Include basic error handling where appropriate (e.g., for file uploads or API calls).
7.  **Output Format:** Your response MUST contain ONLY the Python code for the Streamlit app, enclosed in a single ```python ... ``` block. Do not include any other text, explanations, or apologies outside of the code block.

**User's Request:**
{app_description}
"""
                    try:
                        response = model.generate_content(GENESIS_ENGINE_PROMPT)
                        generated_code = response.text.strip()

                        # Extract code from markdown block
                        if generated_code.startswith("```python"):
                            generated_code = generated_code[len("```python"):].strip()
                        if generated_code.endswith("```"):
                            generated_code = generated_code[:-len("```")].strip()
                        
                        st.session_state.generated_app_code = generated_code
                        
                        safe_name = "".join(c for c in app_description if c.isalnum() or c == ' ').strip()
                        safe_name = safe_name.replace(' ', '_').lower()
                        if not safe_name:
                            safe_name = 'generated_app'
                        st.session_state.generated_app_name = f"{safe_name[:40]}.py"

                    except Exception as e:
                        st.error(f"Cosmic interference during generation: {e}")
                        if 'generated_app_code' in st.session_state:
                            del st.session_state.generated_app_code
            else:
                st.warning("Please describe the app you want to build.")

        # Display download button if code has been generated
        if "generated_app_code" in st.session_state and st.session_state.generated_app_code:
            st.success("✅ Your app script is ready!")
            
            def clear_genesis_engine_output():
                st.session_state.pop("generated_app_code", None)
                st.session_state.pop("generated_app_name", None)

            st.download_button(
                label="📥 Download Your App Script",
                data=st.session_state.generated_app_code,
                file_name=st.session_state.get("generated_app_name", "generated_app.py"),
                mime="text/x-python",
                use_container_width=True,
                on_click=clear_genesis_engine_output
            )

    st.markdown("---")
    st.markdown("### COSMIC CHAT")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📎 Attach files",
        type=['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'csv', 'xls', 'xlsx'],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded_files:
        st.markdown("##### ATTACHED FILES:")
        for file in uploaded_files:
            st.markdown(f'<div class="file-badge">📄 {file.name}</div>', unsafe_allow_html=True)
    
    # --- DATA TOOLS (Enhanced with 4 new tools) ---
    data_files = [f for f in uploaded_files if Path(f.name).suffix.lower() in ['.csv', '.xls', '.xlsx']] if uploaded_files else []
    if data_files:
        st.markdown("---")
        st.markdown("#### 🪄 DATA TOOLS")

        # Tool 1: Magic Visualizer
        st.markdown('<div class="data-tool-button">', unsafe_allow_html=True)
        if st.button("✨ Magic Visualizer", use_container_width=True, help="AI-powered auto visualization"):
            if st.session_state.current_session_id is None:
                persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
                st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

            data_file = data_files[0]
            data_file.seek(0)
            if Path(data_file.name).suffix.lower() == '.csv':
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
            st.session_state.dataframe_for_viz = df

            buffer = io.StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()

            viz_prompt = f"""Generate Python code to create an insightful Plotly visualization from this data.
DataFrame `df` is available with these details:
```
{df.head().to_string()}
```
Info:
```
{info_str}
```
Create a single visualization in ```python block. Final figure must be `fig`. Use apply_cosmic_theme(fig, 'Theme Name')."""
            
            user_message_content = f"🎨 Visualize `{data_file.name}`"
            user_message = save_message(db, st.session_state.current_session_id, "user", user_message_content)
            if user_message: st.session_state.messages.append(user_message)

            session_persona_name = get_session_persona(db, st.session_state.current_session_id)
            cosmic_context = PERSONAS.get(session_persona_name, PERSONAS["Cosmic Intelligence"])
            response_code = get_cosmic_response(viz_prompt, cosmic_context, parts=None)
            
            assistant_message = save_message(db, st.session_state.current_session_id, "assistant", response_code)
            if assistant_message: st.session_state.messages.append(assistant_message)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Tool 2: Statistical Analyzer
        st.markdown('<div class="data-tool-button">', unsafe_allow_html=True)
        if st.button("📊 Statistical Analyzer", use_container_width=True, help="Comprehensive statistical analysis"):
            if st.session_state.current_session_id is None:
                persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
                st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

            data_file = data_files[0]
            data_file.seek(0)
            if Path(data_file.name).suffix.lower() == '.csv':
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
            
            stats_dict = statistical_analysis(df)
            stats_text = f"""📊 **Statistical Analysis Report**

**Dataset Shape:** {stats_dict['shape'][0]} rows × {stats_dict['shape'][1]} columns

**Columns:** {', '.join(stats_dict['columns'])}

**Missing Values:**
{chr(10).join([f'• {k}: {v}' for k, v in stats_dict['missing'].items() if v > 0]) or '• No missing values'}

**Numeric Statistics:**
{pd.DataFrame(stats_dict['numeric_stats']).to_string() if stats_dict['numeric_stats'] else 'No numeric columns'}
"""
            
            user_message = save_message(db, st.session_state.current_session_id, "user", f"📊 Analyze `{data_file.name}`")
            if user_message: st.session_state.messages.append(user_message)
            
            assistant_message = save_message(db, st.session_state.current_session_id, "assistant", stats_text)
            if assistant_message: st.session_state.messages.append(assistant_message)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Tool 3: Correlation Matrix
        st.markdown('<div class="data-tool-button">', unsafe_allow_html=True)
        if st.button("🔗 Correlation Matrix", use_container_width=True, help="Visualize correlations between variables"):
            if st.session_state.current_session_id is None:
                persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
                st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

            data_file = data_files[0]
            data_file.seek(0)
            if Path(data_file.name).suffix.lower() == '.csv':
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
            
            fig = correlation_matrix(df)
            
            user_message = save_message(db, st.session_state.current_session_id, "user", f"🔗 Show correlations in `{data_file.name}`")
            if user_message: st.session_state.messages.append(user_message)
            
            if fig:
                # Use pre-loaded df variable
                code_response = f"""```python
import plotly.graph_objects as go

# Using pre-loaded DataFrame 'df'
numeric_cols = df.select_dtypes(include=['number']).columns
corr = df[numeric_cols].corr()

fig = go.Figure(data=go.Heatmap(
    z=corr.values,
    x=corr.columns,
    y=corr.columns,
    colorscale='Viridis',
    text=corr.values,
    texttemplate='%{{text:.2f}}',
    colorbar=dict(title="Correlation")
))
fig.update_layout(title='Correlation Matrix')
apply_cosmic_theme(fig, 'Quantum Foam')
```"""
                st.session_state.dataframe_for_viz = df
                assistant_message = save_message(db, st.session_state.current_session_id, "assistant", code_response)
                if assistant_message: st.session_state.messages.append(assistant_message)
            else:
                assistant_message = save_message(db, st.session_state.current_session_id, "assistant", "⚠️ Not enough numeric columns for correlation analysis.")
                if assistant_message: st.session_state.messages.append(assistant_message)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Tool 4: Trend Detector
        st.markdown('<div class="data-tool-button">', unsafe_allow_html=True)
        if st.button("📈 Trend Detector", use_container_width=True, help="Detect trends using regression analysis"):
            if st.session_state.current_session_id is None:
                persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
                st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

            data_file = data_files[0]
            data_file.seek(0)
            if Path(data_file.name).suffix.lower() == '.csv':
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
            
            fig = trend_detection(df)
            
            user_message = save_message(db, st.session_state.current_session_id, "user", f"📈 Detect trends in `{data_file.name}`")
            if user_message: st.session_state.messages.append(user_message)
            
            if fig:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                col = numeric_cols[0]
                code_response = f"""```python
import plotly.graph_objects as go
import numpy as np
from scipy import stats

# Using pre-loaded DataFrame 'df'
col = '{col}'
data = df[col].dropna()
x = np.arange(len(data))
slope, intercept, r_value, p_value, std_err = stats.linregress(x, data)

fig = go.Figure()
fig.add_trace(go.Scatter(x=x, y=data, mode='markers', name='Data'))
fig.add_trace(go.Scatter(x=x, y=slope*x + intercept, mode='lines', name=f'Trend (R²={{r_value**2:.3f}})'))
fig.update_layout(title=f'Trend Analysis: {{col}}')
apply_cosmic_theme(fig, 'Nebula Burst')
```"""
                st.session_state.dataframe_for_viz = df
                assistant_message = save_message(db, st.session_state.current_session_id, "assistant", code_response)
                if assistant_message: st.session_state.messages.append(assistant_message)
            else:
                assistant_message = save_message(db, st.session_state.current_session_id, "assistant", "⚠️ No numeric columns found for trend analysis.")
                if assistant_message: st.session_state.messages.append(assistant_message)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Tool 5: Distribution Analyzer
        st.markdown('<div class="data-tool-button">', unsafe_allow_html=True)
        if st.button("📉 Distribution Analyzer", use_container_width=True, help="Analyze data distribution patterns"):
            if st.session_state.current_session_id is None:
                persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
                st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

            data_file = data_files[0]
            data_file.seek(0)
            if Path(data_file.name).suffix.lower() == '.csv':
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
            
            fig = distribution_analysis(df)
            
            user_message = save_message(db, st.session_state.current_session_id, "user", f"📉 Analyze distribution in `{data_file.name}`")
            if user_message: st.session_state.messages.append(user_message)
            
            if fig:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                col = numeric_cols[0]
                code_response = f"""```python
import plotly.graph_objects as go

# Using pre-loaded DataFrame 'df'
col = '{col}'

fig = go.Figure()
fig.add_trace(go.Histogram(x=df[col], name='Distribution', marker=dict(color='#7C4DFF'), opacity=0.7))
fig.update_layout(title=f'Distribution: {{col}}', xaxis_title=col, yaxis_title='Frequency')
apply_cosmic_theme(fig, 'Supernova')
```"""
                st.session_state.dataframe_for_viz = df
                assistant_message = save_message(db, st.session_state.current_session_id, "assistant", code_response)
                if assistant_message: st.session_state.messages.append(assistant_message)
            else:
                assistant_message = save_message(db, st.session_state.current_session_id, "assistant", "⚠️ No numeric columns found for distribution analysis.")
                if assistant_message: st.session_state.messages.append(assistant_message)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # Display chat messages
    for message in st.session_state.messages:
        avatar = "🌌" if message["role"] == "assistant" else "🧑‍🚀"
        with st.chat_message(message["role"], avatar=avatar):
            if message["role"] == "assistant":
                col1, col2 = st.columns([10, 1])
                with col1:
                    parts = message['content'].split('```')
                    for i, part in enumerate(parts):
                        if not part.strip():
                            continue
                        
                        if i % 2 == 1:
                            lines = part.split('\n', 1)
                            lang = lines[0].strip()
                            code = lines[1] if len(lines) > 1 else ""

                            if lang == 'python':
                                try:
                                    local_scope = {
                                        'go': go,
                                        'px': px,
                                        'pd': pd,
                                        'np': np,
                                        'stats': stats,
                                        'apply_cosmic_theme': apply_cosmic_theme
                                    }
                                    if 'dataframe_for_viz' in st.session_state and st.session_state.dataframe_for_viz is not None:
                                        local_scope['df'] = st.session_state.dataframe_for_viz

                                    exec(code, local_scope)
                                    
                                    if 'fig' in local_scope:
                                        # Use unique key based on message timestamp and index
                                        chart_key = f"chart_{message['timestamp']}_{i}"
                                        st.plotly_chart(local_scope['fig'], use_container_width=True, theme=None, key=chart_key)
                                        # Don't clear dataframe - keep it for subsequent charts
                                    else:
                                        st.code(code, language='python')

                                except Exception as e:
                                    st.error(f"🔮 Cosmic Interference: {e}")
                                    st.code(code, language='python')
                            else:
                                st.code(code, language=lang if lang else "plaintext")
                        else:
                            st.markdown(part)
                with col2:
                    if st.button("🔊", key=f"play_{message['timestamp']}", help="Read aloud"):
                        st.session_state.audio_to_play = message['content']
                        st.rerun()
            else:
                st.markdown(message["content"])

            if message["role"] == "assistant" and message.get("suggestions"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 💡 Suggested questions:")
                
                num_suggestions = len(message["suggestions"])
                cols = st.columns(num_suggestions)
                for i, suggestion in enumerate(message["suggestions"]):
                    with cols[i]:
                        if st.button(suggestion, key=f"sugg_{message['timestamp']}_{i}", use_container_width=True):
                            st.session_state.chat_input = suggestion
                            st.rerun()

            if "files" in message and message["files"]:
                for file_name in message["files"]:
                    st.caption(f"📎 {file_name}")
    
    # Chat input
    st.markdown("---")
    prompt = st.text_area("💫 Ask the cosmos...", key="chat_input", height=100)
    send_button = st.button("SEND", use_container_width=True)
    
    if send_button and prompt:
        if st.session_state.current_session_id is None:
            persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
            st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

        st.session_state.dataframe_for_viz = None
        if uploaded_files:
            data_files = [f for f in uploaded_files if Path(f.name).suffix.lower() in ['.csv', '.xls', '.xlsx']]
            if data_files:
                data_file = data_files[0]
                data_file.seek(0)
                if Path(data_file.name).suffix.lower() == '.csv':
                    df = pd.read_csv(data_file)
                else:
                    df = pd.read_excel(data_file)
                st.session_state.dataframe_for_viz = df
                data_file.seek(0)

        file_names = []
        gemini_parts = []
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                content, content_type = process_uploaded_file(uploaded_file)
                if content_type != "error":
                    file_names.append(uploaded_file.name)
                    if content_type == "text":
                        gemini_parts.append(f"--- Document: {uploaded_file.name} ---\n{content}\n")
                    elif content_type == "image":
                        gemini_parts.append(f"--- Image: {uploaded_file.name} ---")
                        gemini_parts.append(content)
        
        user_message = save_message(
            db,
            st.session_state.current_session_id,
            "user",
            prompt,
            file_names if file_names else None
        )
        if user_message:
            st.session_state.messages.append(user_message)
        
        session_persona_name = get_session_persona(db, st.session_state.current_session_id)
        cosmic_context = PERSONAS.get(session_persona_name, PERSONAS["Cosmic Intelligence"])

        response = get_cosmic_response(prompt, cosmic_context, parts=gemini_parts)
        suggestions = get_follow_up_suggestions(prompt, response)
        
        assistant_message = save_message(
            db,
            st.session_state.current_session_id,
            "assistant",
            response,
            suggestions=suggestions
        )
        if assistant_message:
            st.session_state.messages.append(assistant_message)
        
        st.rerun()

    # Audio player for TTS
    if st.session_state.audio_to_play:
        try:
            tts = gTTS(text=st.session_state.audio_to_play, lang='en', slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            
            audio_bytes = audio_fp.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
            audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Could not play audio: {e}")
        finally:
            st.session_state.audio_to_play = None
