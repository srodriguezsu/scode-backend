# Backend - SCODE

An asynchronous REST API built with **FastAPI** that leverages Machine Learning models to optimize employee grouping into project teams based on their hard and soft skills.

## Architecture & Tech Stack
* **Framework:** FastAPI (Python 3.11+)
* **Database:** MySQL 8.0+
* **ORM:** SQLModel
* **Database Migrations:** Alembic

## Prerequisites
Ensure you have the following installed on your system:
* Python 3.11 or higher
* MySQL Server (running locally or via Docker)
* `virtualenv` or built-in `venv` module

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Set up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the `.env.example` file to `.env` and update the values accordingly:

### 5. Run the Server

Start the development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Documentation
Interactive API documentation (Swagger UI) is available at:
* **Swagger UI:** `http://localhost:8000/docs`

