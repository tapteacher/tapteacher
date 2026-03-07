import re

path = r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
tag_pattern = re.compile(r'{%\s*(if|for|block|with|while)\s+.*?%}|{%\s*(endif|endfor|endblock|endwith|endwhile)\s*%}')

print(f"Analyzing {len(lines)} lines...")

for i, line in enumerate(lines):
    line_num = i + 1
    matches = tag_pattern.finditer(line)
    for match in matches:
        tag = match.group().strip()
        # Clean tag content
        core_tag = tag.replace('{%', '').replace('%}', '').strip().split()[0]
        
        if core_tag in ['if', 'for', 'block', 'with']:
            stack.append((core_tag, line_num))
            # print(f"Line {line_num}: Push {core_tag}")
        elif core_tag.startswith('end'):
            expected = core_tag[3:] # endif -> if
            if not stack:
                print(f"ERROR Line {line_num}: Unexpected {core_tag} (Stack empty)")
            else:
                last_tag, last_line = stack.pop()
                if last_tag != expected:
                     print(f"ERROR Line {line_num}: Expected end{last_tag} (opened line {last_line}), found {core_tag}")

if stack:
    print("\nUNCLOSED TAGS:")
    for tag, line in stack:
        print(f"Line {line}: Unclosed {{{{% {tag} ... %}}}}")
        
print("Analysis complete.")
