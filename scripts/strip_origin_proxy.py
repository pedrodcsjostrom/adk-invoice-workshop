"""Make the deployed developer UI loadable in a browser.

Cloud Run's front door refuses any authenticated request that carries a
cross-origin `Origin` header, answering `403 Forbidden: origin not allowed`
before the container sees it. The ADK developer UI is an Angular app whose
bundles are ES module scripts, and module scripts always send `Origin`, so
every bundle is refused and the page renders styled and blank. See
docs/research/cloud-run-origin-403.md for the evidence.

`gcloud run services proxy` is not the problem: it attaches the identity
token either way. The one thing missing is the deletion of that header.

Chain this in front of the proxy and browse the shim instead:

    gcloud run services proxy invoice-agent --region europe-west1 --port 8080
    python scripts/strip_origin_proxy.py          # then open localhost:8090

It rewrites bytes rather than parsing requests, so server-sent events, file
uploads and the streaming chat all pass through untouched.
"""

import asyncio
import re

UP_HOST, UP_PORT = "127.0.0.1", 8080
BIND_HOST, BIND_PORT = "127.0.0.1", 8090

ORIGIN = re.compile(rb"^Origin:[^\r\n]*\r\n", re.MULTILINE | re.IGNORECASE)


async def pump(reader, writer, scrub):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            if scrub:
                data = ORIGIN.sub(b"", data)
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(client_reader, client_writer):
    try:
        up_reader, up_writer = await asyncio.open_connection(UP_HOST, UP_PORT)
    except Exception:
        client_writer.close()
        return
    await asyncio.gather(
        pump(client_reader, up_writer, True),
        pump(up_reader, client_writer, False),
    )


async def main():
    server = await asyncio.start_server(handle, BIND_HOST, BIND_PORT)
    print(
        f"http://{BIND_HOST}:{BIND_PORT} proxies to http://{UP_HOST}:{UP_PORT}, "
        "Origin removed"
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
