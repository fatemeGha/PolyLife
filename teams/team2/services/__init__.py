# Team2 service layer — business logic lives here, not in views.
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic Bridge Pattern (With Temporary Package Context Override)
# ---------------------------------------------------------------------------
# We read and execute the monolithic services.py directly inside the 
# teams.team2.services module's scope. 
# To prevent relative import failures (like 'from .models import ...' which 
# resolves to 'teams.team2.services.models'), we temporarily override the 
# module's __package__ attribute to 'teams.team2' during the execution, 
# and safely restore it afterwards.

try:
    monolithic_file_path = Path(__file__).parent.parent / "services.py"
    
    if monolithic_file_path.exists():
        with open(monolithic_file_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Save original package name
        orig_package = globals().get("__package__")
        
        # Temporarily override package context so relative imports in services.py
        # resolve cleanly to 'teams.team2.models' instead of crashing
        globals()["__package__"] = "teams.team2"
        
        # Execute the code directly in this module's globals
        exec(code, globals())
        
        # Restore the original package context to avoid side effects
        globals()["__package__"] = orig_package
except Exception as e:
    import traceback
    print("--- Failed to execute monolithic services.py ---")
    traceback.print_exc()
    print("-----------------------------------------------")
