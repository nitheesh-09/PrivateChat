def test_direct_and_group_conversations(client):
    # 1. Register 3 users
    r_alice = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    alice_id = r_alice.json()["user"]["id"]

    r_bob = client.post("/api/auth/register", json={"username": "bob", "password": "password456"})
    bob_id = r_bob.json()["user"]["id"]

    r_charlie = client.post("/api/auth/register", json={"username": "charlie", "password": "password789"})
    charlie_id = r_charlie.json()["user"]["id"]

    # 2. Login as Alice
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "alice", "password": "password123"})

    # Create direct conversation with Bob
    direct_resp = client.post("/api/conversations/direct", json={"user_id": bob_id})
    assert direct_resp.status_code == 201
    direct_data = direct_resp.json()
    assert direct_data["type"] == "direct"
    assert direct_data["display_name"] == "bob"
    direct_conv_id = direct_data["id"]

    # Calling direct again should return the existing conversation
    direct_repeat = client.post("/api/conversations/direct", json={"user_id": bob_id})
    assert direct_repeat.status_code in (200, 201)
    assert direct_repeat.json()["id"] == direct_conv_id

    # 3. Create group conversation: "Project Team" with Bob
    group_resp = client.post(
        "/api/conversations/group",
        json={"name": "Project Team", "member_ids": [bob_id]},
    )
    assert group_resp.status_code == 201
    group_data = group_resp.json()
    assert group_data["type"] == "group"
    assert group_data["display_name"] == "Project Team"
    assert len(group_data["members"]) == 2
    group_id = group_data["id"]

    # Add Charlie to group
    add_resp = client.post(
        f"/api/conversations/{group_id}/members",
        json={"member_ids": [charlie_id]},
    )
    assert add_resp.status_code == 200
    assert len(add_resp.json()["members"]) == 3

    # 4. Non-member access test: Charlie is not in direct_conv_id
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "charlie", "password": "password789"})

    unauth_conv = client.get(f"/api/conversations/{direct_conv_id}")
    assert unauth_conv.status_code == 403
    assert "not a member" in unauth_conv.json()["detail"]

    unauth_msgs = client.get(f"/api/conversations/{direct_conv_id}/messages")
    assert unauth_msgs.status_code == 403

    # But Charlie CAN access the group
    group_access = client.get(f"/api/conversations/{group_id}")
    assert group_access.status_code == 200

    # 5. Charlie sends a group message
    send_resp = client.post(
        f"/api/conversations/{group_id}/messages",
        json={"content": "Hello team, Charlie here!"},
    )
    assert send_resp.status_code == 201
    msg_data = send_resp.json()
    assert msg_data["content"] == "Hello team, Charlie here!"
    assert msg_data["sender_username"] == "charlie"
    msg_id = msg_data["id"]

    # 6. Alice fetches group messages
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "alice", "password": "password123"})

    alice_msgs = client.get(f"/api/conversations/{group_id}/messages")
    assert alice_msgs.status_code == 200
    msgs = alice_msgs.json()
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hello team, Charlie here!"

    # Alice marks group messages read
    read_resp = client.post(
        f"/api/conversations/{group_id}/read",
        json={"message_ids": [msg_id]},
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["read_count"] == 1


def test_empty_and_long_messages(client):
    r_alice = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    r_bob = client.post("/api/auth/register", json={"username": "bob", "password": "password456"})
    bob_id = r_bob.json()["user"]["id"]

    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    conv = client.post("/api/conversations/direct", json={"user_id": bob_id}).json()

    # Empty message rejection
    empty_resp = client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "   "})
    assert empty_resp.status_code == 422

    # Too long message rejection (>4000)
    long_resp = client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "X" * 4001})
    assert long_resp.status_code == 422


def test_existing_direct_conversation_is_reused_not_duplicated(client):
    """Calling create direct conversation multiple times or from either participant reuses the same conversation."""
    r1 = client.post("/api/auth/register", json={"username": "user1", "password": "password123"})
    r2 = client.post("/api/auth/register", json={"username": "user2", "password": "password123"})
    user1_id = r1.json()["user"]["id"]
    user2_id = r2.json()["user"]["id"]

    # Login as user1
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "user1", "password": "password123"})

    # 1. First creation
    resp1 = client.post("/api/conversations/direct", json={"user_id": user2_id})
    assert resp1.status_code == 201
    conv_id = resp1.json()["id"]

    # 2. Duplicate creation from user1 -> reuses existing conversation
    resp2 = client.post("/api/conversations/direct", json={"user_id": user2_id})
    assert resp2.status_code in (200, 201)
    assert resp2.json()["id"] == conv_id

    # 3. Duplicate creation from user2 -> reuses existing conversation
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "user2", "password": "password123"})

    resp3 = client.post("/api/conversations/direct", json={"user_id": user1_id})
    assert resp3.status_code in (200, 201)
    assert resp3.json()["id"] == conv_id

    # 4. Verify user2's conversation list only has 1 conversation
    list_resp = client.get("/api/conversations")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_user_cannot_access_or_participate_in_other_users_direct_conversation(client):
    """User3 cannot access conversation details, messages, or send messages to user1-user2 chat."""
    r1 = client.post("/api/auth/register", json={"username": "person1", "password": "password123"})
    r2 = client.post("/api/auth/register", json={"username": "person2", "password": "password123"})
    r3 = client.post("/api/auth/register", json={"username": "person3", "password": "password123"})
    person2_id = r2.json()["user"]["id"]

    # Person1 creates direct conversation with Person2
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "person1", "password": "password123"})
    direct_conv = client.post("/api/conversations/direct", json={"user_id": person2_id}).json()
    conv_id = direct_conv["id"]

    # Send a message
    client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Private message between 1 and 2"})

    # Login as person3
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "person3", "password": "password123"})

    # Person3 attempts to get details of conversation between person1 and person2
    details_resp = client.get(f"/api/conversations/{conv_id}")
    assert details_resp.status_code == 403
    assert "not a member" in details_resp.json()["detail"].lower()

    # Person3 attempts to get messages
    msgs_resp = client.get(f"/api/conversations/{conv_id}/messages")
    assert msgs_resp.status_code == 403

    # Person3 attempts to send a message
    send_resp = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Intruder message"})
    assert send_resp.status_code == 403

