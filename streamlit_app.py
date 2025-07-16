import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="MusiqHub Dashboard", layout="wide")

selected_tab = st.sidebar.radio("Select Page", [ "About", "MusiqHub Dashboard", "Event Profit Summary"])

st.markdown("""
<style>
    table { width: 100%; }
    th, td { text-align: left !important; padding: 8px; }
</style>
""", unsafe_allow_html=True)

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

# Function to get tier and fee based on lesson fee
# Example usage with a DataFrame column:
# df['Tier'], df['Tier Fee'] = zip(*df['Lesson Fee Excl Room & GST'].apply(get_tier_and_fee))
@st.cache_data
def get_tier(lesson_fee):
	if not isinstance(lesson_fee, (int, float)):
		raise ValueError(f"Invalid lesson fee: {lesson_fee}. Must be a numeric value.")
	
	lesson_fee = float(lesson_fee)
	
	if lesson_fee < 11.51:
		return 1
	elif lesson_fee < 13.51:
		return 2
	elif lesson_fee < 15.51:
		return 3
	elif lesson_fee < 17.51:
		return 4
	elif lesson_fee < 20.51:
		return 5
	elif lesson_fee < 26.51:
		return 6
	else:
		return 7

def get_fee(lesson_fee):
	if not isinstance(lesson_fee, (int, float)):
		raise ValueError(f"Invalid lesson fee: {lesson_fee}. Must be a numeric value.")
	
	lesson_fee = float(lesson_fee)
	
	if lesson_fee < 11.51:
		return 1.80
	elif lesson_fee < 13.51:
		return 2.20
	elif lesson_fee < 15.51:
		return 2.60
	elif lesson_fee < 17.51:
		return 3.00
	elif lesson_fee < 20.51:
		return 3.30
	elif lesson_fee < 26.51:
		return 3.60
	else:
		return 4.00

# Tax rate for GST
GST_RATE = 0.10

# Function to get room rate based on room name
# Example usage:
# rate = get_room_rate("BBPS")
def get_room_rate(room_name):
    room_rates = {
        "BBPS": 60.00,
        "St Marks": 20.00,
        "Sunnyhills": 40.00,
        "Farm Cove": 20.00,
				"Golden Grove": 20.00,
				"HPS": 20.00,
				"Oranga": 20.00,
				"Wakaaranga": 20.00,
				"PHS": 20.00,
    }
    return room_rates.get(room_name, 0.0)  # Returns 0.0 if room_name not found

# Function to clean the event sheet data
# This function assumes the input DataFrame has the same structure as the one in the original code
# Usage example:
# df_raw = pd.read_excel("source/2025-02.xlsx", sheet_name=2, header=None)
# df_clean = clean_event_sheet(df_raw)
# st.dataframe(df_clean)
def clean_event_sheet(df):
		# Forward fill Event Date, Duration, Description (room name)
		df[[0, 1, 2]] = df[[0, 1, 2]].ffill()
		# Rename columns for clarity
		expected_columns = ["Event Date", "Duration", "Description", "Teacher Name", "Payroll Amount", "Student Name", "Family", "Status", "Pre-Tax Billed Amount", "Billed Amount"]
		if len(df.columns) >= len(expected_columns):
			df = df.iloc[:, :len(expected_columns)]  # Trim extra columns if present
			df.columns = expected_columns
			# Remove the first row if it matches the column titles
			if (df.iloc[0] == expected_columns).all():
				df = df.iloc[1:].reset_index(drop=True)
		else:
			raise ValueError(f"Column count mismatch: Expected at least {len(expected_columns)}, but got {len(df.columns)}")
		# Drop rows where Student Name is missing or blank
		df = df[df["Student Name"].notna() & (df["Student Name"].astype(str).str.strip() != "")]
		df = df.reset_index(drop=True)
		# Make the blank Pre-Tax Billed Amount 0.0
		df["Pre-Tax Billed Amount"] = df["Pre-Tax Billed Amount"].fillna(0.0)
		# Make the blank Billed Amount 0.0
		df["Billed Amount"] = df["Billed Amount"].fillna(0.0)
		return df


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

elif selected_tab == "Event Profit Summary":
    st.title("Event Profit Summary")

    # Retrieve folder ID from secrets or user input
    folder_id = st.secrets.get("sheet_folder_id")
    if not folder_id:
        folder_id = st.sidebar.text_input("Enter Drive Folder ID", value="", help="Provide the Google Drive folder ID for your Excel files.")
    if not folder_id:
        st.warning("Please set 'sheet_folder_id' in Streamlit secrets or enter it above.")
        st.stop()

    # Let user pick the Excel file from the Drive folder
    files = list_excel_files_from_folder(folder_id)
    file_names = [f["name"] for f in files]
    selected_file = st.sidebar.selectbox("Select Excel file for Event Profit", [""] + file_names)
    if not selected_file:
        st.warning("Please select an Excel file.")
        st.stop()
    file_id = next(f["id"] for f in files if f["name"] == selected_file)

    # Download the Excel file from Drive
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    df_sheet3 = pd.read_excel(fh, sheet_name=2, header=None)
    fh.seek(0)
    df_sheet2 = pd.read_excel(fh, sheet_name=1)

    # Parse sheet3 for sequential event sections
    summaries = {}
    current_desc = None
    for _, row in df_sheet3.iterrows():
        desc_cell = row.iloc[2]
        student_cell = row.iloc[5]
        billed_cell = row.iloc[8]
        if pd.notna(desc_cell):
            current_desc = desc_cell
            summaries.setdefault(current_desc, {"events": 0, "students": 0, "billed": 0})
            summaries[current_desc]["events"] += 1
        elif current_desc:
            if pd.notna(student_cell):
                summaries[current_desc]["students"] += 1
            if pd.notna(billed_cell):
                summaries[current_desc]["billed"] += billed_cell

    # Map room rates from sheet2 (columns A and C)
    rate_map = dict(zip(df_sheet2.iloc[:, 0], df_sheet2.iloc[:, 2]))

    # Build DataFrame rows
    rows = []
    for desc, vals in summaries.items():
        rate = rate_map.get(desc, 0)
        students = vals["students"]
        per_student = rate / students if students else 0
        billed = vals["billed"]
        tax = billed * 0.15
        profit = billed - tax - rate
        rows.append([desc, vals["events"], students, rate, per_student, tax, billed, profit])

    event_summary_df = pd.DataFrame(rows, columns=[
        "Description", "Events", "Students", "Room rate", 
        "Room rate per student", "Tax", "Billed amount", "Profit"
    ])

    st.subheader("Event Profit Summary Table")
    st.dataframe(event_summary_df)

