import streamlit as st
import hashlib
import time
import hmac
from datetime import datetime, timedelta
from tinydb import TinyDB, Query
import socket
import platform
import uuid
import base64
import os

# ============================================================================
# SECURITY INITIALIZATION
# ============================================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'attempts' not in st.session_state:
    st.session_state.attempts = 0
if 'locked' not in st.session_state:
    st.session_state.locked = False
if 'lockout_time' not in st.session_state:
    st.session_state.lockout_time = None
if 'paranoid_mode' not in st.session_state:
    st.session_state.paranoid_mode = False
if 'security_level' not in st.session_state:
    st.session_state.security_level = 0
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = datetime.now()
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None

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

set_page_background_and_style('Gemini_Generated_Image_uou8nluou8nluou8.png')

# ============================================================================
# LOAD SECRETS
# ============================================================================
try:
    MASTER_KEY = st.secrets["master_key"]  # Your unique complex key
    DEVICE_ID = st.secrets.get("authorized_device_id", None)
    
    # Paranoid mode credentials (if first check fails)
    MASTER_PASSWORD = st.secrets.get("master_password", "")
    SECRET_PIN = st.secrets.get("secret_pin", "")
    SECURITY_QUESTION = st.secrets.get("security_question", "")
    SECURITY_ANSWER = st.secrets.get("security_answer", "")
    PATTERN_CODE = st.secrets.get("pattern_code", "")
    BIOMETRIC_HASH = st.secrets.get("biometric_hash", "")
    TEMPORAL_CODE = st.secrets.get("temporal_code", "")
    CRYPTO_CHALLENGE = st.secrets.get("crypto_challenge", "")
    SESSION_TIMEOUT = int(st.secrets.get("session_timeout_minutes", 15))

    # ========================================================================
    # NIGHTMARE MODE SECRETS (Layers 9-20)
    # Add these to your .streamlit/secrets.toml file for the new layers
    # ========================================================================
    VIGENERE_CIPHERTEXT = st.secrets.get("vigenere_ciphertext", "Lsfw, Tpil!")
    VIGENERE_KEY = st.secrets.get("vigenere_key", "KEY")
    VIGENERE_PLAINTEXT = st.secrets.get("vigenere_plaintext", "Hello, World!")

    LOGIC_PUZZLE_QUESTION = st.secrets.get("logic_puzzle_question", "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?")
    LOGIC_PUZZLE_ANSWER = st.secrets.get("logic_puzzle_answer", "A map")

    PRIME_CHALLENGE_N = st.secrets.get("prime_challenge_n", "100")
    PRIME_CHALLENGE_ANSWER = st.secrets.get("prime_challenge_answer", "541")

    HISTORY_QUESTION = st.secrets.get("history_question", "What was the name of the horse that Roman emperor Caligula appointed as consul?")
    HISTORY_ANSWER = st.secrets.get("history_answer", "Incitatus")

    COLOR_SEQUENCE_PROMPT = st.secrets.get("color_sequence_prompt", "Red, Green, Blue")
    COLOR_SEQUENCE_ANSWER = st.secrets.get("color_sequence_answer", "#FF0000#008000#0000FF")

    MORSE_CODE_PROMPT = st.secrets.get("morse_code_prompt", "-. . ...- . .-. / --. --- -. -. .- / --. .. ...- . / -.-- --- ..- / ..- .--")
    MORSE_CODE_ANSWER = st.secrets.get("morse_code_answer", "NEVER GONNA GIVE YOU UP")

    RPN_CHALLENGE = st.secrets.get("rpn_challenge", "5 1 2 + 4 * + 3 -")
    RPN_ANSWER = st.secrets.get("rpn_answer", "14")

    ASCII_ART_PROMPT = st.secrets.get("ascii_art_prompt", "  /\\_/\\ \n ( o.o ) \n  > ^ < ")
    ASCII_ART_ANSWER = st.secrets.get("ascii_art_answer", "cat")

    IMPOSSIBLE_QUESTION = st.secrets.get("impossible_question", "What is the airspeed velocity of an unladen swallow?")
    IMPOSSIBLE_ANSWER = st.secrets.get("impossible_answer", "African or European?")

    FINAL_INSULT_QUESTION = st.secrets.get("final_insult_question", "What is 2 + 2?")
    FINAL_INSULT_ANSWER = st.secrets.get("final_insult_answer", "4")

    TRUE_FINAL_KEY = st.secrets.get("true_final_key", "mercy")
