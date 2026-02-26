from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1GpVZOC38NNFNtx6wfmizlVGdE74Oso3aRmb1NF0zitY"
print("before main")
def main():
    credentials = None
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not credentials or not credentials.valid:
        print("no token.json for credentials")
        if credentials and credentials.expired and credentials.refresh_token:
            print("expired credentials")
            credentials.refresh(Request())
        else:
            print("getting credentials from secret")
            flow = InstalledAppFlow.from_client_secrets_file(
                "..\secrets\credential2.json", SCOPES
            )
            credentials = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            print("new token")
            f.write(credentials.to_json())
    
    try:
        service = build("sheets", "v4", credentials=credentials)
        sheets = service.spreadsheets()
        results = sheets.values().get(spreadsheetId=SPREADSHEET_ID, range="Trade Data!B3:I19").execute()
        values = results.get("values", [])
        if not values:
            print("No data found.")
        for row in values:
            print(values)

        # update
        result : HttpRequest = sheets.values().update(
            spreadsheetId = SPREADSHEET_ID,
            range = "Trade Data!J26",
            valueInputOption = "USER_ENTERED",
            body = {
                "values": [
                    ["test"]
                ]
            }
        ).execute()
        
        print(type(result))
        print(result)
    except HttpError as Err:
        print(Err)
    
if __name__ == "__main__":
    main()