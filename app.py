import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import datetime
import random
import sqlite3
import json
import bcrypt

from cryptography.fernet import Fernet

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Blockchain HIMS Simulator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ENCRYPTION KEY
# ==========================================
KEY = b'IL-LNHIOjec7-qUSenZ8d9wiOGiaICsLHrn8JRscpxM='
cipher = Fernet(KEY)

# ==========================================
# CUSTOM CSS
# ==========================================
st.markdown("""
<style>

.main {
    background-color: #f4f7fb;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #0f172a,
        #1e293b
    );
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

h1, h2, h3 {
    color: #0f172a;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 18px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

.metric-card {
    background: linear-gradient(
        135deg,
        #2563eb,
        #1d4ed8
    );
    color: white;
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
}

.metric-card h1 {
    font-size: 38px;
    margin-bottom: 5px;
}

.metric-card p {
    font-size: 16px;
}

.stButton>button {
    background-color: #2563eb;
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
}

.alert-warning {
    background-color: #fef3c7;
    padding: 15px;
    border-radius: 12px;
    color: #92400e;
    font-weight: bold;
    margin-bottom: 10px;
}

/* ==========================================
HIDE STREAMLIT DEFAULT MENU & FOOTER
========================================== */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

/* Optional:
Hide "Deploy" button
*/
[data-testid="stToolbar"] {
    visibility: hidden;
}

/* Optional:
Hide Streamlit top-right decoration
*/
[data-testid="stDecoration"] {
    display: none;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD DATASET
# ==========================================
df = pd.read_excel(
    "dataset/hospital_data.xlsx"
)

# ==========================================
# SQLITE DATABASE
# ==========================================
conn = sqlite3.connect(
    "blockchain_hims.db",
    check_same_thread=False
)

cursor = conn.cursor()

# ==========================================
# TABLES
# ==========================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS blockchain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_index INTEGER,
    timestamp TEXT,
    data TEXT,
    previous_hash TEXT,
    current_hash TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT,
    patient_name TEXT,
    age INTEGER,
    gender TEXT,
    diagnosis TEXT,
    prescription TEXT,
    referral_time INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    activity TEXT,
    timestamp TEXT
)
""")

conn.commit()

# ==========================================
# LOAD SAVED PATIENTS
# ==========================================
saved_patients = pd.read_sql_query(
    "SELECT * FROM patients",
    conn
)

if not saved_patients.empty:

    saved_patients = saved_patients.rename(columns={
        "patient_id": "Participant_ID",
        "referral_time": "Referral_Time_After_Minutes"
    })

    saved_patients["Role"] = "Patient"
    saved_patients["System_Uptime_Percent"] = 99.9

    df = pd.concat(
        [df, saved_patients],
        ignore_index=True
    )

# ==========================================
# USERS
# ==========================================
users = {

    "admin": {
        "password": bcrypt.hashpw(
            "admin123".encode(),
            bcrypt.gensalt()
        ),
        "role": "Admin"
    },

    "doctor": {
        "password": bcrypt.hashpw(
            "doctor123".encode(),
            bcrypt.gensalt()
        ),
        "role": "Doctor"
    },

    "nurse": {
        "password": bcrypt.hashpw(
            "nurse123".encode(),
            bcrypt.gensalt()
        ),
        "role": "Nurse"
    },

    "patient": {
        "password": bcrypt.hashpw(
            "patient123".encode(),
            bcrypt.gensalt()
        ),
        "role": "Patient"
    }
}

# ==========================================
# SESSION STATE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = ""

if "username" not in st.session_state:
    st.session_state.username = ""

# ==========================================
# ACTIVITY LOGGER
# ==========================================
def log_activity(username, activity):

    timestamp = str(
        datetime.datetime.now()
    )

    cursor.execute("""
    INSERT INTO activity_logs (
        username,
        activity,
        timestamp
    )
    VALUES (?, ?, ?)
    """, (
        username,
        activity,
        timestamp
    ))

    conn.commit()

