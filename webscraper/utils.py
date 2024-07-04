import aiohttp
import asyncio
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
import csv
import os
from dotenv import load_dotenv
from urllib.parse import urljoin, urlparse
import requests
import fitz  # PyMuPDF for handling PDFs
import re
from langdetect import detect, DetectorFactory
from validate_email import validate_email
from .language_mapping import map_language_code  # Import the language mapping function

# Ensures consistent language detection results
DetectorFactory.seed = 0
load_dotenv()
# Function to extract emails from a webpage or text
def extract_emails(text):
    emails = set(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
    valid_emails = set()
    for email in emails:
        if validate_email(email):
            valid_emails.add(email)
    return valid_emails

# Function to normalize URLs
def normalize_url(domain):
    if domain.startswith(("http://", "https://")):
        return domain
    return "http://" + domain

# Function to check if a URL is internal
def is_internal_link(base_url, link):
    base_netloc = urlparse(base_url).netloc
    link_netloc = urlparse(link).netloc
    return base_netloc == '' or base_netloc == link_netloc

# Function to extract the main domain from a URL
def get_main_domain(url):
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')
    if len(domain_parts) > 2:
        return '.'.join(domain_parts[-2:])
    return parsed_url.netloc

# Asynchronous function to scrape a page for emails and detect language
async def scrape_page(url, session):
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    text = ' '.join(soup.stripped_strings)
                elif 'application/pdf' in content_type:
                    pdf_content = await response.read()
                    text = extract_text_from_pdf(pdf_content)
                elif 'text/plain' in content_type:
                    text = await response.text()
                elif 'application/xml' in content_type or 'text/xml' in content_type:
                    xml_content = await response.text()
                    text = extract_text_from_xml(xml_content)
                else:
                    print(f"Unsupported content type at {url}: {content_type}")
                    return set(), None, None
                emails = extract_emails(text)
                language_code = map_language_code(detect(text))
                return emails, soup if 'text/html' in content_type else None, language_code
            else:
                print(f"Failed to access {url}: {response.status} - {response.reason}")
    except Exception as e:
        print(f"Error while accessing {url}: {e}")
    return set(), None, None

# Function to extract text from PDF content
def extract_text_from_pdf(pdf_content):
    text = ""
    try:
        pdf_document = fitz.open("pdf_bytes", pdf_content)
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
    except Exception as e:
        print(f"Error while extracting text from PDF: {e}")
    return text

# Function to extract text from XML content
def extract_text_from_xml(xml_content):
    text = ""
    try:
        root = ET.fromstring(xml_content)
        text = ' '.join(root.itertext())
    except Exception as e:
        print(f"Error while extracting text from XML: {e}")
    return text

# Asynchronous function to scrape the homepage for emails and gather internal links
async def scrape_homepage(domain, session):
    url = normalize_url(domain)
    emails, soup, language_code = await scrape_page(url, session)
    if not soup:
        return emails, set(), language_code
    internal_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(url, href)
        if is_internal_link(url, full_url):
            internal_links.add(full_url)
    return emails, internal_links, language_code

# Asynchronous function to scrape specific internal pages for emails
async def scrape_internal_pages(internal_links, session):
    tasks = [scrape_page(url, session) for url in internal_links]
    results = await asyncio.gather(*tasks)
    emails = set()
    language_code = None
    for new_emails, _, lang_code in results:
        emails.update(new_emails)
        if lang_code:
            language_code = lang_code  # Assume the language is the same for all pages
    return emails, language_code

# Function to add a contact on Brevo through API
def add_contact_to_brevo(email, domain, language_code):
    main_domain = get_main_domain(domain)
    api_url = 'https://api.brevo.com/v3/contacts'
    api_key = os.getenv('SENDINBLUE_API_KEY')  # Get the API key from environment variables
    headers = {
        'Content-Type': 'application/json',
        'api-key': api_key
    }
    data = {
        "email": email,
        "attributes": {
            "DOMINIO": main_domain,
            "TEST_LANG": language_code
        },
        "listIds": [23]  # New list ID
    }
    try:
        response = requests.post(api_url, headers=headers, json=data)
        if response.status_code == 201:
            print(f"Added {email} from {domain} with language {language_code} to Brevo")
            return True
        else:
            print(f"Failed to add {email}: {response.status_code} - {response.text}")
            if response.status_code == 400 and "duplicate_parameter" in response.text:
                print(f"Duplicate contact: {email}")
    except requests.RequestException as e:
        print(f"Error while adding contact to Brevo: {e}")
    return False

# Asynchronous function to process the CSV file and scrape emails
async def process_csv_file(file_path):
    total_scraped = 0
    total_added = 0
    sample_emails = set()
    total_lines = sum(1 for _ in open(file_path)) - 1  # Subtract 1 for header row
    
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            tasks = []
            for row in reader:
                domain = row[0]
                tasks.append(scrape_domain(domain, session))
            results = await asyncio.gather(*tasks)
            for result in results:
                scraped, added, emails = result
                total_scraped += scraped
                total_added += added
                sample_emails.update(emails)

    return {
        'total_scraped': total_scraped,
        'total_added': total_added,
        'sample_emails': list(sample_emails)[:10]  # Limit to 10 emails for the sample
    }

async def scrape_domain(domain, session):
    total_scraped = 0
    total_added = 0
    sample_emails = set()
    
    emails, internal_links, language_code = await scrape_homepage(domain, session)
    total_scraped += len(emails)
    new_emails, lang_code = await scrape_internal_pages(internal_links, session)
    emails.update(new_emails)
    if lang_code:
        language_code = lang_code
    for email in emails:
        if add_contact_to_brevo(email, domain, language_code):
            total_added += 1
            if len(sample_emails) < 10:
                sample_emails.add(email)
    
    return total_scraped, total_added, sample_emails

# Function to run the async process_csv_file function
def run_process(file_path, max_attempts=5):
    attempt = 0
    combined_results = {
        'total_scraped': 0,
        'total_added': 0,
        'sample_emails': set()
    }
    while attempt < max_attempts:
        print(f"Starting attempt {attempt + 1} for processing the CSV file: {file_path}")
        results = asyncio.run(process_csv_file(file_path))
        combined_results['total_scraped'] += results['total_scraped']
        combined_results['total_added'] += results['total_added']
        combined_results['sample_emails'].update(results['sample_emails'])
        attempt += 1
    combined_results['sample_emails'] = list(combined_results['sample_emails'])[:10]
    print(f"Finished processing the CSV file: {file_path} after {attempt} attempts")
    return combined_results

def generate_results_csv(results):
    csv_file_path = 'results.csv'
    try:
        with open(csv_file_path, 'w', newline='') as csvfile:
            fieldnames = ['Total Emails Scraped', 'Total Emails Added', 'Sample Emails']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerow({
                'Total Emails Scraped': results['total_scraped'],
                'Total Emails Added': results['total_added'],
                'Sample Emails': ', '.join(results['sample_emails'])
            })
        print(f"Results CSV generated: {csv_file_path}")
        return csv_file_path
    except Exception as e:
        print(f"Error generating CSV: {e}")
        raise
