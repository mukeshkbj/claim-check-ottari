from starlette.requests import Request

import app


def _req(headers, peer=("10.0.0.1", 1234)):
    return Request({"type": "http", "headers": [(k.encode(), v.encode()) for k, v in headers.items()], "client": peer})


def test_client_ip_ignores_forged_forwarded_for():
    # Shape measured on Render: client-supplied entries first, then the visitor, Cloudflare and Render's LB
    r = _req({"x-forwarded-for": "9.9.9.9, 77.1.2.3, 104.22.160.30, 10.194.248.142", "cf-connecting-ip": "77.1.2.3"})
    assert app._client_ip(r) == "77.1.2.3"


def test_client_ip_falls_back_to_socket_locally():
    assert app._client_ip(_req({})) == "10.0.0.1"


def test_rate_limit_is_per_visitor():
    app._hits.clear()
    for _ in range(app.RATE_PER_HOUR):
        assert not app._rate_limited("1.2.3.4")
    assert app._rate_limited("1.2.3.4")
    assert not app._rate_limited("5.6.7.8")
