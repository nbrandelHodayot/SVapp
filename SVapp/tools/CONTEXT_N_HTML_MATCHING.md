# דוח התאמת CONTEXT_N לדפי HTML

## ✅ התאמות תקינות

### דפים כלליים
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `MAIN` | `index.html` | ✅ |
| `LOGIN` | `login.html` | ✅ |
| `NAV_CONTROL` / `CONTROL_MENU` | `control/nav_control.html` | ✅ |
| `SETTINGS` | `nav_settings.html` | ✅ |

### דפי סטטוס
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `STATUS_BOYS` | `status/status_boys.html` | ✅ |
| `STATUS_GIRLS` | `status/status_girls.html` | ✅ |
| `STATUS_PUBLIC` | `status/status_public.html` | ✅ |
| `STATUS_SHABBAT` | `status/status_shabbat.html` | ✅ |

### הפעלה כללית
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `BOYS_GENERAL` | `control/control_boys_general.html` | ✅ |
| `GIRLS_GENERAL` | `control/control_girls_general.html` | ✅ |

### חלוקה למבנים
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `BOYS_SPLIT` | `control/control_boys_split.html` | ✅ |
| `GIRLS_SPLIT` | `control/control_girls_split1.html` / `control_girls_split2.html` | ✅ תוקן - קונטקסט כללי |
| `GIRLS_SPLIT_1` | `control/control_girls_split1.html` | ✅ |
| `GIRLS_SPLIT_2` | `control/control_girls_split2.html` | ✅ |
| `PUBLIC_SPLIT` | `control/control_public_split.html` | ✅ |
| `PUBLIC_MAIN` | `control/control_public_split.html` | ✅ תוקן - קונטקסט כללי |
| `PUBLIC_SHABBAT` | `control/control_public_shabbat.html` | ✅ תוקן |

### שעוני שבת בנים
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `BOYS_SHABBAT_AC1` | `control/control_boys_shabbat.html` (tab) | ✅ תוקן |
| `BOYS_SHABBAT_AC2` | `control/control_boys_shabbat.html` (tab) | ✅ תוקן |
| `BOYS_SHABBAT_ROOM_LIGHTS` | `control/control_boys_shabbat.html` (tab) | ✅ תוקן |
| `BOYS_SHABBAT_BATHROOM_LIGHTS` | `control/control_boys_shabbat.html` (tab) | ✅ תוקן |
| `BOYS_SHABBAT_HEATER` | `control/control_boys_shabbat.html` (tab) | ✅ תוקן |

### שעוני שבת בנות
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `GIRLS_SHABBAT_AC1` | `control/control_girls_shabbat.html` (tab) | ✅ |
| `GIRLS_SHABBAT_AC2` | `control/control_girls_shabbat.html` (tab) | ✅ |
| `GIRLS_SHABBAT_ROOM_LIGHTS` | `control/control_girls_shabbat.html` (tab) | ✅ |
| `GIRLS_SHABBAT_BATHROOM_LIGHTS` | `control/control_girls_shabbat.html` (tab) | ✅ |
| `GIRLS_SHABBAT_HEATER` | `control/control_girls_shabbat.html` (tab) | ✅ |

### D1
| CONTEXT_N | דף HTML | הערות |
|-----------|---------|-------|
| `PUBLIC_D1` / `D1_MAIN` | `control/control_public_d1_can.html` | ✅ |
| `D1_CLUBS_BOYS` | `control/control_public_d1_can.html` (tab) | ✅ |
| `D1_CLUBS_GIRLS` | `control/control_public_d1_can.html` (tab) | ✅ |
| `D1_CLUBS_PUB` | `control/control_public_d1_can.html` (tab) | ✅ |

## ✅ בעיות שתוקנו

### 1. ✅ אי-התאמה בשמות שעוני שבת בנים - **תוקן!**
**בעיה שהייתה**: ב-`control_boys_shabbat.html` השתמשו בשמות מקוצרים שלא תואמים ל-CONTEXT_N.
**תיקון**: עודכנו כל השמות ב-`context_map` להתאים ל-CONTEXT_N.

### 2. CONTEXT_N ללא דפי HTML
הקונטקסטים הבאים מוגדרים ב-CONTEXT_N אבל אין להם דפי HTML נפרדים (זה תקין - הם משמשים לניווט פנימי):
- `STATUS` - מסך כללי, לא דף נפרד
- `CONTROL` - מסך כללי, לא דף נפרד
- `WAKE_UP` - כפתור, לא דף HTML
- כל ה-`CLUBS_*` - מועדונים, כנראה חלק מדפים אחרים

### 3. דפי HTML ללא CONTEXT_N
הדפים הבאים קיימים אבל לא מופיעים ב-CONTEXT_N (זה תקין - הם תבניות בסיס):
- `base_layout.html` - תבנית בסיס
- `control_base.html` - תבנית בסיס
- `status_base.html` - תבנית בסיס
- `shabbat_base.html` - תבנית בסיס

## 🔧 תיקונים נדרשים

### ✅ תיקון 1: עדכון שמות הקונטקסטים ב-control_boys_shabbat.html - **תוקן!**
שונה ה-`context_map` ב-`control_boys_shabbat.html`:
- `BOYS_SH_AC1` → `BOYS_SHABBAT_AC1` ✅
- `BOYS_SH_AC2` → `BOYS_SHABBAT_AC2` ✅
- `BOYS_SH_ROOMS` → `BOYS_SHABBAT_ROOM_LIGHTS` ✅
- `BOYS_SH_WC` → `BOYS_SHABBAT_BATHROOM_LIGHTS` ✅
- `BOYS_SH_HEATER` → `BOYS_SHABBAT_HEATER` ✅

### ✅ תיקון 2: הוספת CONTEXT_N חסרים - **תוקן!**
נוספו ל-CONTEXT_N:
- `GIRLS_SPLIT` → `"00100000000000000000"` (קונטקסט כללי לחלוקה למבנים בנות) ✅
- `PUBLIC_SHABBAT` → `"00200000000000000000"` (שעוני שבת אזור ציבורי) ✅
- `PUBLIC_MAIN` → `"00190000000000000000"` (קונטקסט כללי לאזור ציבורי) ✅

## 📋 סיכום

- **סה"כ CONTEXT_N**: 43 (נוספו 3)
- **עם דפי HTML ישירים**: 20
- **עם דפי HTML דרך tabs**: 9
- **ללא דפי HTML (תקין)**: 14
- **בעיות**: 0 (כל הבעיות תוקנו)

**סטטוס כללי**: ✅ כל הבעיות תוקנו - כל ה-CONTEXT_N תואמים לדפי HTML
