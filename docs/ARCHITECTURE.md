# RythuCall Architecture

```text
Farmer
   |
   v
Voice / Phone Interface
   |
   v
Backend API
   |
   +-------------------+
   |                   |
   v                   v
Farmer Data       Inventory Data
   |                   |
   v                   v
Eligibility       Outlet Ranking
Engine                |
   |                   |
   +---------+---------+
             |
             v
       Reservation Engine
             |
       +-----+-----+
       |           |
       v           v
   Booking ID    Outlet Portal
       |
       v
   SMS / Notification


   Prototype Components
Frontend

React + Vite

Responsible for the farmer simulation, voice/phone interface, reservation screens and outlet interface.

Backend

Python + FastAPI

Responsible for farmer lookup, eligibility, inventory checking, outlet ranking and reservations.

Database

SQLite / synthetic JSON data during the initial prototype.

AI

OpenAI model for natural-language understanding and multilingual interaction.

Authentication

Synthetic authentication for the prototype.

A production system would use authorized government authentication mechanisms.

Government Integration

Not connected in the prototype.

Production deployment would require authorized APIs and government approvals.