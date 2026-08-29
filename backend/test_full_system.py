import os
import sys
from app import app
from extensions import db
from models import Student, Skill, SkillVerification, SkillGap
from federated.server import run_federated_round, get_federated_history
from ml.salary_model import salary_predictor
from ml.skill_gap_model import skill_gap_model
from ml.readiness_model import readiness_scorer
from utils.badge_checker import get_student_badges
from utils.progress_tracker import record_student_snapshot, get_progress_timeline

print("========================================")
print("RUNNING SKILLBRIDGE FULL SYSTEM TEST")
print("========================================")

with app.app_context():
    # 1. Test ML Models
    print("\n[1] Testing ML Models...")
    gaps = skill_gap_model.evaluate_gaps(["python", "sql"], "Software Engineer")
    print(f"  Skill Gap Coverage: {gaps['overall_coverage']} | Missing: {gaps['missing_required']}")

    salary = salary_predictor.predict_salary(["python", "sql", "git"])
    print(f"  Base Salary Prediction: {salary['estimated_lpa']} LPA")

    sim = salary_predictor.simulate_future_salary(["python", "sql"], ["docker", "aws"])
    print(f"  Salary Boost from Docker+AWS: +INR {sim['projected_boost']} LPA (+{sim['percentage_increase']}%)")

    readiness = readiness_scorer.calculate_readiness(gaps, [])
    print(f"  Readiness Scorer: {readiness['readiness_score']}% ({readiness['tier']})")

    # 2. Test Federated Learning Round
    print("\n[2] Testing Federated Learning Simulation...")
    fl_result = run_federated_round()
    print(f"  FL Round #{fl_result['round_number']} completed with global accuracy: {fl_result['global_accuracy']}")
    print(f"  Nodes participating: {fl_result['participating_nodes']} | Privacy: {fl_result['privacy_guarantee']}")

    history = get_federated_history()
    print(f"  Total historical FL rounds logged in DB: {len(history)}")

    # 3. Test Student & Utilities
    print("\n[3] Testing Student Utilities & Badges...")
    test_student = Student.query.first()
    if test_student:
        badges = get_student_badges(test_student.id)
        unlocked = [b['title'] for b in badges if b['unlocked']]
        print(f"  Student {test_student.name} unlocked badges: {unlocked}")

        snap = record_student_snapshot(test_student.id)
        print(f"  Progress Snapshot recorded: Readiness {snap.readiness_score}%")

        timeline = get_progress_timeline(test_student.id)
        print(f"  Progress Timeline snapshots count: {len(timeline['snapshots'])}")
    else:
        print("  (No student in DB yet for badges test)")

print("\n========================================")
print("ALL SYSTEM MODULES TESTED SUCCESSFULLY!")
print("========================================")
