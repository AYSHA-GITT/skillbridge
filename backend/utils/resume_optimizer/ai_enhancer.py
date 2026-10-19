"""
SkillLens AI - Resume Optimizer: AI Enhancer
Leverages Google Gemini with strict anti-hallucination rules to enhance
bullet points into active STAR/XYZ format and synthesize polished summaries.
Includes a robust rule-based fallback when Gemini API is quota-limited or offline.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List

ACTION_VERB_MAP = {
    "responsible for": ["Architected", "Engineered", "Spearheaded", "Directed"],
    "helped with": ["Collaborated to design", "Co-engineered", "Contributed to building"],
    "helped": ["Facilitated", "Collaborated to deliver", "Co-developed"],
    "worked on": ["Engineered and deployed", "Developed end-to-end", "Implemented"],
    "assisted in": ["Partnered to implement", "Coordinated development of", "Assisted in engineering"],
    "assisted": ["Supported deployment of", "Collaborated on", "Co-engineered"],
    "did": ["Executed", "Implemented", "Delivered"],
    "tasked with": ["Owned execution of", "Spearheaded delivery of", "Led implementation of"],
    "participated in": ["Contributed cross-functionally to", "Actively collaborated on"],
    "handled": ["Orchestrated", "Streamlined", "Administered"],
    "involved in": ["Played a key role in developing", "Co-developed"],
    "contributed to": ["Accelerated development of", "Engineered core modules for"],
    "supported": ["Maintained and enhanced", "Bolstered infrastructure for"],
    "managed some": ["Supervised", "Coordinated delivery of"],
    "took care of": ["Resolved and maintained", "Overseeing maintenance of"]
}


def get_genai_client():
    """Initializes Google GenAI Client using existing backend environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        logging.warning(f"Could not initialize Google GenAI Client: {e}")
        return None


def generate_rule_based_enhancement(
    bullet_text: str,
    target_career: str,
    index: int
) -> Dict[str, Any]:
    """
    Deterministic fallback when Gemini API is rate-limited or unavailable.
    Guarantees zero hallucinations and preserves student facts while transforming
    passive voice to active STAR/XYZ format with clear student fill-in prompts.
    """
    improved = bullet_text.strip()
    explanation = "Enhanced phrasing with active leadership verb and STAR-impact structure."
    matched_weak = None

    lower_text = improved.lower()
    for weak, replacements in ACTION_VERB_MAP.items():
        if lower_text.startswith(weak):
            rep = replacements[index % len(replacements)]
            # Strip weak prefix
            rem = improved[len(weak):].lstrip(' :,-')
            # Capitalize next word
            if rem and rem[0].islower():
                rem = rem[0].lower() + rem[1:]
            improved = f"{rep} {rem}"
            matched_weak = weak
            explanation = f"Replaced passive starter '{weak}' with strong action verb '{rep}' and aligned to measurable results."
            break
        elif f" {weak} " in lower_text:
            rep = replacements[index % len(replacements)]
            improved = re.sub(r'\b' + re.escape(weak) + r'\b', rep.lower(), improved, count=1, flags=re.I)
            matched_weak = weak
            explanation = f"Converted passive phrase '{weak}' into impactful verb '{rep.lower()}'."
            break

    # If lacking metric prompt, append fill-in placeholder
    has_metric = bool(re.search(r'\b\d+(?:%|\+|k|x)?\b', improved, re.I))
    student_prompt = None
    if not has_metric:
        placeholder = " [Quantify impact: e.g. reduced processing time by X% or supported N concurrent users]"
        improved = improved.rstrip('.') + placeholder + "."
        student_prompt = "Add specific numerical metric or scale achieved"

    return {
        'id': f"sug_bullet_{index}",
        'section': 'bullet',
        'type': 'bullet_enhancement',
        'original': bullet_text,
        'improved': improved,
        'explanation': explanation,
        'student_prompt': student_prompt,
        'status': 'pending'
    }


