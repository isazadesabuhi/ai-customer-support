import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pytest

from support.models import Customer

from . import postgres_account_tests

pytestmark = postgres_account_tests


@pytest.mark.django_db(transaction=True)
def test_browser_session_over_http(live_server, agent):
    _, credentials = agent
    customer = Customer.objects.create(
        name="HTTP Test Customer", email="http-test@example.test"
    )
    cookies = CookieJar()
    browser = build_opener(HTTPCookieProcessor(cookies))

    def send(path, data=None, csrf=None):
        headers = {"Origin": "http://localhost:3000"}
        if csrf:
            headers["X-CSRFToken"] = csrf
        if data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode()
        request = Request(f"{live_server.url}/api{path}", data=data, headers=headers)
        try:
            response = browser.open(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            return response.status, json.loads(body) if body else None

    code, bootstrap = send("/auth/csrf/")
    assert code == 200
    assert send("/auth/login/", credentials, bootstrap["csrfToken"])[0] == 200
    assert send("/auth/me/")[1]["role"] == "support_agent"
    assert send("/conversations/")[0] == 200
    payload = {"customer_id": str(customer.pk), "subject": "Live HTTP verification"}
    assert send("/conversations/", payload)[0] == 403
    csrf = send("/auth/csrf/")[1]["csrfToken"]
    assert send("/conversations/", payload, csrf)[0] == 201

    old_session = next(cookie.value for cookie in cookies if cookie.name == "sessionid")
    assert send("/auth/logout/", {}, csrf) == (204, None)
    assert send("/auth/me/")[0] == 403
    replay = Request(
        f"{live_server.url}/api/auth/me/",
        headers={"Cookie": f"sessionid={old_session}"},
    )
    with pytest.raises(HTTPError) as error:
        build_opener().open(replay, timeout=5)
    assert error.value.code == 403
    error.value.close()
