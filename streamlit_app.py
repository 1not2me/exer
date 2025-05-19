import os
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
import requests
from bs4 import BeautifulSoup
import textwrap  # לעיצוב פסקאות במסך

# Load API key from .env file
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create Gemini Pro model
model = genai.GenerativeModel("gemini-1.5-flash")

# Extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except FileNotFoundError:
        return "Error: PDF file not found."
    except Exception as e:
        return f"Error while processing PDF: {e}"
    return text

# Extract text from a web URL
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text_parts = soup.find_all('p')
        return '\n'.join([p.get_text() for p in text_parts])
    except Exception as e:
        return f"Error while fetching URL: {e}"

# Summarize text with Gemini using selected length and format
def summarize_with_gemini(text, length="short", format="paragraph"):
    try:
        chat = model.start_chat()
        if format == "bullets":
            prompt = (
                f"Summarize the following text in a {length} style. "
                f"Present the summary as bullet points – one idea per line:\n\n{text}"
            )
        else:
            prompt = f"Summarize the following text in a {length} style as a paragraph:\n\n{text}"

        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        return f"Error while summarizing with Gemini: {e}"

# Format paragraph nicely with line breaks every X characters
def format_paragraph(text, width=100):
    return "\n".join(textwrap.wrap(text, width=width))

# Main function
def main():
    source_type = input("Enter 'file' to upload a document or 'url' to use a web address: ").lower()

    if source_type == 'file':
        file_path = input("Enter the path to the file (PDF or TXT): ").strip().strip('"')
        if file_path.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.txt'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                text = f"Error while reading TXT file: {e}"
        else:
            text = "Error: Unsupported file format."
    elif source_type == 'url':
        url = input("Enter the web address: ").strip().strip('"')
        text = extract_text_from_url(url)
    else:
        print("Invalid input.")
        return

    if text and not text.startswith("Error"):
        print("\nExtracted text:")
        lines = text.splitlines()
        if len(lines) > 10:
            for line in lines[:10]:
                print(line)
            print("...")
        else:
            print(text)

        summary_length = input("Enter summary length (short / medium / detailed): ").lower()
        summary_format = input("Enter summary format (paragraph / bullets): ").lower()
        summary = summarize_with_gemini(text, length=summary_length, format=summary_format)

        print("\nSummary:")
        if summary_format == "paragraph":
            print(format_paragraph(summary))
        else:
            print(summary)
    else:
        print(text)

if __name__ == "__main__":
    main()
