"""
SkillLens AI - Resume Optimizer: Section Parser
Extracts contact info, summary, experience, projects, education,
skills, and certifications into structured, editable data models.
"""

import re
from typing import Dict, Any, List

SECTION_HEADERS = {
    'summary': [
        'summary', 'professional summary', 'executive summary',
        'career objective', 'objective', 'about me', 'profile'
    ],
    'experience': [
        'experience', 'work experience', 'employment history',
        'work history', 'professional experience', 'internships',
        'internship experience', 'practical experience'
    ],
    'projects': [
        'projects', 'personal projects', 'academic projects',
        'key projects', 'technical projects', 'featured projects'
    ],
    'education': [
        'education', 'academic background', 'educational qualifications',
        'academics', 'degrees and education'
    ],
    'skills': [
        'skills', 'technical skills', 'core competencies', 'technologies',
        'key skills', 'areas of expertise', 'tools & technologies', 'skill set'
    ],
    'certifications': [
        'certifications', 'certificates', 'licenses', 'credentials',
        'courses & certifications', 'awards & achievements', 'honors'
    ]
}


def extract_contact_info(text: str) -> Dict[str, str]:
    """Extracts candidate contact details using robust regex heuristics."""
    contact = {
        'name': '',
        'email': '',
        'phone': '',
        'linkedin': '',
        'github': '',
        'location': '',
        'portfolio': ''
    }

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return contact

    # 1. Candidate Name (usually the first clean header line before contact tokens)
    for line in lines[:5]:
        if (len(line) < 45 and
            not re.search(r'(@|linkedin|github|http|phone|\+?\d{9,})', line, re.I) and
            not any(line.lower().startswith(h) for group in SECTION_HEADERS.values() for h in group)):
            contact['name'] = line
            break

    # 2. Email
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    if email_match:
        contact['email'] = email_match.group(0).strip()

    # 3. Phone Number (handles international +91, standard US, etc.)
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b', text)
    if phone_match:
        contact['phone'] = phone_match.group(0).strip()

    # 4. LinkedIn
    linkedin_match = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/([a-zA-Z0-9_-]+)', text, re.I)
    if linkedin_match:
        contact['linkedin'] = linkedin_match.group(0).strip()

    # 5. GitHub
    github_match = re.search(r'(?:https?:\/\/)?(?:www\.)?github\.com\/([a-zA-Z0-9_-]+)', text, re.I)
    if github_match:
        contact['github'] = github_match.group(0).strip()

    # 6. Portfolio / Website (excluding github/linkedin)
    portfolio_match = re.search(r'https?:\/\/(?!www\.linkedin|linkedin|www\.github|github)[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+(?:\/[^\s]*)?', text, re.I)
    if portfolio_match:
        contact['portfolio'] = portfolio_match.group(0).strip()

    # 7. Location guess from top lines
    location_match = re.search(r'\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?),\s*([A-Z]{2}|[A-Z][a-zA-Z]+)\b', text[:800])
    if location_match:
        contact['location'] = location_match.group(0).strip()

    return contact


def split_raw_sections(text: str) -> Dict[str, List[str]]:
    """Splits raw text into identified resume section chunks."""
    lines = text.split('\n')
    sections: Dict[str, List[str]] = {
        'header': [],
        'summary': [],
        'experience': [],
        'projects': [],
        'education': [],
        'skills': [],
        'certifications': [],
        'other': []
    }

    current_section = 'header'

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_section in sections:
                sections[current_section].append('')
            continue

        lower_line = stripped.lower().rstrip(':')

        # Check if this line is a section heading
        matched_section = None
        for sec_name, header_keywords in SECTION_HEADERS.items():
            for kw in header_keywords:
                # Match exact heading or heading with styling like "=== SKILLS ===" or "1. Skills"
                clean_heading = re.sub(r'^[0-9\.\-\=\*\#\s]+|[=\-\*\#\s]+$', '', lower_line).strip()
                if clean_heading == kw:
                    matched_section = sec_name
                    break
            if matched_section:
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(stripped)

    return sections


def extract_bullet_points(lines: List[str]) -> List[str]:
    """Extracts individual bullet points from a list of text lines."""
    bullets = []
    current_bullet = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect bullet prefixes: •, -, *, 1., 2., etc.
        is_bullet_start = bool(re.match(r'^(?:[\u2022\u25E6\u2043\u2219\*\-\+]|\d+[\.\)])\s*', stripped))

        if is_bullet_start:
            if current_bullet:
                bullets.append(' '.join(current_bullet).strip())
            cleaned = re.sub(r'^(?:[\u2022\u25E6\u2043\u2219\*\-\+]|\d+[\.\)])\s*', '', stripped)
            current_bullet = [cleaned]
        else:
            if current_bullet:
                current_bullet.append(stripped)
            else:
                # If no bullet prefix was used, treat substantial lines as standalone bullets
                if len(stripped) > 20:
                    bullets.append(stripped)

    if current_bullet:
        bullets.append(' '.join(current_bullet).strip())

    return bullets


