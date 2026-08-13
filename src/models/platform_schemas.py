from pydantic import BaseModel


class PlatformStats(BaseModel):
    total_users: int
    total_conversations: int
    total_messages: int
    new_users_last_7_days: int