except Exception as e:
    st.error("⚠️ Security configuration error.")
    st.stop()

# ============================================================================
# DEVICE FINGERPRINTING
# ============================================================================
def generate_device_fingerprint():
    """Generate unique device fingerprint"""
    try:
        hostname = socket.gethostname()
        platform_info = platform.platform()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,2*6,2)][::-1])
        fingerprint = f"{hostname}_{platform_info}_{mac}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()
    except:
        return None

# ============================================================================
# MASTER KEY VERIFICATION (Fast Track for YOU)
# ============================================================================
def verify_master_key(key, device_id=None):
    """
    Single-step verification for the owner.
    Returns a status code:
    - 0: Success (key and device match)
    - 1: Wrong Key
    - 2: Right Key, Wrong Device
    """
    # Hash the master key from secrets and the provided key
    master_key_hash = hashlib.sha512(MASTER_KEY.encode()).hexdigest()
    provided_key_hash = hashlib.sha512(key.encode()).hexdigest()
    
    # 1. First, check if the key itself is correct.
    if provided_key_hash != master_key_hash:
        return 1  # Wrong Key

    # 2. If the key is correct, check the device ID (if it's configured).
    if device_id:
        current_device = generate_device_fingerprint()
        if current_device != device_id:
            return 2  # Right Key, Wrong Device
    
    # 3. If we reach here, the key is correct and the device matches (or isn't set).
    return 0  # Success

# ============================================================================
# LOCKOUT CHECK
# ============================================================================
def check_lockout_status():
    if st.session_state.lockout_time:
        time_diff = datetime.now() - st.session_state.lockout_time
        if time_diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - time_diff
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return True, f"{hours}h {minutes}m {seconds}s"
        else:
            st.session_state.locked = False
            st.session_state.lockout_time = None
            st.session_state.attempts = 0
            st.session_state.paranoid_mode = False
    return False, None

# ============================================================================
# SESSION TIMEOUT
# ============================================================================
def check_session_timeout():
    if st.session_state.authenticated:
        time_diff = datetime.now() - st.session_state.last_activity
        if time_diff > timedelta(minutes=SESSION_TIMEOUT):
            st.session_state.authenticated = False
            st.session_state.security_level = 0
            st.session_state.paranoid_mode = False
            return True
    st.session_state.last_activity = datetime.now()
    return False

# ============================================================================
# MAIN SECURITY CHECK
# ============================================================================

# Check lockout
is_locked, remaining_time = check_lockout_status()
if is_locked:
    st.error(f"🔒 SYSTEM LOCKED FOR 24 HOURS")
    st.warning(f"⏰ Time remaining: {remaining_time}")
    st.divider()
    st.markdown("### 💀 You Failed")
    st.info("The system detected unauthorized access and initiated lockdown protocol.")
    st.caption("🎯 Better luck next time... if you dare try again.")
    st.markdown("---")
    st.markdown("**😈 Owner's Message:**")
    st.success("'Nice try, but this fortress is unbreachable. Come back tomorrow and fail again.' - The Owner")
    st.stop()

# Check session timeout
if check_session_timeout():
    st.warning("⏱️ Session expired. Please login again.")
    time.sleep(1)
    st.rerun()

# ============================================================================
# AUTHENTICATION
# ============================================================================

