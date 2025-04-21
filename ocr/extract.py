#!/usr/bin/env python3
import io
from typing import List
from PIL import Image

import torch
import pypdfium2

import logging

from surya.models import load_predictors
from surya.recognition.languages import replace_lang_with_code
from surya.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

predictors = None
def load_model_once():
    global predictors
    predictors = load_predictors()


def open_pdf(stream: io.BytesIO) -> pypdfium2.PdfDocument:
    return pypdfium2.PdfDocument(stream)


def get_page_image(stream: io.BytesIO, page: int, dpi: int) -> Image.Image:
    doc = open_pdf(stream)
    bmp = doc.render(
        pypdfium2.PdfBitmap.to_pil,
        page_indices=[page - 1],
        scale=dpi / 72,
    )
    img = list(bmp)[0].convert("RGB")
    doc.close()
    return img


def extract_text_from_image(file_path: str, batch_size: int = 4, use_gpu: bool = True) -> str:
    """
    Extracts and returns OCR text from a PDF or image file using Surya pipeline.
    """
    device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
    print(f"→ Using device: {device}")
    global predictors

    # Load input as PIL images
    ext = file_path.lower().rsplit(".", 1)[-1]
    pil_imgs: List[Image.Image] = []
    pil_highres: List[Image.Image] = []

    if ext == "pdf":
        data = open(file_path, "rb").read()
        buf = io.BytesIO(data)
        doc = open_pdf(buf)
        n_pages = len(doc)
        doc.close()
        for p in range(1, n_pages + 1):
            pil_imgs.append(get_page_image(buf, p, settings.IMAGE_DPI))
            pil_highres.append(get_page_image(buf, p, settings.IMAGE_DPI_HIGHRES))
    else:
        img = Image.open(file_path).convert("RGB")
        pil_imgs = [img]
        pil_highres = [img]

    # Helper to batch inputs
    def batched(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    # OCR text result
    final_text = ""

    # Process in batches
    for batch_imgs, batch_high in zip(batched(pil_imgs, batch_size), batched(pil_highres, batch_size)):
        langs = ["en"]
        replace_lang_with_code(langs)
        ocr_preds = predictors["recognition"](
            batch_imgs, [langs]*len(batch_imgs),
            predictors["detection"],
            highres_images=batch_high
        )

        for o in ocr_preds:
            for line in o.text_lines:
                final_text += line.text.strip() + "\n"

    result = {
        "extracted_text": final_text.strip(),
    }
    return result