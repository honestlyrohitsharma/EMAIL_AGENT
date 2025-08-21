import os
import base64
import re
from email.mime.text import MIMEText
from dotenv import load_dotenv


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


import google.generativeai as genai


load_dotenv()


SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]
CREDENTIALS_FILE = 'credentials.json'

# Configure the Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("No Gemini API key found. Please set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=GEMINI_API_KEY)


class EmailAgent:
    def __init__(self):
        """Initializes the EmailAgent by authenticating with Gmail and setting up the Gemini model."""
        self.gmail_service = self._authenticate_gmail()
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ AI Email Agent with Gemini is ready.")

    def _authenticate_gmail(self):
        """Authenticates with the Gmail API using OAuth 2.0."""
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        try:
            service = build('gmail', 'v1', credentials=creds)
            print("Gmail authentication successful.")
            return service
        except HttpError as error:
            print(f'An error occurred during Gmail authentication: {error}')
            return None

    def _get_ai_response(self, prompt):
        """Gets a response from the Gemini API."""
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error interacting with Gemini: {e}")
            return f"Error: Could not get a response from the AI."

    

    def clean_email_body(self, body):
        """Cleans HTML tags and extra whitespace from email body."""
        body = re.sub(r'<.*?>', '', body)
        body = re.sub(r'\s+', ' ', body)
        return body.strip()

    def get_email_content(self, msg_id):
        """Fetches the content of a specific email."""
        try:
            message = self.gmail_service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = message['payload']
            headers = payload['headers']
            
            email_data = { "id": message['id'], "snippet": message['snippet'], "subject": "No Subject", "from": "Unknown Sender", "body": "" }

            for header in headers:
                if header['name'] == 'Subject':
                    email_data['subject'] = header['value']
                if header['name'] == 'From':
                    email_data['from'] = header['value']
            
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body_data = part['body']['data']
                        email_data['body'] = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
            elif 'data' in payload['body']:
                 body_data = payload['body']['data']
                 email_data['body'] = base64.urlsafe_b64decode(body_data).decode('utf-8')

            email_data['body'] = self.clean_email_body(email_data['body'])
            return email_data
        
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
    
    def create_message(self, sender, to, subject, message_text):
        """Create a message for an email."""
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': encoded_message}

    def send_message(self, user_id, message):
        """Send an email message."""
        try:
            sent_message = self.gmail_service.users().messages().send(userId=user_id, body=message).execute()
            print(f"Message sent successfully! Message ID: {sent_message['id']}")
            return sent_message
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

    

    def list_recent_emails(self, count=5):
        """Lists the most recent emails."""
        try:
            results = self.gmail_service.users().messages().list(userId='me', maxResults=count, labelIds=['INBOX']).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("No new messages found.")
                return
            
            print("\n--- Recent Emails ---")
            for msg in messages:
                email_data = self.get_email_content(msg['id'])
                if email_data:
                    print(f"ID: {email_data['id']} | From: {email_data['from']} | Subject: {email_data['subject']}")
        except HttpError as error:
            print(f'An error occurred: {error}')

    def summarize_email(self, email_body):
        """Summarizes email content using Gemini."""
        if not email_body: return "Email body is empty, nothing to summarize."
        prompt = f"Please summarize the following email content in 3-4 key points:\n\n---\n{email_body}\n---"
        return self._get_ai_response(prompt)

    def categorize_email(self, email_body, categories=["Important", "Promotion", "Social", "Work-related", "Personal", "Spam"]):
        """Categorizes an email using Gemini."""
        if not email_body: return "Email body is empty, cannot categorize."
        prompt = (f"Analyze the following email and categorize it into one of these categories: {', '.join(categories)}. Provide only the category name as the answer.\n\n---\n{email_body}\n---")
        category = self._get_ai_response(prompt)
        return category if category in categories else "Uncategorized"

    def draft_reply(self, email_content, user_instruction):
        """Drafts a reply to an email based on user instruction using Gemini."""
        prompt = (f"You are an AI email assistant. Write a professional and helpful reply to the following email. Keep in mind the user's instruction.\n\n"
                  f"**User's Instruction:** '{user_instruction}'\n\n**Original Email:**\nSubject: {email_content['subject']}\nFrom: {email_content['from']}\nBody:\n{email_content['body']}\n\n"
                  f"**Draft your reply below:**")
        return self._get_ai_response(prompt)
    
    def compose_and_send_email(self):
        """Guides user to compose a new email from a prompt and sends it."""
        print("\n--- Compose New Email ---")
        recipient = input("Enter the recipient's email address: ")
        subject = input("Enter the subject line: ")
        user_prompt = input("Enter your prompt for the email content: ")
        
        print("\n🧠 Contacting Gemini to draft the email...")
        full_prompt = (f"You are an email writing assistant. Write a clear and professional email based on the "
                       f"following instruction. Do not include a subject line, just the email body.\n\n"
                       f"Instruction: '{user_prompt}'")
        email_body = self._get_ai_response(full_prompt)

        if "Error:" in email_body:
            print(email_body)
            return

        print("\n" + "="*50)
        print("AI-Generated Email Draft:")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print("-" * 50)
        print(email_body)
        print("="*50 + "\n")

        confirmation = input("Do you want to send this email? (y/n): ").lower()
        if confirmation == 'y':
            message = self.create_message('me', recipient, subject, email_body)
            self.send_message('me', message)
        else:
            print("Email sending aborted by user.")

    def natural_language_search(self, query):
        """Uses Gemini to convert natural language to a Gmail search query."""
        prompt = (f"Convert the following natural language request into a valid Gmail search query string. Only return the query string itself.\n\n"
                  f"**User Request:** '{query}'\n**Gmail Query String:**")
        
        gmail_query = self._get_ai_response(prompt).replace('"', '')
        print(f"\n🧠 AI generated search query: {gmail_query}")
        
        try:
            results = self.gmail_service.users().messages().list(userId='me', q=gmail_query, maxResults=5).execute()
            messages = results.get('messages', [])
            if not messages:
                print("No emails found matching your search.")
                return

            print("\n--- Search Results ---")
            for msg in messages:
                email_data = self.get_email_content(msg['id'])
                if email_data:
                    print(f"ID: {email_data['id']}\nFrom: {email_data['from']}\nSubject: {email_data['subject']}\nSnippet: {email_data['snippet']}\n" + "-"*20)
        except HttpError as error:
            print(f"An error occurred during search: {error}")

