import re
import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import csv
import mimetypes
import numpy as np
import cv2
import logging
import pytesseract
from ultralytics import YOLO
yolo_model = YOLO("YOLO-upi/best.pt")
DEBUG_MODE=False

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parser.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
        ]
)

def ocr_image(path,save_fallback=False):
    try:
        img = Image.open(path)
        text= pytesseract.image_to_string(img)
        
        if not text.strip():
            logging.warning(f"OCR returned blank for: {path}")
            
            #if no text found preprocess img and try again
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(cv_img, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            if save_fallback:
                fallback_path = path.replace('.', '_fallback.')
                cv2.imwrite(fallback_path, thresh)

            logging.info(f"Saved fallback image: {fallback_path}")
            #ocr with preprocessed image
            text = pytesseract.image_to_string(thresh)

            if not text.strip():
                logging.error(f"OCR failed after retry: {path}")
        return text
    except Exception as e:
        print(f"Error processing image {path}: {e}")
        return "Error"


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
        logging.warning("No text provided to extract_amount")
        return None

    lines = text.lower().splitlines()
    amounts = []

    for line in lines:
        if any(key in line for key in total_keywords):
            logging.debug(f"Amount line matched: {line}")
            # Find currency amounts in the line
            found = re.findall(r'(?:rs\.?|inr|₹|\$|eur|usd)?\s?([0-9]{1,3}(?:[,0-9]{0,})?(?:\.\d{1,2})?)', line)
            for amt in found:
                try:
                    clean_amt = float(amt.replace(',', ''))
                    amounts.append(clean_amt)
                except ValueError:
                    logging.warning(f"Failed to convert amount: {amt}")
                    continue

    if amounts:
        return max(amounts)

    # scan entire text for standalone currency amounts if no amounts found in lines
    fallback = re.findall(r'(?:rs\.?|inr|₹|\$|eur|usd)?\s?([0-9]{1,3}(?:[,0-9]{0,})?(?:\.\d{1,2})?)', text)
    fallback_amounts = []
    for amt in fallback:
        try:
            fallback_amounts.append(float(amt.replace(',', '')))
        except ValueError:
            continue

    if fallback_amounts:
        logging.info("Used fallback extraction in extract_amount")
        return max(fallback_amounts)

    logging.warning("No valid amount found")
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

    keywords_pattern = '|'.join(map(re.escape, invoice_keywords))
    pattern = rf'(?i)\b(?:{keywords_pattern})\s*[:#\-]?\s*\n?\s*([A-Z0-9][A-Z0-9\-\/]{{2,}})'

    try:
        matches = re.findall(pattern, text)
        cleaned_matches = []

        for m in matches:
            m = m.strip().replace(' ', '')
            if len(m) >= 3 and re.match(r'^[A-Z0-9\-\/]+$', m):
                cleaned_matches.append(m)

        if cleaned_matches:
            return cleaned_matches[0]

        # Fallback: search lines with any invoice keyword and grab a likely code
        for line in text.splitlines():
            if any(k in line.lower() for k in invoice_keywords):
                match = re.search(r'\b([A-Z0-9\-\/]{3,})\b', line)
                if match:
                    return match.group(1)

    except Exception as e:
        logging.warning(f"Error extracting invoice number: {e}")

    return None


def extract_upi_amount_yolo(image_path):
    
    results = yolo_model(image_path)

    possible_amounts = []

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cropped = Image.open(image_path).crop((x1, y1, x2, y2))
            text = pytesseract.image_to_string(cropped, config="--psm 7")

            # Clean and correct OCR
            text = text.replace(",", ".")
            text = re.sub(r'[^0-9.\s\-]', '', text)

            # Remove '2' if it’s likely an OCR error for ₹
            if re.match(r'^2[\s\-\.]?\d{2,4}$', text.strip()):
                text = re.sub(r'^2[\s\-\.]?', '', text)

            match = re.search(r'\d{1,6}(?:\.\d{2})?', text)
            if match:
                try:
                    amt = float(match.group())
                    possible_amounts.append(amt)
                except:
                    continue

    if possible_amounts:
        return max(possible_amounts)
    return None



INVOICE_KEYWORDS={
    "date": ["invoice date", "inv date", "inv_date", "invoice_date"],
    "invoice_number": ["invoice number", "inv number", "invoice no", "invoice   num", "inv no", "inv num", "invoice#", "inv#", "bill number", "bill no", "invoice", "inv", "bill", "#"],
    "total_amount": ["total", "amount due", "amount paid", "balance due", "payment made", "grand total", "net amount", "payable"],
    "payment_mode": ["payment", "cash", "card", "upi", "online", "bank", "wire transfer"],
    "client_name": ["bill to", "customer", "client", "dear", "to"],
    "currency": ["rs", "rupees", "rupee", "inr", "usd", "$", "eur", "₹", "pound", "pounds", "£"]
}
UPI_KEYWORDS={
    "upi_transaction": ["upi id", "txn id", "transaction id", "UPI transaction ID", "utr","upi txn id"],
    "upi_client": ["paid to", "received by", "to", "from"]
}

def parse_invoice(text, path):
    return {
        "filename": os.path.basename(path),
        "type": "invoice",
        "date": find_line_with_keywords(text, INVOICE_KEYWORDS["date"]) or "Not found",
        "invoice_number": extract_invoice_number(text, INVOICE_KEYWORDS["invoice_number"]) or "Not found",
        "total_amount": extract_amount(text, INVOICE_KEYWORDS["total_amount"]) or "Not found",
        "payment_mode": find_line_with_keywords(text, INVOICE_KEYWORDS["payment_mode"]) or "Not found",
        "client_name": find_block_after_keywords(text, INVOICE_KEYWORDS["client_name"], num_lines=3) or "Not found",
        "currency": extract_currency_symbol(text, INVOICE_KEYWORDS["currency"]) or "Not found",
        "raw_text": text
    }

def parse_upi(text, path):
     return {
        "filename": os.path.basename(path),
        "type": "upi_screenshot",
        "upi_transaction": extract_code(find_block_after_keywords(text, UPI_KEYWORDS["upi_transaction"], num_lines=2)) or "Not found",
        "Upi_client": find_block_after_keywords(text, UPI_KEYWORDS["upi_client"], num_lines=2) or "Not found",
        "total_amount": extract_upi_amount_yolo(path),
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


def is_safe_path(path):
    abs_path = os.path.abspath(path)
    return os.path.isfile(abs_path) and not any(x in path for x in ['..', '~', '//', '\\\\'])

def is_safe_filetype(path):
    SAFE_EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg', '.bmp')
    mime, _ = mimetypes.guess_type(path)
    return path.lower().endswith(SAFE_EXTENSIONS) and mime is not None

def is_file_size_safe(path):
    MAX_FILE_SIZE_MB = 5
    try:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        return size_mb <= MAX_FILE_SIZE_MB
    except Exception as e:
        logging.error(f"File size check failed: {e}")
        return False



if __name__ == '__main__':
    path = input("Enter file path: ").strip()
    if not is_safe_path(path) or not is_safe_filetype(path):
        print("Invalid or unsafe file path")
    elif not os.path.exists(path):
        print("File does not exist")
    elif not is_file_size_safe(path):
        print("File too large. Limit is 5MB.")
    else:
        logging.info("starting to parse")
        res = parse_file(path)
        if 'error' in res:
            print("Error:", res['error'])
        else:
            
            for k, v in res.items():
                if k != 'raw_text':
                    print(f"{k.title().replace('_', ' ')}: {v}")
            output_file = "ParserRecords/upi_parsed.csv" if res["type"] == "upi_screenshot" else "ParserRecords/invoice_parsed.csv"
            save_to_excel(res, output_file)