import asyncio
import unittest
from typing import Any

from app.main import app


class OpenApiDocsTests(unittest.TestCase):
    async def _asgi_get(self, path: str) -> tuple[int, bytes]:
        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("test-client", 50000),
            "server": ("test-server", 80),
            "root_path": "",
        }
        messages: list[dict[str, Any]] = []
        request_sent = False

        async def receive() -> dict[str, Any]:
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        await app(scope, receive, send)

        status = next(
            message["status"]
            for message in messages
            if message["type"] == "http.response.start"
        )
        body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return status, body

    def test_swagger_ui_is_exposed_in_api_docs(self) -> None:
        status, body = asyncio.run(self._asgi_get("/api-docs"))

        self.assertEqual(status, 200)
        self.assertIn(b"swagger", body.lower())
        self.assertEqual(app.docs_url, "/api-docs")
        self.assertEqual(app.openapi_url, "/api-docs/openapi.json")

    def test_endpoint_and_parameters_are_generated_automatically(self) -> None:
        schema = app.openapi()
        self.assertIn("/items", schema["paths"])

        items_get = schema["paths"]["/items"]["get"]
        parameters = {parameter["name"]: parameter for parameter in items_get["parameters"]}

        self.assertIn("category", parameters)
        self.assertEqual(parameters["category"]["in"], "query")

        self.assertIn("limit", parameters)
        self.assertEqual(parameters["limit"]["in"], "query")


if __name__ == "__main__":
    unittest.main()
