"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from typing import Optional, List

from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import Column
from sqlalchemy.types import JSON


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


# SQLModel-based Activity model
class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False)
    description: Optional[str] = None
    schedule: Optional[str] = None
    max_participants: Optional[int] = None
    participants: List[str] = Field(default_factory=list, sa_column=Column(JSON))


# SQLite engine (file-based for dev)
DATABASE_URL = "sqlite:///./activities.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create DB tables and seed initial activities if none exist."""
    SQLModel.metadata.create_all(engine)

    # Seed initial activities if table is empty
    with Session(engine) as session:
        statement = select(Activity)
        result = session.exec(statement)
        any_activity = result.first()
        if not any_activity:
            seed = [
                Activity(name="Chess Club", description="Learn strategies and compete in chess tournaments",
                         schedule="Fridays, 3:30 PM - 5:00 PM", max_participants=12,
                         participants=["michael@mergington.edu", "daniel@mergington.edu"]),
                Activity(name="Programming Class", description="Learn programming fundamentals and build software projects",
                         schedule="Tuesdays and Thursdays, 3:30 PM - 4:30 PM", max_participants=20,
                         participants=["emma@mergington.edu", "sophia@mergington.edu"]),
                Activity(name="Gym Class", description="Physical education and sports activities",
                         schedule="Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM", max_participants=30,
                         participants=["john@mergington.edu", "olivia@mergington.edu"]),
            ]
            for a in seed:
                session.add(a)
            session.commit()


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with Session(engine) as session:
        activities = session.exec(select(Activity)).all()
        # Return a dict keyed by activity name to remain compatible with the original API
        return {
            a.name: {
                "description": a.description,
                "schedule": a.schedule,
                "max_participants": a.max_participants,
                "participants": a.participants,
            }
            for a in activities
        }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with Session(engine) as session:
        statement = select(Activity).where(Activity.name == activity_name)
        activity = session.exec(statement).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        if email in activity.participants:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        # Append and save
        participants = list(activity.participants or [])
        participants.append(email)
        activity.participants = participants
        session.add(activity)
        session.commit()
        return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with Session(engine) as session:
        statement = select(Activity).where(Activity.name == activity_name)
        activity = session.exec(statement).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        participants = list(activity.participants or [])
        if email not in participants:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        participants.remove(email)
        activity.participants = participants
        session.add(activity)
        session.commit()
        return {"message": f"Unregistered {email} from {activity_name}"}