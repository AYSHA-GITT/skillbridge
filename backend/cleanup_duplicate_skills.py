import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Skill, Student, SkillVerification
from extensions import db

def deduplicate_skills():
    with app.app_context():
        students = Student.query.all()
        total_deleted = 0
        total_relinked = 0

        for student in students:
            skills = Skill.query.filter_by(student_id=student.id).all()
            if not skills:
                continue

            by_name = {}
            for s in skills:
                clean_name = s.skill_name.lower().strip()
                by_name.setdefault(clean_name, []).append(s)

            for clean_name, records in by_name.items():
                if len(records) <= 1:
                    continue

                # Find any verifications for these records
                rec_ids = [r.id for r in records]
                verifs = SkillVerification.query.filter(
                    SkillVerification.skill_id.in_(rec_ids)
                ).all()

                # Choose the best primary record:
                # 1. Prefer record with verification
                # 2. Prefer highest extraction_confidence
                # 3. Prefer latest added_on / largest ID
                verified_ids = {v.skill_id for v in verifs}
                
                def sort_key(rec):
                    is_ver = 1 if rec.id in verified_ids else 0
                    conf = rec.extraction_confidence or 0.0
                    return (is_ver, conf, rec.id)

                records_sorted = sorted(records, key=sort_key, reverse=True)
                primary = records_sorted[0]
                duplicates = records_sorted[1:]

                # Re-link any verifications on duplicates to primary
                for v in verifs:
                    if v.skill_id != primary.id:
                        v.skill_id = primary.id
                        total_relinked += 1

                # Delete duplicate records
                for dup in duplicates:
                    db.session.delete(dup)
                    total_deleted += 1

        db.session.commit()
        print(f"Cleanup finished: Deleted {total_deleted} duplicate skill rows, re-linked {total_relinked} verifications.")

if __name__ == '__main__':
    deduplicate_skills()
