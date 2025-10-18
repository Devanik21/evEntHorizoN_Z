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

# --- Plotly for Advanced Visualizations ---
import plotly.graph_objects as go
import plotly.express as px

# --- ADVANCED FEATURE IMPORTS (install with pip) ---
from gtts import gTTS  # For Text-to-Speech: pip install gTTS

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
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"]) # Using 1.5 for better multi-modal and code gen
    model = genai.GenerativeModel('gemini-1.5-flash')
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
    # Sort by created_at descending
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
                'timestamp': msg.get('timestamp', datetime.now().isoformat()) # Add timestamp for TTS key
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
    # Default to "Cosmic Intelligence" if not found for backward compatibility
    return session.get('persona_name', 'Cosmic Intelligence') if session else 'Cosmic Intelligence'

# --- VISUALIZATION THEMES (Feature #10) ---
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
    """
    Applies a futuristic, transparent theme to a Plotly figure.
    This function is intended to be available in the exec scope for the AI.
    """
    if theme_name not in COSMIC_THEMES:
        print(f"Warning: Theme '{theme_name}' not found. Defaulting to 'Nebula Burst'.")
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
        margin=dict(l=20, r=20, t=50, b=20) # Adjust margins for better look
    )
    return fig


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
    
    /* Complete transparency for all containers */
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
    section[data-testid="stSidebar"] {{
        background: transparent !important;
        backdrop-filter: none !important;
        border: none !important;
    }}
    
    /* Remove all borders */
    [data-testid="stSidebar"] {{
        border-right: none !important;
    }}
    
    /* Transparent inputs with subtle hover */
    textarea, input {{
        color: white !important;
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
    }}
    
    textarea:hover, input:hover,
    textarea:focus, input:focus {{
        border-color: rgba(255,255,255,0.3) !important;
        box-shadow: 0 0 15px rgba(255,255,255,0.1) !important;
        background: transparent !important;
    }}
    
    /* Force text area transparency */
    .stTextArea textarea {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    
    .stTextArea > div > div {{
        background: transparent !important;
    }}
    
    /* White text everywhere */
    body, h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdown {{
        color: white !important;
        font-family: 'Inter', sans-serif;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-weight: 700;
        text-align: center;
    }}
    
    .subtitle {{
        color: rgba(255,255,255,0.9);
        font-size: 1.3rem;
        margin-top: -10px;
        letter-spacing: 0.5px;
    }}
    
    .mystic {{
        text-shadow: 0 0 30px rgba(255,255,255,0.6);
        letter-spacing: 1.5px;
    }}
    
    /* Transparent chat messages */
    .stChatMessage {{
        background: transparent !important;
        color: white !important;
    }}
    
    .stChatMessage [data-testid="chatAvatarIcon"] {{
        background: transparent !important;
    }}
    
    /* File badges - minimal glass effect */
    .file-badge {{
        display: inline-block;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.2);
        padding: 5px 12px;
        border-radius: 15px;
        margin: 5px;
        font-size: 0.9rem;
        color: white;
        transition: all 0.3s ease;
    }}
    
    .file-badge:hover {{
        background: rgba(255,255,255,0.1);
        border-color: rgba(255,255,255,0.4);
    }}
    
    /* Session badges */
    .session-item {{
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
        cursor: pointer;
        transition: all 0.3s ease;
    }}
    
    .session-item:hover {{
        background: rgba(255,255,255,0.1);
        border-color: rgba(255,255,255,0.3);
    }}
    
    .session-item.active {{
        background: rgba(255,255,255,0.15);
        border-color: rgba(255,255,255,0.4);
    }}
    
    /* Transparent buttons with glow on hover */
    button {{
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: white !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }}
    
    button:hover {{
        background: rgba(255,255,255,0.1) !important;
        border-color: rgba(255,255,255,0.4) !important;
        box-shadow: 0 0 20px rgba(255,255,255,0.2) !important;
    }}
    
    /* Magic visualizer button */
    .magic-button button {{
        background: linear-gradient(45deg, rgba(0, 180, 255, 0.1), rgba(190, 0, 255, 0.1)) !important;
        border: 1px solid rgba(100, 200, 255, 0.4) !important;
        box-shadow: 0 0 15px rgba(100, 200, 255, 0.2) !important;
    }}

    .magic-button button:hover {{
        box-shadow: 0 0 25px rgba(100, 200, 255, 0.5) !important;
        border-color: rgba(100, 200, 255, 0.7) !important;
        background: linear-gradient(45deg, rgba(0, 180, 255, 0.2), rgba(190, 0, 255, 0.2)) !important;
    }}
    
    /* Footer styling */
    .footer {{
        font-size: 0.9rem;
        background: linear-gradient(90deg, #404040, #1a1a1a, #404040);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        font-weight: 500;
    }}
    
    hr {{
        opacity: 0.2;
        border-color: rgba(255,255,255,0.2);
    }}
    
    /* File uploader specific */
    .stFileUploader label {{
        color: white !important;
    }}
    
    .stFileUploader section {{
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
    }}
    
    .stFileUploader section:hover {{
        border-color: rgba(255,255,255,0.3) !important;
    }}
    
    /* Caption text */
    .stCaptionContainer, small {{
        color: rgba(255,255,255,0.7) !important;
    }}
    
    /* Placeholder text */
    ::placeholder {{
        color: rgba(255,255,255,0.4) !important;
    }}
    
    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        background: transparent;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: rgba(255,255,255,0.2);
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(255,255,255,0.3);
    }}
    
    /* Selectbox */
    .stSelectbox {{
        background: transparent !important;
    }}
    
    .stSelectbox > div > div {{
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
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
            
            # For general queries, provide a summary
            buffer = io.StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()
            summary = f"""The user uploaded a data file named '{uploaded_file.name}'.
Here is a summary of its content. Do not show the raw data unless asked.

First 5 rows:
{df.head().to_string()}

Data columns and types:
{info_str}
"""
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
        # Construct the full request
        request_parts = [cosmic_context, "\n\n---", f"\n\n**User's Query:** {prompt}"]
        
        if parts:
            # Prepend a header for the file contexts
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

        Please generate three short, distinct, and relevant follow-up questions the user might be interested in asking next.
        The questions should encourage further exploration of the topic.
        Return the questions as a JSON-formatted list of strings.
        Example: ["What is a singularity?", "How do black holes evaporate?", "Are wormholes real?"]
        """
        suggestion_response = model.generate_content(suggestion_prompt)
        # Clean up the response to extract only the JSON part
        json_part = suggestion_response.text.strip().replace("```json", "").replace("```", "")
        suggestions = json.loads(json_part)
        # Ensure it's a list of strings
        if isinstance(suggestions, list) and all(isinstance(s, str) for s in suggestions):
            return suggestions[:3] # Return at most 3
        return []
    except (json.JSONDecodeError, TypeError, Exception) as e:
        # If JSON parsing fails or any other error, return an empty list
        print(f"Could not generate/parse follow-up suggestions: {e}")
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

# Main content area - just the title
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<h1 class='mystic'></h1>
<h2 class='subtitle'>Understand the universe</h2>
""", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# Footer in main area
st.markdown("""
<hr>
<p class='footer'></p>
""", unsafe_allow_html=True)

# Sidebar with chat interface
with st.sidebar:
    # --- Persona Selection ---
    st.markdown("### 🧠 AI Persona")
    st.session_state.selected_persona = st.selectbox(
        "Choose the AI's identity",
        options=list(PERSONAS.keys()),
        index=list(PERSONAS.keys()).index(st.session_state.selected_persona),
        label_visibility="collapsed"
    )

    st.markdown("### 🌌 Chat Sessions")
    
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
    search_query = st.text_input("Search history...", placeholder="Filter by name...")

    # Load existing sessions
    sessions = get_all_sessions(db)
    if search_query:
        sessions = [s for s in sessions if search_query.lower() in s.get('session_name', '').lower()]
    
    if sessions:
        st.markdown("---")
        st.markdown("#### History")
        
        for session in sessions[:10]:  # Show last 10 sessions
            session_id = session.doc_id
            session_name = session.get('session_name', 'Unnamed Chat')
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if st.button(
                    f"💬 {session_name}",
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
        st.markdown("#### Active Session")
        current_name = get_session_name(db, st.session_state.current_session_id)

        # Rename UI
        if st.session_state.get('renaming_session_id') == st.session_state.current_session_id:
            with st.form(key='rename_form'):
                new_name_input = st.text_input("Enter new name", value=current_name)
                if st.form_submit_button("Save Name"):
                    rename_session(db, st.session_state.current_session_id, new_name_input)
                    del st.session_state.renaming_session_id
                    st.rerun()
        else:
            st.caption(f"Topic: {current_name}")

        # Control Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Rename", use_container_width=True, help="Rename this chat session"):
                st.session_state.renaming_session_id = st.session_state.current_session_id
                st.rerun()
        with col2:
            markdown_export = format_chat_as_markdown(st.session_state.messages, current_name)
            st.download_button(
                label="📥 Export",
                data=markdown_export,
                file_name=f"{current_name.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True,
                help="Export chat to Markdown file"
            )

    st.markdown("---")
    st.markdown("### 🔮 Cosmic Chat")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📎 Attach files",
        type=['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'csv', 'xls', 'xlsx'],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded_files:
        st.markdown("##### Attached:")
        for file in uploaded_files:
            st.markdown(f'<div class="file-badge">📄 {file.name}</div>', unsafe_allow_html=True)
    
    # --- Magic Visualizer ---
    data_files = [f for f in uploaded_files if Path(f.name).suffix.lower() in ['.csv', '.xls', '.xlsx']] if uploaded_files else []
    if data_files:
        st.markdown("---")
        st.markdown("#### 🪄 Data Tools")
        st.markdown('<div class="magic-button">', unsafe_allow_html=True)
        if st.button("Magic Visualizer", use_container_width=True, help=f"Automatically visualize {data_files[0].name}"):
            if st.session_state.current_session_id is None:
                persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
                st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

            data_file = data_files[0]
            data_file.seek(0)  # Reset file pointer as it might have been read
            if Path(data_file.name).suffix.lower() == '.csv':
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
            
            st.session_state.dataframe_for_viz = df

            buffer = io.StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()

            viz_prompt = f"""The user wants to visualize the uploaded file: '{data_file.name}'.
A pandas DataFrame named `df` has been created from this file and is available in the execution scope.
Here is the head of the DataFrame:
```
{df.head().to_string()}
```
Here is the DataFrame's info:
```
{info_str}
```
Your task is to generate Python code to create a single, insightful Plotly visualization from this `df`.
The code should be a complete, runnable script within a single ```python block.
The final figure object MUST be named `fig`.
You MUST use one of the available cosmic themes by calling `apply_cosmic_theme(fig, 'Theme Name')` at the end of your script.
Respond with only the Python code block, without any additional explanation.
"""
            user_message_content = f"Visualize the data in `{data_file.name}`."
            user_message = save_message(db, st.session_state.current_session_id, "user", user_message_content)
            if user_message: st.session_state.messages.append(user_message)

            session_persona_name = get_session_persona(db, st.session_state.current_session_id)
            cosmic_context = PERSONAS.get(session_persona_name, PERSONAS["Cosmic Intelligence"])
            response_code = get_cosmic_response(viz_prompt, cosmic_context, parts=None)
            
            assistant_message = save_message(db, st.session_state.current_session_id, "assistant", response_code)
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
                    # --- Feature: Enhanced Code Rendering ---
                    parts = message['content'].split('```')
                    for i, part in enumerate(parts):
                        if not part.strip():
                            continue
                        
                        if i % 2 == 1:
                            lines = part.split('\n', 1)
                            lang = lines[0].strip()
                            code = lines[1] if len(lines) > 1 else ""

                            # --- Feature #10: Interactive Cosmic Visualizations ---
                            if lang == 'python':
                                try:
                                    # Prepare a safe execution scope
                                    local_scope = {
                                        'go': go,
                                        'px': px,
                                        'pd': pd,
                                        'apply_cosmic_theme': apply_cosmic_theme
                                    }
                                    # Add dataframe to scope if it exists for visualization
                                    if 'dataframe_for_viz' in st.session_state and st.session_state.dataframe_for_viz is not None:
                                        local_scope['df'] = st.session_state.dataframe_for_viz

                                    exec(code, local_scope)
                                    
                                    if 'fig' in local_scope:
                                        # A plot was successfully generated
                                        st.plotly_chart(local_scope['fig'], use_container_width=True, theme=None)
                                        # Clean up dataframe from session state after use
                                        if 'dataframe_for_viz' in st.session_state:
                                            st.session_state.dataframe_for_viz = None
                                    else:
                                        # The python code did not generate a 'fig' object, so just show the code
                                        st.code(code, language='python')


                                except Exception as e:
                                    st.error(f"🔮 Cosmic Interference: Could not render visualization. Error: {e}")
                                    st.code(code, language='python') # Show the code that failed
                            else:
                                # It's a code block, but not for a plot we can execute
                                st.code(code, language=lang if lang else "plaintext")
                        else: # Even-indexed parts are regular markdown text
                            st.markdown(part)
                with col2:
                    if st.button("🔊", key=f"play_{message['timestamp']}", help="Read aloud"):
                        st.session_state.audio_to_play = message['content']
                        st.rerun()
            else:
                st.markdown(message["content"])

            # --- Feature: Proactive Follow-up Suggestions ---
            if message["role"] == "assistant" and message.get("suggestions"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("###### You might also want to ask:")
                
                # Use columns for a neat layout
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
    
    # Chat input in sidebar
    st.markdown("---")
    prompt = st.text_area("Ask the cosmos...", key="chat_input", height=100)
    send_button = st.button("🪄 Send", use_container_width=True)
    
    if send_button and prompt:
        # Create new session if none exists
        if st.session_state.current_session_id is None:
            persona_name = st.session_state.get('selected_persona', 'Cosmic Intelligence')
            st.session_state.current_session_id = create_new_session(db, persona_name=persona_name)

        # If a data file is attached, load it into a dataframe for visualization.
        # This makes regular chat prompts visualization-aware, fixing the 'df is not defined' error.
        st.session_state.dataframe_for_viz = None # Clear previous df
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
                data_file.seek(0) # Reset pointer for the next processing step

        # Process uploaded files
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
        
        # Save user message to DB and add to session state
        user_message = save_message(
            db,
            st.session_state.current_session_id,
            "user",
            prompt,
            file_names if file_names else None
        )
        if user_message:
            st.session_state.messages.append(user_message)
        
        # Get the persona for the current session
        session_persona_name = get_session_persona(db, st.session_state.current_session_id)
        cosmic_context = PERSONAS.get(session_persona_name, PERSONAS["Cosmic Intelligence"])

        # Generate response
        response = get_cosmic_response(prompt, cosmic_context, parts=gemini_parts)
        suggestions = get_follow_up_suggestions(prompt, response)
        
        # Add assistant response
        assistant_message = save_message(
            db,
            st.session_state.current_session_id,
            "assistant",
            response,
            suggestions=suggestions
        )
        if assistant_message:
            st.session_state.messages.append(assistant_message)
        
        # Rerun to update chat
        st.rerun()

    # Hidden audio player for Text-to-Speech
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
            # Reset the state
            st.session_state.audio_to_play = None
