import os
import re

file_path = r"c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard_v3.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# This pattern looks for the span and joins the district and state variables
# even if they are split by newlines and spaces.
# We will put them on their own lines to avoid long line splitting by formatters.

replacement = """<span class="vacancy-location">
                                    {{ app.vacancy_post.vacancy.institute.district }},
                                    {{ app.vacancy_post.vacancy.institute.state }}
                                </span>"""

# Target the specific split blocks
# Pattern: <span class="vacancy-location"> followed by anything until </span>
pattern = r'<span class="vacancy-location">\{\{\s*app\.vacancy_post\.vacancy\.institute\.district\s*\}\},\s*\{\{\s*\n\s*app\.vacancy_post\.vacancy\.institute\.state\s*\}\}</span>'

# Actually, let's be even broader to catch any variation of that split
pattern_broad = r'<span class="vacancy-location">.*?app\.vacancy_post\.vacancy\.institute\.district.*?app\.vacancy_post\.vacancy\.institute\.state.*?</span>'

new_content = re.sub(pattern_broad, replacement, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("File updated successfully.")