def main():
    """Main function to run the interactive command-line interface."""
    agent = EmailAgent()
    if not agent.gmail_service:
        return

    while True:
        print("\n--- AI Email Assistant Menu (Gemini Powered) ---")
        print("1. List recent emails")
        print("2. Read, Summarize & Categorize an email")
        print("3. Draft a reply to an existing email")
        print("4. Compose and Send a new AI-drafted email") 
        print("5. Search emails with natural language")
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ")

        if choice == '1':
            agent.list_recent_emails()

        elif choice == '2':
            email_id = input("Enter the Email ID to process: ")
            email_content = agent.get_email_content(email_id)
            if email_content:
                print("\n--- Email Content ---")
                print(f"From: {email_content['from']}\nSubject: {email_content['subject']}\n")
                print(f"Body:\n{email_content['body'][:500]}...\n" + "-"*20)
                
                print("\n🧠 Gemini Summary:")
                summary = agent.summarize_email(email_content['body'])
                print(summary)

                print("\n🧠 Gemini Category:")
                category = agent.categorize_email(email_content['body'])
                print(category)

        elif choice == '3':
            email_id = input("Enter the Email ID to reply to: ")
            instruction = input("What should the reply be about? (e.g., 'Politely decline the invitation'): ")
            email_content = agent.get_email_content(email_id)
            if email_content:
                reply = agent.draft_reply(email_content, instruction)
                print("\n--- AI Drafted Reply ---")
                print(reply)

        elif choice == '4':
            agent.compose_and_send_email()

        elif choice == '5':
            query = input("What are you searching for? (e.g., 'emails from my boss about the Q3 report'): ")
            agent.natural_language_search(query)

        elif choice == '6':
            print("Exiting AI Email Assistant. Goodbye!")
            break

        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

if __name__ == '__main__':
    main()