def generate_rule_based_summary(
    current_summary: str,
    target_career: str,
    skills: List[str]
) -> Dict[str, Any]:
    """Fallback executive summary synthesizer."""
    top_skills = ', '.join([s.title() for s in skills[:5]]) if skills else "technical problem-solving and software engineering"
    role_label = (target_career or "Software Engineer").title()

    if current_summary and len(current_summary) > 25:
        improved = (
            f"Results-driven {role_label} with proven competency in {top_skills}. "
            f"{current_summary.strip()} Dedicated to building high-performance, maintainable solutions "
            f"and driving measurable technical value."
        )
        explanation = f"Structured existing summary into a punchy executive pitch emphasizing core skills ({top_skills}) and target career alignment."
    else:
        improved = (
            f"Motivated and detail-oriented aspiring {role_label} skilled in {top_skills}. "
            f"Passionate about applying modern industry methodologies to engineer scalable, reliable systems. "
            f"Eager to contribute technical proficiency and problem-solving skills in a high-impact team environment."
        )
        explanation = f"Created a professional, ATS-optimized career summary highlighting your demonstrated skills ({top_skills}) for {role_label} roles."

    return {
        'id': 'sug_summary',
        'section': 'summary',
        'type': 'summary_rewrite',
        'original': current_summary or "(No summary provided)",
        'improved': improved,
        'explanation': explanation,
        'student_prompt': "Review and customize the summary to reflect your personal career ambition",
        'status': 'pending'
    }