# ==========================================
# LOGIN
# ==========================================
def login():

    st.title("🏥 Blockchain HIMS Login")

    username = st.text_input("Username")

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login"):

        if username in users:

            if bcrypt.checkpw(
                password.encode(),
                users[username]["password"]
            ):

                st.session_state.logged_in = True
                st.session_state.role = users[username]["role"]
                st.session_state.username = username

                log_activity(
                    username,
                    "Logged into system"
                )

                st.success("Login Successful")
                st.rerun()

            else:
                st.error("Wrong Password")

        else:
            st.error("User Not Found")

# ==========================================
# LOGOUT
# ==========================================
def logout():

    log_activity(
        st.session_state.username,
        "Logged out"
    )

    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""

    st.rerun()

# ==========================================
# BLOCKCHAIN
# ==========================================
class Block:

    def __init__(
        self,
        index,
        data,
        previous_hash
    ):

        self.index = index

        self.timestamp = str(
            datetime.datetime.now()
        )

        self.data = data

        self.previous_hash = previous_hash

        self.hash = self.calculate_hash()

    def calculate_hash(self):

        block_string = (
            str(self.index)
            + self.timestamp
            + str(self.data)
            + self.previous_hash
        )

        return hashlib.sha256(
            block_string.encode()
        ).hexdigest()

class Blockchain:

    def __init__(self):

        self.chain = [
            self.create_genesis_block()
        ]

    def create_genesis_block(self):

        return Block(
            0,
            "Genesis Block",
            "0"
        )

    def get_latest_block(self):

        return self.chain[-1]

    def add_block(self, data):

        new_block = Block(
            len(self.chain),
            data,
            self.get_latest_block().hash
        )

        self.chain.append(new_block)

        cursor.execute("""
        INSERT INTO blockchain (
            block_index,
            timestamp,
            data,
            previous_hash,
            current_hash
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            new_block.index,
            new_block.timestamp,
            json.dumps(new_block.data),
            new_block.previous_hash,
            new_block.hash
        ))

        conn.commit()

# ==========================================
# INIT BLOCKCHAIN
# ==========================================
blockchain = Blockchain()

# ==========================================
# SMART CONTRACT
# ==========================================
def smart_contract_validation(
    role,
    referral_time
):

    if role == "Doctor" and referral_time < 30:
        return "APPROVED"

    elif role == "Nurse" and referral_time < 20:
        return "APPROVED"

    elif referral_time > 120:
        return "BLOCKED"

    else:
        return "PENDING"

# ==========================================
# ADD PATIENT
# ==========================================
def add_new_patient():

    global df

    st.subheader("➕ Register New Patient")

    with st.form("patient_form"):

        patient_id = st.text_input(
            "Patient ID",
            value=f"P-{random.randint(1000,9999)}"
        )

        patient_name = st.text_input(
            "Patient Name"
        )

        age = st.number_input(
            "Age",
            1,
            120,
            25
        )

        gender = st.selectbox(
            "Gender",
            ["Male", "Female"]
        )

        diagnosis = st.text_input(
            "Diagnosis"
        )

        prescription = st.text_input(
            "Prescription"
        )

        referral_time = st.number_input(
            "Referral Time",
            1,
            500,
            25
        )

        submit_patient = st.form_submit_button(
            "Register Patient"
        )

    if submit_patient:

        encrypted_diagnosis = cipher.encrypt(
            diagnosis.encode()
        ).decode()

        encrypted_prescription = cipher.encrypt(
            prescription.encode()
        ).decode()

        new_patient = {

            "Participant_ID": patient_id,
            "Role": "Patient",
            "Referral_Time_After_Minutes": referral_time,
            "System_Uptime_Percent": round(
                random.uniform(95, 100),
                2
            ),
            "Patient_Name": patient_name,
            "Age": age,
            "Gender": gender,
            "Diagnosis": encrypted_diagnosis,
            "Prescription": encrypted_prescription
        }

        cursor.execute("""
        INSERT INTO patients (
            patient_id,
            patient_name,
            age,
            gender,
            diagnosis,
            prescription,
            referral_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (

            patient_id,
            patient_name,
            age,
            gender,
            encrypted_diagnosis,
            encrypted_prescription,
            referral_time
        ))

        conn.commit()

        df = pd.concat(
            [
                df,
                pd.DataFrame([new_patient])
            ],
            ignore_index=True
        )

        blockchain.add_block({

            "patient_id": patient_id,
            "doctor": st.session_state.username,
            "timestamp":
            str(datetime.datetime.now())
        })

        log_activity(
            st.session_state.username,
            f"Registered patient {patient_id}"
        )

        st.success(
            "✅ Patient Registered Successfully"
        )

        st.success(
            "⛓ Blockchain Block Created"
        )

# ==========================================
# LOGIN CHECK
# ==========================================
if not st.session_state.logged_in:
    login()
    st.stop()

# ==========================================
# SIDEBAR
# ==========================================
role = st.session_state.role

st.sidebar.title("🏥 HIMS Navigation")

st.sidebar.success(
    f"Logged in as: {role}"
)

if st.sidebar.button("Logout"):
    logout()

# ==========================================
# MENUS
# ==========================================
if role == "Admin":

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Admin Dashboard",
            "Patient Records",
            "Smart Contracts",
            "Blockchain Ledger",
            "Security Analytics",
            "Interoperability Simulation",
            "Research Analytics",
            "Immutability Verification",
            "Referral Workflow",
            "Export Reports",
            "Activity Logs"
        ]
    )

