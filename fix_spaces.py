import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import Institute

def fix():
    institutes = Institute.objects.all()
    count = 0
    for inst in institutes:
        needs_fix = False
        original_name = inst.name
        
        if inst.name != inst.name.strip():
            inst.name = inst.name.strip()
            needs_fix = True
        
        if inst.state != inst.state.strip():
            inst.state = inst.state.strip()
            needs_fix = True
            
        if inst.district != inst.district.strip():
            inst.district = inst.district.strip()
            needs_fix = True
            
        if inst.belief and inst.belief != inst.belief.strip():
            inst.belief = inst.belief.strip()
            needs_fix = True
            
        if needs_fix:
            print(f"Fixing Institute: '{original_name}' -> '{inst.name}'")
            inst.save()
            count += 1
            
    print(f"Fixed {count} institutes.")

if __name__ == '__main__':
    fix()
