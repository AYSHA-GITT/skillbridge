from models import Student, Resume, Skill, SkillVerification, StudyPlan


def get_student_badges(student_id):
    """
    Evaluates student achievement milestones and returns a structured list
    of unlocked and locked badges.
    """
    student = Student.query.get(student_id)
    if not student:
        return []

    resumes_count = Resume.query.filter_by(student_id=student_id).count()
    verifications_count = SkillVerification.query.filter_by(student_id=student_id).count()
    completed_roadmap_count = StudyPlan.query.filter_by(student_id=student_id, is_completed=True).count()
    readiness = student.readiness_score or 0.0

    # High quiz scores check
    high_scores = SkillVerification.query.filter(
        SkillVerification.student_id == student_id,
        SkillVerification.quiz_score_percent >= 80.0
    ).count()

    badges = [
        {
            'id': 'resume_uploaded',
            'title': 'Profile Kickoff',
            'category': 'Onboarding',
            'description': 'Uploaded and parsed your first resume.',
            'icon': 'TbFileCheck',
            'unlocked': resumes_count > 0,
            'progress': 100 if resumes_count > 0 else 0,
            'unlocked_at': student.created_at.strftime('%Y-%m-%d') if resumes_count > 0 else None
        },
        {
            'id': 'first_quiz',
            'title': 'Skill Evaluator',
            'category': 'Verification',
            'description': 'Completed your first AI-curated skill verification quiz.',
            'icon': 'TbBrain',
            'unlocked': verifications_count >= 1,
            'progress': min(100, int((verifications_count / 1) * 100)),
            'unlocked_at': 'Recently' if verifications_count >= 1 else None
        },
        {
            'id': 'three_skills',
            'title': 'Core Competent',
            'category': 'Verification',
            'description': 'Successfully verified 3 or more technical skills.',
            'icon': 'TbAward',
            'unlocked': verifications_count >= 3,
            'progress': min(100, int((verifications_count / 3) * 100)),
            'unlocked_at': 'Recently' if verifications_count >= 3 else None
        },
        {
            'id': 'high_performer',
            'title': 'Quiz Ace',
            'category': 'Mastery',
            'description': 'Scored 80% or higher on any skill verification quiz.',
            'icon': 'TbTrophy',
            'unlocked': high_scores > 0,
            'progress': 100 if high_scores > 0 else 0,
            'unlocked_at': 'Recently' if high_scores > 0 else None
        },
        {
            'id': 'roadmap_starter',
            'title': 'Habit Builder',
            'category': 'Learning',
            'description': 'Completed at least 3 learning roadmap modules.',
            'icon': 'TbFlame',
            'unlocked': completed_roadmap_count >= 3,
            'progress': min(100, int((completed_roadmap_count / 3) * 100)),
            'unlocked_at': 'Recently' if completed_roadmap_count >= 3 else None
        },
        {
            'id': 'career_ready',
            'title': 'Job Ready Pioneer',
            'category': 'Career',
            'description': 'Attained an overall career readiness score of 75% or higher.',
            'icon': 'TbRocket',
            'unlocked': readiness >= 75.0,
            'progress': min(100, int((readiness / 75.0) * 100)),
            'unlocked_at': 'Recently' if readiness >= 75.0 else None
        },
        {
            'id': 'fl_contributor',
            'title': 'Privacy Guardian',
            'category': 'Federated Learning',
            'description': 'Participated in a federated learning round with differential privacy.',
            'icon': 'TbShieldCheck',
            'unlocked': verifications_count > 0, # Once user has verified skills, local partition trains on them
            'progress': 100 if verifications_count > 0 else 0,
            'unlocked_at': 'Recently' if verifications_count > 0 else None
        }
    ]

    return badges
