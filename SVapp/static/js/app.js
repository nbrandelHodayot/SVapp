/**
 * app.js - Production Version
 */

// 1. הגדרת SocketIO
if (!window.socket) {
    window.socket = io();
}

window.socket.on('force_navigate', (data) => {
    // במצב סימולציה אין חזרה אוטומטית - זה רלוונטי רק למצב אמת
    if (window.SIMULATION_MODE) {
        return;
    }
    const currentPage = window.location.pathname.replace('/', '');
    if (currentPage !== data.target_page && currentPage + '.html' !== data.target_page) {
        window.location.href = "/" + data.target_page;
    }
});

// 2. ניהול זמן חוסר פעילות (Auto Logout)
// במצב סימולציה אין חזרה אוטומטית - זה רלוונטי רק למצב אמת
(function() {
    // בדיקה אם זה מצב סימולציה
    if (window.SIMULATION_MODE) {
        console.log("SIMULATION_MODE: Auto logout disabled");
        return;
    }
    
    const timeoutSeconds = window.INACTIVITY_TIMEOUT || 270;
    let inactivityTimer;

    const doAutoLogout = () => window.location.href = '/'; 

    const resetInactivityTimer = () => {
        clearTimeout(inactivityTimer);
        inactivityTimer = setTimeout(doAutoLogout, timeoutSeconds * 1000);
    };

    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
        document.addEventListener(event, resetInactivityTimer, true);
    });
    resetInactivityTimer();
})();

// 3. פונקציות שליטה (חשופות ל-window)
window.sendAction = async function(actionName) {
    const statusFooter = document.getElementById('status-message');
    if (statusFooter) {
        statusFooter.textContent = `שולח: ${actionName}...`;
        statusFooter.style.backgroundColor = '#fffacd'; 
    }

    try {
        const response = await fetch(`/control?action=${encodeURIComponent(actionName)}`);
        if (response.ok) {
            if (statusFooter) {
                statusFooter.textContent = `בוצע: ${actionName}`;
                statusFooter.style.backgroundColor = '#d4edda';
            }
            return true;
        }
        throw new Error('Server Error');
    } catch (err) {
        if (statusFooter) {
            statusFooter.textContent = `שגיאה בתקשורת`;
            statusFooter.style.backgroundColor = '#f8d7da';
        }
        return false;
    }
};

window.handleButtonClick = async function(action, nextUrl, currentContext = null) {
    // בניית פקודה הכוללת הקשר (למשל STATUS_BOYS/TAB_GIRLS)
    const fullAction = currentContext ? `${currentContext}/${action}` : action;
    console.log("Action:", fullAction);

    // במצב סימולציה - מדלג על שליחת פקודה לבקר
    if (!window.SIMULATION_MODE) {
        await window.sendAction(fullAction);
    } else {
        console.log("SIMULATION_MODE: Skipping PLC action, navigating directly");
    }
    
    if (nextUrl && nextUrl !== 'null') {
        setTimeout(() => { window.location.href = nextUrl; }, window.SIMULATION_MODE ? 100 : 800);
    }
};

// 4. עדכוני סטטוס דינמיים (Polling)
window.updateCurrentStatus = async function() {
    // זיהוי אוטומטי של האזור לפי ה-URL
    let area = 'boys';
    if (window.location.pathname.includes('girls')) area = 'girls';
    if (window.location.pathname.includes('public')) area = 'public';
    if (window.location.pathname.includes('shabbat')) area = 'shabbat';

    try {
        const response = await fetch(`/api/status/${area}`);
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            Object.entries(result.data).forEach(([ledId, state]) => {
                const el = document.getElementById('stat_' + ledId);
                if (el) {
                    el.className = `led ${state.toLowerCase()}`;
                }
            });
        }
    } catch (err) {
        console.error("Status Update Failed:", err);
    }
};

window.updateSystemTime = async function() {
    const timeDisplay = document.getElementById('system-time');
    if (!timeDisplay) return;
    try {
        const response = await fetch('/system_time');
        const data = await response.json();
        if (data.status === 'success') timeDisplay.textContent = data.time;
    } catch (e) {}
};

// 5. אתחול
document.addEventListener('DOMContentLoaded', () => {
    window.updateSystemTime();
    setInterval(window.updateSystemTime, 10000);

    if (window.location.pathname.includes('status_')) {
        window.updateCurrentStatus();
        setInterval(window.updateCurrentStatus, 5000);
    }
});