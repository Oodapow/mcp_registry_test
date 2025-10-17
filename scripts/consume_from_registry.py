#!/usr/bin/env python3
"""
Example script showing how to consume MCP servers from the registry.
Demonstrates searching, discovering, and getting installation info for servers.
"""

import requests
import json
from typing import Optional, List, Dict, Any
from urllib.parse import quote


class MCPRegistryClient:
    """Client for interacting with an MCP registry."""
    
    def __init__(self, registry_url: str = "http://localhost:8080"):
        self.registry_url = registry_url.rstrip('/')
        self.api_base = f"{self.registry_url}/v0.1"
    
    def list_servers(
        self, 
        search: Optional[str] = None,
        version: str = "latest",
        limit: int = 30,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List servers from the registry.
        
        Args:
            search: Search term to filter servers (substring match on name)
            version: Filter by version ('latest' or specific version)
            limit: Number of results per page (1-100)
            cursor: Pagination cursor for next page
            
        Returns:
            Response with servers list and pagination info
        """
        params = {
            "limit": limit,
            "version": version,
        }
        if search:
            params["search"] = search
        if cursor:
            params["cursor"] = cursor
        
        response = requests.get(f"{self.api_base}/servers", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_server(self, server_name: str) -> Dict[str, Any]:
        """
        Get the latest version of a specific server.
        
        Args:
            server_name: Full server name (e.g., 'io.modelcontextprotocol.anonymous/mcp-math-server')
            
        Returns:
            Server details including metadata
        """
        # Use the versions endpoint with 'latest' to get the latest version
        return self.get_server_version(server_name, "latest")
    
    def get_server_version(self, server_name: str, version: str) -> Dict[str, Any]:
        """
        Get a specific version of a server.
        
        Args:
            server_name: Full server name
            version: Specific version or 'latest'
            
        Returns:
            Server details for that version
        """
        encoded_name = quote(server_name, safe='')
        encoded_version = quote(version, safe='')
        response = requests.get(
            f"{self.api_base}/servers/{encoded_name}/versions/{encoded_version}"
        )
        response.raise_for_status()
        return response.json()
    
    def list_server_versions(self, server_name: str) -> Dict[str, Any]:
        """
        List all versions of a server.
        
        Args:
            server_name: Full server name
            
        Returns:
            List of all versions
        """
        encoded_name = quote(server_name, safe='')
        response = requests.get(f"{self.api_base}/servers/{encoded_name}/versions")
        response.raise_for_status()
        return response.json()


def print_server_info(server_data: Dict[str, Any], detailed: bool = False):
    """Pretty print server information."""
    server = server_data.get('server', {})
    meta = server_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
    
    print(f"\n{'='*70}")
    print(f"📦 {server.get('title', 'N/A')}")
    print(f"{'='*70}")
    print(f"Name:        {server.get('name', 'N/A')}")
    print(f"Version:     {server.get('version', 'N/A')}")
    print(f"Description: {server.get('description', 'N/A')}")
    
    if repo := server.get('repository'):
        print(f"Repository:  {repo.get('url', 'N/A')}")
    
    if meta:
        print(f"\nStatus:      {meta.get('status', 'N/A')}")
        print(f"Published:   {meta.get('publishedAt', 'N/A')}")
        if meta.get('isLatest'):
            print(f"Latest:      ✓ This is the latest version")
    
    if detailed and (packages := server.get('packages')):
        print(f"\n📦 Installation Packages:")
        for pkg in packages:
            print(f"   Type:     {pkg.get('type', 'N/A')}")
            print(f"   Name:     {pkg.get('name', 'N/A')}")
            if install_cmd := pkg.get('installCommand'):
                print(f"   Install:  {install_cmd}")
            if run_cmd := pkg.get('runCommand'):
                print(f"   Run:      {run_cmd}")
            print()


def example_1_search_servers(client: MCPRegistryClient):
    """Example 1: Search for servers in the registry."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Search for Math Servers")
    print("="*70)
    
    # Search for servers containing "math" in their name
    result = client.list_servers(search="math", limit=10)
    
    servers = result.get('servers', [])
    print(f"\nFound {len(servers)} server(s) matching 'math':")
    
    for server_data in servers:
        server = server_data.get('server', {})
        print(f"  • {server.get('name')} v{server.get('version')} - {server.get('title')}")


def example_2_get_specific_server(client: MCPRegistryClient, server_name: str):
    """Example 2: Get details for a specific server."""
    print("\n" + "="*70)
    print(f"EXAMPLE 2: Get Server Details")
    print("="*70)
    
    try:
        server_data = client.get_server(server_name)
        print_server_info(server_data, detailed=True)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"\n❌ Server '{server_name}' not found in registry")
        else:
            raise


