from utils.ai_question_generator import generate_questions

questions = generate_questions("Flask")

print("\nGenerated Questions:\n")

for i, q in enumerate(questions, start=1):
    print(f"{i}. {q['question']}")
    print(f"A. {q['option_a']}")
    print(f"B. {q['option_b']}")
    print(f"C. {q['option_c']}")
    print(f"D. {q['option_d']}")
    print(f"Correct: {q['correct_answer']}")
    print("-" * 50)