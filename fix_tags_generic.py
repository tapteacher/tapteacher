import sys
import os

def fix_file(path):
    print(f"Fixing {path}...")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].rstrip('\n')
            # Check if line ends with {% (allowing for whitespace)
            if line.rstrip().endswith('{%'):
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
            
        print(f"Fixed split tags in {path}.")

    except Exception as e:
        print(f"Error fixing {path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            fix_file(p)
    else:
        # Default to the one hurting us now
        fix_file(r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\syllabus_topic_detail.html')
