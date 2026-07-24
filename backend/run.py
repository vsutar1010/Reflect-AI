"""
ReflectAI Backend Entry Point

Run the development server using:

    python run.py

The FastAPI application is located in:
    app/main.py
"""

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()