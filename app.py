import re
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

def preprocess_image(image_pil):
    img_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    return denoised

def clean_line(line):
    line = line.strip()
    if len(line) < 2:
        return None
    
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \'-.,!?')
    clean = ''.join(c if c in allowed else ' ' for c in line)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    if len(clean) < 2:
        return None
    
    symbol_pattern = r'^[\(\)\[\]\{\}\_\-\=\+\*\#\@\^\.\,\:\;\<\>\/\\\|\~]+$'
    if re.match(symbol_pattern, clean):
        return None
    
    return clean

def clean_text(text):
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        result = clean_line(line)
        if result:
            cleaned.append(result)
    return '\n'.join(cleaned)

def read_pdf(pdf_path):
    print(f"Leyendo {pdf_path}...")
    pages = convert_from_path(pdf_path, dpi=300)
    all_text = ""

    for i, page in enumerate(pages):
        print(f"Procesando pagina {i + 1}...")
        
        img_processed = preprocess_image(page)
        text = pytesseract.image_to_string(img_processed, lang='eng')
        text = clean_text(text)
        
        all_text += "=== PAGINA " + str(i + 1) + " ===\n\n"
        all_text += text + "\n\n"
        all_text += "=== FIN PAGINA " + str(i + 1) + " ===\n\n"

    return all_text

pdf_path = "documento.pdf"
final_text = read_pdf(pdf_path)

with open("texto_limpio.txt", "w", encoding="utf-8") as f:
    f.write(final_text)

print("Listo! Revisa texto_limpio.txt")