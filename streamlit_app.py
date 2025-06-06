import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="MusiqHub Dashboard", layout="wide")

# Tab selection
selected_tab = st.sidebar.radio("Select Page", ["MusiqHub Dashboard", "Event Profit Summary"])

# Common CSS
st.markdown("""
<style>
    table { width: 100%; }
    th, td { text-align: left !important; padding: 8px; }
</style>
""", unsafe_allow_html=True)

# Google Drive Setup (from secrets)
@st.cache_resource
def get_drive_service():
    service_account_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)

def list_excel_files_from_folder(folder_id):
    service = get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'",
        pageSize=50,
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])

# ---- MusiqHub Dashboard ----
if selected_tab == "MusiqHub Dashboard":
    st.title("MusiqHub Franchise Dashboard")
    st.sidebar.header("Filters")
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"], key="main_csv")

    if "full_data" not in st.session_state:
        years = [2022, 2023, 2024]
        terms = ["Term 1", "Term 2", "Term 3", "Term 4"]
        franchisees = ["Bob Smith", "Alice Johnson", "Tom Lee", "Sophie Wright", "David Brown", "Emma Green", "Chris Adams", "Laura Hill", "James Fox", "Nina Wood"]
        schools = ["Mt Roskill Grammar", "Epsom Girls Grammar", "Avondale College", "Lynfield College", "Onehunga High", "Auckland Grammar", "St Cuthbert's", "Baradene College", "Western Springs College", "Selwyn College"]
        instruments = ["Guitar", "Piano", "Drums", "Violin", "Flute"]

        np.random.seed(42)
        data = []
        for f in franchisees:
            for s in schools[:2]:
                for y in years:
                    for t in terms:
                        for i in instruments:
                            student_count = np.random.randint(1, 6)
                            lesson_count = student_count * np.random.randint(4, 10)
                            new_enrolments = np.random.randint(0, 3)
                            cancellations = np.random.randint(0, 3)
                            avg_revenue = np.random.uniform(25, 50)
                            lifetime_revenue = avg_revenue * student_count * np.random.randint(3, 8)
                            gross_profit = lifetime_revenue * 0.65
                            data.append([f, s, y, t, i, student_count, lesson_count, new_enrolments, cancellations, avg_revenue, lifetime_revenue, gross_profit])

        st.session_state["full_data"] = pd.DataFrame(data, columns=[
            "Franchisee", "School", "Year", "Term", "Instrument",
            "Student Count", "Lesson Count", "New Enrolments", "Cancellations",
            "Avg Revenue", "Lifetime Revenue", "Gross Profit"
        ])

    if uploaded_file is not None:
        new_data = pd.read_csv(uploaded_file)
        st.session_state["full_data"] = pd.concat([st.session_state["full_data"], new_data], ignore_index=True)

    df = st.session_state["full_data"]

    years = sorted(df["Year"].unique())
    terms = sorted(df["Term"].unique())
    franchisees = sorted(df["Franchisee"].unique())

    selected_year = st.sidebar.selectbox("Filter by Year", ["All"] + list(years), index=0)
    selected_term = st.sidebar.selectbox("Filter by Term", ["All"] + list(terms), index=0)
    selected_franchisee = st.sidebar.selectbox("Filter by Franchisee", ["All"] + list(franchisees), index=0)

    filtered_df = df.copy()
    if selected_year != "All":
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]
    if selected_term != "All":
        filtered_df = filtered_df[filtered_df["Term"] == selected_term]
    if selected_franchisee != "All":
        filtered_df = filtered_df[filtered_df["Franchisee"] == selected_franchisee]

    with st.expander("School by Number of Students by Term / Year"):
        st.markdown(filtered_df.groupby(["Year", "Term", "School"]).agg({"Student Count": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("School by Instrument by Student Numbers"):
        st.markdown(filtered_df.groupby(["School", "Instrument"]).agg({"Student Count": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Franchisee by School by Student Numbers by Term / Year"):
        st.markdown(filtered_df.groupby(["Franchisee", "School", "Year", "Term"]).agg({"Student Count": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Franchisee by School by Lesson Numbers by Term / Year"):
        st.markdown(filtered_df.groupby(["Franchisee", "School", "Year", "Term"]).agg({"Lesson Count": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Franchisee by School by Instrument (Number of Students)"):
        st.markdown(filtered_df.groupby(["Franchisee", "School", "Instrument"]).agg({"Student Count": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("New Student Enrolment by Franchisee"):
        st.markdown(filtered_df.groupby("Franchisee").agg({"New Enrolments": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Retention Rate by Franchisee"):
        retention = filtered_df.groupby("Franchisee").agg({"Student Count": "sum", "New Enrolments": "sum"}).reset_index()
        retention["Retention Rate %"] = (1 - retention["New Enrolments"] / retention["Student Count"]).fillna(0) * 100
        st.markdown(retention[["Franchisee", "Retention Rate %"]].to_html(index=False), unsafe_allow_html=True)

    with st.expander("Lesson Cancellations by Franchisee"):
        st.markdown(filtered_df.groupby("Franchisee").agg({"Cancellations": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Average Revenue per Student by Franchisee"):
        st.markdown(filtered_df.groupby("Franchisee").agg({"Avg Revenue": "mean"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Average Lifetime Revenue per Student by Franchisee"):
        st.markdown(filtered_df.groupby("Franchisee").agg({"Lifetime Revenue": "mean"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Total Revenue by Franchisee"):
        st.markdown(filtered_df.groupby("Franchisee").agg({"Lifetime Revenue": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

    with st.expander("Gross Profit by Franchisee"):
        st.markdown(filtered_df.groupby("Franchisee").agg({"Gross Profit": "sum"}).reset_index().to_html(index=False), unsafe_allow_html=True)

# ---- Event Profit Summary ----
elif selected_tab == "Event Profit Summary":
    st.title("Event Profit Summary")

    folder_id = st.text_input("Enter Google Drive Folder ID:", "")
    if folder_id:
        files = list_excel_files_from_folder(folder_id)
        st.write("### Available Files in Folder:")

        file_names = [f["name"] for f in files]
        selected_file = st.selectbox("Choose a file to view:", file_names)

        if selected_file:
            selected_file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
            if selected_file_id:
                service = get_drive_service()
                request = service.files().get_media(fileId=selected_file_id)

                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                fh.seek(0)
                xls = pd.ExcelFile(fh)

                df_events = xls.parse(xls.sheet_names[2])
                df_room = xls.parse("Room Hire")

                df_room = df_room.rename(columns={df_room.columns[0]: "School", df_room.columns[5]: "Room Hire"})
                df_room = df_room[["School", "Room Hire"]]

                df_merged = pd.merge(df_events, df_room, how="left", on="School")
                df_merged["Room Hire"].fillna(0, inplace=True)

                df_merged["Revenue"] = df_merged["Total Students"] * df_merged["Fee Per Student"]
                df_merged["MusiqHub Profit"] = df_merged["Revenue"] - df_merged["Tutor Fee"] - df_merged["Support Fee"] - df_merged["Room Hire"]

                total_row = pd.DataFrame({
                    "School": ["Total"],
                    "Total Students": [df_merged["Total Students"].sum()],
                    "Fee Per Student": [""],
                    "Tutor Fee": [df_merged["Tutor Fee"].sum()],
                    "Support Fee": [df_merged["Support Fee"].sum()],
                    "Room Hire": [df_merged["Room Hire"].sum()],
                    "Revenue": [df_merged["Revenue"].sum()],
                    "MusiqHub Profit": [df_merged["MusiqHub Profit"].sum()]
                })

                df_display = pd.concat([df_merged, total_row], ignore_index=True)
                st.dataframe(df_display)
    else:
        st.info("Paste a Google Drive folder ID above to view files.")