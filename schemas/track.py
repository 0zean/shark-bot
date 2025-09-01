from pydantic import BaseModel


class Track(BaseModel):
    url: str
    title: str
    thumbnail_url: str | None
    duration: int | None