def example_3_list_versions(client: MCPRegistryClient, server_name: str):
    """Example 3: List all versions of a server."""
    print("\n" + "="*70)
    print(f"EXAMPLE 3: List All Versions")
    print("="*70)
    
    try:
        result = client.list_server_versions(server_name)
        versions = result.get('versions', [])
        
        print(f"\nAvailable versions of {server_name}:")
        for version_data in versions:
            version_info = version_data.get('version', {})
            meta = version_data.get('_meta', {}).get('io.modelcontextprotocol.registry/official', {})
            
            version_str = version_info.get('version', 'unknown')
            published = meta.get('publishedAt', 'N/A')
            latest = " (LATEST)" if meta.get('isLatest') else ""
            
            print(f"  • v{version_str}{latest} - published {published}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"\n❌ Server '{server_name}' not found")
        else:
            raise


def example_4_list_all_servers(client: MCPRegistryClient):
    """Example 4: List all servers with pagination."""
    print("\n" + "="*70)
    print("EXAMPLE 4: List All Servers (with pagination)")
    print("="*70)
    
    all_servers = []
    cursor = None
    page = 1
    
    while True:
        result = client.list_servers(limit=10, cursor=cursor)
        servers = result.get('servers', [])
        all_servers.extend(servers)
        
        print(f"\nPage {page}: Found {len(servers)} servers")
        
        cursor = result.get('nextCursor')
        if not cursor:
            break
        page += 1
    
    print(f"\n✓ Total servers in registry: {len(all_servers)}")
    print("\nServers:")
    for server_data in all_servers:
        server = server_data.get('server', {})
        print(f"  • {server.get('name')} v{server.get('version')}")


def example_5_installation_info(client: MCPRegistryClient, server_name: str):
    """Example 5: Get installation information."""
    print("\n" + "="*70)
    print("EXAMPLE 5: How to Use This Server")
    print("="*70)
    
    try:
        server_data = client.get_server(server_name)
        server = server_data.get('server', {})
        
        print(f"\n📖 Installation Guide for {server.get('title', server_name)}")
        print("\nOption 1: Direct Installation")
        
        packages = server.get('packages', [])
        if packages:
            for pkg in packages:
                pkg_type = pkg.get('type')
                pkg_name = pkg.get('name')
                
                if pkg_type == 'npm':
                    print(f"  npm install -g {pkg_name}")
                elif pkg_type == 'pypi':
                    print(f"  pip install {pkg_name}")
                elif pkg_type == 'docker':
                    print(f"  docker pull {pkg_name}")
                
                if run_cmd := pkg.get('runCommand'):
                    print(f"  {run_cmd}")
        else:
            print("  No pre-packaged installation available.")
            if repo := server.get('repository'):
                print(f"  Clone and build from source: {repo.get('url')}")
        
        print("\nOption 2: Use with MCP Client (e.g., Claude Desktop)")
        print("  Add to your MCP client config:")
        
        # Get command from first package if available
        command = "path-to-server"
        if packages and len(packages) > 0:
            first_pkg = packages[0]
            command = first_pkg.get('runCommand', 'server-command')
        
        print(f"""
  {{
    "mcpServers": {{
      "{server.get('name', 'server').split('/')[-1]}": {{
        "command": "{command}"
      }}
    }}
  }}
        """)
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"\n❌ Server '{server_name}' not found")
        else:
            raise


def main():
    """Main function demonstrating registry consumption."""
    print("="*70)
    print("MCP Registry Consumer - Example Usage")
    print("="*70)
    print("\nThis script demonstrates how to discover and consume MCP servers")
    print("from the registry using the REST API.")
    
    # Initialize client (using local registry, change to production as needed)
    registry_url = "http://localhost:8080"
    print(f"\nRegistry URL: {registry_url}")
    
    client = MCPRegistryClient(registry_url)
    
    # Check registry connectivity
    try:
        response = requests.get(f"{registry_url}/health")
        print(f"✓ Registry is accessible")
    except Exception as e:
        print(f"❌ Cannot connect to registry: {e}")
        print("\nMake sure the registry is running:")
        print("  cd registry && make docker-up")
        return
    
    # Example server to work with
    server_name = "io.modelcontextprotocol.anonymous/mcp-math-server"
    
    # Run examples
    try:
        example_1_search_servers(client)
        example_2_get_specific_server(client, server_name)
        example_3_list_versions(client, server_name)
        example_4_list_all_servers(client)
        example_5_installation_info(client, server_name)
        
        print("\n" + "="*70)
        print("✓ All examples completed successfully!")
        print("="*70)
        print("\nNext Steps:")
        print("  • Use these patterns in your MCP client or subregistry")
        print("  • Add caching to handle registry downtime")
        print("  • Implement error handling for production use")
        print("  • See API docs: http://localhost:8080/docs")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

