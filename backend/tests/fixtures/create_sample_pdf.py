"""Run once to generate sample.pdf used in tests: python create_sample_pdf.py"""

from __future__ import annotations

from pathlib import Path

import fitz

OUTPUT = Path(__file__).parent / "sample.pdf"

doc = fitz.open()
for _ in range(3):
    page = doc.new_page()
    page.insert_text(
        (50, 100),
        "This is a sample PDF document created for automated testing. " * 20,
    )
doc.save(str(OUTPUT))
doc.close()
print(f"Written {OUTPUT}")
