from app import app
from extensions import db
from models import (
    Student, Resume, Skill, SkillVerification, QuestionBank,
    SkillGap, StudyPlan, Progress, FLTrainingRound
)

with app.app_context():
    db.drop_all()
    print("🗑️  All old tables dropped")
    db.create_all()
    print("✅ All tables recreated with current schema")