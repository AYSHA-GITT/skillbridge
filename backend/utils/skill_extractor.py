from data.skills_list import KNOWN_SKILLS


def split_into_sections(text):
    """
    Naive section splitter — looks for common resume headers
    (SKILLS, PROJECTS, EXPERIENCE, EDUCATION) and splits text under them.
    Returns a dict: {section_name: section_text}
    """
    headers = ["skills", "projects", "experience", "education",
               "certifications", "summary"]

    lines = text.split("\n")
    sections = {}
    current_section = "general"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip().lower()
        matched_header = None
        for header in headers:
            if stripped == header or stripped.startswith(header):
                matched_header = header
                break

        if matched_header:
            current_section = matched_header
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, [])
            sections[current_section].append(line)

    # Join each section's lines back into text
    return {name: "\n".join(lines) for name, lines in sections.items()}


def extract_skills(resume_text):
    """
    Scans resume text for known skills and assigns a confidence score
    based on how many distinct sections mention each skill.

    Returns a list of dicts: [{"skill_name": ..., "confidence": ...}, ...]
    """
    sections = split_into_sections(resume_text)
    text_lower = resume_text.lower()

    results = []

    for skill in KNOWN_SKILLS:
        if skill not in text_lower:
            continue  # skill not mentioned at all — skip

        # Count how many distinct sections mention this skill
        sections_mentioning = 0
        in_skills_section_only = False

        for section_name, section_text in sections.items():
            if skill in section_text.lower():
                sections_mentioning += 1

        # Confidence rule:
        if sections_mentioning >= 2:
            confidence = 0.85  # mentioned in skills list AND elsewhere
        elif sections_mentioning == 1:
            # Check if that one mention is inside the "skills" section only
            skills_section_text = sections.get("skills", "").lower()
            if skill in skills_section_text:
                confidence = 0.35  # just listed, no supporting evidence
            else:
                confidence = 0.55  # mentioned once, but not in a skills list
                                     # (e.g. only in project text) — still
                                     # somewhat meaningful
        else:
            confidence = 0.0

        results.append({
            "skill_name": skill,
            "extraction_confidence": round(confidence, 2)
        })

    return results