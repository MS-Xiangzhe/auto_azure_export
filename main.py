#!/usr/bin/env python3
"""
Microsoft Graph Explorer MCP Server
Playwright automation for Microsoft Graph Explorer with MCP streaming transport
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Graph Explorer URL
GRAPH_EXPLORER_URL = "https://developer.microsoft.com/en-us/graph/graph-explorer"


# Pydantic models for better AI understanding
class ScreenshotOptions(BaseModel):
    """Options for taking screenshots."""

    full_page: bool = Field(
        default=False,
        description="Whether to capture the full page (True) or just the viewport (False)",
    )
    element_selector: Optional[str] = Field(
        default=None,
        description="CSS selector for specific element to capture (e.g., '.main-content', '#response-area')",
    )
    save_path: Optional[str] = Field(
        default=None,
        description="Absolute file path to save the screenshot (e.g., 'C:\\screenshots\\page.png', '/home/user/screenshots/page.png')",
    )



class ApiRequestConfig(BaseModel):
    """Configuration for Microsoft Graph API requests."""

    url: str = Field(
        description="Microsoft Graph API endpoint URL (e.g., 'https://graph.microsoft.com/v1.0/me')"
    )
    method: str = Field(
        default="GET", description="HTTP method: GET, POST, PUT, PATCH, or DELETE"
    )
    body: Optional[str] = Field(
        default=None,
        description='Request body content - supports any JSON structure without escaping (e.g., {"subject": "Test Email"})',
    )


class RequestBodyData(BaseModel):
    """Schema for request body data."""

    content: Any = Field(
        description="Request body content - supports any type: JSON objects, strings, arrays, etc. No escaping needed for JSON."
    )
    content_type: str = Field(
        default="application/json", description="Content type of the request body"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            # Custom JSON encoder if needed
        }


class GraphExplorerResponse(BaseModel):
    """Response from Graph Explorer operations."""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable status message")
    data: Optional[str] = Field(
        default=None, description="Additional data returned by the operation"
    )


class GraphExplorerMCP:
    """Microsoft Graph Explorer MCP Server using FastMCP"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

        # Create FastMCP server with streamable HTTP transport
        self.mcp = FastMCP(
            name="Graph Explorer Server",
            stateless_http=True,  # Stateless for better scalability
            json_response=True,  # JSON responses for better compatibility
        )

        # Register tools
        self.setup_tools()

    def setup_tools(self):
        """Setup MCP tools"""

        @self.mcp.tool()
        async def graph_explorer_screenshot(
            full_page: bool = False,
            element_selector: Optional[str] = None,
            save_path: Optional[str] = None,
        ) -> str:
            """Take screenshot of Microsoft Graph Explorer current page.

            Args:
                full_page: Whether to capture full page (default: False)
                element_selector: Optional CSS selector for specific element to capture
                save_path: Optional absolute file path to save the screenshot

            Returns:
                str: Success message with screenshot information

            Examples:
                - Basic screenshot: graph_explorer_screenshot()
                - Full page screenshot: graph_explorer_screenshot(full_page=True)
                - Element screenshot: graph_explorer_screenshot(element_selector="#response-area")
                - Save to file: graph_explorer_screenshot(save_path="C:\\screenshots\\graph.png")

            Note: save_path must be an absolute path, not relative.
            """
            # Validate inputs using Pydantic model
            options = ScreenshotOptions(
                full_page=full_page,
                element_selector=element_selector,
                save_path=save_path,
            )

            # Validate that save_path is absolute if provided
            if save_path:
                path_obj = Path(save_path)
                if not path_obj.is_absolute():
                    raise ValueError(
                        f"save_path must be an absolute path, got: {save_path}"
                    )

            return await self._take_screenshot_async(
                options.full_page,
                options.element_selector,
                options.save_path,
            )

        @self.mcp.tool()
        async def graph_explorer_navigate() -> str:
            """Navigate to Microsoft Graph Explorer page

            This tool refreshes the page to the Graph Explorer URL and ensures
            the page is fully loaded before returning.

            Returns:
                str: Success message with current page URL
            """
            return await self._navigate_to_graph_explorer_async()

        @self.mcp.tool()
        async def graph_explorer_set_url(api_url: str) -> str:
            """Set the API URL in the Graph Explorer query input.

            Args:
                api_url: Microsoft Graph API endpoint URL

            Returns:
                str: Success message with the URL that was set

            Examples:
                - Get user profile: graph_explorer_set_url("https://graph.microsoft.com/v1.0/me")
                - List users: graph_explorer_set_url("https://graph.microsoft.com/v1.0/users")
                - Get mail: graph_explorer_set_url("https://graph.microsoft.com/v1.0/me/messages")
            """
            # Validate URL format
            if not api_url.startswith("https://graph.microsoft.com/"):
                raise ValueError("URL must be a valid Microsoft Graph API endpoint")

            return await self._set_api_url_async(api_url)

        @self.mcp.tool()
        async def graph_explorer_set_method(method: str) -> str:
            """Set the HTTP method in the Graph Explorer dropdown.

            Args:
                method: HTTP method to use for the API request

            Returns:
                str: Success message with the method that was set

            Supported methods:
                - GET: Retrieve data (default for most operations)
                - POST: Create new resources
                - PUT: Update/replace entire resources
                - PATCH: Update specific fields of resources
                - DELETE: Remove resources

            Examples:
                - Read data: graph_explorer_set_method("GET")
                - Create resource: graph_explorer_set_method("POST")
                - Update resource: graph_explorer_set_method("PATCH")
            """
            # Validate method using our model
            valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
            method_upper = method.upper()

            if method_upper not in valid_methods:
                raise ValueError(
                    f"Invalid HTTP method: {method}. Must be one of: {valid_methods}"
                )

            return await self._set_http_method_async(method_upper)

        @self.mcp.tool()
        async def graph_explorer_set_request_body(body: Any) -> str:
            """Set the request body content in Graph Explorer.

            Args:
                body: Request body content - supports any type without escaping

            Returns:
                str: Success message with confirmation of body being set

            Supported body types (no escaping needed):
                - JSON object: {"key": "value", "number": 123}
                - JSON array: [{"id": 1}, {"id": 2}]
                - String: "Hello World"
                - Number: 42
                - Boolean: True

            Examples:
                - Send email: graph_explorer_set_request_body({
                    "subject": "Test Email",
                    "body": {"content": "Hello World", "contentType": "Text"},
                    "toRecipients": [{"emailAddress": {"address": "user@example.com"}}]
                  })
                - Create user: graph_explorer_set_request_body({
                    "displayName": "John Doe",
                    "userPrincipalName": "john@example.com",
                    "accountEnabled": True
                  })
                - Simple string: graph_explorer_set_request_body("Plain text content")
                - Array data: graph_explorer_set_request_body([{"name": "Item 1"}, {"name": "Item 2"}])

            Note: JSON objects are automatically serialized - no need to escape quotes or convert to strings.
            """
            # Validate and process body using Pydantic model
            try:
                body_data = RequestBodyData(content=body)

                # Convert to string if it's not already
                if isinstance(body_data.content, dict):
                    import json

                    body_str = json.dumps(body_data.content, indent=2)
                else:
                    body_str = str(body_data.content)

                return await self._set_request_body_async(body_str)

            except Exception as e:
                raise ValueError(f"Invalid request body format: {str(e)}")

        @self.mcp.tool()
        async def graph_explorer_get_response_body() -> str:
            """Get the response body content from Graph Explorer.

            Returns:
                str: Response body content as JSON string or plain text

            This tool:
                1. Clicks the "Response preview" tab
                2. Retrieves content from the Monaco editor
                3. Returns the raw response data

            Use this after running a query to see the API response.
            """
            return await self._get_response_body_async()

        @self.mcp.tool()
        async def graph_explorer_get_response_status() -> str:
            """Get the response status information from Graph Explorer.

            Returns:
                str: Response status information including HTTP status code, message, and timing

            This tool:
                1. Looks for the status message bar in the response area
                2. Extracts the HTTP status code, status message, and response time
                3. Returns the complete status information

            Use this after running a query to check the API response status.
            The response format is typically: "STATUS_MESSAGE - STATUS_CODE - RESPONSE_TIME"
            Example: "OK - 200 - 723 ms"
            """
            return await self._get_response_status_async()

        @self.mcp.tool()
        async def graph_explorer_view_image(image_path: str) -> ImageContent:
            """View an image from the specified file path.

            Args:
                image_path: Absolute path to the image file to view

            Returns:
                ImageContent: Image binary data with metadata

            Supported formats:
                - PNG (.png)
                - JPEG (.jpg, .jpeg)
                - GIF (.gif)
                - BMP (.bmp)
                - WEBP (.webp)

            Examples:
                - View screenshot: graph_explorer_view_image("C:\\screenshots\\graph.png")
                - View saved image: graph_explorer_view_image("/home/user/images/photo.jpg")

            Note: image_path must be an absolute path to an existing image file.
            """
            return await self._view_image_async(image_path)

        @self.mcp.tool()
        async def graph_explorer_run_query() -> str:
            """Execute the configured API query in Graph Explorer.

            Returns:
                str: Success message indicating the query was executed

            This tool:
                1. Clicks the "Run query" button
                2. Waits for the request to complete
                3. Returns confirmation message

            Use this after setting up the URL, method, and request body.
            After running, use graph_explorer_get_response_body() to see results.
            """
            return await self._run_query_async()

    async def ensure_browser(self):
        """Ensure browser instance exists"""
        if not self.browser:
            self.playwright = await async_playwright().start()

            # Connect to existing browser instance (similar to reference project)
            self.browser = await self.playwright.chromium.connect_over_cdp(
                "http://localhost:9222"
            )
            logger.info("✅ Connected to existing browser")

            # Use the default context from existing browser
            self.context = self.browser.contexts[0]
            self.page = await self.context.new_page()

            logger.info("✅ Browser instance created and ready")

    async def _take_screenshot_async(
        self,
        full_page: bool,
        element_selector: Optional[str],
        save_path: Optional[str],
    ) -> str:
        """Async screenshot implementation with auto-scroll to top"""
        await self.ensure_browser()

        try:
            # Scroll to top of the page before taking screenshot for consistency
            logger.info("📜 Scrolling to top of the page...")
            await self.page.evaluate("window.scrollTo(0, 0)")

            # Wait a moment for the scroll to complete and content to settle
            await asyncio.sleep(0.5)

            if element_selector:
                # Capture specific element
                element = await self.page.wait_for_selector(
                    element_selector, timeout=10000
                )
                if not element:
                    raise Exception(f"Element not found: {element_selector}")

                # For element screenshots, scroll the element into view
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)

                # Element screenshots don't support full_page parameter
                screenshot_options = {"type": "png"}
                screenshot_data = await element.screenshot(**screenshot_options)
                logger.info(f"✅ Screenshot taken of element: {element_selector}")
            else:
                # Capture full page or viewport
                screenshot_options = {"full_page": full_page, "type": "png"}
                screenshot_data = await self.page.screenshot(**screenshot_options)
                logger.info("✅ Screenshot taken of full page/viewport")

            # Save to file if path is provided
            if save_path:
                # Convert to Path object for modern path operations
                save_path_obj = Path(save_path)

                # Create parent directories if they don't exist
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)

                # Save the screenshot to the specified path
                save_path_obj.write_bytes(screenshot_data)

                logger.info(f"✅ Screenshot saved to: {save_path_obj.absolute()}")

            # Return success message
            size_info = f"({len(screenshot_data)} bytes)"
            if save_path:
                return f"✅ Screenshot captured and saved to {save_path} {size_info}"
            else:
                return f"✅ Screenshot captured successfully {size_info}"

        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            raise Exception(f"Screenshot failed: {str(e)}")

    async def _navigate_to_graph_explorer_async(self) -> str:
        """Async navigation to Graph Explorer implementation"""
        await self.ensure_browser()

        try:
            logger.info("🔄 Navigating to Graph Explorer...")

            # Navigate to Graph Explorer and wait for page to load
            await self.page.goto(GRAPH_EXPLORER_URL, wait_until="domcontentloaded")

            # Wait a bit more for dynamic content to load
            await asyncio.sleep(3)

            # Bring page to front for human interaction
            await self.page.bring_to_front()

            # Minimize sidebar to have more space for the main content
            try:
                # Use the most precise selector to target the clickable span element
                minimize_button_selector = (
                    'button[aria-label="Minimize sidebar"] span.fui-Button__icon'
                )

                minimize_button = await self.page.wait_for_selector(
                    minimize_button_selector, timeout=3000, state="visible"
                )

                if minimize_button:
                    logger.info("✅ Found minimize sidebar button")
                    await minimize_button.click(force=True)
                    await asyncio.sleep(0.5)
                    logger.info("✅ Sidebar minimize action completed")
                else:
                    logger.warning(
                        "⚠️ Minimize sidebar button not found, continuing anyway"
                    )

            except Exception as sidebar_error:
                logger.warning(f"⚠️ Could not minimize sidebar: {sidebar_error}")

            # Get current URL to verify navigation
            current_url = self.page.url

            logger.info(f"✅ Successfully navigated to: {current_url}")
            return f"Successfully navigated to Graph Explorer: {current_url}"

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            raise Exception(f"Navigation failed: {str(e)}")

    async def _set_api_url_async(self, api_url: str) -> str:
        """Async API URL setting implementation using JavaScript injection"""
        await self.ensure_browser()

        try:
            logger.info(f"🔧 Setting API URL to: {api_url}")

            # Use JavaScript injection to set the URL directly
            # This approach bypasses focus issues and Monaco editor complications
            success = await self.page.evaluate(
                """
                (apiUrl) => {
                    // Define possible selectors for the API URL input
                    const selectors = [
                        'textarea[aria-label*="Query sample input"]',
                        'input[aria-label*="Query sample input"]',
                    ];
                    
                    let inputElement = null;
                    
                    // Try to find the input element
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            inputElement = elements[0];
                            console.log('Found input element with selector:', selector);
                            break;
                        }
                    }
                    
                    if (!inputElement) {
                        console.error('No input element found');
                        return { success: false, error: 'Input element not found' };
                    }
                    
                    try {
                        // Method 1: Direct value setting
                        inputElement.value = apiUrl;
                        
                        // Method 2: Try to trigger Monaco editor API if available
                        if (window.monaco && window.monaco.editor) {
                            const editors = window.monaco.editor.getEditors();
                            if (editors && editors.length > 0) {
                                // Find the editor that contains our input element
                                for (const editor of editors) {
                                    const editorElement = editor.getDomNode();
                                    if (editorElement && editorElement.contains(inputElement)) {
                                        editor.setValue(apiUrl);
                                        console.log('Set value via Monaco editor API');
                                        break;
                                    }
                                }
                            }
                        }
                        
                        // Method 3: Dispatch input events to notify the UI
                        inputElement.dispatchEvent(new Event('input', { bubbles: true }));
                        inputElement.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        // Method 4: Focus and blur to ensure UI updates
                        inputElement.focus();
                        inputElement.blur();
                        inputElement.focus();
                        
                        console.log('Successfully set API URL to:', apiUrl);
                        return { 
                            success: true, 
                            value: inputElement.value,
                            method: 'JavaScript injection'
                        };
                        
                    } catch (error) {
                        console.error('Error setting value:', error);
                        return { success: false, error: error.message };
                    }
                }
                """,
                api_url,
            )

            if success and success.get("success"):
                final_value = success.get("value", api_url)
                logger.info(
                    f"✅ Successfully set API URL via JavaScript injection: {final_value}"
                )
                return f"Successfully set API URL to: {final_value}"
            else:
                error_msg = (
                    success.get("error", "Unknown error")
                    if success
                    else "JavaScript evaluation failed"
                )
                logger.error(f"❌ Failed to set API URL: {error_msg}")
                raise Exception(f"Failed to set API URL: {error_msg}")

        except Exception as e:
            logger.error(f"Set URL error: {e}")
            raise Exception(f"Failed to set API URL: {str(e)}")

    async def _set_http_method_async(self, method: str) -> str:
        """Async HTTP method setting implementation"""
        await self.ensure_browser()

        try:
            # Validate method
            valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
            method = method.upper()
            if method not in valid_methods:
                raise Exception(
                    f"Invalid HTTP method: {method}. Valid methods are: {valid_methods}"
                )

            logger.info(f"🔧 Setting HTTP method to: {method}")

            # Find the HTTP method dropdown button using aria-labelledby
            dropdown_selector = 'button[aria-labelledby="http-method-dropdown"]'

            # Wait for the dropdown button to be available
            dropdown_button = await self.page.wait_for_selector(
                dropdown_selector, timeout=10000
            )
            if not dropdown_button:
                raise Exception("HTTP method dropdown button not found")

            # Click to open the dropdown
            await dropdown_button.click()

            # Wait for the dropdown menu to appear
            await asyncio.sleep(0.5)

            # Find and click the option with the desired method
            # Look for the Badge text within the dropdown options
            option_selector = f'div[role="option"] .fui-Badge:has-text("{method}")'

            # Try alternative selector if the first one doesn't work
            try:
                option_element = await self.page.wait_for_selector(
                    option_selector, timeout=3000
                )
            except:
                # Fallback: find by text content
                option_element = await self.page.wait_for_selector(
                    f'div[role="option"]:has-text("{method}")', timeout=3000
                )

            if not option_element:
                raise Exception(f"HTTP method option '{method}' not found in dropdown")

            # Click on the option
            await option_element.click()

            # Wait for the UI to update
            await asyncio.sleep(1)

            # Verify the method was set by checking the button text
            current_method = await dropdown_button.text_content()

            logger.info(f"✅ Successfully set HTTP method to: {current_method}")
            return f"Successfully set HTTP method to: {current_method}"

        except Exception as e:
            logger.error(f"Set HTTP method error: {e}")
            raise Exception(f"Failed to set HTTP method: {str(e)}")

    async def _set_request_body_async(self, body: str) -> str:
        """Async request body setting implementation"""
        await self.ensure_browser()

        try:
            logger.info(f"🔧 Setting request body content...")

            # First, click on the Request Body tab
            tab_selector = 'button[role="tab"][value="request-body"]'
            tab_button = await self.page.wait_for_selector(tab_selector, timeout=10000)
            if not tab_button:
                raise Exception("Request Body tab not found")

            # Click the Request Body tab
            await tab_button.click()
            await asyncio.sleep(1)

            # Find the Monaco editor in the REQUEST area (not response area)
            # Based on the HTML structure, the request area has id="request-area"
            # and the Monaco editor is inside it
            request_area_selector = "#request-area"
            request_area = await self.page.wait_for_selector(
                request_area_selector, timeout=5000
            )
            if not request_area:
                raise Exception("Request area not found")

            # Find the Monaco editor specifically in the request area
            # Use more specific selectors targeting the request area
            editor_selectors = [
                "#request-area #monaco-editor textarea.inputarea",
                '#request-area #monaco-editor textarea[aria-label="Editor content"]',
                "#request-area .monaco-editor textarea.inputarea",
                "#request-area textarea.inputarea",
                # Fallback: target the first Monaco editor (should be in request area)
                'div[data-keybinding-context="1"] textarea.inputarea',
            ]

            editor_element = None
            for selector in editor_selectors:
                try:
                    editor_element = await self.page.wait_for_selector(
                        selector, timeout=3000, state="visible"
                    )
                    if editor_element:
                        logger.info(f"✅ Found Monaco editor with selector: {selector}")
                        break
                except:
                    continue

            if not editor_element:
                raise Exception("Monaco editor not found in request area")

            # Focus the textarea directly
            await editor_element.focus()
            await asyncio.sleep(0.5)

            # Try to set content directly through Monaco editor API first
            try:
                # Use Monaco editor API to set content directly (bypasses autocomplete)
                content_set = await self.page.evaluate(
                    """
                    (bodyContent) => {
                        const editors = window.monaco?.editor?.getEditors();
                        if (editors && editors.length > 0) {
                            // Find the request editor (first one or by context)
                            const requestEditor = editors[0];
                            if (requestEditor) {
                                // Set content directly, bypassing autocomplete
                                requestEditor.setValue(bodyContent);
                                return true;
                            }
                        }
                        return false;
                    }
                    """,
                    body,
                )

                if content_set:
                    logger.info("✅ Content set directly through Monaco API")
                else:
                    # Fallback to keyboard input method
                    logger.info("⚠️ Monaco API not available, using keyboard input")
                    await self._set_content_via_keyboard(body)

            except Exception as monaco_error:
                logger.warning(
                    f"⚠️ Monaco API failed: {monaco_error}, using keyboard input"
                )
                await self._set_content_via_keyboard(body)

            # Wait for content to be set
            await asyncio.sleep(0.5)

            # Auto-format JSON using Monaco editor's format shortcut
            # This will properly format the JSON with correct indentation and syntax highlighting
            await self.page.keyboard.press("Shift+Alt+f")

            # Wait for formatting to complete
            await asyncio.sleep(1)

            logger.info(f"✅ Successfully set request body content")
            return f"Successfully set request body content ({len(body)} characters)"

        except Exception as e:
            logger.error(f"Set request body error: {e}")
            raise Exception(f"Failed to set request body: {str(e)}")

    async def _set_content_via_keyboard(self, body: str):
        """Set content via keyboard input with autocomplete handling"""
        try:
            # Disable autocomplete temporarily by pressing Escape first
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.2)

            # Clear existing content
            await self.page.keyboard.press("Control+a")
            await asyncio.sleep(0.3)

            # Set content character by character to avoid autocomplete issues
            # For shorter content, use regular typing
            if len(body) < 500:
                await self.page.keyboard.type(body)
            else:
                # For longer content, use clipboard to avoid timeout
                await self.page.evaluate(
                    "navigator.clipboard.writeText(arguments[0])", body
                )
                await asyncio.sleep(0.2)
                await self.page.keyboard.press("Control+v")

        except Exception as keyboard_error:
            logger.warning(f"⚠️ Keyboard input method failed: {keyboard_error}")
            # Last resort: direct textarea value setting
            await self.page.evaluate(
                """
                (bodyContent) => {
                    const textareas = document.querySelectorAll('#request-area textarea.inputarea');
                    if (textareas.length > 0) {
                        textareas[0].value = bodyContent;
                        // Trigger input event to notify Monaco
                        textareas[0].dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
                """,
                body,
            )

    async def _get_response_body_async(self) -> str:
        """Async response body retrieval implementation"""
        await self.ensure_browser()

        try:
            logger.info("📖 Getting response body content...")

            # First, click on the Response preview tab to ensure we're in the right area
            response_tab_selector = 'button[role="tab"][value="Response preview"]'
            response_tab_button = await self.page.wait_for_selector(
                response_tab_selector, timeout=10000
            )
            if not response_tab_button:
                raise Exception("Response preview tab not found")

            # Click the Response preview tab
            await response_tab_button.click()
            await asyncio.sleep(1)

            # Find the Monaco editor in the RESPONSE area
            # Based on the HTML structure, the response area has id="response-area"
            response_area_selector = "#response-area"
            response_area = await self.page.wait_for_selector(
                response_area_selector, timeout=5000
            )
            if not response_area:
                raise Exception("Response area not found")

            # Find the Monaco editor specifically in the response area
            # Use multiple selectors to find the editor
            editor_selectors = [
                "#response-area #monaco-editor textarea.inputarea",
                '#response-area #monaco-editor textarea[aria-label="Editor content"]',
                "#response-area .monaco-editor textarea.inputarea",
                "#response-area textarea.inputarea",
                # Fallback: target the second Monaco editor (should be in response area)
                'div[data-keybinding-context="2"] textarea.inputarea',
            ]

            editor_element = None
            for selector in editor_selectors:
                try:
                    editor_element = await self.page.wait_for_selector(
                        selector, timeout=3000, state="visible"
                    )
                    if editor_element:
                        logger.info(
                            f"✅ Found Monaco editor in response area with selector: {selector}"
                        )
                        break
                except:
                    continue

            if not editor_element:
                raise Exception("Monaco editor not found in response area")

            # Get the content from the editor
            # Focus the textarea first
            await editor_element.focus()
            await asyncio.sleep(0.5)

            # Select all content and copy it
            await self.page.keyboard.press("Control+a")
            await asyncio.sleep(0.5)

            # Get the selected text content
            content = await self.page.evaluate("() => window.getSelection().toString()")

            # If that doesn't work, try getting the value directly from the textarea
            if not content:
                content = await editor_element.input_value()

            # If still no content, try getting from the editor's model
            if not content:
                # Try to get content from Monaco editor's model via JavaScript
                content = await self.page.evaluate(
                    """
                    () => {
                        const editors = window.monaco?.editor?.getEditors();
                        if (editors && editors.length > 1) {
                            // Get the second editor (response area)
                            const responseEditor = editors[1];
                            return responseEditor.getValue();
                        }
                        return null;
                    }
                """
                )

            if not content:
                content = "No content found in response area"

            logger.info(
                f"✅ Successfully retrieved response body content ({len(content)} characters)"
            )
            return content.strip()

        except Exception as e:
            logger.error(f"Get response body error: {e}")
            raise Exception(f"Failed to get response body: {str(e)}")

    async def _get_response_status_async(self) -> str:
        """Async response status retrieval implementation"""
        await self.ensure_browser()

        try:
            logger.info("📊 Getting response status information...")

            # Look for the MessageBar in the request-response-area
            status_selector = "#request-response-area .fui-MessageBar"

            # Wait for the status element to be available
            status_element = await self.page.wait_for_selector(
                status_selector, timeout=5000, state="visible"
            )

            if not status_element:
                raise Exception("Status element not found")

            # Get the text content from the status element
            status_content = await status_element.text_content()

            if not status_content:
                raise Exception("Status element found but no content extracted")

            # Clean up the status content
            status_content = status_content.strip()

            logger.info(f"✅ Successfully retrieved response status: {status_content}")
            return status_content

        except Exception as e:
            logger.error(f"Get response status error: {e}")
            raise Exception(f"Failed to get response status: {str(e)}")

    async def _run_query_async(self) -> str:
        """Async query execution implementation"""
        await self.ensure_browser()

        try:
            logger.info("🚀 Running API query...")

            # Find the "Run query" button using multiple selectors
            # Based on the HTML structure, look for the button with "Run query" text
            run_button_selectors = [
                'button:has-text("Run query")',
                'button[aria-label*="Run"]',
                'button span:has-text("Run query")',
                'button:has(span:has-text("Run query"))',
                # Fallback: look for button with play icon
                'button:has(svg path[d*="M17.22 8.69"])',
            ]

            run_button = None
            for selector in run_button_selectors:
                try:
                    run_button = await self.page.wait_for_selector(
                        selector, timeout=3000, state="visible"
                    )
                    if run_button:
                        logger.info(
                            f"✅ Found Run query button with selector: {selector}"
                        )
                        break
                except:
                    continue

            if not run_button:
                raise Exception("Run query button not found")

            # Check if the button is enabled (not disabled)
            is_disabled = await run_button.is_disabled()
            if is_disabled:
                raise Exception("Run query button is disabled")

            # Click the Run query button
            await run_button.click()

            # Wait a moment for the request to be initiated
            await asyncio.sleep(2)

            # Check if there's a loading spinner (indicates request is in progress)
            try:
                spinner = await self.page.wait_for_selector(
                    'div[role="progressbar"], .fui-Spinner', timeout=1000
                )
                if spinner:
                    logger.info("📡 Request is being processed...")
                    # Wait for the spinner to disappear (request completed)
                    await self.page.wait_for_selector(
                        'div[role="progressbar"], .fui-Spinner',
                        state="hidden",
                        timeout=30000,
                    )
            except:
                # No spinner found, request might be very fast
                pass

            # Wait additional time for response to be displayed
            await asyncio.sleep(2)

            logger.info("✅ Successfully executed API query")
            return (
                "Successfully executed API query. Check the response area for results."
            )

        except Exception as e:
            logger.error(f"Run query error: {e}")
            raise Exception(f"Failed to run query: {str(e)}")

    async def _view_image_async(self, image_path: str) -> ImageContent:
        """Async image viewing implementation that returns binary image data"""
        try:
            # Validate that the image path is provided
            if not image_path:
                raise ValueError("Image path is required")

            # Convert to Path object for modern path operations
            image_path_obj = Path(image_path)

            # Validate that the path is absolute
            if not image_path_obj.is_absolute():
                raise ValueError(f"Image path must be absolute, got: {image_path}")

            # Check if file exists
            if not image_path_obj.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Check if it's a file (not a directory)
            if not image_path_obj.is_file():
                raise ValueError(f"Path is not a file: {image_path}")

            # Validate file extension (case-insensitive)
            supported_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            file_extension = image_path_obj.suffix.lower()
            
            if file_extension not in supported_extensions:
                raise ValueError(
                    f"Unsupported image format: {file_extension}. "
                    f"Supported formats: {', '.join(supported_extensions)}"
                )

            # Get file size for information
            file_size = image_path_obj.stat().st_size
            
            # Format file size in human-readable format
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            # Get MIME type
            import mimetypes
            mime_type = mimetypes.guess_type(str(image_path_obj))[0]
            if not mime_type:
                # Fallback MIME types
                mime_type_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp'
                }
                mime_type = mime_type_map.get(file_extension, 'image/png')

            # Read image binary data
            image_data = image_path_obj.read_bytes()

            logger.info(f"✅ Successfully loaded image: {image_path_obj.name} ({size_str})")
            logger.info(f"📷 MIME type: {mime_type}")

            # Return ImageContent object with binary data
            return ImageContent(
                type="image",
                data=image_data,
                mimeType=mime_type
            )

        except Exception as e:
            logger.error(f"View image error: {e}")
            raise Exception(f"Failed to view image: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up browser resources.

        This method properly closes:
        1. Browser context (tabs, cookies, etc.)
        2. Browser instance
        3. Playwright runtime

        Should be called when shutting down the server to prevent
        resource leaks and zombie processes.
        """
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def run_server(self) -> None:
        """Run the MCP server with streamable HTTP transport.

        This method:
        1. Starts the FastMCP server with HTTP transport
        2. Handles graceful shutdown on KeyboardInterrupt
        3. Performs cleanup on exit

        The server runs indefinitely until stopped by the user (Ctrl+C)
        or an unhandled exception occurs.
        """
        logger.info("🚀 Starting Graph Explorer MCP Server...")
        logger.info("🌐 Using MCP streamable HTTP transport")

        try:
            # Run with streamable HTTP transport
            self.mcp.run(transport="streamable-http")
        except KeyboardInterrupt:
            logger.info("🛑 Server stopped by user")
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
        finally:
            asyncio.run(self.cleanup())


# Create global server instance
server = GraphExplorerMCP()


def main() -> None:
    """Main entry point for the Graph Explorer MCP Server.

    This function creates and starts the server instance.

    Prerequisites:
        - Chrome browser running with remote debugging enabled on port 9222
        - Command: chrome.exe --remote-debugging-port=9222

    Usage:
        python main.py

    The server will start and expose MCP tools for Graph Explorer automation.
    """
    server.run_server()


if __name__ == "__main__":
    main()
