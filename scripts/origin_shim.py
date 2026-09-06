"""The Origin shim: the one command that opens your deployed service.

Cloud Run's front door refuses any authenticated request carrying an `Origin`
header the service did not issue, answering `403 Forbidden: origin not allowed`
before the container ever sees it. A browser attaches that header to every
request that is not a plain page load, including a same-origin form post, so
an upload from the deployed page dies at the front door. `gcloud run services
proxy` is not the problem — it signs each request either way — and the one
thing missing is the deletion of that header. The evidence and the diagnoses
that were rejected on the way are in docs/research/cloud-run-origin-403.md,
and the decision to treat this as the way in rather than as a workaround is
ADR-0004.

Run it and open the URL it prints:

    python scripts/origin_shim.py

That is the whole of it. Behind that one line the shim starts the proxy as a
child process on a port of its own, listens on the port you browse, deletes
`Origin` from everything on the way through, and takes the proxy down with it
when you press Ctrl-C. It used to be two terminals and a second port number,
which is a poor thing to ask of a room of sixty during a dead window (#61).

It rewrites bytes rather than parsing requests, so server-sent events, file
uploads and the streaming chat all pass through untouched.

Everything is overridable, by flag or by environment variable, but the
defaults are what this kit deploys:

    python scripts/origin_shim.py --service invoice-agent \\
        --region europe-west1 --project my-project --port 8080
"""

import argparse
import asyncio
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

# Read out of infra/variables.tf, where the Terraform every attendee applies
# declares the same two defaults.
DEFAULT_SERVICE = "invoice-agent"
DEFAULT_REGION = "europe-west1"

# The port the attendee opens. 8080 because that is the port every other
# document in the kit already tells them to browse.
DEFAULT_PORT = 8080

# How long the proxy gets to come up before we decide something is wrong. It
# resolves the service and mints a token first, so it is not instant.
PROXY_START_TIMEOUT = 30.0

ORIGIN = re.compile(rb"^Origin:[^\r\n]*\r\n", re.MULTILINE | re.IGNORECASE)


class Unusable(Exception):
    """A precondition failed in a way the person running this can act on.

    Carried as an exception only so the checks can be written top to bottom.
    It is printed as a plain sentence and never as a traceback: an attendee
    reading a stack trace during a dead window is a segment going late (#61).
    """


# ------------------------------------------------------------ the stripping --


async def pump(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    strip_origin: bool,
) -> None:
    """Copy one direction of a connection, deleting `Origin` on the way out.

    Bytes rather than parsed requests, which is why file uploads, server-sent
    events and anything else the page sends survive a rewrite that only ever
    removes one header line.

    Every failure here is a connection ending, which is what a browser does all
    day: a tab closed mid-request, a reload, a keep-alive timing out. There is
    nothing to report and nobody to report it to, so both directions are closed
    and the shim carries on serving the next one.
    """
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            if strip_origin:
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


async def handle(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_port: int,
) -> None:
    """One browser connection, joined to one connection to the proxy.

    Only the browser's half is stripped. What comes back has no `Origin` on it
    to remove, and rewriting a response would risk the one thing this script
    promises not to touch.
    """
    try:
        up_reader, up_writer = await asyncio.open_connection(
            "127.0.0.1", upstream_port
        )
    except Exception:
        # The proxy is gone or still coming up. Drop this connection rather
        # than the shim; the browser will show a failed request, which is a
        # truer signal than a hang.
        client_writer.close()
        return
    await asyncio.gather(
        pump(client_reader, up_writer, strip_origin=True),
        pump(up_reader, client_writer, strip_origin=False),
    )


# --------------------------------------------------------------- the checks --


def check_proxy_binary(gcloud):
    """Refuse to start when the proxy this depends on is not installed.

    `cloud-run-proxy` is a separate gcloud component and a stock install does
    not have it, which is why the pre-flight checks for it the day before. It
    is checked again here because the day before is not when people read the
    report.
    """
    if shutil.which(gcloud) is None:
        raise Unusable(
            f"'{gcloud}' is not on your PATH, so there is no proxy to run. "
            "Install the Google Cloud SDK: "
            "https://docs.cloud.google.com/sdk/docs/install"
        )

    sdk_root = run_gcloud(
        [gcloud, "info", "--format=value(installation.sdk_root)"]
    )
    if sdk_root and os.path.exists(os.path.join(sdk_root, "bin", "cloud-run-proxy")):
        return
    components = run_gcloud(
        [gcloud, "components", "list", "--only-local-state", "--format=value(id)"]
    )
    if components is not None and "cloud-run-proxy" in components.split():
        return
    if components is None and not sdk_root:
        # gcloud would not answer either question. That is odd but it is not
        # proof the component is missing, and guessing wrong here would stop
        # someone whose proxy works fine. Let the proxy speak for itself.
        return

    raise Unusable(
        "The cloud-run-proxy component is not installed, and it is what "
        "reaches your private service. Install it with: "
        "gcloud components install cloud-run-proxy   (on an apt gcloud: "
        "sudo apt-get install google-cloud-cli-cloud-run-proxy)"
    )


