/**
 * app.js - לוגיקת שליטה, סנכרון HMI וניהול חוסר פעילות (גרסה מאוחדת ומתוקנת)
 */

// ==========================================
// 1. ניהול זמן חוסר פעילות (Auto Logout)
// ==========================================
(function() {
    // ה-JavaScript ינסה לקחת את הערך שהזרקנו מה-config. 
    // אם הוא לא מוצא אותו (למשל במקרה של שגיאה), הוא יברירת מחדל ל-300 שניות.
    const timeoutSeconds = window.INACTIVITY_TIMEOUT || 300;
    let inactivityTimer;

    console.log(`Auto-logout system initialized. Timeout: ${timeoutSeconds} seconds.`);

    function doAutoLogout() {
        console.log("Inactivity detected. Redirecting to logout...");
        // הפניה לנתיב הניתוק בשרת
        window.location.href = '';
    }

    function resetInactivityTimer() {
        // בכל פעם שיש פעילות, אנחנו מאפסים את השעון ומתחילים ספירה מחדש
        clearTimeout(inactivityTimer);
        inactivityTimer = setTimeout(doAutoLogout, timeoutSeconds * 1000);
    }

    // רשימת אירועים שנחשבים כ"פעילות משתמש"
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    activityEvents.forEach(event => {
        document.addEventListener(event, resetInactivityTimer, true);
    });

    // הפעלה ראשונית של הטיימר עם טעינת הדף
    resetInactivityTimer();
})();

// ==========================================
// 2. פונקציות שליטה מול השרת
// ==========================================

/**
 * פונקציה לשליחת פקודה לשרת
 */
async function sendAction(actionName) {
    const statusFooter = document.getElementById('status-message');
    
    if (statusFooter) {
        statusFooter.textContent = `שולח לבקר: ${actionName}...`;
        statusFooter.style.backgroundColor = '#fffacd'; 
    }

    try {
        const response = await fetch(`/control?action=${actionName}`);
        const data = await response.json();

        if (response.ok) {
            if (statusFooter) {
                statusFooter.textContent = `בוצע: ${actionName}`;
                statusFooter.style.backgroundColor = '#d4edda';
            }
            return true;
        } else {
            throw new Error(data.message || 'שגיאת שרת');
        }
    } catch (err) {
        console.error('Fetch error:', err);
        if (statusFooter) {
            statusFooter.textContent = `שגיאה: ${err.message}`;
            statusFooter.style.backgroundColor = '#f8d7da';
        }
        return false;
    }
}

/**
 * handleButtonClick - לוגיקת ניווט עם שליחת פקודה
 * גרסה מתוקנת המונעת ניווט ל-null
 */
async function handleButtonClick(action, nextUrl, currentContext) {
    const fullAction = currentContext ? `${currentContext}/${action}` : action;
    console.log("Processing action:", fullAction);

    // שליחה לשרת
    await sendAction(fullAction);
    
    // ניווט יתבצע רק אם הוגדר URL יעד תקין
    // אנחנו בודקים ש-nextUrl קיים, שהוא לא null, ושהוא לא המחרוזת "null"
    if (nextUrl && nextUrl !== 'null' && nextUrl !== null) {
        console.log("Navigating to:", nextUrl);
        setTimeout(() => {
            window.location.href = nextUrl;
        }, 1200);
    } else {
        console.log("No navigation required, staying on page.");
        // אופציונלי: עדכון נורות מקומי אם מדובר בדף בנים
        if (typeof updateBoysGeneralStatus === 'function') {
            setTimeout(updateBoysGeneralStatus, 1000);
        }
    }
}

/**
 * navigateTo - פונקציית הניווט שנקראת מה-HTML (מתקן את ה-ReferenceError)
 */
window.navigateTo = async function(targetUrl, action) {
    console.log("Navigating to:", targetUrl, "Action:", action);
    // קריאה לפונקציית הלוגיקה המרכזית עם הפרמטרים בסדר הנכון
    await handleButtonClick(action, targetUrl);
};

/**
 * פונקציית חזרה אוטומטית
 */
async function goBack() {
    const urlElement = document.getElementById('nav-back-url');
    const actionElement = document.getElementById('nav-back-action');
    
    if (!urlElement || !actionElement) return;

    const targetUrl = urlElement.value.trim();
    const screenName = actionElement.value.trim();
    const fullBackAction = `BACK_${screenName}`;
    
    await sendAction(fullBackAction);
    
    setTimeout(() => {
        window.location.href = targetUrl;
    }, 1200);
}

// ==========================================
// 3. עדכוני סטטוס וזמן (Polling)
// ==========================================

/**
 * עדכון זמן המערכת ב-Header
 */
async function updateSystemTime() {
    const timeDisplay = document.getElementById('system-time');
    if (!timeDisplay) return;
    try {
        const response = await fetch('/system_time');
        const data = await response.json();
        if (data.status === 'success') {
            timeDisplay.textContent = data.time;
        }
    } catch (e) {}
}

/**
 * עדכון מצב נורות (LEDs) בדף סטטוס בנים
 */
async function updateBoysGeneralStatus() {
    try {
        const response = await fetch('/api/status/boys_general_full');
        const result = await response.json();
        
        if (result.status === 'success') {
            for (const [ledId, state] of Object.entries(result.data)) {
                const el = document.getElementById('stat_' + ledId);
                if (el) {
                    // הסרת כל המצבים הקודמים
                    el.classList.remove('on', 'off', 'unknown');
                    
                    if (state === 'ON') {
                        el.classList.add('on'); // ירוק
                    } else if (state === 'OFF') {
                        el.classList.add('off'); // אדום
                    } else {
                        el.classList.add('unknown'); // אפור פועם - זה יגיד לנו שהזיהוי נכשל
                    }
                }
            }
        }
    } catch (err) {
        console.error("נכשל עדכון נורות בנים:", err);
    }
}

/**
 * עדכון סטטוס שירותים
 */
async function refreshRestroomStatus() {
    try {
        const response = await fetch('/api/status/restrooms');
        const result = await response.json();
        
        if (result.status === 'success') {
            const container = document.getElementById('leds-restrooms');
            if (!container) return;
            
            container.innerHTML = ''; 
            for (const [house, state] of Object.entries(result.data)) {
                const label = house.replace('house_', 'בית ').replace('a', ' א').replace('b', ' ב');
                const html = `
                    <div class="led-item">
                        <span>${label}</span>
                        <div class="led-dot ${state.toLowerCase()}"></div>
                    </div>`;
                container.innerHTML += html;
            }
        }
    } catch (e) { console.error("Update restrooms failed", e); }
}

// ==========================================
// 4. אתחול בטעינת הדף (DOM Ready)
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // 1. עדכון זמן מערכת - רץ תמיד בכל הדפים (מומלץ להשאיר)
    updateSystemTime();
    setInterval(updateSystemTime, 10000);

    // 2. לוגיקה ספציפית לדף סטטוס בנים
    if (window.location.pathname.includes('boys_general')) {
        // מפעיל עדכון ראשון מיד
        updateBoysGeneralStatus();
        // קובע רענון כל 5 שניות
        setInterval(updateBoysGeneralStatus, 5000);
        
        /* הערה: אם updateBoysGeneralStatus מעדכן גם את השירותים 
           לפי ה-ID (stat_T_...), אין צורך בבלוק של refreshRestroomStatus.
           מחק אותו כדי למנוע כפל פניות לשרת.
        */
    }
});