def parse_experience_section(lines: List[str]) -> List[Dict[str, Any]]:
    """Parses work experience entries with title, company, dates, and bullets."""
    if not lines:
        return []

    entries = []
    current_entry = {
        'role': '',
        'company': '',
        'period': '',
        'location': '',
        'bullets': []
    }
    raw_bullets_lines = []

    date_regex = re.compile(
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{4}\s*(?:-|–|to|until)\s*(?:Present|Current|\w+\s*\d{4}|\d{4})\b',
        re.I
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        has_date = date_regex.search(stripped)
        is_bullet = bool(re.match(r'^(?:[\u2022\u25E6\u2043\u2219\*\-\+]|\d+[\.\)])\s*', stripped))

        # Check if this line is a continuation date for the current entry
        if has_date and current_entry['role'] and not current_entry['period'] and not raw_bullets_lines and not is_bullet:
            current_entry['period'] = has_date.group(0).strip()
            rem = stripped.replace(current_entry['period'], '').strip(' |-,–()')
            if rem and not current_entry['company']:
                current_entry['company'] = rem
            elif rem and not current_entry['location']:
                current_entry['location'] = rem
            continue

        # A new entry starts when we encounter a new header/date line while the current entry is already populated
        is_new_header = (has_date or ('|' in stripped and not is_bullet)) and not is_bullet

        if is_new_header:
            if current_entry['role'] or current_entry['company'] or raw_bullets_lines:
                current_entry['bullets'] = extract_bullet_points(raw_bullets_lines)
                if not current_entry['bullets'] and raw_bullets_lines:
                    current_entry['bullets'] = [l for l in raw_bullets_lines if len(l.strip()) > 10]
                entries.append(current_entry)
                current_entry = {'role': '', 'company': '', 'period': '', 'location': '', 'bullets': []}
                raw_bullets_lines = []

            # Parse role, company, period from this header line
            if has_date:
                current_entry['period'] = has_date.group(0).strip()
                rem = stripped.replace(current_entry['period'], '').strip(' |-,–()')
            else:
                rem = stripped

            parts = [p.strip() for p in re.split(r'\||–|-|,', rem) if p.strip()]
            if len(parts) >= 2:
                current_entry['role'] = parts[0]
                current_entry['company'] = parts[1]
                if len(parts) >= 3:
                    current_entry['location'] = parts[2]
            elif len(parts) == 1:
                current_entry['role'] = parts[0]
        elif is_bullet:
            raw_bullets_lines.append(stripped)
        else:
            if not current_entry['role']:
                current_entry['role'] = stripped
            elif not current_entry['company']:
                current_entry['company'] = stripped
            else:
                raw_bullets_lines.append(stripped)

    if current_entry['role'] or current_entry['company'] or raw_bullets_lines:
        current_entry['bullets'] = extract_bullet_points(raw_bullets_lines)
        if not current_entry['bullets'] and raw_bullets_lines:
            current_entry['bullets'] = [l for l in raw_bullets_lines if len(l.strip()) > 10]
        entries.append(current_entry)

    return entries


def parse_projects_section(lines: List[str]) -> List[Dict[str, Any]]:
    """Parses projects with title, tech stack, and description bullets."""
    if not lines:
        return []

    projects = []
    current_project = {
        'name': '',
        'technologies': '',
        'link': '',
        'bullets': []
    }
    raw_bullets = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_bullet = bool(re.match(r'^(?:[\u2022\u25E6\u2043\u2219\*\-\+]|\d+[\.\)])\s*', stripped))

        # Check for project title line (e.g. "Smart Attendance System | Python, OpenCV")
        if not is_bullet and ('|' in stripped or len(stripped) < 70 and not raw_bullets):
            if current_project['name'] or raw_bullets:
                current_project['bullets'] = extract_bullet_points(raw_bullets)
                if not current_project['bullets'] and raw_bullets:
                    current_project['bullets'] = [l for l in raw_bullets if len(l.strip()) > 10]
                projects.append(current_project)
                current_project = {'name': '', 'technologies': '', 'link': '', 'bullets': []}
                raw_bullets = []

            if '|' in stripped:
                parts = [p.strip() for p in stripped.split('|')]
                current_project['name'] = parts[0]
                current_project['technologies'] = parts[1] if len(parts) > 1 else ''
            else:
                current_project['name'] = stripped
        elif is_bullet:
            raw_bullets.append(stripped)
        else:
            if not current_project['name']:
                current_project['name'] = stripped
            else:
                raw_bullets.append(stripped)

    if current_project['name'] or raw_bullets:
        current_project['bullets'] = extract_bullet_points(raw_bullets)
        if not current_project['bullets'] and raw_bullets:
            current_project['bullets'] = [l for l in raw_bullets if len(l.strip()) > 10]
        projects.append(current_project)

    return projects


def parse_education_section(lines: List[str]) -> List[Dict[str, str]]:
    """Parses education degrees, institutions, years, and grades."""
    if not lines:
        return []

    degrees = []
    current = {'degree': '', 'institution': '', 'year': '', 'score': ''}

    year_regex = re.compile(r'\b(19\d{2}|20\d{2})\s*(?:-|–|to)?\s*(19\d{2}|20\d{2}|Present)?\b')
    gpa_regex = re.compile(r'\b(?:GPA|CGPA|Percentage|Score)?\s*[:=]?\s*(\d{1,2}(?:\.\d{1,2})?|\d{2,3}%)\b', re.I)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        yr_match = year_regex.search(stripped)
        gpa_match = gpa_regex.search(stripped)

        if yr_match or ('college' in stripped.lower() or 'university' in stripped.lower() or 'institute' in stripped.lower()):
            if current['degree'] or current['institution']:
                degrees.append(current)
                current = {'degree': '', 'institution': '', 'year': '', 'score': ''}

            if yr_match:
                current['year'] = yr_match.group(0).strip()
            if gpa_match:
                current['score'] = gpa_match.group(0).strip()

            clean_line = stripped
            if yr_match:
                clean_line = clean_line.replace(yr_match.group(0), '')
            if gpa_match:
                clean_line = clean_line.replace(gpa_match.group(0), '')
            parts = [p.strip() for p in re.split(r'\||–|-|,', clean_line) if p.strip()]

            if parts:
                if any(k in parts[0].lower() for k in ['bachelor', 'master', 'b.tech', 'm.tech', 'b.e', 'b.sc', 'm.sc', 'diploma']):
                    current['degree'] = parts[0]
                    if len(parts) > 1:
                        current['institution'] = parts[1]
                else:
                    current['institution'] = parts[0]
                    if len(parts) > 1:
                        current['degree'] = parts[1]
        else:
            if not current['degree']:
                current['degree'] = stripped
            elif not current['institution']:
                current['institution'] = stripped

    if current['degree'] or current['institution']:
        degrees.append(current)

    return degrees


def parse_skills_section(lines: List[str]) -> List[str]:
    """Parses skills into an ordered, deduplicated list of clean skill strings."""
    if not lines:
        return []

    extracted = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Remove category labels like "Languages:", "Frameworks:"
        cleaned = re.sub(r'^[A-Za-z\s]+:\s*', '', stripped)
        items = re.split(r'[,|•·\/\t]+', cleaned)
        for item in items:
            s = item.strip().strip('-*•')
            if s and len(s) < 40 and not s.lower().startswith('skill'):
                if s not in extracted:
                    extracted.append(s)
    return extracted


def parse_certifications_section(lines: List[str]) -> List[str]:
    """Parses certifications and licenses list."""
    if not lines:
        return []

    certs = []
    for line in lines:
        stripped = line.strip().lstrip('-*• ')
        if stripped and len(stripped) > 4:
            certs.append(stripped)
    return certs


def parse_resume_to_structured_json(raw_text: str) -> Dict[str, Any]:
    """
    Main parser entrypoint.
    Converts plain text into a structured, fully editable schema.
    """
    raw_sections = split_raw_sections(raw_text)
    contact = extract_contact_info(raw_text)

    # Executive Summary: join summary lines
    summary_text = ' '.join(
        [l.strip() for l in raw_sections.get('summary', []) if l.strip()]
    ).strip()

    # Experience
    experience_entries = parse_experience_section(raw_sections.get('experience', []))

    # Projects
    project_entries = parse_projects_section(raw_sections.get('projects', []))

    # Education
    education_entries = parse_education_section(raw_sections.get('education', []))

    # Skills
    skills_list = parse_skills_section(raw_sections.get('skills', []))

    # Certifications
    certifications_list = parse_certifications_section(raw_sections.get('certifications', []))

    return {
        'contact': contact,
        'summary': summary_text,
        'experience': experience_entries,
        'projects': project_entries,
        'education': education_entries,
        'skills': skills_list,
        'certifications': certifications_list,
        'raw_text': raw_text
    }
