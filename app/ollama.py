"""HTTP client for one configured, private Ollama runtime."""
import http.client
import ipaddress
import json
import os
import re
import socket
from urllib.parse import urlsplit


class LocalInferenceError(RuntimeError):
    pass


NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7",
))


def address_for(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    for _, _, _, _, address in addresses:
        ip = ipaddress.ip_address(address[0])
        if any(ip in network for network in NETWORKS):
            return str(ip)
    raise LocalInferenceError("Configure a private Ollama address.")


class Ollama:
    def __init__(self):
        self.model = os.environ.get("AI_MODEL", "qwen3.5:0.8b")
        origin = urlsplit(os.environ.get("AI_BASE_URL", "http://ollama:11434"))
        self.keep_alive = os.environ.get("AI_KEEP_ALIVE", "2m")
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,100}", self.model) or "cloud" in self.model.lower():
            raise LocalInferenceError("Choose a locally installed Ollama model.")
        if not re.fullmatch(r"0|[1-9][0-9]{0,3}[smh]", self.keep_alive):
            raise LocalInferenceError("Choose a valid Ollama keep-alive duration.")
        if (origin.scheme != "http" or not origin.hostname or origin.username or origin.password
                or origin.path not in ("", "/") or origin.query or origin.fragment):
            raise LocalInferenceError("Configure a private HTTP address for Ollama.")
        self.host, self.port = origin.hostname, origin.port or 11434

    def request(self, path, data):
        connection = None
        try:
            address = address_for(self.host, self.port)
            connection = http.client.HTTPConnection(address, self.port, timeout=100)
            host_header = f"[{self.host}]" if ":" in self.host else self.host
            connection.request("POST", path, json.dumps(data).encode(),
                               {"Content-Type": "application/json", "Host": f"{host_header}:{self.port}"})
            response = connection.getresponse()
            raw = response.read(96_001)
            if response.status != 200 or len(raw) > 96_000:
                raise LocalInferenceError("The private Ollama service could not complete the request.")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise LocalInferenceError("Ollama returned an invalid response.")
            return parsed
        except (OSError, ValueError, http.client.HTTPException):
            raise LocalInferenceError("The private Ollama service is unavailable.") from None
        finally:
            if connection:
                connection.close()

    def generate(self, schema, instructions, text, image=None):
        model = self.request("/api/show", {"model": self.model})
        info = model.get("model_info") or {}
        if not info or model.get("remote_host") or model.get("remote_model"):
            raise LocalInferenceError("Install the selected model in the private Ollama service.")
        user = {"role": "user", "content": text}
        if image:
            user["images"] = [image]
        response = self.request("/api/chat", {
            "model": self.model, "think": False, "stream": False, "keep_alive": self.keep_alive,
            "format": schema, "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 800, "num_thread": 2},
            "messages": [{"role": "system", "content": instructions}, user],
        })
        if response.get("done_reason") == "length":
            raise LocalInferenceError("The local model output reached its limit.")
        try:
            return response["message"]["content"]
        except (TypeError, KeyError):
            raise LocalInferenceError("The private Ollama service returned an invalid response.") from None
