import os
import re

def fix_edit_vacancy():
    path = r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\edit_vacancy.html'
    if not os.path.exists(path):
        print("File not found!")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Explicit replacements for known errors
    replacements = {
        "vacancy.institute.state==state": "vacancy.institute.state == state",
        "vacancy.institute.category=='govt'": "vacancy.institute.category == 'govt'",
        "vacancy.institute.category=='semi'": "vacancy.institute.category == 'semi'",
        "vacancy.institute.category=='private'": "vacancy.institute.category == 'private'",
        "vacancy.institute.category=='coaching'": "vacancy.institute.category == 'coaching'",
    }
    
    new_content = content
    for old, new in replacements.items():
        if old in new_content:
            print(f"Replacing '{old}' with '{new}'")
            new_content = new_content.replace(old, new)
    
    # Generic regex fixes for any other == issues (non-greedy)
    # Find {% if ... ==... %} where spaces are missing
    
    def add_spaces(match):
        inner = match.group(2)
        # Add spaces around == if missing
        inner = re.sub(r'([^\s])==', r'\1 ==', inner)
        inner = re.sub(r'==([^\s])', r'== \1', inner)
        return match.group(1) + inner + match.group(3)

    new_content = re.sub(r'(\{\%|\{\{)(.*?)(\%\}|\}\})', add_spaces, new_content, flags=re.DOTALL)


    if new_content != content:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(new_content)
        print("SUCCESS: Cleaned and fixed edit_vacancy.html")
    else:
        print("No changes needed")

if __name__ == "__main__":
    fix_edit_vacancy()
