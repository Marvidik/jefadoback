import os
import glob

# Files to update
files = []
files.extend(glob.glob("templates/emails/**/*.html", recursive=True))
files.extend([
    "accounts/serializers.py",
    "accounts/services.py",
    "core/email_service.py",
    "transactions/services/checkoutservice.py",
    "sellers/services/orderservices.py",
])

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r") as f:
            content = f.read()
        
        # Replace variations
        new_content = content.replace("Jefado", "Jefedo")
        new_content = new_content.replace("jefado", "jefedo")
        new_content = new_content.replace("JEFADO", "JEFEDO")
        
        if new_content != content:
            with open(fpath, "w") as f:
                f.write(new_content)
            print(f"Updated {fpath}")

print("Done")
