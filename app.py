import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import pandas as pd
import datetime
import json

# --- कॉन्फिगरेशन (Secrets से आएगा) ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GOOGLE_SHEET_JSON = json.loads(st.secrets["GOOGLE_SHEET_JSON"])
SPREADSHEET_NAME = "Udhaar Book"

genai.configure(api_key=GEMINI_API_KEY)

def get_sheet_by_name(sheet_name):
    scope = ["https://google.com", "https://googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_SHEET_JSON, scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).worksheet(sheet_name)

# --- ऐप इंटरफेस ---
st.title("🌐 AI यूनिवर्सल खाता बुक")

if 'user_phone' not in st.session_state:
    st.subheader("📱 ऐप में प्रवेश करें")
    phone_input = st.text_input("अपना 10 अंकों का मोबाइल नंबर डालें:")
    if st.button("लॉगिन करें 🚀"):
        if len(phone_input) == 10 and phone_input.isdigit():
            u_sheet = get_sheet_by_name("Users")
            users_data = u_sheet.get_all_records()
            df_users = pd.DataFrame(users_data)
            
            if df_users.empty or str(phone_input) not in df_users['Phone'].astype(str).values:
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                u_sheet.append_row([phone_input, today_str, "Trial"])
            
            st.session_state['user_phone'] = phone_input
            st.rerun()
        else:
            st.error("कृपया एक वैध 10 अंकों का नंबर डालें।")
    st.stop()

# ट्रायल और सब्सक्रिप्शन चेक
user_phone = st.session_state['user_phone']
u_sheet = get_sheet_by_name("Users")
df_users = pd.DataFrame(u_sheet.get_all_records())
user_row = df_users[df_users['Phone'].astype(str) == str(user_phone)].iloc[0]

reg_date = datetime.datetime.strptime(str(user_row['Registration Date']), "%Y-%m-%d").date()
status = str(user_row['Status'])
days_used = (datetime.date.today() - reg_date).days

if days_used > 3 and status != "Active":
    st.error("🚨 आपका 3 दिन का फ्री ट्रायल समाप्त हो गया है!")
    st.subheader("🔒 ऐप चालू करने के लिए सब्सक्रिप्शन लें")
    st.write("💸 **कीमत: सिर्फ ₹199 / महीना**")
    st.markdown("### 💳 UPI ID: `yourupi@okaxis` (यहाँ अपना UPI लिखें)")
    st.markdown("[💬 स्क्रीनशॉट भेजें (WhatsApp)](https://wa.meैंने%20199%20का%20भुगतान%20कर%20दिया%20है)")
    st.stop()

if status == "Trial":
    st.info(f"🎁 फ्री ट्रायल मोड: आपके पास {4 - days_used} दिन बाकी हैं।")

# लेजर रिकॉर्ड दिखाना
try:
    l_sheet = get_sheet_by_name("Ledger")
    df_ledger = pd.DataFrame(l_sheet.get_all_records())
    if not df_ledger.empty:
        st.subheader("👥 आपका लाइव उधारी रिकॉर्ड")
        st.dataframe(df_ledger)
except:
    pass

# 🌍 फ्री Gemini AI इंजन
def ask_gemini_ai(user_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Analyze this text in any language: "{user_text}". Extract details into JSON format ONLY. Do not include markdown or backticks like ```json.
    Format: {{"name": "Customer Name", "action": "'credit' or 'paid' or 'clear'", "amount": number, "phone": "phone or null"}}"""
    response = model.generate_content(prompt)
    return json.loads(response.text.strip())

# उधारी जोड़ने/अपडेट करने का लॉजिक
def update_ledger(parsed_data):
    sheet = get_sheet_by_name("Ledger")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    name = parsed_data['name']
    action = parsed_data['action']
    amount = float(parsed_data['amount']) if parsed_data['amount'] else 0
    phone = parsed_data['phone'] if parsed_data['phone'] else "98765xxxxx"
    
    if not name: return "❌ AI नाम नहीं पहचान पाया।"

    if df.empty or name not in df['Name'].values:
        if action == 'credit': sheet.append_row([name, phone, amount, 0, amount])
        elif action == 'paid': sheet.append_row([name, phone, 0, amount, -amount])
        return f"✨ नया ग्राहक **{name}** जोड़ा गया!"
    else:
        cell = sheet.find(name)
        row_idx = cell.row
        current_credit = float(sheet.cell(row_idx, 3).value or 0)
        current_paid = float(sheet.cell(row_idx, 4).value or 0)
        
        if action == 'credit':
            new_credit = current_credit + amount
            sheet.update_cell(row_idx, 3, new_credit)
            sheet.update_cell(row_idx, 5, new_credit - current_paid)
            return f"✅ {name}: ₹{amount} उधार जोड़े गए।"
        elif action == 'paid':
            new_paid = current_paid + amount
            sheet.update_cell(row_idx, 4, new_paid)
            sheet.update_cell(row_idx, 5, current_credit - new_paid)
            return f"💵 {name}: ₹{amount} जमा किए गए।"
        elif action == 'clear':
            sheet.update_cell(row_idx, 3, current_credit)
            sheet.update_cell(row_idx, 4, current_credit)
            sheet.update_cell(row_idx, 5, 0)
            return f"🗑️ {name} का पूरा हिसाब क्लियर कर दिया गया है!"

st.markdown("---")
st.subheader("✍️ AI मोड: लिखें या बोलें")
user_input = st.text_input("उदाहरण: 'रमेश ने 400 का सामान लिया' या 'सुरेश का हिसाब क्लियर'")

if st.button("सुरक्षित करें 🚀"):
    if user_input:
        with st.spinner("AI काम कर रहा है..."):
            try:
                parsed = ask_gemini_ai(user_input)
                result_msg = update_ledger(parsed)
                st.success(result_msg)
                st.rerun()
            except Exception as e:
                st.error(f"त्रुटि: {e}")
