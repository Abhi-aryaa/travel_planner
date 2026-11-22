"""Request/response validation models (all validation lives on the server)."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    budget: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TripUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    budget: Optional[float] = Field(default=None, ge=0)


class DestinationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    place_id: Optional[str] = None
    address: Optional[str] = ""
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    notes: str = Field(default="", max_length=2000)


class DestinationUpdate(BaseModel):
    notes: str = Field(default="", max_length=2000)


class ActivityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    date: date
    time: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    destination_id: Optional[str] = None
    estimated_cost: float = Field(default=0, ge=0)
    actual_cost: Optional[float] = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=2000)


class ActivityUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    date: Optional[date] = None
    time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    estimated_cost: Optional[float] = Field(default=None, ge=0)
    actual_cost: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)

    @field_validator("prompt")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()
