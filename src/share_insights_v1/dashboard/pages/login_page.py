import streamlit as st
import hashlib

class LoginManager:
    def __init__(self):
        # Simple hardcoded users for demo (in production, use database)
        self.users = {
            "admin": {"password": self._hash_password("xyz123#"), "role": "admin"},
            "analyst": {"password": self._hash_password("analyst123"), "role": "analyst-user"},
            "demo": {"password": self._hash_password("demo"), "role": "analyst-user"}
        }
    
    def _hash_password(self, password):
        """Simple password hashing"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username, password, role):
        """Authenticate user credentials"""
        if username in self.users:
            user = self.users[username]
            if user["password"] == self._hash_password(password) and user["role"] == role:
                return True
        return False
    
    def get_user_role(self, username):
        """Get user role"""
        return self.users.get(username, {}).get("role")

def render_login_page():
    """Render the login page"""
    st.set_page_config(
        page_title="Stock Analysis Login",
        page_icon="🔐",
        layout="centered"
    )
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Stock Analysis Login")
        st.markdown("---")
        
        # Login form
        with st.form("login_form"):
            st.subheader("Please Login")
            
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            role = st.selectbox("Role", ["admin", "analyst-user"])
            
            login_button = st.form_submit_button("Login", type="primary", use_container_width=True)
            
            if login_button:
                login_manager = LoginManager()
                
                if not username or not password:
                    st.error("Please enter both username and password")
                elif login_manager.authenticate(username, password, role):
                    # Set session state
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = role
                    st.success(f"Welcome {username}! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid credentials or role mismatch")
        
        # Demo credentials info
        st.markdown("---")
        st.info("**Demo Credentials:**")
        st.markdown("""
        **Admin User:**
        - Username: `admin`
        - Password: `xyz123#`
        - Role: `admin`
        
        **Analyst User:**
        - Username: `analyst`
        - Password: `analyst123`
        - Role: `analyst-user`
        
        **Demo User:**
        - Username: `demo`
        - Password: `demo`
        - Role: `analyst-user`
        """)

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get("logged_in", False)

def logout():
    """Logout user"""
    for key in ["logged_in", "username", "user_role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def render_navigation():
    """Render navigation bar with logout"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"**Welcome, {st.session_state.username}** ({st.session_state.user_role})")
    
    with col3:
        if st.button("Logout", type="secondary"):
            logout()

def main():
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    # Check authentication
    if not check_authentication():
        render_login_page()
    else:
        # User is logged in, show success message
        st.success("✅ Login successful! Please navigate back to the main dashboard.")
        st.info("You can close this page and return to the main dashboard.")

if __name__ == "__main__":
    main()