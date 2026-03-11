import json
import os
import asyncio
from pathlib import Path
import re
from pydantic import BaseModel, Field

try:
    from groq import Groq
except ImportError:
    Groq = None

def check_api_health(api_key: str) -> bool:
    """Verifies that the Groq API is accessible and the key is valid."""
    if not Groq:
        print("Groq SDK not installed.")
        return False
        
    try:
        client = Groq(api_key=api_key)
        # A lightweight call to verify authentication and connectivity
        client.models.list()
        return True
    except Exception as e:
        print(f"API Health Check Failed: {e}")
        return False
        
def has_frontmatter(content: str) -> bool:
    """Check if the markdown content already has YAML frontmatter."""
    return content.startswith("---")

class MetadataResponse(BaseModel):
    semantic_filename: str = Field(description="A kebab-case filename suitable for this chapter, keeping numeric prefixes if present.")
    chapter_title: str = Field(description="The clean, human-readable title of the chapter.")

def extract_metadata(content_snippet: str, api_key: str) -> MetadataResponse | None:
    if not Groq:
        raise ImportError("groq package is not installed")
        
    client = Groq(api_key=api_key)
    
    prompt = f"""
    You are a metadata extractor for a RAG system. Analyze the following markdown snippet from a book chapter.
    Return ONLY a JSON object with exactly these two keys:
    1. "semantic_filename": A lowercase, kebab-case filename representing the chapter's main topic.
    2. "chapter_title": The clean, human-readable title of the chapter without any '#' symbols.
    
    Snippet:
    {content_snippet[:2000]}
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a machine that outputs strict JSON with exactly two keys: 'semantic_filename' and 'chapter_title'."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result_str = chat_completion.choices[0].message.content
        data = json.loads(result_str)
        return MetadataResponse(**data)
    except Exception as e:
        print(f"Error during LLM extraction: {e}")
        # print the raw string to debug
        try:
             print(f"Raw output: {result_str}")
        except:
             pass
        return None

def process_file(file_path: Path, api_key: str, book_title: str):
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        return

    if has_frontmatter(content):
        print(f"Skipping {file_path.name} (Already enriched)")
        return
        
    print(f"Processing {file_path.name}...")
    metadata = extract_metadata(content, api_key)
    
    if not metadata:
        print(f"Failed to extract metadata for {file_path}")
        return
        
    # Construct frontmatter
    frontmatter = f"---\nbook_title: \"{book_title}\"\nchapter_title: \"{metadata.chapter_title}\"\n---\n\n"
    new_content = frontmatter + content
    
    # Ensure new filename has .md extension
    new_filename = metadata.semantic_filename
    if not new_filename.endswith(".md"):
        new_filename += ".md"
        
    # Maintain numeric ordering from original filename if possible (e.g. chapter_001.md -> 01-...)
    match = re.search(r'(\d+)', file_path.name)
    if match and not re.search(r'^\d', new_filename):
         # if the original had a number, and the new one doesn't start with a number, prepend it.
         num = match.group(1)
         new_filename = f"{num}-{new_filename}"
        
    new_path = file_path.parent / new_filename
    
    # Write and rename
    try:
        new_path.write_text(new_content, encoding="utf-8")
        if file_path != new_path:
            file_path.unlink()
        print(f"✅ Renamed to {new_filename}")
    except Exception as e:
        print(f"Error writing to {new_path}: {e}")

async def main(target_dir: str):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is missing. Please set it in .env or your environment.")
        return

    print("Checking Groq API Health...")
    if not check_api_health(api_key):
        print("Fatal: Groq API is unreachable or key is invalid. Aborting.")
        return
    print("API Health Check: OK")

    output_path = Path(target_dir)
    if not output_path.exists():
        print(f"Directory {target_dir} not found.")
        return

    # Find all books (directories in output/)
    for book_dir in output_path.iterdir():
        if not book_dir.is_dir():
            continue
            
        # Try to make a nice book title from the slug
        book_title = book_dir.name.replace("-", " ").title()
        
        md_files = list(book_dir.glob("*.md"))
        for i, md_file in enumerate(md_files):
            process_file(md_file, api_key, book_title)
            # Basic rate limiting to avoid hitting Groq's RPM limits
            await asyncio.sleep(2.5) 

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
    target = sys.argv[1] if len(sys.argv) > 1 else "output"
    asyncio.run(main(target))