def enhance_resume_with_ai(
    parsed_sections: Dict[str, Any],
    analysis_results: Dict[str, Any],
    target_career: str = None
) -> Dict[str, Any]:
    """
    Main enhancement engine.
    Queries Gemini with strict anti-hallucination prompts.
    Falls back gracefully to deterministic rule-based generator on any exception.
    """
    weak_bullets = analysis_results.get('weak_bullet_points', [])
    missing_required = analysis_results.get('missing_required_skills', [])
    skills = parsed_sections.get('skills', [])
    summary = parsed_sections.get('summary', '')
    target = target_career or analysis_results.get('target_career', 'Software Engineer')

    # Prepare bullet samples for enhancement (up to 8 to stay concise and responsive)
    bullets_to_enhance = weak_bullets[:8]

    # Check if Gemini client is available
    ai_client = get_genai_client()

    gemini_suggestions = []
    gemini_summary = None

    if ai_client and (bullets_to_enhance or not summary):
        bullets_payload = [
            {"id": f"sug_b_{i}", "original": b['original_text'], "issues": b['issues']}
            for i, b in enumerate(bullets_to_enhance)
        ]

        prompt = f"""
You are the SkillBridge Resume Optimizer AI.
You help university students optimize their resume for applicant tracking systems (ATS) and human technical recruiters.

TARGET CAREER ROLE: {target}
CANDIDATE KNOWN SKILLS: {', '.join(skills) if skills else 'Not specified'}
CURRENT EXECUTIVE SUMMARY: "{summary}"

BULLET POINTS NEEDING IMPROVEMENT:
{json.dumps(bullets_payload, indent=2)}

STRICT ANTI-HALLUCINATION INSTRUCTIONS:
1. NEVER invent skills, qualifications, work experience, companies, or dates not present in the original text.
2. NEVER invent numerical metrics or fake accomplishments (e.g., do NOT claim "increased revenue by 45%" if the original did not state it).
3. If a bullet point lacks metrics or quantitative scale, convert it into an active STAR/XYZ statement (Action Verb + Context + Result) AND insert an explicit student fill-in placeholder:
   Format: [Quantify impact: e.g. reduced latency by X% or handled N records]
4. Replace weak or passive verbs (e.g., "responsible for", "helped", "worked on") with strong technical action verbs (e.g., "Architected", "Engineered", "Orchestrated", "Implemented", "Streamlined", "Refactored").
5. Write a concise, impactful 2-3 sentence Executive Summary tailored to {target}.
6. For each suggestion, provide a concise explanation (1 sentence) explaining why the change improves ATS match and recruiter appeal.

Respond with ONLY valid JSON with this exact schema:
{{
  "improved_summary": "...",
  "summary_explanation": "...",
  "enhanced_bullets": [
    {{
      "id": "sug_b_0",
      "improved": "...",
      "explanation": "...",
      "student_prompt": "Optional note if student must fill in a metric"
    }}
  ]
}}
"""
        models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"]
        for model in models_to_try:
            try:
                response = ai_client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                raw_text = (response.text or "").strip()
                # Clean Markdown code fences if returned
                if raw_text.startswith("```"):
                    raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
                    raw_text = re.sub(r'\s*```$', '', raw_text)

                data = json.loads(raw_text)
                if 'enhanced_bullets' in data:
                    gemini_suggestions = data['enhanced_bullets']
                    gemini_summary = data.get('improved_summary')
                    summary_exp = data.get('summary_explanation', 'Optimized summary for target role.')
                    break
            except Exception as e:
                logging.warning(f"Resume Optimizer Gemini call failed on model {model}: {e}")

    # Build final suggestions list combining Gemini or Fallback
    final_suggestions = []
    student_prompts = []

    # 1. Summary suggestion
    if gemini_summary:
        final_suggestions.append({
            'id': 'sug_summary',
            'section': 'summary',
            'type': 'summary_rewrite',
            'original': summary or "(No summary provided)",
            'improved': gemini_summary,
            'explanation': summary_exp,
            'student_prompt': 'Review and personalize this executive summary',
            'status': 'pending'
        })
    else:
        sum_sug = generate_rule_based_summary(summary, target, skills)
        final_suggestions.append(sum_sug)

    # 2. Bullet suggestions
    gemini_map = {item.get('id'): item for item in gemini_suggestions if isinstance(item, dict)}

    for i, weak_bullet in enumerate(bullets_to_enhance):
        gemini_item = gemini_map.get(f"sug_b_{i}")
        if gemini_item and gemini_item.get('improved'):
            final_suggestions.append({
                'id': f"sug_bullet_{i}",
                'section': weak_bullet.get('source', 'experience'),
                'item_index': weak_bullet.get('item_index', 0),
                'bullet_index': weak_bullet.get('bullet_index', 0),
                'type': 'bullet_enhancement',
                'original': weak_bullet['original_text'],
                'improved': gemini_item['improved'],
                'explanation': gemini_item.get('explanation', 'Enhanced with active action verb and STAR format.'),
                'student_prompt': gemini_item.get('student_prompt') or 'Provide specific measurable impact',
                'status': 'pending'
            })
            if gemini_item.get('student_prompt'):
                student_prompts.append({
                    'target': weak_bullet['original_text'][:40] + '...',
                    'prompt': gemini_item['student_prompt']
                })
        else:
            fallback_sug = generate_rule_based_enhancement(weak_bullet['original_text'], target, i)
            fallback_sug['section'] = weak_bullet.get('source', 'experience')
            fallback_sug['item_index'] = weak_bullet.get('item_index', 0)
            fallback_sug['bullet_index'] = weak_bullet.get('bullet_index', 0)
            final_suggestions.append(fallback_sug)
            if fallback_sug.get('student_prompt'):
                student_prompts.append({
                    'target': weak_bullet['original_text'][:40] + '...',
                    'prompt': fallback_sug['student_prompt']
                })

    # 3. Missing skills guidance suggestions (Strictly as student verification prompts)
    for i, missing_skill in enumerate(missing_required[:5]):
        final_suggestions.append({
            'id': f"sug_skill_{i}",
            'section': 'skills',
            'type': 'missing_skill_prompt',
            'original': f"Skill '{missing_skill}' missing from resume",
            'improved': f"Add '{missing_skill}' to Technical Skills (Only if proficient)",
            'explanation': f"The role '{target}' strongly emphasizes '{missing_skill}'. If you have completed projects, coursework, or self-study with this tool, add it.",
            'student_prompt': f"Verify you have hands-on experience in {missing_skill} before adding to your resume",
            'skill_to_add': missing_skill,
            'status': 'pending'
        })
        student_prompts.append({
            'target': f"Required Skill: {missing_skill}",
            'prompt': f"Confirm your personal knowledge of {missing_skill} before incorporating into projects."
        })

    # Generate an initial optimized copy of the parsed sections
    optimized_sections = json.loads(json.dumps(parsed_sections))

    # Apply summary suggestion to optimized draft
    if final_suggestions and final_suggestions[0]['type'] == 'summary_rewrite':
        optimized_sections['summary'] = final_suggestions[0]['improved']

    # Apply bullet suggestions to draft
    for sug in final_suggestions:
        if sug.get('type') == 'bullet_enhancement':
            sec = sug.get('section', '').lower()
            i_idx = sug.get('item_index', 0)
            b_idx = sug.get('bullet_index', 0)

            if 'experience' in sec and i_idx < len(optimized_sections.get('experience', [])):
                bullets = optimized_sections['experience'][i_idx].get('bullets', [])
                if b_idx < len(bullets):
                    bullets[b_idx] = sug['improved']
            elif 'project' in sec and i_idx < len(optimized_sections.get('projects', [])):
                bullets = optimized_sections['projects'][i_idx].get('bullets', [])
                if b_idx < len(bullets):
                    bullets[b_idx] = sug['improved']

    return {
        'suggestions': final_suggestions,
        'student_prompts': student_prompts,
        'optimized_sections': optimized_sections,
        'ai_powered': bool(gemini_suggestions or gemini_summary)
    }
