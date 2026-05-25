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

Create a `.env` file in the root directory (or `.env.local` for local development) with the following structure:

```env
# Database Configuration
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=scode_db
```

### 5. Database Setup

**A. Using Alembic (Recommended for Migrations)**

Run the following commands to create the necessary tables:

```bash
alembic upgrade head
```

**B. Direct MySQL Creation**
If you prefer to create the database directly, ensure the database exists and run the schema script:

```bash
mysql -u <user> -p < <path/to/schema.sql>
```

### 6. Run the Server

Start the development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Documentation
Interactive API documentation (Swagger UI) is available at:
* **Swagger UI:** `http://localhost:8000/docs`

