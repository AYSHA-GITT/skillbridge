from app import app
from extensions import db
from models import (
    Student, Resume, Skill, SkillVerification, QuestionBank,
    SkillGap, StudyPlan, Progress, FLTrainingRound
)

with app.app_context():
    db.create_all()
    print("✅ All tables created successfully on Supabase!")
    print("Tables created:")
    print("  - students")
    print("  - resumes")
    print("  - skills")
    print("  - skill_verifications")
    print("  - question_bank")
    print("  - skill_gaps")
    print("  - study_plans")
    print("  - progress")
    print("  - fl_training_rounds")