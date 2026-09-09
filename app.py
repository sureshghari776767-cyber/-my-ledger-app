import streamlit as st
from openai import OpenAI
import pandas as pd
import json

# --- नए तरीके से OpenAI क्लाइंट सेटअप ---
# यह नए OpenAI वर्जन (v1.0.0+) के नियमों के अनुसार है
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("📊 AI स्मार्ट खाता बुक")

# --- डेटाबेस सेटअप (ऐप की अपनी मेमोरी में) ---
if 'ledger_data' not in st.session_state:
    st.session_state['ledger_data'] = []

# --- नया AI इंजन जो आपकी भाषा समझेगा ---
def ask_openai_ai(user_text):
    prompt = f"""Analyze this text in any language: "{user_text}". Extract details into JSON format ONLY. Do not include markdown or backticks like ```json.
    Format: {{"name": "Customer Name", "action": "'credit' or 'paid' or 'clear'", "amount": number, "phone": "phone or null"}}"""
    
    # नए वर्जन का सही कोड syntax
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return json.loads(response.choices[0].message.content.strip())

# --- डेटा अपडेट करने का लॉजिक ---
def update_internal_ledger(parsed_data):
    name = parsed_data['name']
    action = parsed_data['action']
    amount = float(parsed_data['amount']) if parsed_data['amount'] else 0
    phone = parsed_data['phone'] if parsed_data['phone'] else "98765xxxxx"
    
    if not name:
        return "❌ AI नाम नहीं पहचान पाया। कृपया स्पष्ट नाम लिखें।"
    
    ledger = st.session_state['ledger_data']
    found = False
    
    for item in ledger:
        if item['Name'].lower() == name.lower():
            found = True
            if action == 'credit':
                item['Total Credit'] += amount
            elif action == 'paid':
                item['Total Paid'] += amount
            elif action == 'clear':
                item['Total Paid'] = item['Total Credit']
            item['Net Balance'] = item['Total Credit'] - item['Total Paid']
            break
            
    if not found:
        new_entry = {
            "Name": name,
            "Phone": phone,
            "Total Credit": amount if action == 'credit' else 0,
            "Total Paid": amount if action == 'paid' else 0,
            "Net Balance": amount if action == 'credit' else -amount
        }
        ledger.append(new_entry)
        
    st.session_state['ledger_data'] = ledger
    return "✅ खाता बुक में एंट्री सुरक्षित हो गई!"

# --- लाइव रिकॉर्ड बोर्ड (डैशबोर्ड) ---
df = pd.DataFrame(st.session_state['ledger_data'])
if not df.empty:
    st.subheader("👥 आपका लाइव उधारी रिकॉर्ड")
    st.dataframe(df)
else:
    st.info("अभी कोई रिकॉर्ड नहीं है। नीचे लिखकर शुरुआत करें!")

st.markdown("---")
st.subheader("✍️ AI मोड: किसी भी भाषा में लिखें या बोलें")
user_input = st.text_input("उदाहरण: 'रमेश ने 500 का सामान उधार लिया' या 'सुरेश का पूरा हिसाब क्लियर करो'")

if st.button("सुरक्षित करें 🚀"):
    if user_input:
        with st.spinner("AI काम कर रहा है..."):
            try:
                parsed = ask_openai_ai(user_input)
                msg = update_internal_ledger(parsed)
                st.success(msg)
                st.rerun()
            except Exception as e:
                st.error(f"त्रुटि: {e}")
