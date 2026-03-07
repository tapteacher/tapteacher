import re

path = r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard.html'

try:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')
        # Check if line ends with {% (allowing for whitespace)
        if line.strip().endswith('{%'):
            # Join with next line
            if i + 1 < len(lines):
                next_line = lines[i+1].lstrip()
                joined = line + " " + next_line
                new_lines.append(joined)
                i += 2 # Skip next line
            else:
                new_lines.append(lines[i]) # End of file case
                i += 1
        else:
            new_lines.append(lines[i])
            i += 1

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print(f"Processed {len(lines)} lines. Fixed split tags.")

except Exception as e:
    print(f"Error: {e}")
