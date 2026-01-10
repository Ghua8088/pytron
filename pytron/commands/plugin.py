import argparse
import os
import sys
import shutil
import zipfile
import requests
import json
from pathlib import Path
from ..console import log, print_rule

def cmd_plugin(args: argparse.Namespace) -> int:
    if args.plugin_command == "install":
        return plugin_install(args)
    elif args.plugin_command == "list":
        return plugin_list(args)
    elif args.plugin_command == "uninstall":
        return plugin_uninstall(args)
    elif args.plugin_command == "create":
        return plugin_create(args)
    else:
        log("No plugin command specified. Use 'install', 'list', 'uninstall', or 'create'.", style="error")
        return 1

def plugin_create(args):
    name = args.name
    
    # Check if we are in a Pytron app project
    # We look for common markers like settings.json or a requirements.json
    is_pytron_project = os.path.exists("settings.json") or os.path.exists("requirements.json")
    
    if is_pytron_project:
        plugins_dir = Path("plugins")
        if not plugins_dir.exists():
            log("Pytron project detected. Creating 'plugins/' directory.", style="info")
            plugins_dir.mkdir()
        plugin_path = plugins_dir / name
    else:
        log("Standalone mode: Creating plugin directory in current folder.", style="info")
        plugin_path = Path(name)

    if plugin_path.exists():
        log(f"Plugin directory '{name}' already exists.", style="error")
        return 1
    
    plugin_path.mkdir()
    
    # 1. manifest.json
    manifest = {
        "name": name,
        "version": "1.0.0",
        "entry_point": f"main:{name.capitalize()}Plugin",
        "ui_entry": f"{name}_widget.js",
        "python_dependencies": [],
        "npm_dependencies": {},
        "description": "Auto-generated Pytron plugin"
    }
    (plugin_path / "manifest.json").write_text(json.dumps(manifest, indent=4))
    
    # 2. Python Code
    python_code = f"""import logging

class {name.capitalize()}Plugin:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(f"Plugin.{name}")

    def setup(self):
        \"\"\"Standard Pytron plugin setup hook.\"\"\"
        self.app.expose(self.greet, name="{name}_greet")
        
        # Example usage of Scoped Storage
        count = self.app.storage.get("load_count", 0)
        self.app.storage.set("load_count", count + 1)
        self.logger.info(f"Plugin loaded {{count + 1}} times.")

    def greet(self, user="User"):
        return f"Hello {{user}} from {name} plugin!"
"""
    (plugin_path / "main.py").write_text(python_code)
    
    # 3. JS Widget
    js_code = f"""/**
 * {name} Web Component
 */
class {name.capitalize()}Widget extends HTMLElement {{
    constructor() {{
        super();
        this.attachShadow({{ mode: 'open' }});
    }}

    connectedCallback() {{
        this.render();
    }}

    async callGreet() {{
        const welcome = await window.pytron.{name}_greet("Explorer");
        alert(welcome);
    }}

    render() {{
        this.shadowRoot.innerHTML = `
            <style>
                :host {{
                    display: block;
                    padding: 1rem;
                    background: #1e293b;
                    border-radius: 8px;
                    color: white;
                    border: 1px solid #334155;
                }}
                button {{
                    background: #38bdf8;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: bold;
                }}
            </style>
            <div>
                <strong>{name.capitalize()} Plugin</strong>
                <p>Welcome to your new isolated plugin!</p>
                <button onclick="this.getRootNode().host.callGreet()">Test Bridge</button>
            </div>
        `;
    }}
}}

if (!customElements.get('{name}-widget')) {{
    customElements.define('{name}-widget', {name.capitalize()}Widget);
}}
"""
    (plugin_path / f"{name}_widget.js").write_text(js_code)
    
    log(f"Successfully scaffolded plugin: {name}", style="success")
    log(f"Location: {plugin_path}")
    return 0

def plugin_install(args):
    return perform_plugin_install(args.identifier)

