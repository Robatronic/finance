import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer
import cv2



model = Model("vosk-model-small-en-us-0.15")
rec = KaldiRecognizer(model, 16000)
audio_q = queue.Queue()

def audio_callback(indata, frames, time, status):
    audio_q.put(bytes(indata))

def listen_for_command():
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        while True:
            data = audio_q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                if text:
                    return text

def capture_receipt_image():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    cam.release()
    return frame

import easyocr

reader = easyocr.Reader(['en'])

def extract_text(image):
    results = reader.readtext(image, detail=0)
    return "\n".join(results)

import re

def parse_receipt(text):
    lines = text.split("\n")

    # Vendor = first non-empty line
    vendor = next((l for l in lines if l.strip()), "")

    # Date
    date_regex = r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b"
    date_match = re.search(date_regex, text)
    date = date_match.group(1) if date_match else ""

    # Total
    total_regex = r"total[:\s]*\$?(\d+\.\d{2})"
    total_match = re.search(total_regex, text.lower())
    total = total_match.group(1) if total_match else ""

    # Line items (very naive example)
    item_regex = r"(.+?)\s+(\d+\.\d{2})"
    items = re.findall(item_regex, text)

    return {
        "vendor": vendor,
        "date": date,
        "total": total,
        "items": items
    }

from PIL import Image, ImageDraw, ImageFont
import numpy as np

def annotate_preview(image, parsed):
    img = Image.fromarray(image)
    draw = ImageDraw.Draw(img)

    text = f"Vendor: {parsed['vendor']}\nDate: {parsed['date']}\nTotal: {parsed['total']}"
    draw.text((10, 10), text, fill="yellow")

    return img

import csv

def append_to_csv(parsed):
    with open("receipts.csv", "a", newline="") as f:
        writer = csv.writer(f)
        for item, price in parsed["items"]:
            writer.writerow([parsed["date"], parsed["vendor"], price, item])


def main():
    while True:
        print("Say 'scan receipt' to begin.")
        cmd = listen_for_command()

        if "scan" in cmd:
            image = capture_receipt_image()
            text = extract_text(image)
            parsed = parse_receipt(text)
            preview = annotate_preview(image, parsed)

            preview.show()

            print("Say 'save' to store or 'next' to discard.")
            cmd2 = listen_for_command()

            if "save" in cmd2:
                append_to_csv(parsed)
                print("Saved.")

