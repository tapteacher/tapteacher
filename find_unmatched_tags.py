import re

path = r'c:\Users\DELL\OneDrive\Desktop\tapteacher\core\templates\core\user_dashboard.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Track if/endif, for/endfor, block/endblock
stack = []
errors = []

for i, line in enumerate(lines, 1):
    # Find all template tags
    if_tags = re.findall(r'{%\s*if\s+', line)
    elif_tags = re.findall(r'{%\s*elif\s+', line)
    else_tags = re.findall(r'{%\s*else\s*%}', line)
    endif_tags = re.findall(r'{%\s*endif\s*%}', line)
    for_tags = re.findall(r'{%\s*for\s+', line)
    endfor_tags = re.findall(r'{%\s*endfor\s*%}', line)
    block_tags = re.findall(r'{%\s*block\s+', line)
    endblock_tags = re.findall(r'{%\s*endblock\s*%}', line)
    
    # Push opening tags
    for _ in if_tags:
        stack.append(('if', i))
    for _ in for_tags:
        stack.append(('for', i))
    for _ in block_tags:
        stack.append(('block', i))
    
    # Pop closing tags
    for _ in endif_tags:
        if stack and stack[-1][0] == 'if':
            stack.pop()
        else:
            errors.append(f"Line {i}: Unexpected endif (no matching if)")
    
    for _ in endfor_tags:
        if stack and stack[-1][0] == 'for':
            stack.pop()
        else:
            errors.append(f"Line {i}: Unexpected endfor (no matching for)")
    
    for _ in endblock_tags:
        if stack and stack[-1][0] == 'block':
            stack.pop()
        else:
            errors.append(f"Line {i}: Unexpected endblock (no matching block)")

# Check for unclosed tags
if stack:
    print("Unclosed tags:")
    for tag_type, line_num in stack:
        print(f"  Line {line_num}: Unclosed {tag_type}")
else:
    print("All tags properly matched!")

if errors:
    print("\nErrors found:")
    for error in errors:
        print(f"  {error}")
