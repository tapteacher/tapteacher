import os

path = r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\syllabus_topic_detail.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.rstrip().endswith('{%'):
        print(f"Line {i+1}: {line.strip()}")
        if i + 1 < len(lines):
            print(f"Line {i+2}: {lines[i+1].strip()}")
