"""Run once with a database migration role before starting API workers."""

from cv_assistant.agent.graph import initialize_database


if __name__ == "__main__":
    initialize_database()
