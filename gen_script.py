import re

with open('core/templates/core/admin_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Wrap Manager Connect Link
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*Manage connect link)',
    r'{% if "manage_connect_link" in assigned_roles or is_superadmin %}\n        \1',
    html
)
html = html.replace('</form>\n            </div>\n        </div>\n\n        <div class="accordion-item">\n            <div class="accordion-header"',
                    '</form>\n            </div>\n        </div>\n        {% endif %}\n\n        <div class="accordion-item">\n            <div class="accordion-header"', 1)

# 2. Upload Syllabus
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*Upload Syllabus)',
    r'{% if "upload_syllabus" in assigned_roles or is_superadmin %}\n        \1',
    html
)
html = html.replace('            </div>\n        </div>\n\n    </div>\n    <div class="col-right">',
                    '            </div>\n        </div>\n        {% endif %}\n\n    </div>\n    <div class="col-right">', 1)

# 3. Upload Vacancy
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*Upload Vacancy)',
    r'{% if "upload_vacancy" in assigned_roles or is_superadmin %}\n        \1',
    html
)
html = html.replace('</form>\n            </div>\n        </div>\n\n        <div class="accordion-item">\n            <div class="accordion-header"',
                    '</form>\n            </div>\n        </div>\n        {% endif %}\n\n        <div class="accordion-item">\n            <div class="accordion-header"', 2) # Might match multiple

# 4. Submitted Vacancies
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*Submitted Vacancies)',
    r'{% if "submitted_vacancies" in assigned_roles or is_superadmin %}\n        \1',
    html
)
# Hide applicants
html = re.sub(r'(<span style="margin-left: 10px; color: #2e7d32;">[^<]*Applicants: \{\{ vac.total_applicants \}\}</span>)',
              r'{% if not is_hr %}\1{% endif %}', html)
html = re.sub(r'(<a href="\{% url \'vacancy_applicants\' vac.id %\}"[^>]*>\s*<span>[^<]*</span> Check Applicants\s*</a>)',
              r'{% if not is_hr %}\1{% endif %}', html)


# 5. User Details
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*<span[^>]*>\s*👥 User Details)',
    r'{% if "user_details" in assigned_roles or is_superadmin %}\n        \1',
    html
)

# 6. Manage Email Templates
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*<span[^>]*>\s*📧 Manage Email Templates)',
    r'{% if "manage_email_templates" in assigned_roles or is_superadmin %}\n        \1',
    html
)

# 7. User Chats
html = re.sub(
    r'(<div class="accordion-item">\s*<div class="accordion-header"[^>]*>\s*<span[^>]*>\s*💬 User Chats)',
    r'{% if "user_chats" in assigned_roles or is_superadmin %}\n        \1',
    html
)

