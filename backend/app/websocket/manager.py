import logging
from typing import Dict, Set, List, Any
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    def __init__(self):
        # Map user_id -> set of active WebSockets (supports multiple tabs / devices)
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept connection and register under user_id."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Active sockets: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket) -> bool:
        """
        Unregister WebSocket for user_id.
        Returns True if the user has no remaining active connections (went offline).
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"User {user_id} disconnected completely (now offline).")
                return True
        logger.info(f"User {user_id} closed a socket.")
        return False

    def is_user_online(self, user_id: str) -> bool:
        """Check if user has at least one active WebSocket connection."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send JSON message to all active sockets of a specific user."""
        if user_id not in self.active_connections:
            return

        dead_sockets = set()
        for ws in list(self.active_connections[user_id]):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending message to user {user_id}: {e}")
                dead_sockets.add(ws)

        for ws in dead_sockets:
            self.disconnect(user_id, ws)

    async def broadcast_to_users(self, user_ids: List[str], message: Dict[str, Any]):
        """Broadcast JSON message to multiple users (e.g. all members of a conversation)."""
        for uid in set(user_ids):
            await self.send_to_user(uid, message)


manager = ConnectionManager()
