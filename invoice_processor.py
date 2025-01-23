import os
import cv2
import numpy as np
import json
import pandas as pd
import easyocr
import fitz  # PyMuPDF
import docx2txt
import requests
import base64
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Global constants
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50)) * 1024 * 1024

# Initialize EasyOCR reader (cached)
_reader = None


def get_easyocr_reader():
    """Get or initialize EasyOCR reader."""
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'])
    return _reader


def enhance_image(image_array):
    """
    Apply various image enhancement techniques to improve OCR accuracy.

    Args:
        image_array: numpy array of the image

    Returns:
        Enhanced image array
    """
    try:
        # Convert to grayscale if image is colored
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh)

        # Increase contrast
        contrast = cv2.convertScaleAbs(denoised, alpha=1.5, beta=0)

        return contrast

    except Exception as e:
        print(f"Warning in image enhancement: {str(e)}")
        return image_array


def process_with_easyocr(image_array):
    """
    Extract text from image using EasyOCR.

    Args:
        image_array: numpy array of the image

    Returns:
        Extracted text string
    """
    try:
        # Get EasyOCR reader
        reader = get_easyocr_reader()

        # Enhance image
        enhanced_image = enhance_image(image_array)

        # Perform OCR
        results = reader.readtext(enhanced_image)

        # Extract and combine text
        text = ' '.join([result[1] for result in results])

        return text.strip()
    except Exception as e:
        print(f"Error in EasyOCR processing: {str(e)}")
        return ""


def process_with_online_ocr(image_array):
    """
    Process image with OCR.space API as a backup method.

    Args:
        image_array: numpy array of the image

    Returns:
        Extracted text string
    """
    try:
        # Convert image array to bytes
        is_success, buffer = cv2.imencode(".jpg", image_array)
        if not is_success:
            return ""

        # Convert to base64
        img_bytes = base64.b64encode(buffer)

        # OCR.space API endpoint and parameters
        url = "https://api.ocr.space/parse/image"
        payload = {
            'apikey': os.getenv('OCR_SPACE_API_KEY', 'helloworld'),
            'language': 'eng',
            'base64Image': f'data:image/jpg;base64,{img_bytes.decode()}'
        }

        # Make API request
        response = requests.post(url, data=payload)
        result = response.json()

        if result.get('ParsedResults'):
            return result['ParsedResults'][0]['ParsedText']
        return ""

    except Exception as e:
        print(f"Warning in online OCR: {str(e)}")
        return ""


def extract_text_from_pdf(file_path):
    """
    Extract text from PDF using PyMuPDF.

    Args:
        file_path: path to the PDF file

    Returns:
        Extracted text string
    """
    try:
        # Open PDF
        pdf_document = fitz.open(file_path)
        text = ""

        # Extract text from each page
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()

        pdf_document.close()
        return text.strip()

    except Exception as e:
        print(f"Warning in PDF text extraction: {str(e)}")
        return ""


def process_with_groq(text):
    """
    Process extracted text with Groq API for information extraction.

    Args:
        text: extracted text from document

    Returns:
        Dictionary containing extracted information
    """
    try:
        prompt = """
        Analyze the following invoice text and extract all relevant details.
        Return the data in JSON format with these fields:
        - Invoice Number
        - Date
        - Due Date
        - Total Amount
        - Vendor Name
        - Line Items (array with):
            * Description
            * Quantity
            * Unit Price
            * Total Price
        - Subtotal
        - Tax Amount
        - Payment Terms
        - Billing Address
        - Currency
        - Additional Notes

        Invoice text:
        {text}

        Return only the JSON object with these fields. Format numerical values appropriately.
        """

        # Make API request
        completion = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system",
                 "content": "You are an expert invoice analyzer. Extract information in clean JSON format."},
                {"role": "user", "content": prompt.format(text=text)}
            ],
            temperature=0.1,
            max_tokens=2000
        )

        # Extract JSON from response
        response_text = completion.choices[0].message.content
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {"error": "No valid JSON found in response"}

    except Exception as e:
        return {"error": f"Groq API Error: {str(e)}"}


def process_file(file_path):
    """
    Main function to process uploaded files and extract invoice data.

    Args:
        file_path: path to the uploaded file

    Returns:
        Dictionary containing extracted invoice data
    """
    try:
        # Check file size
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            return {"error": f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit"}

        text = ""
        file_extension = os.path.splitext(file_path)[1].lower()

        # Process based on file type
        if file_extension in ['.png', '.jpg', '.jpeg']:
            # Read image
            image = cv2.imread(file_path)
            if image is None:
                return {"error": "Failed to read image file"}

            # Try EasyOCR first
            text = process_with_easyocr(image)

            # If EasyOCR fails, try online OCR
            if not text.strip():
                text = process_with_online_ocr(image)

        elif file_extension == '.pdf':
            # Try PyMuPDF first
            text = extract_text_from_pdf(file_path)

            # If text extraction fails, try OCR methods
            if not text.strip():
                try:
                    # Convert first page to image
                    pdf = fitz.open(file_path)
                    page = pdf[0]
                    pix = page.get_pixmap()

                    # Convert to OpenCV format
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                    # Try OCR methods
                    text = process_with_easyocr(image)
                    if not text.strip():
                        text = process_with_online_ocr(image)

                except Exception as e:
                    print(f"Warning in PDF processing: {str(e)}")

        elif file_extension == '.docx':
            # Process DOCX
            text = docx2txt.process(file_path)

        else:
            return {"error": "Unsupported file type"}

        # Check if text was extracted
        if not text.strip():
            return {"error": "No text could be extracted from the file"}

        # Process with Groq
        result = process_with_groq(text)

        # Add source file name to result
        result['source_file'] = os.path.basename(file_path)

        return result

    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}
    finally:
        # Clean up: remove temporary files if needed
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Failed to remove temporary file: {str(e)}")


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        result = process_file(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Please provide a file path as argument")