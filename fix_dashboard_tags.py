import re

path = r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the specific split tag on line 181-182
content = content.replace(
    '{% if verification.exp_file %}Current: {{ verification.exp_file.name }}{%\r\n                                            endif %}',
    '{% if verification.exp_file %}Current: {{ verification.exp_file.name }}{% endif %}'
)

# Also try without \r
content = content.replace(
    '{% if verification.exp_file %}Current: {{ verification.exp_file.name }}{%\n                                            endif %}',
    '{% if verification.exp_file %}Current: {{ verification.exp_file.name }}{% endif %}'
)

# Generic fix for any split {%\n pattern
content = re.sub(r'\{%\s*\n\s*endif\s*%\}', '{% endif %}', content)
content = re.sub(r'\{%\s*\r\n\s*endif\s*%\}', '{% endif %}', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed split tags in user_dashboard.html")
