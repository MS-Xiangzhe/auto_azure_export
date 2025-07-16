# Auto Azure Export - MCP Server

A Model Context Protocol (MCP) server for automating Microsoft Graph Explorer operations using Playwright.

## Features

- 🌐 Connect to existing Edge browser instance
- 📸 Screenshot functionality with FastMCP
- � Streamable HTTP transport for better scalability
- 🎯 Microsoft Graph Explorer automation
- 🔧 Stateless operation for multi-node deployments

## Installation

### Prerequisites

- Python 3.12+
- uv (recommended) or pip

### Setup

1. Clone the repository and navigate to the project directory
2. Install dependencies:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

3. Install Playwright browsers:

```bash
playwright install msedge
```

## Usage

### Starting the Server

```bash
# Using uv
uv run python main.py

# Or using pip
python main.py
```

The server will start with streamable HTTP transport on the default MCP port.

### MCP Integration

This server uses the official MCP Python SDK with FastMCP for streamable HTTP transport. It can be integrated with:

- Claude Desktop
- MCP clients
- Other MCP-compatible applications

### MCP Tool Usage

The server provides the following MCP tool:

#### `graph_explorer_screenshot`

Take a screenshot of the Microsoft Graph Explorer page.

**Parameters:**
- `full_page` (boolean, optional): Whether to capture the full page (default: False)
- `element_selector` (string, optional): CSS selector to capture a specific element

**Returns:**
- `Image`: Screenshot image data in PNG format

### Testing with MCP Inspector

```bash
# Test the server with MCP development tools
uv run mcp dev main.py

# Install in Claude Desktop
uv run mcp install main.py
```

## Development

### Project Structure

```
auto_azure_export/
├── main.py              # Main MCP server implementation
├── requirements.txt     # Python dependencies
├── pyproject.toml      # Project configuration
├── .env                # Environment variables
└── README.md           # This file
```

### Environment Variables

Configure the server behavior using `.env` file:

```env
# Edge browser debug port
EDGE_DEBUG_PORT=9222

# Graph Explorer URL
GRAPH_EXPLORER_URL=https://developer.microsoft.com/en-us/graph/graph-explorer

# Log level
LOG_LEVEL=INFO

# Timeout settings (milliseconds)
DEFAULT_TIMEOUT=10000
REQUEST_TIMEOUT=30000
```

### Browser Connection

The server automatically:
1. Tries to connect to an existing Edge browser with debugging enabled on port 9222
2. If no existing browser is found, launches a new Edge instance
3. Navigates to Microsoft Graph Explorer
4. Maintains the browser session for subsequent requests

## Configuration

### MCP Server Settings

The server is configured with:
- **Stateless HTTP**: Enabled for better scalability
- **JSON Response**: Enabled for better compatibility
- **Streamable HTTP Transport**: For production deployments

### Browser Settings

The server launches Edge with the following arguments:
- `--remote-debugging-port=9222`: Enable remote debugging
- `--no-first-run`: Skip first run setup
- `--no-default-browser-check`: Skip default browser check
- `--disable-blink-features=AutomationControlled`: Hide automation detection
- `--disable-web-security`: Disable web security (for automation)

### Viewport Configuration

Default viewport: 1920x1080

## Troubleshooting

### Common Issues

1. **Browser connection fails**: Ensure no other applications are using port 9222
2. **Screenshot timeout**: Check if Graph Explorer is loading properly
3. **Element not found**: Verify CSS selectors are valid
4. **MCP connection issues**: Ensure MCP client is properly configured

### Logs

The server logs important events including:
- Browser connection status
- Navigation success/failure
- Screenshot operations
- MCP tool calls
- Errors and exceptions

## MCP Protocol

This server implements the Model Context Protocol specification and supports:
- Tool discovery and execution
- Image data transfer
- Structured output
- Error handling
- Stateless operation

For more information about MCP, visit the [Model Context Protocol documentation](https://modelcontextprotocol.io/).