elif role == "Doctor":

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Doctor Dashboard",
            "Patient Records",
            "Referral Center"
        ]
    )

elif role == "Nurse":

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Nurse Dashboard"
        ]
    )

else:

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Patient Portal"
        ]
    )

# ==========================================
# SECURITY ALERT SIMULATION
# ==========================================

# Disabled automatic unauthorized access alerts

# If you want to manually show alerts later,
# you can use:
#
# st.warning("Unauthorized access attempt detected")
#
# But currently this section does nothing.
    
# ==========================================
# ADMIN DASHBOARD
# ==========================================
if menu == "Admin Dashboard":

    st.title("🏥 Admin Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(f"""
        <div class='metric-card'>
        <h1>{len(df)}</h1>
        <p>Total Participants</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown(f"""
        <div class='metric-card'>
        <h1>{round(df['System_Uptime_Percent'].mean(),2)}%</h1>
        <p>Average Uptime</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:

        st.markdown(f"""
        <div class='metric-card'>
        <h1>{round(df['Referral_Time_After_Minutes'].mean(),2)}</h1>
        <p>Average Referral Time</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# PATIENT RECORDS
# ==========================================
elif menu == "Patient Records":

    st.title("🩺 Patient Records")

    patient_id = st.selectbox(
        "Select Patient",
        df["Participant_ID"]
    )

    log_activity(
        st.session_state.username,
        f"Viewed patient {patient_id}"
    )

    patient = df[
        df["Participant_ID"] == patient_id
    ].iloc[0]

    st.dataframe(
        patient.to_frame(),
        use_container_width=True
    )

# ==========================================
# SMART CONTRACTS
# ==========================================
elif menu == "Smart Contracts":

    st.title("📜 Smart Contracts")

    selected_role = st.selectbox(
        "Role",
        df["Role"].unique()
    )

    referral_time = st.number_input(
        "Referral Time",
        1,
        500,
        25
    )

    result = smart_contract_validation(
        selected_role,
        referral_time
    )

    st.success(f"Result: {result}")

# ==========================================
# BLOCKCHAIN LEDGER
# ==========================================
elif menu == "Blockchain Ledger":

    st.title("⛓ Blockchain Ledger")

    blockchain_data = pd.read_sql_query(
        "SELECT * FROM blockchain",
        conn
    )

    st.dataframe(
        blockchain_data,
        use_container_width=True
    )

# ==========================================
# SECURITY ANALYTICS
# ==========================================
elif menu == "Security Analytics":

    st.title("🛡 AI Security Analytics")

    security_logs = []

    for i in range(20):

        security_logs.append({

            "User":
            f"User-{i}",

            "Login Attempts":
            random.randint(1, 10),

            "Risk Level":
            random.choice(
                ["LOW", "MEDIUM", "HIGH"]
            )
        })

    threat_df = pd.DataFrame(
        security_logs
    )

    st.dataframe(
        threat_df,
        use_container_width=True
    )

# ==========================================
# INTEROPERABILITY SIMULATION
# ==========================================
elif menu == "Interoperability Simulation":

    st.title("🌐 Hospital Interoperability")

    hospital_a = pd.DataFrame({
        "Patient_ID": ["PA-101", "PA-102"],
        "Hospital": ["Hospital A", "Hospital A"],
        "Diagnosis": ["Malaria", "Typhoid"]
    })

    hospital_b = pd.DataFrame({
        "Patient_ID": ["PB-201", "PB-202"],
        "Hospital": ["Hospital B", "Hospital B"],
        "Diagnosis": ["Diabetes", "Ulcer"]
    })

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏥 Hospital A")
        st.dataframe(hospital_a)

    with col2:
        st.subheader("🏥 Hospital B")
        st.dataframe(hospital_b)

    st.markdown("---")

    patient_transfer = st.selectbox(
        "Select Patient",
        hospital_a["Patient_ID"]
    )

    if st.button("Transfer To Hospital B"):

        blockchain.add_block({

            "patient_transfer":
            patient_transfer,

            "from":
            "Hospital A",

            "to":
            "Hospital B",

            "timestamp":
            str(datetime.datetime.now())
        })

        log_activity(
            st.session_state.username,
            f"Transferred {patient_transfer}"
        )

        st.success(
            "Patient Successfully Transferred"
        )

# ==========================================
# RESEARCH ANALYTICS
# ==========================================
elif menu == "Research Analytics":

    st.title("📊 Thesis Research Analytics")

    breach_df = pd.DataFrame({

        "System": [
            "Traditional HIMS",
            "Blockchain HIMS"
        ],

        "Breaches": [
            48,
            7
        ]
    })

    fig1 = px.bar(
        breach_df,
        x="System",
        y="Breaches",
        title="Security Breach Reduction",
        text_auto=True
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    referral_df = pd.DataFrame({

        "System": [
            "Traditional",
            "Blockchain"
        ],

        "Referral Time": [
            120,
            35
        ]
    })

    fig2 = px.bar(
        referral_df,
        x="System",
        y="Referral Time",
        title="Referral Time Reduction",
        text_auto=True
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    uptime_df = pd.DataFrame({

        "System": [
            "Traditional",
            "Blockchain"
        ],

        "Uptime": [
            92,
            99.9
        ]
    })

    fig3 = px.line(
        uptime_df,
        x="System",
        y="Uptime",
        markers=True,
        title="System Uptime Comparison"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

# ==========================================
# IMMUTABILITY
# ==========================================
elif menu == "Immutability Verification":

    st.title(
        "🔍 Blockchain Immutability Verification"
    )

    selected_patient = st.selectbox(
        "Select Record",
        df["Participant_ID"]
    )

    patient = df[
        df["Participant_ID"] == selected_patient
    ].iloc[0]

    original_hash = hashlib.sha256(
        str(patient.to_dict()).encode()
    ).hexdigest()

    tamper = st.checkbox(
        "Simulate Data Tampering"
    )

    modified_patient = patient.copy()

    if tamper:

        modified_patient[
            "Referral_Time_After_Minutes"
        ] += 50

    new_hash = hashlib.sha256(
        str(modified_patient.to_dict()).encode()
    ).hexdigest()

    if original_hash == new_hash:

        st.success(
            "✅ Record Verified"
        )

    else:

        st.error(
            "⚠ Hash Mismatch Detected"
        )

# ==========================================
# REFERRAL WORKFLOW
# ==========================================
elif menu == "Referral Workflow":

    st.title(
        "🚑 Referral Workflow"
    )

    workflow_steps = [

        "Patient Registered",
        "Doctor Review",
        "Referral Created",
        "Blockchain Verification",
        "Receiving Hospital Approval",
        "Completed"
    ]

    for step in workflow_steps:

        st.success(f"✅ {step}")

# ==========================================
# EXPORT REPORTS
# ==========================================
elif menu == "Export Reports":

    st.title("📄 Export Reports")

    blockchain_logs = pd.read_sql_query(
        "SELECT * FROM blockchain",
        conn
    )

    csv = blockchain_logs.to_csv(
        index=False
    ).encode('utf-8')

    st.download_button(

        label="⬇ Download Blockchain Audit Logs",

        data=csv,

        file_name="blockchain_audit_logs.csv",

        mime="text/csv"
    )

# ==========================================
# ACTIVITY LOGS
# ==========================================
elif menu == "Activity Logs":

    st.title("📜 Activity Logs")

    logs = pd.read_sql_query(
        """
        SELECT * FROM activity_logs
        ORDER BY id DESC
        """,
        conn
    )

    st.dataframe(
        logs,
        use_container_width=True
    )

# ==========================================
# DOCTOR DASHBOARD
# ==========================================
elif menu == "Doctor Dashboard":

    st.title("🩺 Doctor Dashboard")

    add_new_patient()

# ==========================================
# REFERRAL CENTER
# ==========================================
elif menu == "Referral Center":

    st.title("🚑 Referral Center")

    patient = st.selectbox(
        "Select Patient",
        df["Participant_ID"]
    )

    hospital = st.selectbox(
        "Refer To",
        [
            "Hospital A",
            "Hospital B",
            "Radiology",
            "Pharmacy",
            "Lab"
        ]
    )

    if st.button("Send Referral"):

        blockchain.add_block({

            "patient": patient,
            "referral_hospital": hospital,
            "doctor":
            st.session_state.username,
            "timestamp":
            str(datetime.datetime.now())
        })

        log_activity(
            st.session_state.username,
            f"Referred patient {patient}"
        )

        st.success(
            f"Referral Sent to {hospital}"
        )

# ==========================================
# NURSE DASHBOARD
# ==========================================
elif menu == "Nurse Dashboard":

    st.title("👩‍⚕ Nurse Dashboard")

    st.markdown("""
    <div class='card'>
    Nurses can monitor patients,
    track referral times,
    and observe hospital workflows.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(f"""
        <div class='metric-card'>
        <h1>{len(df)}</h1>
        <p>Total Patients</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown(f"""
        <div class='metric-card'>
        <h1>{round(df['Referral_Time_After_Minutes'].mean(),2)}</h1>
        <p>Average Referral Time</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("📋 Patient Monitoring")

    st.dataframe(
        df.tail(15),
        use_container_width=True
    )

    st.markdown("---")

    monitoring_df = pd.DataFrame({

        "Hour": [
            "08:00",
            "10:00",
            "12:00",
            "14:00",
            "16:00"
        ],

        "Patients Monitored": [
            12,
            18,
            25,
            20,
            15
        ]
    })

    fig = px.line(
        monitoring_df,
        x="Hour",
        y="Patients Monitored",
        markers=True,
        title="Patient Monitoring Activity"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
    
# ==========================================
# PATIENT PORTAL
# ==========================================
elif menu == "Patient Portal":

    st.title("🧑 Patient Portal")

    st.info("Diagnosis: Malaria")

    st.info("Prescription: Coartem")

    st.info("Doctor: Dr. Ouma")

    st.markdown("---")

    st.subheader(
        "🔐 Blockchain Consent Management"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "Grant Doctor Access"
        ):

            log_activity(
                st.session_state.username,
                "Granted doctor access"
            )

            blockchain.add_block({

                "patient":
                st.session_state.username,

                "action":
                "Granted Doctor Access",

                "timestamp":
                str(datetime.datetime.now())
            })

            st.success(
                "Doctor Access Granted"
            )

    with col2:

        if st.button(
            "Revoke Access"
        ):

            log_activity(
                st.session_state.username,
                "Revoked doctor access"
            )

            blockchain.add_block({

                "patient":
                st.session_state.username,

                "action":
                "Revoked Doctor Access",

                "timestamp":
                str(datetime.datetime.now())
            })

            st.warning(
                "Doctor Access Revoked"
            )

    with col3:

        if st.button(
            "Emergency Access"
        ):

            log_activity(
                st.session_state.username,
                "Activated emergency access"
            )

            blockchain.add_block({

                "patient":
                st.session_state.username,

                "action":
                "Emergency Access Activated",

                "timestamp":
                str(datetime.datetime.now())
            })

            st.error(
                "Emergency Access Activated"
            )

    st.markdown("---")

    st.subheader("📜 Access History")

    patient_logs = pd.read_sql_query(
        """
        SELECT * FROM activity_logs
        ORDER BY id DESC
        LIMIT 10
        """,
        conn
    )

    st.dataframe(
        patient_logs,
        use_container_width=True
    )

    st.success(
        "✔ Kenya Data Protection Act Compliant"
    )

    st.success(
        "✔ Blockchain Consent Logged"
    )

    st.success(
        "✔ Patient-Controlled Access"
    )