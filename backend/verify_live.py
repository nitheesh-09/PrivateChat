import asyncio
import json
import httpx
import websockets

BACKEND_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/chat"


def receive_event_of_type(messages_queue, target_type: str):
    for idx, msg in enumerate(messages_queue):
        if msg.get("type") == target_type:
            return messages_queue.pop(idx)
    return None


async def main():
    print("=" * 65)
    print("STARTING LIVE END-TO-END VERIFICATION: DIRECT & GROUP CHAT")
    print("=" * 65)

    # 1. Health check
    async with httpx.AsyncClient() as client:
        health = await client.get(f"{BACKEND_URL}/api/health")
        print("[1] Backend Health:", health.json())
        assert health.status_code == 200

    # 2. Register 4 users: Alice, Bob, Charlie, David (demonstrates NO 2-user limit!)
    users = ["alice", "bob", "charlie", "david"]
    cookies = {}
    user_ids = {}

    print("\n[2] Registering Multiple Users (No Limit)...")
    for u in users:
        c = httpx.AsyncClient(base_url=BACKEND_URL)
        r = await c.post("/api/auth/register", json={"username": u, "password": "password123"})
        if r.status_code != 201:
            r = await c.post("/api/auth/login", json={"username": u, "password": "password123"})
        assert r.status_code in [200, 201], f"Auth failed for {u}: {r.text}"
        user_ids[u] = r.json()["user"]["id"]
        cookies[u] = r.cookies.get("access_token")
        assert cookies[u] is not None
        print(f"    -> User registered: {u} (ID: {user_ids[u]})")
        await c.aclose()

    # 3. Alice creates Direct Chat with Bob
    alice_client = httpx.AsyncClient(base_url=BACKEND_URL, cookies={"access_token": cookies["alice"]})
    print("\n[3] Alice starting Direct Conversation with Bob...")
    direct_res = await alice_client.post("/api/conversations/direct", json={"user_id": user_ids["bob"]})
    assert direct_res.status_code == 201
    direct_conv = direct_res.json()
    direct_id = direct_conv["id"]
    print(f"    -> Direct Chat created: ID {direct_id}, Display Name: {direct_conv['display_name']}")
    assert direct_conv["display_name"] == "bob"

    # 4. Alice creates Group Chat "College Friends" with Bob and Charlie
    print("\n[4] Alice creating Group Conversation 'College Friends' with Bob & Charlie...")
    group_res = await alice_client.post(
        "/api/conversations/group",
        json={"name": "College Friends", "member_ids": [user_ids["bob"], user_ids["charlie"]]},
    )
    assert group_res.status_code == 201
    group_conv = group_res.json()
    group_id = group_conv["id"]
    print(f"    -> Group created: ID {group_id}, Name: {group_conv['display_name']}, Members: {len(group_conv['members'])}")
    assert group_conv["display_name"] == "College Friends"
    assert len(group_conv["members"]) == 3

    # 5. Add David to the Group
    print("\n[5] Adding David to 'College Friends'...")
    add_res = await alice_client.post(f"/api/conversations/{group_id}/members", json={"member_ids": [user_ids["david"]]})
    assert add_res.status_code == 200
    assert len(add_res.json()["members"]) == 4
    print("    -> David added successfully! Total members: 4")

    # 6. Authorization test: David attempts to access Alice & Bob's direct chat -> must be 403 Forbidden
    david_client = httpx.AsyncClient(base_url=BACKEND_URL, cookies={"access_token": cookies["david"]})
    print("\n[6] Testing Authorization: Non-member David accessing Direct Chat...")
    unauth_res = await david_client.get(f"/api/conversations/{direct_id}/messages")
    print(f"    -> Response: {unauth_res.status_code} ({unauth_res.json()['detail']})")
    assert unauth_res.status_code == 403
    print("    -> Security guard confirmed: Non-members cannot view messages!")

    # 7. Real-Time Group Chat over WebSockets: Alice, Bob, and Charlie connect
    print("\n[7] Testing Real-Time WebSocket Group Chat...")
    bob_headers = {"Cookie": f"access_token={cookies['bob']}"}
    charlie_headers = {"Cookie": f"access_token={cookies['charlie']}"}
    alice_headers = {"Cookie": f"access_token={cookies['alice']}"}

    async with websockets.connect(WS_URL, additional_headers=bob_headers) as ws_bob:
        async with websockets.connect(WS_URL, additional_headers=charlie_headers) as ws_charlie:
            async with websockets.connect(WS_URL, additional_headers=alice_headers) as ws_alice:
                print("    -> Alice, Bob, and Charlie connected via WebSockets.")

                # Alice sends message to the group
                print("    -> Alice sending group message: 'Hey everyone, welcome to the group!'")
                await ws_alice.send(json.dumps({
                    "type": "send_message",
                    "conversation_id": group_id,
                    "content": "Hey everyone, welcome to the group!",
                }))

                # Collect messages for Bob
                bob_received = None
                for _ in range(5):
                    raw = await ws_bob.recv()
                    data = json.loads(raw)
                    if data.get("type") == "new_message" and data.get("conversation_id") == group_id:
                        bob_received = data
                        break

                assert bob_received is not None
                print(f"    -> Bob received group message in real time from {bob_received['message']['sender_username']}: '{bob_received['message']['content']}'")
                assert bob_received["message"]["content"] == "Hey everyone, welcome to the group!"
                assert bob_received["message"]["sender_username"] == "alice"
                msg_id = bob_received["message"]["id"]

                # Collect messages for Charlie
                charlie_received = None
                for _ in range(5):
                    raw = await ws_charlie.recv()
                    data = json.loads(raw)
                    if data.get("type") == "new_message" and data.get("conversation_id") == group_id:
                        charlie_received = data
                        break

                assert charlie_received is not None
                print(f"    -> Charlie received group message in real time from {charlie_received['message']['sender_username']}: '{charlie_received['message']['content']}'")
                assert charlie_received["message"]["content"] == "Hey everyone, welcome to the group!"

                # Bob marks the group message as read
                print("\n[8] Bob marking group message read...")
                await ws_bob.send(json.dumps({
                    "type": "mark_read",
                    "conversation_id": group_id,
                    "message_ids": [msg_id],
                }))

                # Alice receives read receipt
                alice_receipt = None
                for _ in range(5):
                    raw = await ws_alice.recv()
                    data = json.loads(raw)
                    if data.get("type") == "messages_read" and data.get("conversation_id") == group_id:
                        alice_receipt = data
                        break

                assert alice_receipt is not None
                print(f"    -> Alice received real-time read receipt for message {alice_receipt['message_ids']}")

    # 8. Check message persistence in database via REST
    print("\n[9] Verifying Group Message Persistence via REST API...")
    msgs_res = await alice_client.get(f"/api/conversations/{group_id}/messages")
    assert msgs_res.status_code == 200
    stored_msgs = msgs_res.json()
    print(f"    -> Retrieved {len(stored_msgs)} messages from database for group:")
    for m in stored_msgs:
        print(f"       [{m['sender_username']}] {m['content']} (Status: {m['status']})")

    await alice_client.aclose()
    await david_client.aclose()

    print("\n" + "=" * 65)
    print("ALL DIRECT AND GROUP REAL-TIME TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
