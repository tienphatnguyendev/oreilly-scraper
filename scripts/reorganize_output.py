import json
import shutil
from pathlib import Path

def reorganize_directory(output_path: Path):
    if not output_path.exists():
        return
        
    for state_file in list(output_path.rglob("state.json")):
        book_dir = state_file.parent
        
        # Read state to get slug
        with open(state_file, 'r') as f:
            state_data = json.load(f)
            
        url = state_data.get('book_url', '')
        parts = [p for p in url.split('/') if p]
        
        book_slug = book_dir.name
        
        # Try to find a better slug from chapter URLs if book_url uses '-'
        better_slug_found = False
        chapters = state_data.get('chapters', [])
        if chapters:
            first_chapter_url = chapters[0].get('url', '')
            c_parts = [p for p in first_chapter_url.split('/') if p]
            try:
                view_index = c_parts.index('view')
                if len(c_parts) > view_index + 1 and c_parts[view_index + 1] != '-':
                    book_slug = c_parts[view_index + 1]
                    better_slug_found = True
            except ValueError:
                pass
                
        if not better_slug_found:
            if len(parts) >= 2 and parts[-2] != "-":
                book_slug = parts[-2]
            elif len(parts) >= 1:
                book_slug = parts[-1]
            
        target_dir = output_path / book_slug
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Move markdown/pdf files from chapters/
        chapters_dir = book_dir / "chapters"
        if chapters_dir.exists() and chapters_dir.is_dir():
            for item in chapters_dir.iterdir():
                if item.is_file():
                    shutil.move(str(item), str(target_dir / item.name))
            try:
                chapters_dir.rmdir()
            except OSError:
                pass
                
        # Move all other files (like state.json)
        for item in book_dir.iterdir():
            if item.is_file() and item != target_dir:
                # avoid overwriting if target_dir is the same as book_dir and file is already there
                if item.parent != target_dir:
                     shutil.move(str(item), str(target_dir / item.name))
                     
        # Clean up empty parent directories up to output_path
        if target_dir != book_dir:
            current = book_dir
            while current != output_path and current != target_dir:
                try:
                    current.rmdir()
                    current = current.parent
                except OSError:
                    break
                
        # Update state.json
        new_state_path = target_dir / "state.json"
        if new_state_path.exists():
            modified = False
            for chapter in state_data.get('chapters', []):
                for key in ['markdown_path', 'pdf_path']:
                    if key in chapter and chapter[key] and chapter[key].startswith('chapters/'):
                        chapter[key] = chapter[key].replace('chapters/', '')
                        modified = True
            if modified:
                with open(new_state_path, 'w') as f:
                    json.dump(state_data, f, indent=2)

if __name__ == "__main__":
    reorganize_directory(Path("output"))
