import os
import time
import requests
import json
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
import google.generativeai as genai
import subprocess


# ─────────────────────────────────────────────────────────────────────────────
# Load Environment Variables and Google Sheets Setup
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()

SPREADSHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = "Sheet1"
RANGE_NAME = f"{SHEET_NAME}!A1:D1000"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]


CREDENTIALS_FILE = "credentials.json"
TOKEN_PICKLE = "token.pickle"

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")


def get_user_credentials():
    """Retrieve or refresh user credentials for Google Sheets"""
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)

    return creds


creds = get_user_credentials()
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()


# ─────────────────────────────────────────────────────────────────────────────
# Sync Function: Check, Query Gemini, Write Back
# ─────────────────────────────────────────────────────────────────────────────
def fetch_sheet_data():
    """Fetch customer data from the Google Sheet and return it as a DataFrame."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME)
        .execute()
    )

    values = result.get("values", [])
    filtered_values = [row for row in values if any(cell.strip() for cell in row)]

    if not filtered_values:
        print("⚠️ No data found in the customer sheet.")
        return pd.DataFrame(), RANGE_NAME

    headers = filtered_values[0]
    data_rows = filtered_values[1:]

    num_columns = len(headers)

    normalized_rows = [
        (
            row[:num_columns] + [""] * (num_columns - len(row))
            if len(row) != num_columns
            else row
        )
        for row in data_rows
    ]

    df = pd.DataFrame(normalized_rows, columns=headers)

    values = result.get("values", [])

    return df


# def replyToQuery(query: str, answer: str) -> str:
#     """Write a proper answer to the query given the data"""

#     prompt = (
#         f"""You are a research assistant for a travel company.
#         You need to answer queries that customers have.
#         I will provide you with a query and a researched answer.
#         Your task is to rewrite it clearly and professionally, keeping all useful information like phone numbers, addresses, links, and important facts.
#         \n\nQuery:\n{query}
#         \n\nResearched Answer:\n{answer}
#         \n\nRewritten Response:

#         \n\n Make sure you only return the Rewritten response and nothing else in plain text.
#         """
#     )


#     response = gemini_model.generate_content(prompt)
#     # print("Response is")
#     # print(response)

#     finalAnswer = response.text

#     return finalAnswer


def replyToQuery(query: str, answer: str, p: str) -> str:
    """Generate a human-like response to a customer query using researched data."""

    prompt = (
        "You are an assistant for a travel company.\n"
        f"{p}\n\n"
        "Don't remove the images from the answer. Include them in the response wherever they are relevant.\n"
        f"Query:\n{query}\n\n"
        f"Researched Answer:\n{answer}\n\n"
        "Written Response:\n\n"
        "Make sure you only return the Written response and nothing else in plain text."
    )

    # print("Prompt is:")
    # print(prompt)

    response = gemini_model.generate_content(prompt)
    finalAnswer = response.text

    return finalAnswer


def run_deerflow(query: str) -> str:
    deerflow_main = "/Users/priyakeshri/Desktop/Recent/Intern/newfile/deer-flow/main.py"
    command = ["uv", "run", deerflow_main, query]
    output_lines = []

    try:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as process:
            for line in process.stdout:
                print(line, end="")
                output_lines.append(line)

        full_output = "".join(output_lines)

        # ✅ Extract the final report starting from "reporter response:"
        marker = "reporter response:"
        marker_index = full_output.find(marker)

        if marker_index != -1:
            final_report = full_output[marker_index + len(marker) :].strip()
            return final_report
        else:
            return "⚠️ 'reporter response:' not found in output.\n" + full_output.strip()

    except Exception as e:
        return f"❌ Error: {str(e)}"


def sync_sheet():
    try:
        df = fetch_sheet_data()

        # print(df)
        # exit

        for index, row in df.iterrows():
            task_type = row.get("task_type", "").strip().lower()
            task_info = row.get("task_info", "").strip().lower()
            query = task_type + ":" + task_info
            answer = row.get("Answer", "").strip().lower()
            prompt = row.get("Prompt", "").strip().lower()
            if query == "" or answer != "":
                continue

            print(f"Processing: {query}")

            ans = run_deerflow(query)
            fullAns = replyToQuery(query, ans, prompt)

            headers = df.columns.tolist()
            answer_col_index = headers.index("Answer")
            column_letter = chr(65 + answer_col_index)

            update_range = f"{SHEET_NAME}!{column_letter}{index+2}"
            body = {"values": [[fullAns]]}
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=update_range,
                valueInputOption="RAW",
                body=body,
            ).execute()
            print(f"📝 Wrote answer to {update_range}")

    except Exception as e:
        print(f"Exception during sync: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Run Every 10 Seconds
# ─────────────────────────────────────────────────────────────────────────────

print("Start")
while True:
    sync_sheet()
    time.sleep(10)
