from app import app
from extensions import db
from models import QuestionBank

questions = [
    # Python
    {"skill_name": "python", "question": "What is the output of print(type([]))?",
     "option_a": "<class 'list'>", "option_b": "<class 'array'>",
     "option_c": "<class 'tuple'>", "option_d": "<class 'dict'>",
     "correct_answer": "A", "difficulty": "Easy"},
    {"skill_name": "python", "question": "Which keyword is used to define a function in Python?",
     "option_a": "func", "option_b": "def",
     "option_c": "function", "option_d": "define",
     "correct_answer": "B", "difficulty": "Easy"},
    {"skill_name": "python", "question": "What does 'len()' return for a string?",
     "option_a": "Number of words", "option_b": "Number of characters",
     "option_c": "Memory size", "option_d": "ASCII sum",
     "correct_answer": "B", "difficulty": "Easy"},
    {"skill_name": "python", "question": "What is a list comprehension used for?",
     "option_a": "Creating lists concisely", "option_b": "Deleting lists",
     "option_c": "Sorting dictionaries", "option_d": "Importing modules",
     "correct_answer": "A", "difficulty": "Medium"},

    # SQL
    {"skill_name": "sql", "question": "Which SQL clause is used to filter rows?",
     "option_a": "ORDER BY", "option_b": "GROUP BY",
     "option_c": "WHERE", "option_d": "HAVING",
     "correct_answer": "C", "difficulty": "Easy"},
    {"skill_name": "sql", "question": "Which command removes a table entirely, including its structure?",
     "option_a": "DELETE", "option_b": "DROP",
     "option_c": "TRUNCATE", "option_d": "REMOVE",
     "correct_answer": "B", "difficulty": "Medium"},
    {"skill_name": "sql", "question": "What does a PRIMARY KEY enforce?",
     "option_a": "Sorted order", "option_b": "Uniqueness and non-null",
     "option_c": "Fast text search", "option_d": "Foreign relation only",
     "correct_answer": "B", "difficulty": "Easy"},

    # Java
    {"skill_name": "java", "question": "Which of these is NOT a Java access modifier?",
     "option_a": "public", "option_b": "private",
     "option_c": "shared", "option_d": "protected",
     "correct_answer": "C", "difficulty": "Easy"},
    {"skill_name": "java", "question": "What is the entry point method of a Java program?",
     "option_a": "start()", "option_b": "main()",
     "option_c": "run()", "option_d": "init()",
     "correct_answer": "B", "difficulty": "Easy"},

    # Machine Learning
    {"skill_name": "machine learning", "question": "What does 'overfitting' mean?",
     "option_a": "Model performs well on new data",
     "option_b": "Model memorizes training data but fails on new data",
     "option_c": "Model trains too fast",
     "option_d": "Model uses too little data",
     "correct_answer": "B", "difficulty": "Medium"},
    {"skill_name": "machine learning", "question": "Which of these is a supervised learning algorithm?",
     "option_a": "K-Means", "option_b": "Random Forest",
     "option_c": "PCA", "option_d": "DBSCAN",
     "correct_answer": "B", "difficulty": "Medium"},

    # Git
    {"skill_name": "git", "question": "Which command creates a new branch in Git?",
     "option_a": "git branch <name>", "option_b": "git new <name>",
     "option_c": "git create <name>", "option_d": "git checkout-new <name>",
     "correct_answer": "A", "difficulty": "Easy"},
]

with app.app_context():
    for q in questions:
        db.session.add(QuestionBank(**q))
    db.session.commit()
    print(f"✅ Seeded {len(questions)} questions into question_bank")