import re

# Read the file
with open(r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the tab button - replace multiline template tag with single line
content = re.sub(
    r'<button class="tab-btn active" onclick="switchTab\(\'verification\'\)">{% if verification\.full_name %}{{[\s\n\r]*verification\.full_name\|first_name[\s\n\r]*}}\'s Dashboard{% else %}User Profile{% endif %}</button>',
    r'<button class="tab-btn active" onclick="switchTab(\'verification\')">{% if verification.full_name %}{{ verification.full_name|first_name }}\'s Dashboard{% else %}User Profile{% endif %}</button>',
    content,
    flags=re.DOTALL
)

# Fix the profile title - replace multiline template tag with single line
content = re.sub(
    r'{% if verification\.full_name %}{{ verification\.full_name\|first_name }}\'s Profile{%[\s\n\r]*else[\s\n\r]*%}User Profile{% endif %}</div>',
    r'{% if verification.full_name %}{{ verification.full_name|first_name }}\'s Profile{% else %}User Profile{% endif %}</div>',
    content,
    flags=re.DOTALL
)

# Write the file back
with open(r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("File fixed successfully!")
