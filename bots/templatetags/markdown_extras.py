from django import template
from django.utils.safestring import mark_safe
import html
import re

register = template.Library()

@register.filter
def markdown(text):
    """Convert markdown text to HTML"""
    if not text:
        return ""
    
    # Escape HTML first
    text = html.escape(text)
    
    # Convert markdown to HTML
    # Bold text **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
    
    # Italic text *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
    
    # Code blocks ```code```
    text = re.sub(r'```([\s\S]*?)```', r'<pre><code>\1</code></pre>', text)
    
    # Inline code `code`
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # Headers
    text = re.sub(r'^### (.*$)', r'<h6>\1</h6>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*$)', r'<h5>\1</h5>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*$)', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    
    # Process lists first, before paragraph processing
    # Handle empty lines between list items to keep them in the same list
    lines = text.split('\n')
    processed_lines = []
    in_bullet_list = False
    in_numbered_list = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for bullet points
        bullet_match = re.match(r'^[\s]*[-*+]\s+(.*)', line)
        # Check for numbered lists
        number_match = re.match(r'^[\s]*\d+\.\s+(.*)', line)

        if bullet_match:
            if not in_bullet_list:
                if in_numbered_list:
                    processed_lines.append('</ol>')
                    in_numbered_list = False
                processed_lines.append('<ul>')
                in_bullet_list = True
            processed_lines.append(f'<li>{bullet_match.group(1)}</li>')
        elif number_match:
            if not in_numbered_list:
                if in_bullet_list:
                    processed_lines.append('</ul>')
                    in_bullet_list = False
                processed_lines.append('<ol>')
                in_numbered_list = True
            processed_lines.append(f'<li>{number_match.group(1)}</li>')
        else:
            # Check if this is an empty line followed by another list item
            if line.strip() == '' and i + 1 < len(lines):
                next_line = lines[i + 1]
                next_bullet = re.match(r'^[\s]*[-*+]\s+(.*)', next_line)
                next_number = re.match(r'^[\s]*\d+\.\s+(.*)', next_line)

                # If next line is a list item of the same type, skip this empty line
                if (in_bullet_list and next_bullet) or (in_numbered_list and next_number):
                    i += 1
                    continue

            # Close any open lists when we hit a non-list line
            if in_bullet_list:
                processed_lines.append('</ul>')
                in_bullet_list = False
            if in_numbered_list:
                processed_lines.append('</ol>')
                in_numbered_list = False
            processed_lines.append(line)

        i += 1

    # Close any remaining open lists
    if in_bullet_list:
        processed_lines.append('</ul>')
    if in_numbered_list:
        processed_lines.append('</ol>')

    text = '\n'.join(processed_lines)
    
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    
    # Handle paragraphs more carefully to preserve list structures
    # Split by double line breaks but preserve list blocks
    sections = re.split(r'\n\s*\n', text)
    formatted_sections = []

    for section in sections:
        section = section.strip()
        if section:
            # Check if this section contains list elements
            if '<ol>' in section or '<ul>' in section or section.startswith('<li>'):
                # This is a list section, don't wrap in paragraphs
                formatted_sections.append(section)
            elif re.match(r'^<(h[1-6]|pre|blockquote)', section):
                # This is already a block element
                formatted_sections.append(section)
            else:
                # This is regular text, wrap in paragraph
                section = section.replace('\n', '<br>')
                formatted_sections.append(f'<p>{section}</p>')

    text = '\n\n'.join(formatted_sections)
    
    # Clean up empty paragraphs
    text = re.sub(r'<p>\s*</p>', '', text)
    
    return mark_safe(text)