def check_service(gcloud, service, region, project):
    """Refuse to start when there is nothing at the other end.

    The proxy's own message for a service that is not there is a wall of
    gcloud error, and the usual causes are mundane: the deploy has not
    finished, or the wrong project is selected.
    """
    command = [
        gcloud,
        "run",
        "services",
        "describe",
        service,
        f"--region={region}",
        "--format=value(status.url)",
    ]
    if project:
        command.append(f"--project={project}")
    if run_gcloud(command):
        return

    named = f"'{service}' in {region}"
    if project:
        named += f" of project {project}"
    raise Unusable(
        f"There is no Cloud Run service {named}, or you cannot see it. "
        "Check that your deploy finished and that the right project is "
        "selected (gcloud config get-value project), or name the service "
        "with --service, --region and --project."
    )


def run_gcloud(command):
    """One gcloud call, answered with its stdout, or None when it failed.

    Every check here would rather carry on than crash, so nothing in this
    file ever sees a CalledProcessError.
    """
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip()


# ---------------------------------------------------------------- the child --


def free_port():
    """A port nobody is using, for the proxy to listen on.

    The proxy's port is an implementation detail now that there is one
    command, and asking the OS for a free one means a second shim, an `adk
    web`, or anything else already running cannot collide with it.
    """
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_proxy(gcloud, service, region, project, port):
    """Start `gcloud run services proxy` and wait until it answers.

    It is given its own session so that taking it down takes down everything
    it spawned. gcloud is a shell script that execs a Python that execs the
    proxy, and terminating only the process we hold leaves the real proxy
    holding the port — an orphan the next run then collides with (#61).
    """
    command = [
        gcloud,
        "run",
        "services",
        "proxy",
        service,
        f"--region={region}",
        f"--port={port}",
    ]
    if project:
        command.append(f"--project={project}")

    try:
        child = subprocess.Popen(command, start_new_session=True)
    except OSError as error:
        raise Unusable(f"Could not start '{gcloud}': {error}") from None

    waited = 0.0
    while waited < PROXY_START_TIMEOUT:
        if child.poll() is not None:
            raise Unusable(
                "The proxy stopped before it was listening. Its own message "
                "is above this line. Most often that is an expired login: "
                "gcloud auth login"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return child
        except OSError:
            pass
        waited += 0.25
        time.sleep(0.25)

    stop_proxy(child)
    raise Unusable(
        f"The proxy did not start listening within {PROXY_START_TIMEOUT:.0f} "
        "seconds. Try running it on its own to see what it says: "
        f"{' '.join(command)}"
    )


def stop_proxy(child):
    """Take the proxy down, and everything it started with it."""
    if child.poll() is not None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(child.pid), sig)
        except OSError:
            return
        try:
            child.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


# ----------------------------------------------------------------- the shim --


async def serve(bind_port, upstream_port):
    """Listen until a signal arrives, then return so the child can be stopped.

    Ctrl-C and a `kill` are handled the same way and both unwind through the
    caller's `finally`, because "leaves no orphaned process" is an acceptance
    criterion and not a best effort.
    """
    server = await asyncio.start_server(
        lambda reader, writer: handle(reader, writer, upstream_port),
        "127.0.0.1",
        bind_port,
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    print(f"Open http://127.0.0.1:{bind_port}", flush=True)
    print("Ctrl-C to stop. This also stops the proxy it started.", flush=True)
    async with server:
        await stop.wait()


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="origin_shim.py",
        description=(
            "The Origin shim: run the Cloud Run proxy, delete the Origin "
            "header Cloud Run refuses, and print the URL to open."
        ),
    )
    parser.add_argument(
        "--service",
        default=os.environ.get("SERVICE", DEFAULT_SERVICE),
        help="Cloud Run service to reach (env SERVICE, default %(default)s)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("REGION", DEFAULT_REGION),
        help="region it is deployed in (env REGION, default %(default)s)",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("PROJECT", ""),
        help="project it lives in (env PROJECT, default: whichever project "
        "gcloud is set to)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", DEFAULT_PORT)),
        help="port to open in the browser (env PORT, default %(default)s)",
    )
    # Hidden, because an attendee has no reason to change it and the help is
    # read under time pressure. It exists so the failure paths above can be
    # exercised against a stand-in, which is the only way this script gets
    # tried without a live Cloud Run service.
    parser.add_argument(
        "--gcloud",
        default=os.environ.get("GCLOUD", "gcloud"),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        check_proxy_binary(args.gcloud)
        check_service(args.gcloud, args.service, args.region, args.project)
        proxy_port = free_port()
        child = start_proxy(
            args.gcloud, args.service, args.region, args.project, proxy_port
        )
    except Unusable as problem:
        print(problem, file=sys.stderr)
        return 1

    try:
        asyncio.run(serve(args.port, proxy_port))
    except OSError as error:
        # Almost always "address already in use", which needs the port named.
        print(
            f"Could not listen on port {args.port}: {error}. Something else "
            "is using it — stop it, or pass --port with another number.",
            file=sys.stderr,
        )
        return 1
    finally:
        stop_proxy(child)
    return 0


if __name__ == "__main__":
    sys.exit(main())
