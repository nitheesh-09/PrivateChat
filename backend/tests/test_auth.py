import pytest


def test_registration_with_username_and_password(client):
    """1. Registration with username + password ONLY (no email)."""
    resp = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "user" in data
    user = data["user"]
    assert user["username"] == "alice"
    assert "id" in user
    assert "created_at" in user
    assert "last_seen" in user
    # Verify no email field exists in user model or response
    assert "email" not in user
    assert "access_token" in resp.cookies


def test_successful_login_with_username_and_password(client):
    """2. Successful login with username + password."""
    # Register user first
    reg_resp = client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "securepassword123"},
    )
    assert reg_resp.status_code == 201

    # Clear cookies to simulate fresh session
    client.cookies.clear()

    # Login
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "securepassword123"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["user"]["username"] == "bob"
    assert "access_token" in login_resp.cookies


def test_duplicate_username_rejection(client):
    """3. Duplicate username rejection with exact required error message."""
    client.post(
        "/api/auth/register",
        json={"username": "charlie", "password": "password123"},
    )
    # Attempt duplicate
    dup_resp = client.post(
        "/api/auth/register",
        json={"username": "charlie", "password": "different_password"},
    )
    assert dup_resp.status_code == 400
    assert dup_resp.json()["detail"] == "Username already exists. Please choose another username."


def test_case_insensitive_duplicate_username_rejection(client):
    """4. Case-insensitive duplicate username rejection (Alice vs alice vs ALICE)."""
    # Register Alice
    r1 = client.post(
        "/api/auth/register",
        json={"username": "Alice", "password": "password123"},
    )
    assert r1.status_code == 201

    # Attempt to register lowercase alice
    r2 = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password456"},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"] == "Username already exists. Please choose another username."

    # Attempt to register uppercase ALICE
    r3 = client.post(
        "/api/auth/register",
        json={"username": "ALICE", "password": "password789"},
    )
    assert r3.status_code == 400
    assert r3.json()["detail"] == "Username already exists. Please choose another username."

    # Verify login works case-insensitively with correct password
    client.cookies.clear()
    login_case = client.post(
        "/api/auth/login",
        json={"username": "ALICE", "password": "password123"},
    )
    assert login_case.status_code == 200
    assert login_case.json()["user"]["username"] == "alice"


def test_invalid_login(client):
    """5. Invalid login returns generic error without leaking username existence."""
    client.post(
        "/api/auth/register",
        json={"username": "david", "password": "correct_password"},
    )

    # 1. Non-existent user
    resp_nonexistent = client.post(
        "/api/auth/login",
        json={"username": "ghost_user", "password": "somepassword"},
    )
    assert resp_nonexistent.status_code == 401
    assert resp_nonexistent.json()["detail"] == "Invalid username or password."

    # 2. Existing user with wrong password
    resp_wrong_pass = client.post(
        "/api/auth/login",
        json={"username": "david", "password": "wrong_password"},
    )
    assert resp_wrong_pass.status_code == 401
    assert resp_wrong_pass.json()["detail"] == "Invalid username or password."

    # Assert exact same error message to avoid user enumeration
    assert resp_nonexistent.json()["detail"] == resp_wrong_pass.json()["detail"]


def test_protected_routes(client):
    """6. Protected routes reject unauthorized requests without valid JWT cookie."""
    client.cookies.clear()

    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 401

    users_resp = client.get("/api/users")
    assert users_resp.status_code == 401

    conv_resp = client.get("/api/conversations")
    assert conv_resp.status_code == 401

    direct_resp = client.post("/api/conversations/direct", json={"user_id": "dummy-id"})
    assert direct_resp.status_code == 401


def test_logout(client):
    """7. Logout clears authentication cookie and invalidates session access."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"username": "elena", "password": "password123"},
    )

    # Authenticated me should succeed
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["username"] == "elena"

    # Logout
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully."

    # Clear cookie from test client to reflect browser deletion behavior
    client.cookies.clear()
    unauth_resp = client.get("/api/auth/me")
    assert unauth_resp.status_code == 401


def test_users_list_and_search_normalized(client):
    """Search registered users using normalized case-insensitive logic."""
    client.post("/api/auth/register", json={"username": "rahul", "password": "password123"})
    client.post("/api/auth/register", json={"username": "priya", "password": "password123"})

    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "priya", "password": "password123"})

    # Search with uppercase or mixed case
    search_resp = client.get("/api/users/search?q=RAHUL")
    assert search_resp.status_code == 200
    users = search_resp.json()
    assert len(users) == 1
    assert users[0]["username"] == "rahul"


def test_authenticated_user_can_retrieve_other_users_and_self_is_excluded(client):
    """
    Symmetric discovery test:
    - User1 registers, User2 registers.
    - User1 discovers User2 (User1 excluded).
    - User2 discovers User1 (User2 excluded).
    """
    client.post("/api/auth/register", json={"username": "user1", "password": "password123"})
    client.post("/api/auth/register", json={"username": "user2", "password": "password123"})

    # 1. Login as user1
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "user1", "password": "password123"})

    resp1 = client.get("/api/users")
    assert resp1.status_code == 200
    users_for_1 = [u["username"] for u in resp1.json()]
    assert "user2" in users_for_1
    assert "user1" not in users_for_1

    # Verify no-cache headers
    assert "no-store" in resp1.headers.get("Cache-Control", "")

    # 2. Login as user2
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "user2", "password": "password123"})

    resp2 = client.get("/api/users")
    assert resp2.status_code == 200
    users_for_2 = [u["username"] for u in resp2.json()]
    assert "user1" in users_for_2
    assert "user2" not in users_for_2


def test_three_users_discovery(client):
    """
    Test with 3+ users:
    - A third user can discover User1 and User2, but not themselves.
    """
    client.post("/api/auth/register", json={"username": "alpha", "password": "password123"})
    client.post("/api/auth/register", json={"username": "beta", "password": "password123"})
    client.post("/api/auth/register", json={"username": "gamma", "password": "password123"})

    # Login as gamma
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "gamma", "password": "password123"})

    resp = client.get("/api/users")
    assert resp.status_code == 200
    discovered = [u["username"] for u in resp.json()]
    assert "alpha" in discovered
    assert "beta" in discovered
    assert "gamma" not in discovered

    # Search for alpha
    search_alpha = client.get("/api/users/search?q=alpha")
    assert search_alpha.status_code == 200
    assert len(search_alpha.json()) == 1
    assert search_alpha.json()[0]["username"] == "alpha"

    # Search for self should return empty list
    search_self = client.get("/api/users/search?q=gamma")
    assert search_self.status_code == 200
    assert len(search_self.json()) == 0


def test_unauthenticated_user_cannot_retrieve_or_search_users(client):
    """Unauthenticated users cannot retrieve or search users."""
    client.cookies.clear()

    resp_list = client.get("/api/users")
    assert resp_list.status_code == 401

    resp_search = client.get("/api/users/search?q=test")
    assert resp_search.status_code == 401