def perform_plugin_install(identifier: str) -> int:
    parts = identifier.split(".")
    
    if len(parts) < 2:
        log("Invalid identifier format. Use 'username.repo' or 'username.repo.version'", style="error")
        return 1
        
    username = parts[0]
    repo = parts[1]
    version = parts[2] if len(parts) > 2 else "latest"
    
    # Resolve target plugins directory
    plugins_dir = Path("plugins")
    if not plugins_dir.exists():
        log("No 'plugins/' directory found in current project. Creating it...")
        plugins_dir.mkdir()
        
    target_plugin_path = plugins_dir / repo
    if target_plugin_path.exists():
        log(f"Plugin '{repo}' already exists at {target_plugin_path}. Use uninstall first if you want to reinstall.", style="warning")
        return 1
        
    print_rule(f"Installing Plugin: {username}/{repo} ({version})")
    
    # GitHub API Authentication
    headers = {}
    token = os.environ.get("PYTRON_GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        log("Using PYTRON_GITHUB_TOKEN for authentication.")
        
    try:
        if version == "latest":
            api_url = f"https://api.github.com/repos/{username}/{repo}/releases/latest"
        else:
            api_url = f"https://api.github.com/repos/{username}/{repo}/releases/tags/{version}"
            
        log(f"Fetching release info from: {api_url}")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 404:
            log(f"No release found for {username}/{repo}. Checking main branch source...", style="warning")
            zip_url = f"https://github.com/ {username}/{repo}/archive/refs/heads/main.zip"
        elif response.status_code != 200:
            log(f"GitHub API Error: {response.status_code} - {response.text}", style="error")
            return 1
        else:
            rel_data = response.json()
            zip_url = rel_data.get("zipball_url")
            log(f"Found release: {rel_data.get('tag_name')}")
            
        if not zip_url:
            log("Could not find a valid zip download URL.", style="error")
            return 1
            
        # Download
        log(f"Downloading from: {zip_url}")
        zip_response = requests.get(zip_url, headers=headers, stream=True)
        zip_tmp = Path("plugin_tmp.zip")
        
        with open(zip_tmp, 'wb') as f:
            for chunk in zip_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # Extract
        log("Extracting plugin...")
        with zipfile.ZipFile(zip_tmp, 'r') as zip_ref:
            # GitHub zips have a top-level folder 'user-repo-hash'
            # We want to extract its contents into plugins/repo
            top_folder = zip_ref.namelist()[0].split('/')[0]
            zip_ref.extractall("plugin_extract_tmp")
            
        shutil.move(os.path.join("plugin_extract_tmp", top_folder), target_plugin_path)
        
        # Cleanup
        os.remove(zip_tmp)
        shutil.rmtree("plugin_extract_tmp")
        
        # Verify Manifest
        manifest_path = target_plugin_path / "manifest.json"
        if manifest_path.exists():
            log(f"Successfully installed '{repo}'", style="success")
            with open(manifest_path, "r") as f:
                data = json.load(f)
                log(f"Plugin Metadata: {data.get('name')} v{data.get('version')}")
        else:
            log(f"Warning: Installed plugin '{repo}' is missing a manifest.json. It may not load correctly.", style="warning")
            
        return 0
        
    except Exception as e:
        log(f"Extraction failed: {e}", style="error")
        return 1

def plugin_list(args):
    plugins_dir = Path("plugins")
    if not plugins_dir.exists():
        log("No plugins/ directory found.")
        return 0
        
    print_rule("Installed Plugins")
    for item in plugins_dir.iterdir():
        if item.is_dir():
            manifest = item / "manifest.json"
            if manifest.exists():
                with open(manifest, "r") as f:
                    data = json.load(f)
                    log(f"- {data.get('name')} (v{data.get('version')})")
            else:
                log(f"- {item.name} (No Manifest)")
    return 0

def plugin_uninstall(args):
    name = args.name
    plugin_path = Path("plugins") / name
    if plugin_path.exists():
        log(f"Removing plugin: {name}")
        shutil.rmtree(plugin_path)
        log("Done.", style="success")
    else:
        log(f"Plugin '{name}' not found.", style="error")
    return 0