role_given_html = """
        <!-- Role Given UI inserted here -->
        {% if is_superadmin %}
        <div class="accordion-item">
            <div class="accordion-header" onclick="toggleAccordion(this)">
                <span style="display: flex; align-items: center; gap: 10px;">🛡️ Role Given</span>
                <span class="accordion-icon">v</span>
            </div>
            <div class="accordion-content" style="display: none; padding: 20px; border-top: 1px solid #f0f0f0;">
                <form id="role-form" action="{% url 'admin_dashboard' %}" method="post">
                    {% csrf_token %}
                    <input type="hidden" name="save_admin_roles" value="1">
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>Email ID of HR/Admin</label>
                            <input type="email" name="hr_email" placeholder="Enter Gmail ID" required style="width: 100%; box-sizing: border-box;">
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 20px; align-items: center; margin-top: 20px;">
                        <div style="flex: 1;">
                            <label style="font-size: 14px; font-weight: 500; display: block; margin-bottom: 8px;">Available Roles</label>
                            <select id="available-roles" multiple style="width: 100%; height: 150px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px;">
                                <option value="manage_connect_link">Manage Connect Link</option>
                                <option value="upload_syllabus">Upload Syllabus</option>
                                <option value="upload_vacancy">Upload Vacancy</option>
                                <option value="submitted_vacancies">Submitted Vacancies</option>
                                <option value="user_details">User Details</option>
                                <option value="manage_email_templates">Manage Email Templates</option>
                                <option value="user_chats">User Chats</option>
                            </select>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <button type="button" onclick="moveRole('available-roles', 'assigned-roles')" style="padding: 8px; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; background: white;">&gt;&gt;</button>
                            <button type="button" onclick="moveRole('assigned-roles', 'available-roles')" style="padding: 8px; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; background: white;">&lt;&lt;</button>
                        </div>
                        <div style="flex: 1;">
                            <label style="font-size: 14px; font-weight: 500; display: block; margin-bottom: 8px;">Assigned Roles</label>
                            <select id="assigned-roles" multiple style="width: 100%; height: 150px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px;">
                            </select>
                        </div>
                    </div>
                    <input type="hidden" name="assigned_roles_json" id="assigned_roles_json">
                    <div style="margin-top: 20px; text-align: right;">
                        <button type="button" onclick="submitRoles()" class="btn-action" style="background: #111; color: white; display: inline-flex;">Save Roles</button>
                    </div>
                </form>
            </div>
        </div>
        <script>
            function moveRole(fromId, toId) {
                const fromSelect = document.getElementById(fromId);
                const toSelect = document.getElementById(toId);
                const selectedOptions = Array.from(fromSelect.selectedOptions);
                selectedOptions.forEach(option => {
                    toSelect.appendChild(option);
                });
            }
            function submitRoles() {
                const assignedSelect = document.getElementById('assigned-roles');
                const roles = Array.from(assignedSelect.options).map(opt => opt.value);
                document.getElementById('assigned_roles_json').value = JSON.stringify(roles);
                document.getElementById('role-form').submit();
            }
            document.getElementById('available-roles').addEventListener('dblclick', function() { moveRole('available-roles', 'assigned-roles'); });
            document.getElementById('assigned-roles').addEventListener('dblclick', function() { moveRole('assigned-roles', 'available-roles'); });
        </script>
        {% endif %}
"""

# Let's cleanly inject {% endif %} at the end of each block. This is easier if we just match `</div>\n        <div class="accordion-item">`.
# Wait, user_chats is the last one.
# So I'll just write a script that does a beautiful state-machine parsing to inject `{% endif %}` correctly!

with open('fix_dashboard.py', 'w') as f2:
    f2.write('''
import re
with open('core/templates/core/admin_dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_accordion = False
current_role = None

# Mappings of header text to role name
role_map = {
    "Manage connect link": "manage_connect_link",
    "Upload Syllabus": "upload_syllabus",
    "Upload Vacancy": "upload_vacancy",
    "Submitted Vacancies": "submitted_vacancies",
    "User Details": "user_details",
    "Manage Email Templates": "manage_email_templates",
    "User Chats": "user_chats"
}

accordion_divs = 0

for i, line in enumerate(lines):
    if '<div class="accordion-item">' in line:
        # Check next few lines for role
        role_found = None
        for j in range(1, 5):
            if i + j < len(lines):
                for key, val in role_map.items():
                    if key in lines[i+j]:
                        role_found = val
                        break
                if role_found:
                    break
        
        if role_found:
            new_lines.append(f"        {{% if '{role_found}' in assigned_roles or is_superadmin %}}\\n")
            current_role = role_found
            accordion_divs = 0
            in_accordion = True
            
    if in_accordion:
        if '<div' in line:
            accordion_divs += line.count('<div')
        if '</div' in line:
            accordion_divs -= line.count('</div')
    
    # Hide applicants logic
    if "Applicants: {{ vac.total_applicants }}" in line:
        line = line.replace('<span', '{% if not is_hr %}<span').replace('</span>', '</span>{% endif %}')
    if "Check Applicants" in line and "<a href" in new_lines[-1] and "vacancy_applicants" in new_lines[-1]:
        new_lines.insert(-1, "        {% if not is_hr %}\\n")
        line = line + "        {% endif %}\\n"
    elif "Check Applicants" in line and "<a href" in line:
        line = "{% if not is_hr %}" + line.replace("</a>", "</a>{% endif %}")

    new_lines.append(line)
    
    if in_accordion and accordion_divs == 0 and '</div>' in line: # closed!
        new_lines.append(f"        {{% endif %}}\\n")
        
        # If it was User Chats, append Role Given
        if current_role == "user_chats":
            new_lines.append("""''' + role_given_html.replace('"', '\\"') + '''""")
            
        in_accordion = False
        current_role = None

with open('core/templates/core/admin_dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
''')
