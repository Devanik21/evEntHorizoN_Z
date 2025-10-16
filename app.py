import streamlit as st
from PIL import Image
import base64
import os
import google.generativeai as genai
import io
import PyPDF2
import docx
from pathlib import Path
import json
from datetime import datetime
from tinydb import TinyDB, Query

# --- PAGE CONFIG ---
st.set_page_config(page_title="Understand the Universe", page_icon="🌌", layout="centered")

# --- CONFIGURE GEMINI API ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    st.error(f"⚠️ API Configuration Error: {str(e)}")

# --- DATABASE FUNCTIONS ---
def init_database():
    """Initialize TinyDB database for chat history."""
    db = TinyDB('cosmic_chats.json')
    return db

def create_new_session(db, session_name=None):
    """Create a new chat session."""
    if session_name is None:
        session_name = f"Cosmic Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    sessions_table = db.table('sessions')
    session_id = sessions_table.insert({
        'session_name': session_name,
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

def save_message(db, session_id, role, content, files=None):
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
        
        messages = session.get('messages', [])
        messages.append(message)
        sessions_table.update({'messages': messages}, doc_ids=[session_id])

def load_session_messages(db, session_id):
    """Load all messages for a session."""
    sessions_table = db.table('sessions')
    session = sessions_table.get(doc_id=session_id)
    
    if session:
        messages = []
        for msg in session.get('messages', []):
            message = {
                'role': msg['role'],
                'content': msg['content']
            }
            if 'files' in msg:
                message['files'] = msg['files']
            messages.append(message)
        return messages
    return []

def delete_session(db, session_id):
    """Delete a chat session."""
    sessions_table = db.table('sessions')
    sessions_table.remove(doc_ids=[session_id])

def get_session_name(db, session_id):
    """Get session name by ID."""
    sessions_table = db.table('sessions')
    session = sessions_table.get(doc_id=session_id)
    return session.get('session_name', 'Unknown') if session else 'Unknown'

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
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            image = Image.open(uploaded_file)
            return image, "image"
        else:
            return f"Unsupported file type: {file_extension}", "error"
    except Exception as e:
        return f"Error processing file: {str(e)}", "error"

def get_cosmic_response(prompt, file_content=None, file_type=None):
    """Generate response using Gemini API with optional file context."""
    try:
        cosmic_context = "You are a cosmic intelligence exploring the mysteries of the universe. Answer questions with wonder, scientific accuracy, and philosophical depth. Keep responses insightful yet accessible."
        
        if file_content and file_type == "text":
            full_prompt = f"{cosmic_context}\n\nDocument context:\n{file_content}\n\nQuestion: {prompt}"
            response = model.generate_content(full_prompt)
        elif file_content and file_type == "image":
            full_prompt = f"{cosmic_context}\n\nQuestion: {prompt}"
            response = model.generate_content([full_prompt, file_content])
        else:
            full_prompt = f"{cosmic_context}\n\nQuestion: {prompt}"
            response = model.generate_content(full_prompt)
        
        return response.text
    except Exception as e:
        return f"✨ The cosmic signals are unclear: {str(e)}"

# --- APP LAYOUT ---
set_page_background_and_style('black_hole.png')

# Initialize database
db = init_database()

# Initialize session state
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Main content area - just the title
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<h1 class='mystic'>♾️</h1>
<h2 class='subtitle'>Understand the universe</h2>
""", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# Footer in main area
st.markdown("""
<hr>
<p class='footer'>A voyage into cosmic intelligence ✨</p>
""", unsafe_allow_html=True)

# Sidebar with chat interface
with st.sidebar:
    st.markdown("### 🌌 Chat Sessions")
    
    # New chat button
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("✨ New Chat", use_container_width=True):
            new_session_id = create_new_session(db)
            st.session_state.current_session_id = new_session_id
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("🔄", use_container_width=True):
            st.rerun()
    
    # Load existing sessions
    sessions = get_all_sessions(db)
    
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
    
    st.markdown("---")
    st.markdown("### 🔮 Cosmic Chat")
    
    # Show current session name
    if st.session_state.current_session_id:
        current_name = get_session_name(db, st.session_state.current_session_id)
        st.caption(f"Current: {current_name}")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📎 Attach files",
        type=['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded_files:
        st.markdown("#### Attached:")
        for file in uploaded_files:
            st.markdown(f'<div class="file-badge">📄 {file.name}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🌌" if message["role"] == "assistant" else "🧑‍🚀"):
            st.markdown(message["content"])
            if "files" in message and message["files"]:
                for file_name in message["files"]:
                    st.caption(f"📎 {file_name}")
    
    # Chat input in sidebar
    prompt = st.text_area("Ask the cosmos...", key="chat_input", height=100)
    send_button = st.button("🪄 Send", use_container_width=True)
    
    if send_button and prompt:
        # Create new session if none exists
        if st.session_state.current_session_id is None:
            st.session_state.current_session_id = create_new_session(db)
        
        # Process uploaded files
        file_contents = []
        file_names = []
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                content, content_type = process_uploaded_file(uploaded_file)
                if content_type != "error":
                    file_contents.append((content, content_type))
                    file_names.append(uploaded_file.name)
        
        # Add user message
        user_message = {"role": "user", "content": prompt}
        if file_names:
            user_message["files"] = file_names
        st.session_state.messages.append(user_message)
        
        # Save to database
        save_message(
            db,
            st.session_state.current_session_id,
            "user",
            prompt,
            file_names if file_names else None
        )
        
        # Generate response
        combined_text = ""
        image_content = None
        
        for content, content_type in file_contents:
            if content_type == "text":
                combined_text += f"\n{content}\n"
            elif content_type == "image":
                image_content = content
        
        if combined_text and image_content:
            response = get_cosmic_response(prompt, combined_text, "text")
        elif image_content:
            response = get_cosmic_response(prompt, image_content, "image")
        elif combined_text:
            response = get_cosmic_response(prompt, combined_text, "text")
        else:
            response = get_cosmic_response(prompt)
        
        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Save to database
        save_message(
            db,
            st.session_state.current_session_id,
            "assistant",
            response
        )
        
        # Rerun to update chat
        st.rerun()
