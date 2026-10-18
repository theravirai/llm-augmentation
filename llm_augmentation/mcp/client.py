import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

class McpClient:
    """
    Subprocess client for SootUpMcpServer implementing JSON-RPC 2.0 over standard I/O.
    """

    def __init__(self, sootup_engine_dir: str | Path, default_target_dir: str | Path | None = None):
        self.engine_dir = Path(sootup_engine_dir).resolve()
        self.default_target_dir = str(Path(default_target_dir).resolve()) if default_target_dir else ""
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._start_server()

    def _start_server(self):
        classpath_file = self.engine_dir / "classpath.txt"
        classes_dir = self.engine_dir / "target" / "classes"

        if not classes_dir.exists():
            # Build engine if not built yet
            subprocess.run(["mvn", "clean", "compile", "-q"], cwd=self.engine_dir, check=True)

        if not classpath_file.exists():
            subprocess.run(
                ["mvn", "dependency:build-classpath", f"-Dmdep.outputFile={classpath_file}", "-q"],
                cwd=self.engine_dir,
                check=True
            )

        with open(classpath_file, "r", encoding="utf-8") as f:
            deps_cp = f.read().strip()

        full_cp = f"{classes_dir}:{deps_cp}"
        cmd = ["java", "-cp", full_cp, "org.sootup.analyzer.SootUpMcpServer"]
        if self.default_target_dir:
            cmd.append(self.default_target_dir)

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.engine_dir
        )

        # Handshake initialize
        self._initialize()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("SootUp MCP Server process is not running.")

        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method
        }
        if params is not None:
            payload["params"] = params

        line = json.dumps(payload) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()

        # Read response line
        resp_line = self.process.stdout.readline()
        if not resp_line:
            stderr_out = self.process.stderr.read()
            raise RuntimeError(f"SootUp MCP Server closed stream unexpectedly. Stderr: {stderr_out}")

        resp = json.loads(resp_line.strip())
        if "error" in resp:
            raise RuntimeError(f"MCP RPC Error ({resp['error'].get('code')}): {resp['error'].get('message')}")

        return resp.get("result", {})

    def _initialize(self):
        init_params = {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "llm-augmentation-client",
                "version": "1.0.0"
            }
        }
        if self.default_target_dir:
            init_params["initializationOptions"] = {
                "target_dir": self.default_target_dir
            }

        res = self._send_request("initialize", init_params)

        # Send notifications/initialized (one-way notification)
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self.process.stdin.write(json.dumps(notif) + "\n")
        self.process.stdin.flush()

    def list_tools(self) -> List[Dict[str, Any]]:
        res = self._send_request("tools/list")
        return res.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Calls a SootUp static analysis tool.
        Returns the formatted string response from the static analyzer.
        """
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        res = self._send_request("tools/call", params)
        content = res.get("content", [])
        if content and isinstance(content, list):
            text_items = [item.get("text", "") for item in content if item.get("type") == "text"]
            return "\n".join(text_items)
        return str(res)

    def close(self):
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            finally:
                self.process = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
