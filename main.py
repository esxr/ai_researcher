
from src.process.core import generate_outline_direct
from src.process.utilities import setup_environment, fetch_related_subjects

def main():
    setup_environment()
    topic = "Example Topic"
    outline = generate_outline_direct(topic)
    related_subjects = fetch_related_subjects(topic)
    print(f"Outline: {outline.as_str}")
    print(f"Related Subjects: {related_subjects}")

if __name__ == "__main__":
    main()
