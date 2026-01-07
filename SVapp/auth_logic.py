# login.py
import logging
import config_app as config

logger = logging.getLogger(__name__)

def verify_app_user(username, password):
    """בודק האם המשתמש והסיסמה תואמים להגדרות ב-config"""
    if not username or not password:
        return False
    
    username_lower = username.lower()
    if username_lower in config.USERS:
        if config.USERS[username_lower] == str(password):
            logger.info(f"User {username} authenticated successfully.")
            return True
            
    logger.warning(f"Failed login attempt: {username}")
    return False