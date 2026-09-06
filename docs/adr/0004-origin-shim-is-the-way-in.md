# Reaching the deployed service goes through the Origin shim

Cloud Run's front door refuses any authenticated request carrying an `Origin`
header the service did not issue, answering `403 Forbidden: origin not allowed`
before the container sees it. Browsers attach that header to every request that
is not a plain page load, including a same-origin form post. Measured against
the live service: a POST with no `Origin` reaches the container, the same POST
with `Origin: http://localhost:8080` is refused. So an upload page served from
Cloud Run renders and then fails on its first upload.

The service cannot simply be made public. Domain restricted sharing blocks an
`allUsers` invoker binding for corporate attendees, which is why
`gcloud run services proxy` is in the path at all, and that proxy passes
`Origin` through untouched. The supported way in is therefore one command that
runs the proxy and deletes that one header, and the workshop documents it as
the way in rather than as a workaround.

Evidence and the rejected diagnoses are in
[`docs/research/cloud-run-origin-403.md`](../research/cloud-run-origin-403.md).
