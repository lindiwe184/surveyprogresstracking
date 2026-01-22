import streamlit as st
import requests
from typing import Optional, Dict, Any
from config import get_api_base_url

API_BASE_URL = get_api_base_url().rstrip("/")


class AuthManager:
    """Handle authentication for the Streamlit frontend."""
    
    def __init__(self):
        self.token_key = "auth_token"
        self.user_key = "current_user"
    
    def login(self, username: str, password: str) -> bool:
        """Attempt to log in with username/password."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Store authentication data in session state
                st.session_state[self.token_key] = data.get("access_token")
                st.session_state[self.user_key] = data.get("user")
                return True
            else:
                error_msg = response.json().get("error", "Login failed")
                st.error(error_msg)
                return False
                
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {e}")
            return False
        except Exception as e:
            st.error(f"Login error: {e}")
            return False
    
    def logout(self):
        """Log out the current user."""
        try:
            if self.is_authenticated():
                headers = self.get_auth_headers()
                requests.post(
                    f"{API_BASE_URL}/api/auth/logout",
                    headers=headers,
                    timeout=10
                )
        except:
            pass  # Ignore errors during logout
        
        # Clear session state
        if self.token_key in st.session_state:
            del st.session_state[self.token_key]
        if self.user_key in st.session_state:
            del st.session_state[self.user_key]
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return (
            self.token_key in st.session_state and 
            st.session_state[self.token_key] and
            self.user_key in st.session_state and
            st.session_state[self.user_key]
        )
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        if self.is_authenticated():
            return st.session_state[self.user_key]
        return None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if self.is_authenticated():
            return {
                "Authorization": f"Bearer {st.session_state[self.token_key]}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}
    
    def is_admin(self) -> bool:
        """Check if current user has admin privileges."""
        user = self.get_current_user()
        if user:
            return user.get("role") in ["admin", "superadmin"]
        return False
    
    def is_superadmin(self) -> bool:
        """Check if current user has superadmin privileges."""
        user = self.get_current_user()
        if user:
            return user.get("role") == "superadmin"
        return False
    
    def require_auth(self):
        """Decorator/function to require authentication."""
        if not self.is_authenticated():
            st.error("Please log in to access this page.")
            self.show_login_form()
            st.stop()
    
    def require_admin(self):
        """Decorator/function to require admin privileges."""
        self.require_auth()
        if not self.is_admin():
            st.error("Admin privileges required to access this page.")
            st.stop()
    
    def show_login_form(self):
        """Display the login form."""
        st.markdown("## Login")
        
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if username and password:
                    if self.login(username, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.error("Please enter both username and password")
    
    def show_user_info(self):
        """Display current user information in sidebar."""
        if self.is_authenticated():
            user = self.get_current_user()
            st.sidebar.markdown("---")
            st.sidebar.markdown("### User Info")
            st.sidebar.write(f"**Username:** {user.get('username', 'Unknown')}")
            st.sidebar.write(f"**Role:** {user.get('role', 'user').title()}")
            
            if st.sidebar.button("Logout"):
                self.logout()
                st.rerun()


def authenticated_request(method: str, endpoint: str, auth_manager: AuthManager, **kwargs) -> requests.Response:
    """Make an authenticated request to the API."""
    headers = auth_manager.get_auth_headers()
    if "headers" in kwargs:
        kwargs["headers"].update(headers)
    else:
        kwargs["headers"] = headers
    
    url = f"{API_BASE_URL}{endpoint}"
    
    if method.upper() == "GET":
        return requests.get(url, **kwargs)
    elif method.upper() == "POST":
        return requests.post(url, **kwargs)
    elif method.upper() == "PUT":
        return requests.put(url, **kwargs)
    elif method.upper() == "DELETE":
        return requests.delete(url, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")


# Global auth manager instance
auth_manager = AuthManager()