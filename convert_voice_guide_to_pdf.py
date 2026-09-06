#!/usr/bin/env python3
"""Convert VOICE_PIPELINE_GUIDE.md to PDF"""

from fpdf import FPDF
import os
import re

# Replace Unicode characters that fpdf's built-in fonts can't handle
def sanitize(text):
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '-',    # bullet
        '\u2192': '->',   # right arrow
        '\u2190': '<-',   # left arrow
        '\u26a0': '!',    # warning sign
        '\u2705': '[OK]', # check mark
        '\u274c': '[X]',  # cross mark
        '\u2714': '[x]',  # heavy check mark
        '\u2718': '[ ]',  # heavy ballot x
        '\u2611': '[x]',  # ballot box with check
        '\u2610': '[ ]',  # ballot box
        '\u23f0': '',     # alarm clock emoji
        '\U0001f399': '', # microphone emoji
        '\U0001f3a4': '[mic]', # microphone emoji variant
        '\U0001f4e1': '[sat]', # satellite emoji
        '\U0001f4e2': '[horn]', # horn emoji
        '\U0001f4f1': '[phone]', # phone emoji
        '\U0001f4f7': '', # camera emoji
        '\U0001f50a': '[vol]', # volume emoji
        '\U0001f6c0': '', # bath emoji
        '\U0001f680': '', # rocket emoji
        '\U0001f4a4': '', # zzz emoji
        '\U0001f4bb': '', # laptop emoji
        '\U0001f527': '', # wrench emoji
        '\U0001f4cb': '', # clipboard emoji
        '\U0001f310': '', # globe emoji
        '\u2601': '',     # cloud emoji
        '\U0001f4ca': '', # bar chart emoji
        '\U0001f4c8': '', # chart increasing emoji
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Fallback: replace any remaining non-latin1 chars
    result = []
    for ch in text:
        try:
            ch.encode('latin-1')
            result.append(ch)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)


class VoiceGuidePDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, sanitize('Voice Pipeline Guide | EcoSphere Winners4'), new_x="LMARGIN", new_y="NEXT", align='C')
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    def h1(self, text):
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(233, 69, 96)
        self.cell(0, 14, sanitize(text), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(233, 69, 96)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def h2(self, text):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(15, 52, 96)
        self.cell(0, 10, sanitize(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def h3(self, text):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(83, 52, 131)
        self.cell(0, 8, sanitize(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, sanitize(text))
        self.ln(2)

    def bullet(self, text, indent=0):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        x = 10 + indent
        self.set_x(x)
        self.cell(5, 6, '-', new_x="RIGHT", new_y="TOP")
        self.multi_cell(190 - indent - 5, 6, sanitize(text))
        self.ln(1)

    def checkbox_item(self, checked, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        symbol = '[x]' if checked else '[ ]'
        self.set_x(15)
        self.cell(10, 6, symbol, new_x="RIGHT", new_y="TOP")
        self.multi_cell(175, 6, sanitize(text))
        self.ln(1)

    def code_block(self, code):
        self.set_font('Courier', '', 8)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(40, 40, 40)
        lines = code.strip().split('\n')
        line_height = 4.5
        block_height = len(lines) * line_height + 6

        if self.get_y() + block_height > 270:
            self.add_page()

        y_start = self.get_y()
        self.rect(10, y_start, 190, block_height, 'F')
        self.ln(3)
        for line in lines:
            sanitized = sanitize(line)
            if len(sanitized) > 95:
                sanitized = sanitized[:92] + '...'
            self.cell(5, line_height, '', new_x="RIGHT", new_y="TOP")
            self.cell(0, line_height, sanitized, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def blockquote(self, text):
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.set_x(15)
        self.multi_cell(180, 6, sanitize(text))
        self.ln(2)


def clean_md(text):
    """Remove markdown formatting for plain text"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()


def convert_md_to_pdf(md_path, pdf_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pdf = VoiceGuidePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    lines = content.split('\n')
    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]

        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                code_content = '\n'.join(code_lines)
                if code_content.strip():
                    pdf.code_block(code_content)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Horizontal rule
        if line.strip() == '---':
            pdf.ln(3)
            i += 1
            continue

        # Headings
        if line.startswith('# '):
            # Skip the top-level title (already in header)
            i += 1
            continue
        elif line.startswith('## '):
            title = line[3:].strip()
            pdf.h2(title)
            i += 1
            continue
        elif line.startswith('### '):
            title = line[4:].strip()
            pdf.h3(title)
            i += 1
            continue

        # Blockquote
        if line.startswith('>'):
            text = line[1:].strip()
            text = clean_md(text)
            pdf.blockquote(text)
            i += 1
            continue

        # Checkbox items
        m = re.match(r'\s*- \[([ xX])\]', line)
        if m:
            checked = m.group(1).lower() == 'x'
            text = re.sub(r'\s*- \[[ xX]\]\s*', '', line)
            text = clean_md(text)
            pdf.checkbox_item(checked, text)
            i += 1
            continue

        # Bullet points
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            text = clean_md(text)
            indent = len(line) - len(line.lstrip())
            pdf.bullet(text, indent)
            i += 1
            continue

        # Numbered list
        num_match = re.match(r'(\d+)\.\s', line.strip())
        if num_match:
            text = re.sub(r'\s*\d+\.\s*', '', line.strip())
            text = clean_md(text)
            num = num_match.group(1)
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(40, 40, 40)
            pdf.set_x(15)
            pdf.cell(8, 6, f'{num}.', new_x="RIGHT", new_y="TOP")
            pdf.multi_cell(172, 6, sanitize(text))
            pdf.ln(1)
            i += 1
            continue

        # Regular text
        text = clean_md(line)
        if text:
            pdf.body_text(text)
        i += 1

    pdf.output(pdf_path)
    print(f"PDF saved to: {pdf_path}")


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(base_dir, 'VOICE_PIPELINE_GUIDE.md')
    pdf_path = os.path.join(base_dir, 'VOICE_PIPELINE_GUIDE.pdf')
    convert_md_to_pdf(md_path, pdf_path)
