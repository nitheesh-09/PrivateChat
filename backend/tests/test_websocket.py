import pytest
from starlette.websockets import WebSocketDisconnect
from app.auth.security import create_access_token


def test_websocket_unauthorized_rejection(client):
    """Test that unauthenticated WebSocket connections are closed."""
    with pytest.raises((WebSocketDisconnect, Exception)):
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()


def receive_event_of_type(ws, target_type: str, max_tries: int = 5):
    for _ in range(max_tries):
        evt = ws.receive_json()
        if evt.get("type") == target_type:
            return evt
    raise TimeoutError(f"Did not receive event of type {target_type}")


def test_websocket_group_broadcast_and_receipts(client):
    """Test real-time message broadcasting to all members of a group."""
    # Register 3 users: Alice, Bob, Charlie
    r_alice = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    alice_id = r_alice.json()["user"]["id"]

    r_bob = client.post("/api/auth/register", json={"username": "bob", "password": "password456"})
    bob_id = r_bob.json()["user"]["id"]

    r_charlie = client.post("/api/auth/register", json={"username": "charlie", "password": "password789"})
    charlie_id = r_charlie.json()["user"]["id"]

    # Alice creates a group with Bob and Charlie
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    group_resp = client.post(
        "/api/conversations/group",
        json={"name": "Dev Team", "member_ids": [bob_id, charlie_id]},
    )
    group_id = group_resp.json()["id"]

    client.cookies.clear()
    alice_token = create_access_token(alice_id)
    bob_token = create_access_token(bob_id)
    charlie_token = create_access_token(charlie_id)

    # 1. Alice, Bob, and Charlie connect via WebSockets
    with client.websocket_connect(f"/ws/chat?token={bob_token}") as ws_bob:
        with client.websocket_connect(f"/ws/chat?token={charlie_token}") as ws_charlie:
            with client.websocket_connect(f"/ws/chat?token={alice_token}") as ws_alice:

                # Ping test
                ws_alice.send_json({"type": "ping"})
                assert ws_alice.receive_json()["type"] == "pong"

                # 2. Alice sends a group message
                ws_alice.send_json({
                    "type": "send_message",
                    "conversation_id": group_id,
                    "content": "Sprint kickoff meeting starting now!",
                })

                # Alice receives confirmation
                alice_event = receive_event_of_type(ws_alice, "new_message")
                assert alice_event["message"]["content"] == "Sprint kickoff meeting starting now!"
                assert alice_event["message"]["sender_username"] == "alice"
                msg_id = alice_event["message"]["id"]

                # Bob receives the group message in real time
                bob_event = receive_event_of_type(ws_bob, "new_message")
                assert bob_event["message"]["id"] == msg_id
                assert bob_event["message"]["content"] == "Sprint kickoff meeting starting now!"
                assert bob_event["message"]["sender_username"] == "alice"

                # Charlie also receives the group message in real time
                charlie_event = receive_event_of_type(ws_charlie, "new_message")
                assert charlie_event["message"]["id"] == msg_id
                assert charlie_event["message"]["content"] == "Sprint kickoff meeting starting now!"
                assert charlie_event["message"]["sender_username"] == "alice"

                # 3. Bob marks message as read
                ws_bob.send_json({
                    "type": "mark_read",
                    "conversation_id": group_id,
                    "message_ids": [msg_id],
                })

                # Alice receives read receipt
                alice_read_receipt = receive_event_of_type(ws_alice, "messages_read")
                assert msg_id in alice_read_receipt["message_ids"]


def test_websocket_non_member_cannot_send_to_conversation(client):
    """Test that a non-member cannot post messages to a private conversation."""
    r_alice = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    alice_id = r_alice.json()["user"]["id"]
    r_bob = client.post("/api/auth/register", json={"username": "bob", "password": "password456"})
    bob_id = r_bob.json()["user"]["id"]
    r_intruder = client.post("/api/auth/register", json={"username": "intruder", "password": "password000"})
    intruder_id = r_intruder.json()["user"]["id"]

    # Alice creates direct chat with Bob
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    direct_conv = client.post("/api/conversations/direct", json={"user_id": bob_id}).json()
    conv_id = direct_conv["id"]

    client.cookies.clear()
    intruder_token = create_access_token(intruder_id)

    with client.websocket_connect(f"/ws/chat?token={intruder_token}") as ws_intruder:
        ws_intruder.send_json({
            "type": "send_message",
            "conversation_id": conv_id,
            "content": "I should not be able to send this!",
        })
        err = ws_intruder.receive_json()
        assert err["type"] == "error"
        assert "not a member" in err["message"]
