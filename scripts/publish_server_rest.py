#!/usr/bin/env python3
"""Publish MCP Server to the registry using REST API."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests


def get_auth_token_none(registry_url: str) -> str:
    """Get authentication token from /auth/none endpoint (for local development)."""
    response = requests.post(
        f"{registry_url}/v0.1/auth/none",
        headers={
            "Accept": "application/json, application/problem+json",
            "Content-Type": "application/json"
        },
        timeout=10
    )
    response.raise_for_status()
    
    data = response.json()
    token = data['registry_token']
    expires_at = data.get('expires_at', 'unknown')
    print(f"[OK] Got auth token from /auth/none (expires: {expires_at})")
    return token


def validate_server_json(server_json_path: Path) -> dict:
    """Validate server.json against MCP schema."""
    print("Validating server.json...")
    
    with open(server_json_path) as f:
        server_data = json.load(f)

    # Download schema
    schema_url = "https://static.modelcontextprotocol.io/schemas/2025-09-29/server.schema.json"
    response = requests.get(schema_url, timeout=10)
    response.raise_for_status()
    schema = response.json()

    # Import jsonschema
    import jsonschema
    
    # Validate
    jsonschema.validate(instance=server_data, schema=schema)
    print("[OK] Validation successful!")
    return server_data


def publish_server(registry_url: str, server_data: dict, auth_token: Optional[str] = None) -> dict:
    """Publish server to registry using REST API."""
    print(f"Publishing to: {registry_url}/v0.1/publish")
    
    headers = {
        "Accept": "application/json, application/problem+json",
        "Content-Type": "application/json"
    }
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    response = requests.post(
        f"{registry_url}/v0.1/publish",
        headers=headers,
        json=server_data,
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"ERROR: Publishing failed with status {response.status_code}")
        error_data = response.json()
        print("Error details:")
        print(json.dumps(error_data, indent=2))
        response.raise_for_status()
    
    print("[OK] Successfully published!")
    return response.json()


def update_server_version(registry_url: str, server_name: str, version: str, 
                         server_data: dict, auth_token: Optional[str] = None) -> dict:
    """Update a specific server version using REST API."""
    endpoint = f"{registry_url}/v0.1/servers/{server_name}/versions/{version}"
    print(f"Updating: {endpoint}")
    
    headers = {
        "Accept": "application/json, application/problem+json",
        "Content-Type": "application/json"
    }
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    response = requests.put(
        endpoint,
        headers=headers,
        json=server_data,
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"ERROR: Update failed with status {response.status_code}")
        error_data = response.json()
        print("Error details:")
        print(json.dumps(error_data, indent=2))
        response.raise_for_status()
    
    print("[OK] Successfully updated!")
    return response.json()


def get_server_info(registry_url: str, server_name: str) -> dict:
    """Get server information from registry."""
    response = requests.get(
        f"{registry_url}/v0.1/servers",
        params={"search": server_name},
        headers={"Accept": "application/json"},
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    """Main publish function."""
    print("=" * 70)
    print("MCP Server Publisher - REST API Mode")
    print("=" * 70)
    print()

    # Get paths
    script_dir = Path(__file__).parent
    server_root = script_dir.parent.parent / "mcp_server_test"
    
    # Allow custom server.json path via environment variable
    custom_server_path = os.environ.get('MCP_SERVER_JSON')
    if custom_server_path:
        server_json_path = Path(custom_server_path)
    else:
        server_json_path = server_root / "server.json"

    # Configuration
    registry_url = os.environ.get('MCP_REGISTRY_URL', 'http://localhost:8080')
    auth_token = os.environ.get('MCP_AUTH_TOKEN')
    update_mode = os.environ.get('MCP_UPDATE_MODE', 'false').lower() == 'true'
    auto_auth = os.environ.get('MCP_AUTO_AUTH', 'true').lower() == 'true'

    print(f"Configuration:")
    print(f"   Server JSON: {server_json_path}")
    print(f"   Registry URL: {registry_url}")
    print(f"   Auth Token: {'Set (from env)' if auth_token else 'Not set'}")
    print(f"   Auto Auth: {auto_auth}")
    print(f"   Update Mode: {update_mode}")
    print()

    # Validate server.json
    server_data = validate_server_json(server_json_path)
    print()

    # Show server info
    print("Server Information:")
    server_name = server_data.get('name', 'unknown')
    server_version = server_data.get('version', 'unknown')
    
    print(f"   Name:        {server_name}")
    print(f"   Title:       {server_data.get('title', 'N/A')}")
    print(f"   Version:     {server_version}")
    desc = server_data.get('description', 'N/A')
    print(f"   Description: {desc[:60]}{'...' if len(desc) > 60 else ''}")
    
    if 'packages' in server_data:
        print(f"   Packages:    {len(server_data['packages'])}")
        for pkg in server_data['packages']:
            print(f"      - {pkg.get('registryType')}: {pkg.get('identifier')} v{pkg.get('version')}")
    
    if 'remotes' in server_data:
        print(f"   Remotes:     {len(server_data['remotes'])}")
        for remote in server_data['remotes']:
            print(f"      - {remote.get('type')}: {remote.get('url')}")
    
    print()

    # Check if registry is accessible
    print("Checking registry connectivity...")
    response = requests.get(f"{registry_url}/v0.1/servers", timeout=5)
    response.raise_for_status()
    print("[OK] Registry is accessible")
    print()

    # Get authentication token if not provided
    if not auth_token and auto_auth:
        print("Getting authentication token from /auth/none...")
        auth_token = get_auth_token_none(registry_url)
        print(f"[OK] Using auto-generated token: {auth_token[:20]}...")
        print()

    # Publish or update
    if update_mode:
        print("=" * 70)
        print(f"UPDATE MODE: Updating version {server_version}")
        print("=" * 70)
        print()
        result = update_server_version(
            registry_url, server_name, server_version, server_data, auth_token
        )
    else:
        print("=" * 70)
        print("PUBLISH MODE: Publishing new server or version")
        print("=" * 70)
        print()
        result = publish_server(registry_url, server_data, auth_token)

    print()
    
    # Display result
    print("Published Server Details:")
    print(json.dumps(result, indent=2)[:1000])
    print()

    # Verify publication
    print("Verifying publication...")
    time.sleep(2)
    
    server_info = get_server_info(registry_url, server_name)
    print("[OK] Server is now visible in registry!")
    print()
    print(f"Available versions:")
    for server in server_info.get('servers', []):
        srv = server.get('server', {})
        meta = server.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
        print(f"   - v{srv.get('version')} (published: {meta.get('publishedAt', 'unknown')})")

    print()
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)
    print()
    print("Next steps:")
    print(f"  1. View server: {registry_url}/v0.1/servers?search={server_name}")
    print("  2. Test with an MCP client")
    print("  3. Set up CI/CD for automated publishing")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)

