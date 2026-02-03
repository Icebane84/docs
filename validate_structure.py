import os
import json
import re
import sys
from typing import Any, Dict, List, Set, Optional

# Reconfigure stdout to be unbuffered
sys.stdout.reconfigure(encoding='utf-8')

DOCS_ROOT = os.getcwd()
DOCS_JSON_PATH = os.path.join(DOCS_ROOT, 'docs.json')

def load_docs_json() -> Optional[Dict[str, Any]]:
    try:
        with open(DOCS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: docs.json not found at {DOCS_JSON_PATH}", flush=True)
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing docs.json: {e}", flush=True)
        return None

def validate_schema(config: Dict[str, Any]) -> List[str]:
    print("\n🔍 Validating Schema...", flush=True)
    errors = []
    
    # 1. Check Required Keys
    required_keys = ["name", "logo", "favicon", "colors", "theme", "navigation"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required key: '{key}'")

    # 2. Validate Theme
    valid_themes = ["mint", "maple", "palm", "willow", "linden", "almond", "aspen"]
    if "theme" in config and config["theme"] not in valid_themes:
        errors.append(f"Invalid theme '{config['theme']}'. Expected one of: {', '.join(valid_themes)}")

    # 3. Validate Navigation Structure
    if "navigation" in config:
        nav = config["navigation"]
        if isinstance(nav, list):
             # Legacy array of groups - Valid
             pass
        elif isinstance(nav, dict):
             if "tabs" not in nav:
                 errors.append("Navigation object must contain 'tabs' array.")
        else:
             errors.append("Navigation must be either an array of groups or an object with 'tabs'.")

    return errors

def extract_pages_from_groups(groups: List[Dict[str, Any]]) -> Set[str]:
    """Helper to extract flat page list from groups."""
    pages = set()
    for group in groups:
        if 'pages' in group:
            for page in group['pages']:
                if isinstance(page, str):
                    pages.add(page)
                elif isinstance(page, dict) and 'pages' in page: # Subpages
                     # Simple recursion for subpages if needed, for now ignoring deep nesting
                     # as per previous logic, but let's be safe
                     pass 
    return pages

def get_nav_pages(config: Dict[str, Any]) -> Set[str]:
    if 'navigation' not in config:
        return set()

    nav = config['navigation']
    groups = []
    
    # Normalize to list of groups whether it's legacy list or new tabs dict
    if isinstance(nav, list):
        groups = nav
    elif isinstance(nav, dict) and 'tabs' in nav:
        for tab in nav['tabs']:
            if 'groups' in tab:
                groups.extend(tab['groups'])
    
    return extract_pages_from_groups(groups)

def find_mdx_files() -> Set[str]:
    mdx_files = set()
    for root, _, files in os.walk(DOCS_ROOT): # 'dirs' unused, replaced with _
        if 'node_modules' in root.split(os.sep) or '.git' in root.split(os.sep):
            continue
            
        for file in files:
            if file.endswith('.mdx'):
                rel_path = os.path.relpath(os.path.join(root, file), DOCS_ROOT)
                rel_path_no_ext = os.path.splitext(rel_path)[0]
                rel_path_normalized = rel_path_no_ext.replace(os.sep, '/')
                mdx_files.add(rel_path_normalized)
    return mdx_files

def extract_links(file_path: str) -> List[str]:
    links = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        matches = re.findall(r'\[.*?\]\((.*?)\)', content)
        for link in matches:
             if not link.startswith(('http', 'https', 'mailto', '#')):
                 links.append(link)
    return links

def validate_links(found_files: Set[str], nav_pages: Set[str]) -> None:
    print("\n🔍 Scanning Internal Links...", flush=True)
    broken_links = []
    
    for file_rel_path in found_files:
        file_disk_path = os.path.join(DOCS_ROOT, file_rel_path.replace('/', os.sep) + '.mdx')
        if not os.path.exists(file_disk_path):
             continue
             
        links = extract_links(file_disk_path)
        for link in links:
            clean_link = link.split('#')[0]
            # Handle relative path navigation if needed, currently checking match against known files
            
            target = clean_link[1:] if clean_link.startswith('/') else clean_link
                 
            if target not in found_files and target != "index" and target not in nav_pages:
                 broken_links.append(f"{file_rel_path} -> {link}")

    if broken_links:
        print("⚠️ [BROKEN LINKS] Potential broken internal links detected:", flush=True)
        for bl in broken_links:
            print(f"  - {bl}", flush=True)
    else:
        print("✅ [LINKS] No broken internal link paths detected (AbsolutePath Check).", flush=True)

def validate() -> None:
    print("🔍 Synarche Documentation Validator Initiated...\n", flush=True)
    
    config = load_docs_json()
    if not config:
        return

    # Schema Validation
    schema_errors = validate_schema(config)
    if schema_errors:
        print("❌ [SCHEMA] Errors detected in docs.json:", flush=True)
        for err in schema_errors:
            print(f"  - {err}", flush=True)
    else:
        print("✅ [SCHEMA] docs.json schema appears valid.", flush=True)

    nav_pages = get_nav_pages(config)
    found_files = find_mdx_files()
    
    # 1. Check for Missing Files
    missing_files = [page for page in nav_pages if page not in found_files]

    if missing_files:
        print("❌ [MISSING] The following pages are in docs.json but file missing:", flush=True)
        for f in missing_files:
            print(f"  - {f}", flush=True)
    else:
        print("✅ [NAV] All docs.json pages exist on disk.", flush=True)

    # 2. Check for Orphan Files
    orphans = found_files - nav_pages
    if 'index' in orphans:
        orphans.remove('index')
    
    if orphans:
        print("\n⚠️ [ORPHAN] The following MDX files found but NOT in docs.json navigation:", flush=True)
        for f in orphans:
            print(f"  - {f}", flush=True)
    else:
        print("✅ [CLEAN] No orphan MDX files found.", flush=True)

    # 3. Link Validation
    validate_links(found_files, nav_pages)

    print("\n🏁 Validation Complete.", flush=True)

if __name__ == "__main__":
    validate()
