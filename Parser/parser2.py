import re
import os
import pytesseract
from PIL import Image
#import pdfplumber
from pdf2image import convert_from_path
import csv


def ocr_image(path):
    img = Image.open(path)
    return pytesseract.image_to_string(img)


def pdf_to_text(path):
    text = ""  
    images = convert_from_path(path)
    for img in images:
        img.save("temp.png")
        text += ocr_image("temp.png") + "\n"
        os.remove("temp.png")
    return text


def find_line_with_keywords(text, keywords):
    lines = text.lower().splitlines()
    for line in lines:
        for key in keywords:
            if key in line:
                return line.strip()
    return None

def find_block_after_keywords(text, keywords, num_lines):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for key in keywords:
            if key.lower() in line.lower():
                block = [line.strip()]
                for j in range(1, num_lines):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        if next_line:
                            block.append(next_line)
                return " ".join(block)
    return None


def extract_amount(text, total_keywords):
    if not text:
        return None
    
    for keyword in total_keywords:
        #amount patterns
        pattern = (
            rf'(?i){keyword}.*?[:\s]*[\.\-]?\s*(?:rs\.?|inr|₹|\$|eur|usd)?\s*([0-9,]+(?:\.\d+)?|\d+)'
        )
        match = re.search(pattern, text)
        if match:
            amt = match.group(1).replace(',', '')
            try:
                return float(amt)
            except:
                continue
    # find standalone amounts if nothing is found with patterns
    fallback = re.findall(r'(?i)(?:rs\.?|inr|₹|\$|eur|usd)\s?([0-9,]+(?:\.\d{2})?)', text)
    fallback = [float(f.replace(',', '')) for f in fallback]
    if fallback:
        return max(fallback)
    return None


def extract_code(line):
    if not line:
        return None
    for word in line.split():
        if any(c.isdigit() for c in word):
            return word.strip(':#')
    return None

def extract_currency_symbol(text, currency_keywords):
    for word in re.findall(r'\b\w+\b|₹|\$', text):
        lower_word = word.lower()
        if lower_word in currency_keywords or word in ['₹', '$', '€', '£']:
            return word.upper() if word.isalpha() else word
    return None


def extract_invoice_number(text, invoice_keywords):
    if not text:
        return None
    #patterns
    keywords_pattern = '|'.join(invoice_keywords)
    pattern = rf'(?i)\b(?:{keywords_pattern})\s*[:#\-]?\s*\n?\s*([A-Z0-9][A-Z0-9\-\/]{{2,}})'

    matches = re.findall(pattern, text)
    cleaned_matches = []

    for m in matches:
        m = m.strip().replace(' ', '')
        if len(m) >= 3 and re.match(r'^[A-Z0-9\-\/]+$', m):
            cleaned_matches.append(m)

    # first match
    if cleaned_matches:
        return cleaned_matches[0]

    # Fallback: search lines with "invoice" or "inv" and extract codes there
    for line in text.splitlines():
        if any(k in line.lower() for k in invoice_keywords):
            match = re.search(r'\b([A-Z0-9\-\/]{3,})\b', line)
            if match:
                return match.group(1)
    
    return None


def extract_upi_amount_from_center(image_path):
    img = Image.open(image_path)
    width, height = img.size

    # Crop area
    top = int(height * 0.22)
    bottom = int(height * 0.32)
    left = 0
    right = width

    cropped = img.crop((left, top, right, bottom))
    #parse the cropped image
    text = pytesseract.image_to_string(cropped)

    # Extract number from text
    match = re.search(r'\d{2,6}(\.\d{1,2})?', text.replace(',', ''))
    if match:
        return float(match.group()), text
    return None, text


def parse_invoice(text, path):
    date_keywords = ['invoice date','inv date','inv_date','invoice_date']
    invoice_keywords = ['invoice number', 'inv number', 'invoice no', 'invoice num','inv no', 'inv num', 'invoice#', 'inv#', 'bill number', 'bill no','invoice', 'inv', 'bill', '#']
    total_keywords = ['total', 'amount due', 'amount paid', 'balance due','payment made', 'grand total', 'net amount', 'payable']
    payment_keywords = ['payment', 'cash', 'card', 'upi', 'online','bank','wire transfer']
    client_keywords = ['bill to', 'customer', 'client', 'dear']
    currency_keywords = ['rs','rupees','rupee','inr', 'usd', '$', 'eur', '₹','pound','pounds','£']


    return {
        "filename": os.path.basename(path),
        "type": "invoice",
        "date": find_line_with_keywords(text, date_keywords) or "Not found",
        "invoice_number": extract_invoice_number(text,invoice_keywords) or "Not found",
        "total_amount": extract_amount(text, total_keywords) or "Not found",
        "payment_mode": find_line_with_keywords(text, payment_keywords) or "Not found",
        "client_name": find_block_after_keywords(text, client_keywords,num_lines=3) or "Not found",
        "currency": extract_currency_symbol(text, currency_keywords) or "Not found",
        "raw_text": text
    }


def parse_upi(text, path):
    upi_keywords = ['upi id', 'txn id', 'transaction id','UPI transaction ID']
    total_keywords = ['total', 'amount']
    upi_client_keywords=['paid to', 'received by','to','from']

    return {
        "filename": os.path.basename(path),
        "type": "upi_screenshot",
        "upi_transaction": extract_code(find_block_after_keywords(text, upi_keywords,num_lines=2)) or "Not found",
        "Upi_client": find_block_after_keywords(text, upi_client_keywords,num_lines=2) or "Not found",
        "total_amount": extract_upi_amount_from_center(path),
        "raw_text": text,
    }


def detect_type(text):
    upi_signals = ['upi id', 'txn id', 'transaction id', 'paid to', 'received by','UPI transaction ID']
    for word in upi_signals:
        if word in text.lower():
            return 'upi'
    return 'invoice'


def parse_file(path):
    if path.lower().endswith(".pdf"):
        text = pdf_to_text(path)
    elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
        text = ocr_image(path)
    else:
        return {"error": "Unsupported file type"}
    #print("text:",text[:1000])
    file_type = detect_type(text)
    if file_type == 'upi':
        return parse_upi(text, path)
    else:
        return parse_invoice(text, path)


def save_to_excel(data, fname):
    fieldnames = [k for k in data if k != 'raw_text']
    with open(fname, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #writer.writeheader()
        writer.writerow({k: v for k, v in data.items() if k in fieldnames})
    print(f"Saved to {fname}")


if __name__ == '__main__':
    path = input("Enter file path: ").strip()
    if os.path.exists(path):
        res = parse_file(path)
        if 'error' in res:
            print("Error:", res['error'])
        else:
            for k, v in res.items():
                if k != 'raw_text':
                    print(f"{k.title().replace('_', ' ')}: {v}")
            output_file = "ParserRecords/upi_parsed.csv" if res["type"] == "upi_screenshot" else "ParserRecords/invoice_parsed.csv"
            save_to_excel(res, output_file)

    else:
        print("File does not exist")