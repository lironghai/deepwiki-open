import json
import subprocess
import logging
import asyncio
import os
import platform

logger = logging.getLogger(__name__)

class GraphRetriever:
    """
    Interacts with GitNexus MCP server to retrieve graph-based insights.
    Uses stdio transport to communicate with the `gitnexus mcp` process.
    """
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._message_id = 1
        
        async def _call_mcp_tool(self, tool_name: str, arguments: dict):
        """
        Start the gitnexus mcp process, send a single JSON-RPC tool call, and return the result.
        """
        import shutil
        gitnexus_cmd = "gitnexus" if shutil.which("gitnexus") else "npx"
        if platform.system() == "Windows":
            gitnexus_cmd = "gitnexus.cmd" if shutil.which("gitnexus.cmd") else "npx.cmd"
        
        cmd = [gitnexus_cmd]
        if "npx" in gitnexus_cmd:
            cmd.extend(["-y", "gitnexus"])
        cmd.append("mcp")

        try:
            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.repo_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Prepare initialize request
            init_req = {
                "jsonrpc": "2.0",
                "id": self._message_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "deepwiki-client",
                        "version": "1.0.0"
                    }
                }
            }
            self._message_id += 1
            
            # Send initialize
            process.stdin.write(json.dumps(init_req).encode('utf-8') + b'\n')
            await process.stdin.drain()
            
            # Read initialize response
            init_res_line = await process.stdout.readline()
            if not init_res_line:
                stderr_output = await process.stderr.read()
                logger.error(f"GitNexus MCP failed to start. stderr: {stderr_output.decode('utf-8')}")
                return None
                
            # Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            process.stdin.write(json.dumps(initialized_notif).encode('utf-8') + b'\n')
            await process.stdin.drain()
            
            # Prepare tool call request
            tool_req = {
                "jsonrpc": "2.0",
                "id": self._message_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            self._message_id += 1
            
            # Send tool call
            process.stdin.write(json.dumps(tool_req).encode('utf-8') + b'\n')
            await process.stdin.drain()
            
            # Read tool response
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                try:
                    response = json.loads(line.decode('utf-8'))
                    if "id" in response and response["id"] == tool_req["id"]:
                        # Close the process gracefully
                        process.stdin.close()
                        await process.wait()
                        
                        if "error" in response:
                            logger.error(f"GitNexus tool {tool_name} error: {response['error']}")
                            return None
                            
                        # Parse the MCP tool response content
                        content = response.get("result", {}).get("content", [])
                        if content and len(content) > 0 and content[0].get("type") == "text":
                            return content[0].get("text")
                        return None
                except json.JSONDecodeError:
                    continue
            
            process.stdin.close()
            await process.wait()
            return None
            
        except Exception as e:
            logger.error(f"Error executing GitNexus MCP tool {tool_name}: {e}")
            return None

    async def query_context(self, query_text: str) -> str:
        """
        Use GitNexus 'query' tool to perform a process-grouped hybrid search.
        """
        logger.info(f"Querying GitNexus graph for: {query_text}")
        result = await self._call_mcp_tool("query", {"query": query_text})
        return result
        
    async def get_impact(self, target: str, direction: str = "upstream") -> str:
        """
        Use GitNexus 'impact' tool to analyze blast radius.
        """
        logger.info(f"Getting GitNexus impact for: {target}")
        result = await self._call_mcp_tool("impact", {
            "target": target, 
            "direction": direction,
            "minConfidence": 0.8
        })
        return result