elif selected_tab == "About":
		st.title("About MusiqHub Dashboard")
		st.markdown("""
		
		
		
		""")
		# Read both Excel files (first sheet by default)
		df_feb = pd.read_excel("source/2025-02.xlsx")
		df_mar = pd.read_excel("source/2025-03.xlsx")


		# Display the third sheet of the February file
		st.subheader("February 2025 Data")
		df_feb_sheet3 = pd.read_excel("source/2025-02.xlsx", sheet_name=2, header=None)
		df_feb_cleaned = clean_event_sheet(df_feb_sheet3)
		st.dataframe(df_feb_cleaned) 

		# From the cleaned DataFrame, so there is a Student Name and the Description, so each student has divider of comma (,) it's mean more than one student in the same room
		# I want to show the each student name with their Description column
		# st.subheader("February 2025 Student Names and Descriptions")
		# if "Student Name" in df_feb_cleaned.columns and "Description" in df_feb_cleaned.columns:
		# 	# Split the Student Name by comma and explode the DataFrame
		# 	df_feb_cleaned["Student Name"] = df_feb_cleaned["Student Name"].str.split(",")
		# 	df_feb_exploded = df_feb_cleaned.explode("Student Name")
		# 	# Remove leading/trailing spaces from Student Name
		# 	df_feb_exploded["Student Name"] = df_feb_exploded["Student Name"].str.strip()
		# 	# Remove rows where Student Name is blank
		# 	df_feb_exploded = df_feb_exploded[df_feb_exploded["Student Name"].notna() & (df_feb_exploded["Student Name"].astype(str).str.strip() != "")]
		# 	# Show the DataFrame with Student Name and Description
		# 	df_student_per_room = df_feb_exploded[["Student Name", "Description"]].drop_duplicates().reset_index(drop=True)
			# st.markdown(df_student_per_room.to_html(index=False), unsafe_allow_html=True)

		# Based on the df_student_per_room DataFrame, calculate how much is student for each room Description, Total students
		st.subheader("February 2025 Total Students per Description (Room)")
		if "Description" in df_feb_cleaned.columns:
			# Count the number of unique students per room Description
			df_feb_exploded = df_feb_cleaned.explode("Student Name")
			total_students_per_room = df_feb_exploded.groupby("Description")["Student Name"].nunique().reset_index()
			total_students_per_room.columns = ["Description", "Total Room Usage"]
			# Calculate the room rate per student
			room_rate_per_student_map = {
				desc: get_room_rate(desc) / total_students if total_students > 0 else 0
				for desc, total_students in zip(total_students_per_room["Description"], total_students_per_room["Total Room Usage"])
			}
			total_students_per_room["Room Rate per Students"] = total_students_per_room["Description"].map(room_rate_per_student_map)
			st.markdown(total_students_per_room.to_html(index=False), unsafe_allow_html=True)

		# Just show the Description, Billed Amount from the cleaned DataFrame
		# st.subheader("February 2025 Profit per student")
		df_feb_cleaned["Profit"] = df_feb_cleaned.apply(
			lambda row: 0 if row["Billed Amount"] == 0.0 else row["Billed Amount"] - (row["Billed Amount"] * GST_RATE) - get_fee(row["Billed Amount"]) - room_rate_per_student_map.get(row["Description"], 0),
			axis=1
		)

		# st.markdown(df_feb_cleaned[["Event Date", "Duration","Description", "Billed Amount", "Profit"]].to_html(index=False), unsafe_allow_html=True)
		

		# Convert the above data to a DataFrame and sum the profit per Description
		st.subheader("February 2025 Total Profit per Room")
		# Calculate total profit and total billed amount per room
		profit_per_room = df_feb_cleaned.groupby("Description").agg({
			"Profit": "sum",
			"Billed Amount": "sum"
		}).reset_index()
		profit_per_room = profit_per_room.rename(columns={"Profit": "Total Profit (-10% GST)", "Billed Amount": "Total Billed Amount"})
		profit_per_room["Room rate per Students"] = profit_per_room["Description"].map(room_rate_per_student_map)
		profit_per_room = profit_per_room[["Description", "Room rate per Students", "Total Billed Amount", "Total Profit (-10% GST)"]]
		# Add a new row for totals
		total_profit = profit_per_room["Total Profit (-10% GST)"].sum()
		total_billed = profit_per_room["Total Billed Amount"].sum()
		total_row = pd.DataFrame([["Total", None, total_billed, total_profit]], columns=["Description", "Room rate per Students", "Total Billed Amount", "Total Profit (-10% GST)"])
		profit_per_room = pd.concat([profit_per_room, total_row], ignore_index=True)

		# Display the updated DataFrame
		st.dataframe(profit_per_room)