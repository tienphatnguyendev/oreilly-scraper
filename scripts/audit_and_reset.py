import json
from pathlib import Path

def audit_library(output_dir: Path):
    if not output_dir.exists():
        print(f"Directory {output_dir} does not exist.")
        return
        
    corrupted_count = 0
    for state_file in output_dir.rglob("state.json"):
        book_dir = state_file.parent
        with open(state_file, 'r') as f:
            state_data = json.load(f)
            
        modified = False
        for chapter in state_data.get('chapters', []):
            if chapter.get('status') == 'downloaded':
                # Check markdown file
                md_path = chapter.get('markdown_path')
                if md_path:
                    full_path = book_dir / md_path
                    # Determine if corrupted: missing file, or file is too small (< 200 bytes)
                    is_corrupted = False
                    if not full_path.exists():
                        is_corrupted = True
                    elif full_path.stat().st_size < 200:
                        is_corrupted = True
                        
                    if is_corrupted:
                        print(f"Flagging corrupted chapter: {full_path}")
                        chapter['status'] = 'pending'
                        modified = True
                        corrupted_count += 1
                        if full_path.exists():
                            full_path.unlink() # Delete the bad file
                            
        if modified:
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
    print(f"Audit complete. Reset {corrupted_count} corrupted chapters to pending.")

if __name__ == "__main__":
    audit_library(Path("output"))