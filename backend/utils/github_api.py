import os
import urllib.parse
import urllib.request
import json
import logging

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

CURATED_PROJECTS = {
    'python': [
        {'name': 'Automate The Boring Stuff with Python', 'description': 'Practical automation scripts and project exercises.', 'stars': 61000, 'url': 'https://github.com/asweigart/simple-turtle-tutorial-for-python'},
        {'name': 'Python Mini Projects', 'description': 'Collection of beginner to intermediate Python hands-on projects.', 'stars': 14200, 'url': 'https://github.com/Python-World/python-mini-projects'}
    ],
    'machine learning': [
        {'name': 'ML From Scratch', 'description': 'Clean Python implementations of machine learning models.', 'stars': 34000, 'url': 'https://github.com/eriklindernoren/ML-From-Scratch'},
        {'name': 'Hand-on Machine Learning', 'description': 'Notebooks demonstrating end-to-end ML workflows.', 'stars': 42000, 'url': 'https://github.com/ageron/handson-ml3'}
    ],
    'react': [
        {'name': 'React Projects Showcase', 'description': 'Real-world frontend web application examples.', 'stars': 18500, 'url': 'https://github.com/john-smilga/react-projects'},
        {'name': 'Awesome React', 'description': 'Curated list of delightful React applications and tools.', 'stars': 64000, 'url': 'https://github.com/enaqx/awesome-react'}
    ],
    'sql': [
        {'name': 'SQL Murder Mystery', 'description': 'Interactive game designed to build SQL querying proficiency.', 'stars': 4200, 'url': 'https://github.com/NUKnightLab/sql-mysteries'},
        {'name': 'Awesome SQL', 'description': 'Resources and project databases to master SQL queries.', 'stars': 6800, 'url': 'https://github.com/romdim/awesome-sql'}
    ],
    'docker': [
        {'name': 'Docker Curriculum', 'description': 'A comprehensive tutorial on getting started with Docker.', 'stars': 23000, 'url': 'https://github.com/prakhar1989/docker-curriculum'}
    ]
}


def search_github_projects(skill_name, max_results=2):
    """
    Finds GitHub repositories for a given skill to provide hands-on practice.
    Falls back to curated high-quality repositories.
    """
    clean_skill = skill_name.lower().strip()
    if clean_skill in CURATED_PROJECTS:
        return CURATED_PROJECTS[clean_skill][:max_results]

    headers = {'User-Agent': 'SkillBridge-App'}
    if GITHUB_TOKEN and GITHUB_TOKEN != 'your_github_token_here':
        headers['Authorization'] = f'token {GITHUB_TOKEN}'

    query = urllib.parse.quote(f"{clean_skill} beginner tutorial project")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={max_results}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get('items', [])
            projects = []
            for item in items:
                projects.append({
                    'name': item.get('name', skill_name),
                    'description': item.get('description', f'Hands-on project repository for {skill_name}'),
                    'stars': item.get('stargazers_count', 0),
                    'url': item.get('html_url', f"https://github.com/search?q={query}")
                })
            if projects:
                return projects
    except Exception as e:
        logging.warning(f"GitHub API search failed: {e}")

    # Fallback
    return [
        {
            'name': f'Awesome {skill_name.capitalize()}',
            'description': f'Curated guides, tutorials, and beginner repositories for {skill_name}.',
            'stars': 1200,
            'url': f"https://github.com/search?q={urllib.parse.quote(clean_skill)}"
        }
    ]
