# Local synthetic relay

Run `python -m morrowdock_integrations.mock --port 8765` after setting
MORROWDOCK_TOKEN to a disposable local value. The implementation is in
`morrowdock_integrations/mock.py` so installed SDK users can run it too.
It binds loopback, has no outbound calls, uses the contract validators, and keeps
all items, requests and uploaded bytes in memory. See the root quick start and
[REST reference](../contract/REST.md). Never use it for real learner data.