if not st.session_state.authenticated:
    
    # ========================================================================
    # FAST TRACK: Single Master Key (For YOU)
    # ========================================================================
    if not st.session_state.paranoid_mode:
        st.title("🔐 Secure Access")
        
        master_key = st.text_input("Master Key", type="password", key="master_key_input")
        
        if st.button("Unlock", type="primary"):
            verification_result = verify_master_key(master_key, DEVICE_ID)

            if verification_result == 0:
                # SUCCESS - Instant access for YOU
                st.session_state.authenticated = True
                st.session_state.attempts = 0
                st.session_state.last_activity = datetime.now()
                st.success("✓ Access Granted")
                time.sleep(0.3)
                st.rerun()
            
            elif verification_result == 2:
                # RIGHT KEY, WRONG DEVICE - Show recovery info
                st.error("❌ Master Key is correct, but Device ID has changed.")
                st.warning("This can happen if your network or hardware configuration changes. Please update your secrets file.")
                current_device = generate_device_fingerprint()
                st.markdown("**Your NEW Device ID is:**")
                st.code(current_device, language="text")
                st.markdown("**Update this line in `.streamlit/secrets.toml`:**")
                st.code(f'authorized_device_id = "{current_device}"', language="toml")

            else: # verification_result == 1 (Wrong Key)
                # WRONG KEY - Trigger paranoid mode (potential thief)
                st.session_state.attempts += 1
                st.session_state.paranoid_mode = True
                st.error("⚠️ SECURITY BREACH DETECTED")
                time.sleep(0.5)
                st.rerun()
        
        # Show device setup if needed
        if not DEVICE_ID:
            with st.expander("⚙️ First Time Setup - Device Registration"):
                st.warning("**Device ID not configured. Complete setup for maximum security.**")
                current_device = generate_device_fingerprint()
                st.code(current_device, language="text")
                st.markdown("**Add this to `.streamlit/secrets.toml`:**")
                st.code(f'authorized_device_id = "{current_device}"', language="toml")
    
    # ========================================================================
    # PARANOID MODE: Multi-Layer Defense (For Thieves)
    # ========================================================================
    else:
        st.title("🚨 SECURITY BREACH DETECTED")
        st.error("⚠️ UNAUTHORIZED ACCESS ATTEMPT IN PROGRESS")
        
        # Intimidation header
        st.warning("⏱️ All attempts are being logged and traced...")
        st.caption(f"🔍 IP Tracking Active | 📍 Location: Agartala, Tripura, IN | ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show attempt counter prominently
        if st.session_state.attempts > 0:
            st.error(f"SYSTEM INTEGRITY COMPROMISED. ATTEMPT {st.session_state.attempts}/3 LOGGED.")
        
        st.divider()
        
        # Difficulty indicator
        progress_text = f"Security Layer {st.session_state.security_level + 1} of 20"
        st.progress((st.session_state.security_level) / 20, text=progress_text)
        
        st.markdown("---")
        
        # LAYER 1: Password
        if st.session_state.security_level == 0:
            st.subheader("🔐 Layer 1: Master Password")
            password = st.text_input("Password", type="password", key="pwd")
            
            if st.button("Verify", type="primary", key="btn1"):
                if password == MASTER_PASSWORD:
                    st.session_state.security_level = 1
                    st.success("✓ Layer 1 cleared... 7 more to go")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts >= 3:
                        st.session_state.locked = True
                        st.session_state.lockout_time = datetime.now()
                        st.error("🔒 ACCESS DENIED. 24-HOUR LOCKOUT INITIATED.")
                        st.info("Your attempts have been futile. The system is now sealed.")
                        time.sleep(3)
                        st.rerun()
                    st.rerun() # Psychological warfare: just refresh, no feedback
        
        # LAYER 2: PIN
        elif st.session_state.security_level == 1:
            st.success("✓ Layer 1: Password - CLEARED")
            st.subheader("🔢 Layer 2: Secret PIN")
            pin = st.text_input("PIN Code", type="password", key="pin")
            
            if st.button("Verify", type="primary", key="btn2"):
                if pin == SECRET_PIN:
                    st.session_state.security_level = 2
                    st.success("✓ Layer 2 cleared... impressive, but 6 more remain")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts >= 3:
                        st.session_state.locked = True
                        st.session_state.lockout_time = datetime.now()
                        st.error("🔒 ACCESS DENIED. 24-HOUR LOCKOUT INITIATED.")
                        st.info("Your persistence is admirable, but ultimately pointless. Goodbye.")
                        time.sleep(3)
                        st.rerun()
                    st.rerun() # Psychological warfare
        
        # LAYER 3: Security Question
        elif st.session_state.security_level == 2:
            st.success("✓ Layer 1: Password - CLEARED")
            st.success("✓ Layer 2: PIN - CLEARED")
            st.subheader("❓ Layer 3: Cryptographic Challenge")
            st.info(f"**Question:** {SECURITY_QUESTION}")
            answer = st.text_input("Answer", type="password", key="ans")
            
            if st.button("Verify", type="primary", key="btn3"):
                if answer.lower().strip() == SECURITY_ANSWER.lower().strip():
                    st.session_state.security_level = 3
                    st.success("✓ Layer 3 cleared... you're persistent. 5 more layers.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts >= 3:
                        st.session_state.locked = True
                        st.session_state.lockout_time = datetime.now()
                        st.error("🔒 ACCESS DENIED. 24-HOUR LOCKOUT INITIATED.")
                        st.info("You have failed the final test of wit. The gate is closed.")
                        time.sleep(3)
                        st.rerun()
                    st.rerun() # Psychological warfare
        
        # LAYER 4: Device Check
        elif st.session_state.security_level == 3:
            st.success("✓ Layers 1-3: CLEARED")
            st.subheader("💻 Layer 4: Hardware Verification")
            
            current_device = generate_device_fingerprint()
            
            with st.spinner("Scanning hardware signature..."):
                time.sleep(2)
            
            if DEVICE_ID and current_device == DEVICE_ID:
                st.session_state.security_level = 4
                st.success("✓ Authorized device detected")
                time.sleep(0.5)
                st.rerun()
            else:
                # The ultimate punishment: instant, unavoidable failure.
                st.error("FATAL SECURITY EXCEPTION: HARDWARE MISMATCH")
                st.warning("This path is closed to you. It was never open.")
                st.session_state.locked = True
                st.session_state.lockout_time = datetime.now()
                time.sleep(3)
                st.rerun()
        
        # LAYER 5: Pattern Lock
        elif st.session_state.security_level == 4:
            st.success("✓ Layers 1-4: CLEARED")
            st.subheader("🎯 Layer 5: Pattern Sequence")
            st.info("Follow the path.")
            pattern = st.text_input("Pattern Code", type="password", key="pattern")
            
            if st.button("Verify", type="primary", key="btn5"):
                if pattern == PATTERN_CODE:
                    st.session_state.security_level = 5
                    st.success("✓ Layer 5 cleared... unbelievable. 3 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("SEQUENCE INVALID. PROTOCOL VIOLATION.")
                    st.warning("You have strayed from the path. There is no recovery.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()
        
        # LAYER 6: Biometric Hash
        elif st.session_state.security_level == 5:
            st.success("✓ Layers 1-5: CLEARED")
            st.subheader("🧬 Layer 6: Biometric Signature")
            st.info("Provide your unique biological key.")
            bio_input = st.text_input("Biometric Code", type="password", key="bio")
            
            if st.button("Verify", type="primary", key="btn6"):
                bio_hash = hashlib.sha256(bio_input.encode()).hexdigest()
                if bio_hash == BIOMETRIC_HASH:
                    st.session_state.security_level = 6
                    st.success("✓ Layer 6 cleared... you're incredible. 2 more.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("BIOMETRIC SIGNATURE REJECTED.")
                    st.warning("Your very essence is incorrect. This system does not recognize you.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()
        
        # LAYER 7: Temporal Code
        elif st.session_state.security_level == 6:
            st.success("✓ Layers 1-6: CLEARED")
            st.subheader("⏰ Layer 7: Temporal Authentication")
            st.info("Synchronize with the timeline.")
            temporal = st.text_input("Temporal Code", type="password", key="temp")
            
            if st.button("Verify", type="primary", key="btn7"):
                if temporal == TEMPORAL_CODE:
                    st.session_state.security_level = 7
                    st.success("✓ Layer 7 cleared... ONE FINAL LAYER REMAINS")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("TEMPORAL ANOMALY DETECTED.")
                    st.warning("You are out of sync with reality. Access denied across all timelines.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()
        
        # LAYER 8: Final Cryptographic Challenge
        elif st.session_state.security_level == 7:
            st.success("✓ Layers 1-7: ALL CLEARED")
            st.subheader("🔥 Layer 8: Cryptographic Proof")
            st.error("This is a difficult barrier. There are no second chances.")
            crypto = st.text_input("Cryptographic Key", type="password", key="crypto")
            
            if st.button("Verify", type="primary", key="btn8"):
                crypto_verify = hmac.new(
                    MASTER_PASSWORD.encode(),
                    crypto.encode(),
                    hashlib.sha512
                ).hexdigest()
                
                if crypto_verify == CRYPTO_CHALLENGE:
                    st.session_state.security_level = 8
                    st.success("✓ Layer 8 cleared... The real challenge begins now. 12 more layers.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("FINAL VERIFICATION FAILED. ALL HOPE IS LOST.")
                    st.warning("You reached the end only to fail. The ultimate despair.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()
        
        # LAYER 9: Vigenère Cipher
        elif st.session_state.security_level == 8:
            st.success("✓ Layers 1-8: CLEARED")
            st.subheader("📜 Layer 9: Vigenère Cipher")
            st.info("An old-school challenge. Decode the message.")
            st.code(f"Ciphertext: {VIGENERE_CIPHERTEXT}\nKey: {VIGENERE_KEY}", language="text")
            answer = st.text_input("Decoded Plaintext", key="vigenere")
            
            if st.button("Verify", type="primary", key="btn9"):
                if answer.strip() == VIGENERE_PLAINTEXT:
                    st.session_state.security_level = 9
                    st.success("✓ Layer 9 cleared. A classicist. 11 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("DECRYPTION FAILED. The secrets remain hidden.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 10: Logic Puzzle
        elif st.session_state.security_level == 9:
            st.success("✓ Layers 1-9: CLEARED")
            st.subheader("🧠 Layer 10: Logic Puzzle")
            st.info(LOGIC_PUZZLE_QUESTION)
            answer = st.text_input("Your Answer", key="logic")
            
            if st.button("Verify", type="primary", key="btn10"):
                if answer.strip().lower() == LOGIC_PUZZLE_ANSWER.lower():
                    st.session_state.security_level = 10
                    st.success("✓ Layer 10 cleared. A sharp mind. 10 to go.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("LOGIC ERROR. Your reasoning is flawed.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 11: Prime Number Challenge
        elif st.session_state.security_level == 10:
            st.success("✓ Layers 1-10: CLEARED")
            st.subheader(f"🔢 Layer 11: Prime Number Challenge")
            st.info(f"What is the {PRIME_CHALLENGE_N}th prime number?")
            answer = st.text_input("Prime Number", key="prime")
            
            if st.button("Verify", type="primary", key="btn11"):
                if answer.strip() == PRIME_CHALLENGE_ANSWER:
                    st.session_state.security_level = 11
                    st.success("✓ Layer 11 cleared. Mathematically inclined. 9 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("CALCULATION ERROR. The numbers do not align.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 12: Historical Trivia
        elif st.session_state.security_level == 11:
            st.success("✓ Layers 1-11: CLEARED")
            st.subheader("🏛️ Layer 12: Historical Trivia")
            st.info(HISTORY_QUESTION)
            answer = st.text_input("Answer", key="history")
            
            if st.button("Verify", type="primary", key="btn12"):
                if answer.strip().lower() == HISTORY_ANSWER.lower():
                    st.session_state.security_level = 12
                    st.success("✓ Layer 12 cleared. A historian, I see. 8 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("HISTORICAL INACCURACY. The past is not on your side.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 13: Color Hex Code
        elif st.session_state.security_level == 12:
            st.success("✓ Layers 1-12: CLEARED")
            st.subheader("🎨 Layer 13: Color Code Challenge")
            st.info(f"Concatenate the standard hex codes for the following colors: {COLOR_SEQUENCE_PROMPT}")
            answer = st.text_input("Hex String", key="color")
            
            if st.button("Verify", type="primary", key="btn13"):
                if answer.strip().upper() == COLOR_SEQUENCE_ANSWER.upper():
                    st.session_state.security_level = 13
                    st.success("✓ Layer 13 cleared. A colorful mind. 7 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("COLOR MISMATCH. Your spectrum is off.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 14: Morse Code
        elif st.session_state.security_level == 13:
            st.success("✓ Layers 1-13: CLEARED")
            st.subheader("📡 Layer 14: Morse Code")
            st.info("An urgent message has arrived. Decode it.")
            st.code(MORSE_CODE_PROMPT, language="text")
            answer = st.text_input("Message", key="morse")
            
            if st.button("Verify", type="primary", key="btn14"):
                if answer.strip().upper() == MORSE_CODE_ANSWER.upper():
                    st.session_state.security_level = 14
                    st.success("✓ Layer 14 cleared. You read the signals. 6 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("TRANSMISSION GARBLED. Message not understood.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 15: Reverse Polish Notation
        elif st.session_state.security_level == 14:
            st.success("✓ Layers 1-14: CLEARED")
            st.subheader("🧮 Layer 15: Reverse Polish Notation")
            st.info("Calculate the value of the following expression:")
            st.code(RPN_CHALLENGE, language="text")
            answer = st.text_input("Result", key="rpn")
            
            if st.button("Verify", type="primary", key="btn15"):
                if answer.strip() == RPN_ANSWER:
                    st.session_state.security_level = 15
                    st.success("✓ Layer 15 cleared. Your logic is backwards, yet correct. 5 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("STACK OVERFLOW. Calculation incorrect.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 16: ASCII Art Recognition
        elif st.session_state.security_level == 15:
            st.success("✓ Layers 1-15: CLEARED")
            st.subheader("🖼️ Layer 16: ASCII Art Recognition")
            st.info("What creature is this?")
            st.code(ASCII_ART_PROMPT, language="text")
            answer = st.text_input("Creature", key="ascii")
            
            if st.button("Verify", type="primary", key="btn16"):
                if answer.strip().lower() == ASCII_ART_ANSWER.lower():
                    st.session_state.security_level = 16
                    st.success("✓ Layer 16 cleared. You see through the noise. 4 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("PATTERN UNRECOGNIZED. Your eyes deceive you.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 17: The Waiting Game
        elif st.session_state.security_level == 16:
            st.success("✓ Layers 1-16: CLEARED")
            st.subheader("⏳ Layer 17: The Waiting Game")
            st.info("Patience is a virtue. Prove yours.")
            st.warning("The system is performing a deep integrity scan. This will take time. Do not refresh the page.")
            
            if st.button("Begin Scan", type="primary", key="btn17"):
                with st.spinner("Scanning... 2 minutes remaining..."):
                    time.sleep(20) # NOTE: Shortened for practical use. Increase for more pain.
                with st.spinner("Defragmenting memory sectors... 1 minute remaining..."):
                    time.sleep(10)
                with st.spinner("Verifying quantum entanglement... 30 seconds remaining..."):
                    time.sleep(5)
                
                st.session_state.security_level = 17
                st.success("✓ Layer 17 cleared. Your patience is... noted. 3 remain.")
                time.sleep(1)
                st.rerun()

        # LAYER 18: The Impossible Question
        elif st.session_state.security_level == 17:
            st.success("✓ Layers 1-17: CLEARED")
            st.subheader("🤔 Layer 18: The Impossible Question")
            st.info(IMPOSSIBLE_QUESTION)
            answer = st.text_input("Answer", key="swallow")
            
            if st.button("Verify", type="primary", key="btn18"):
                if answer.strip().lower() == IMPOSSIBLE_ANSWER.lower():
                    st.session_state.security_level = 18
                    st.success("✓ Layer 18 cleared. You know your Monty Python. 2 remain.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("INCORRECT. You have been cast into the Gorge of Eternal Peril.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 19: The Final Insult
        elif st.session_state.security_level == 18:
            st.success("✓ Layers 1-18: CLEARED")
            st.subheader("🤡 Layer 19: The Final Insult")
            st.info("After all those challenges, a simple test of basic arithmetic.")
            st.error(f"What is {FINAL_INSULT_QUESTION}?")
            answer = st.text_input("Answer", key="insult")
            
            if st.button("Verify", type="primary", key="btn19"):
                if answer.strip() == FINAL_INSULT_ANSWER:
                    st.session_state.security_level = 19
                    st.success("✓ Layer 19 cleared. You didn't overthink it. The final layer awaits.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("To fail on this... is the greatest shame. Lockout initiated.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()

        # LAYER 20: The True Final Key
        elif st.session_state.security_level == 19:
            st.success("✓ Layers 1-19: CLEARED")
            st.subheader("🔑 Layer 20: The Final Key")
            st.info("After all that, you deserve a simple end. Or do you?")
            st.warning("The key is a single word. A plea.")
            answer = st.text_input("The Final Word", type="password", key="finalkey")
            
            if st.button("Unlock", type="primary", key="btn20"):
                if answer.strip().lower() == TRUE_FINAL_KEY.lower():
                    st.session_state.security_level = 20
                    st.balloons()
                    st.success("✓ Layer 20 cleared. The system is yours.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("SO CLOSE. You fell at the final hurdle. The ultimate failure.")
                    st.session_state.locked = True
                    st.session_state.lockout_time = datetime.now()
                    time.sleep(3)
                    st.rerun()
        
        # FINAL: Grant Access
        elif st.session_state.security_level == 20:
            st.session_state.authenticated = True
            st.session_state.attempts = 0
            st.session_state.paranoid_mode = False
            st.session_state.security_level = 0
            st.success("All 20 layers passed - Access granted")
            time.sleep(0.5)
            st.rerun()
    
    st.stop()

# ============================================================================
# AUTHENTICATED AREA
# ============================================================================

st.title("✅ Secure Data House")
st.success("🔓 You are in. Welcome to your most secure large data house.")

# Initialize TinyDB
db = TinyDB('secure_datastore.json')
sessions_table = db.table('sessions')
data_table = db.table('data')
Data = Query()

# --- SESSION MANAGEMENT (SIDEBAR) ---
st.sidebar.title("Data House Sessions")

# Logout Button
if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.session_state.security_level = 0
    st.session_state.paranoid_mode = False
    st.session_state.current_session_id = None
    st.rerun()

st.divider()

st.sidebar.divider()

# Create a new session
new_session_name = st.sidebar.text_input("New Session Name", key="new_session_name")
if st.sidebar.button("Create Session", disabled=not new_session_name):
    if sessions_table.search(Data.name == new_session_name):
        st.sidebar.warning("Session name already exists.")
    else:
        session_id = sessions_table.insert({
            'name': new_session_name,
            'created_at': datetime.now().isoformat()
        })
        st.session_state.current_session_id = session_id
        st.sidebar.success(f"Session '{new_session_name}' created.")
        time.sleep(1)
        st.rerun()

# Select an existing session
all_sessions = sessions_table.all()
if all_sessions:
    session_options = {session['name']: session.doc_id for session in all_sessions}
    
    # Find the index of the current session to set the default value for selectbox
    current_session_index = 0
    if st.session_state.current_session_id:
        for i, session in enumerate(all_sessions):
            if session.doc_id == st.session_state.current_session_id:
                current_session_index = i
                break

    selected_session_name = st.sidebar.selectbox(
        "Select a Session",
        options=session_options.keys(),
        index=current_session_index,
        key="session_selector"
    )
    
    if selected_session_name:
        st.session_state.current_session_id = session_options[selected_session_name]
else:
    st.sidebar.info("No sessions found. Create one to begin.")

# --- MAIN CONTENT AREA ---
if not st.session_state.current_session_id:
    st.info("👈 Please create or select a session from the sidebar to start.")
    st.stop()

# Display current session info
current_session_doc = sessions_table.get(doc_id=st.session_state.current_session_id)
if current_session_doc:
    st.header(f"🗂️ Session: {current_session_doc['name']}")
else:
    st.error("Selected session not found. It may have been deleted.")
    st.session_state.current_session_id = None
    st.stop()

# Tabs for adding content
tab1, tab2 = st.tabs(["📝 Write Note", "📂 Upload File"])

with tab1:
    st.subheader("Add a Secure Note")
    note_content = st.text_area("Your note...", height=200, key="note_area")
    if st.button("Save Note", disabled=not note_content):
        data_table.insert({
            'session_id': st.session_state.current_session_id,
            'type': 'note',
            'content': note_content,
            'timestamp': datetime.now().isoformat()
        })
        st.success("Note saved!")
        time.sleep(1)
        st.rerun()

with tab2:
    st.subheader("Upload a Secure File")
    uploaded_file = st.file_uploader("Choose a file of any type", key="file_uploader")
    if uploaded_file is not None:
        if st.button("Save File"):
            file_bytes = uploaded_file.getvalue()
            b64_content = base64.b64encode(file_bytes).decode('utf-8')
            
            data_table.insert({
                'session_id': st.session_state.current_session_id,
                'type': 'file',
                'filename': uploaded_file.name,
                'mimetype': uploaded_file.type,
                'content': b64_content,
                'timestamp': datetime.now().isoformat()
            })
            st.success(f"File '{uploaded_file.name}' saved!")
            time.sleep(1)
            st.rerun()

st.divider()

# --- DISPLAY SESSION CONTENT ---
st.header("🔐 Stored Data in this Session")

session_data = sorted(
    data_table.search(Data.session_id == st.session_state.current_session_id),
    key=lambda x: x['timestamp'],
    reverse=True
)

if not session_data:
    st.info("This session is empty. Add notes or upload files above.")
else:
    for i, item in enumerate(session_data):
        item_ts = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        
        if item['type'] == 'note':
            with st.expander(f"📝 Note - {item_ts}"):
                st.markdown(item['content'])
        
        elif item['type'] == 'file':
            with st.container():
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"📂 **File:** `{item['filename']}` ({item_ts})")
                with col2:
                    file_bytes_to_download = base64.b64decode(item['content'])
                    st.download_button(
                        label="Download",
                        data=file_bytes_to_download,
                        file_name=item['filename'],
                        mime=item['mimetype'],
                        key=f"download_{i}"
                    )
                st.divider()
