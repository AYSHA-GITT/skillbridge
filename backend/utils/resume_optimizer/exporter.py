"""
SkillLens AI - Resume Optimizer: Exporter
Generates professional, ATS-compliant PDF and DOCX resumes from structured data.
Streams files directly into memory buffers without altering original student files.
"""

import io
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)


def generate_resume_docx(sections: Dict[str, Any]) -> io.BytesIO:
    """
    Creates a clean, ATS-compliant Word document (.docx) using python-docx.
    """
    doc = Document()

    # Set 0.5 inch page margins
    sections_docx = doc.sections
    for section in sections_docx:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)

    contact = sections.get('contact', {})
    name = contact.get('name') or "Candidate Name"

    # Name Header
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(2)
    run_name = p_name.add_run(name)
    run_name.font.name = 'Calibri'
    run_name.font.size = Pt(20)
    run_name.font.bold = True
    run_name.font.color.rgb = RGBColor(17, 24, 39)  # Dark charcoal

    # Contact line
    contact_parts = []
    if contact.get('phone'):
        contact_parts.append(contact['phone'])
    if contact.get('email'):
        contact_parts.append(contact['email'])
    if contact.get('linkedin'):
        contact_parts.append(contact['linkedin'])
    if contact.get('github'):
        contact_parts.append(contact['github'])
    if contact.get('location'):
        contact_parts.append(contact['location'])

    if contact_parts:
        p_contact = doc.add_paragraph()
        p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_contact.paragraph_format.space_after = Pt(10)
        p_contact.paragraph_format.space_before = Pt(0)
        run_contact = p_contact.add_run("  |  ".join(contact_parts))
        run_contact.font.name = 'Calibri'
        run_contact.font.size = Pt(9.5)
        run_contact.font.color.rgb = RGBColor(75, 85, 99)

    def add_section_header(title: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title.upper())
        run.font.name = 'Calibri'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(15, 118, 110)  # Teal/Accent brand color

    # Executive Summary
    summary = sections.get('summary', '').strip()
    if summary:
        add_section_header("Professional Summary")
        p_sum = doc.add_paragraph()
        p_sum.paragraph_format.space_after = Pt(6)
        p_sum.paragraph_format.line_spacing = 1.15
        run_sum = p_sum.add_run(summary)
        run_sum.font.name = 'Calibri'
        run_sum.font.size = Pt(10)

    # Technical Skills
    skills = sections.get('skills', [])
    if skills:
        add_section_header("Technical Skills")
        p_sk = doc.add_paragraph()
        p_sk.paragraph_format.space_after = Pt(6)
        run_sk_label = p_sk.add_run("Core Competencies: ")
        run_sk_label.font.name = 'Calibri'
        run_sk_label.font.size = Pt(10)
        run_sk_label.font.bold = True
        run_sk = p_sk.add_run(", ".join(skills))
        run_sk.font.name = 'Calibri'
        run_sk.font.size = Pt(10)

    # Work Experience
    experience = sections.get('experience', [])
    if experience:
        add_section_header("Work Experience")
        for exp in experience:
            p_exp_head = doc.add_paragraph()
            p_exp_head.paragraph_format.space_before = Pt(4)
            p_exp_head.paragraph_format.space_after = Pt(1)
            p_exp_head.paragraph_format.keep_with_next = True

            role = exp.get('role', '')
            company = exp.get('company', '')
            period = exp.get('period', '')
            location = exp.get('location', '')

            run_role = p_exp_head.add_run(role)
            run_role.font.name = 'Calibri'
            run_role.font.size = Pt(10.5)
            run_role.font.bold = True

            if company:
                run_sep = p_exp_head.add_run(" — ")
                run_sep.font.name = 'Calibri'
                run_company = p_exp_head.add_run(company)
                run_company.font.name = 'Calibri'
                run_company.font.size = Pt(10)
                run_company.font.italic = True

            meta_items = [item for item in [location, period] if item]
            if meta_items:
                run_meta = p_exp_head.add_run(f"  ({', '.join(meta_items)})")
                run_meta.font.name = 'Calibri'
                run_meta.font.size = Pt(9.5)
                run_meta.font.color.rgb = RGBColor(107, 114, 128)

            for bullet in exp.get('bullets', []):
                p_b = doc.add_paragraph(style='List Bullet')
                p_b.paragraph_format.space_before = Pt(0)
                p_b.paragraph_format.space_after = Pt(2)
                p_b.paragraph_format.line_spacing = 1.15
                run_b = p_b.add_run(bullet.strip())
                run_b.font.name = 'Calibri'
                run_b.font.size = Pt(9.5)

    # Projects
    projects = sections.get('projects', [])
    if projects:
        add_section_header("Key Projects")
        for proj in projects:
            p_proj_head = doc.add_paragraph()
            p_proj_head.paragraph_format.space_before = Pt(4)
            p_proj_head.paragraph_format.space_after = Pt(1)
            p_proj_head.paragraph_format.keep_with_next = True

            name = proj.get('name', 'Project')
            tech = proj.get('technologies', '')

            run_pname = p_proj_head.add_run(name)
            run_pname.font.name = 'Calibri'
            run_pname.font.size = Pt(10.5)
            run_pname.font.bold = True

            if tech:
                run_tech = p_proj_head.add_run(f" | {tech}")
                run_tech.font.name = 'Calibri'
                run_tech.font.size = Pt(9.5)
                run_tech.font.italic = True
                run_tech.font.color.rgb = RGBColor(15, 118, 110)

            for bullet in proj.get('bullets', []):
                p_b = doc.add_paragraph(style='List Bullet')
                p_b.paragraph_format.space_before = Pt(0)
                p_b.paragraph_format.space_after = Pt(2)
                p_b.paragraph_format.line_spacing = 1.15
                run_b = p_b.add_run(bullet.strip())
                run_b.font.name = 'Calibri'
                run_b.font.size = Pt(9.5)

    # Education
    education = sections.get('education', [])
    if education:
        add_section_header("Education")
        for edu in education:
            p_edu = doc.add_paragraph()
            p_edu.paragraph_format.space_before = Pt(2)
            p_edu.paragraph_format.space_after = Pt(2)

            degree = edu.get('degree', '')
            inst = edu.get('institution', '')
            year = edu.get('year', '')
            score = edu.get('score', '')

            if degree:
                run_deg = p_edu.add_run(degree)
                run_deg.font.name = 'Calibri'
                run_deg.font.size = Pt(10)
                run_deg.font.bold = True

            if inst:
                sep = " — " if degree else ""
                run_inst = p_edu.add_run(f"{sep}{inst}")
                run_inst.font.name = 'Calibri'
                run_inst.font.size = Pt(10)

            details = [d for d in [year, score] if d]
            if details:
                run_det = p_edu.add_run(f"  ({', '.join(details)})")
                run_det.font.name = 'Calibri'
                run_det.font.size = Pt(9)
                run_det.font.color.rgb = RGBColor(107, 114, 128)

    # Certifications
    certifications = sections.get('certifications', [])
    if certifications:
        add_section_header("Certifications & Achievements")
        for cert in certifications:
            p_cert = doc.add_paragraph(style='List Bullet')
            p_cert.paragraph_format.space_before = Pt(0)
            p_cert.paragraph_format.space_after = Pt(1.5)
            run_c = p_cert.add_run(cert.strip())
            run_c.font.name = 'Calibri'
            run_c.font.size = Pt(9.5)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def generate_resume_pdf(sections: Dict[str, Any]) -> io.BytesIO:
    """
    Creates an ATS-friendly, clean modern PDF using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    style_name = ParagraphStyle(
        'ResumeName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1,  # Centered
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=2
    )

    style_contact = ParagraphStyle(
        'ResumeContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=1,  # Centered
        textColor=colors.HexColor('#475569'),
        spaceAfter=8
    )

    style_heading = ParagraphStyle(
        'ResumeHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#0d9488'),  # Teal-600
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'ResumeBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=4
    )

    style_item_title = ParagraphStyle(
        'ResumeItemTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#0f172a'),
        keepWithNext=True
    )

    style_item_meta = ParagraphStyle(
        'ResumeItemMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        alignment=2,  # Right aligned
        keepWithNext=True
    )

    style_bullet = ParagraphStyle(
        'ResumeBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        leftIndent=12,
        firstLineIndent=-10,
        textColor=colors.HexColor('#334155'),
        spaceAfter=2
    )

    story = []

    contact = sections.get('contact', {})
    name = contact.get('name') or "Candidate Name"
    story.append(Paragraph(f"<b>{name}</b>", style_name))

    contact_parts = []
    if contact.get('phone'):
        contact_parts.append(contact['phone'])
    if contact.get('email'):
        contact_parts.append(contact['email'])
    if contact.get('linkedin'):
        contact_parts.append(contact['linkedin'])
    if contact.get('github'):
        contact_parts.append(contact['github'])
    if contact.get('location'):
        contact_parts.append(contact['location'])

    if contact_parts:
        story.append(Paragraph(" &nbsp;|&nbsp; ".join(contact_parts), style_contact))

    def add_section_divider(title: str):
        story.append(Paragraph(f"<b>{title.upper()}</b>", style_heading))
        story.append(HRFlowable(
            width="100%", thickness=0.75, color=colors.HexColor('#0d9488'),
            spaceBefore=1, spaceAfter=4
        ))

    # Summary
    summary = sections.get('summary', '').strip()
    if summary:
        add_section_divider("Professional Summary")
        story.append(Paragraph(summary, style_body))

    # Skills
    skills = sections.get('skills', [])
    if skills:
        add_section_divider("Technical Skills")
        skills_str = "<b>Core Competencies:</b> " + ", ".join(skills)
        story.append(Paragraph(skills_str, style_body))

    # Experience
    experience = sections.get('experience', [])
    if experience:
        add_section_divider("Work Experience")
        for exp in experience:
            role = exp.get('role', '')
            company = exp.get('company', '')
            period = exp.get('period', '')
            location = exp.get('location', '')

            title_html = f"<b>{role}</b>"
            if company:
                title_html += f" &nbsp;—&nbsp; <i>{company}</i>"

            meta_html = period or ""
            if location:
                meta_html += f" | {location}" if meta_html else location

            # Row with Role on Left and Date on Right
            row_table = Table(
                [[Paragraph(title_html, style_item_title), Paragraph(meta_html, style_item_meta)]],
                colWidths=[400, 140]
            )
            row_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(row_table)

            for bullet in exp.get('bullets', []):
                clean_b = bullet.strip().lstrip('•-* ')
                story.append(Paragraph(f"&bull; {clean_b}", style_bullet))
            story.append(Spacer(1, 3))

    # Projects
    projects = sections.get('projects', [])
    if projects:
        add_section_divider("Key Projects")
        for proj in projects:
            p_name = proj.get('name', 'Project')
            tech = proj.get('technologies', '')

            title_html = f"<b>{p_name}</b>"
            meta_html = f"<i>{tech}</i>" if tech else ""

            row_table = Table(
                [[Paragraph(title_html, style_item_title), Paragraph(meta_html, style_item_meta)]],
                colWidths=[360, 180]
            )
            row_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(row_table)

            for bullet in proj.get('bullets', []):
                clean_b = bullet.strip().lstrip('•-* ')
                story.append(Paragraph(f"&bull; {clean_b}", style_bullet))
            story.append(Spacer(1, 3))

    # Education
    education = sections.get('education', [])
    if education:
        add_section_divider("Education")
        for edu in education:
            degree = edu.get('degree', '')
            inst = edu.get('institution', '')
            year = edu.get('year', '')
            score = edu.get('score', '')

            deg_html = f"<b>{degree}</b>" if degree else ""
            if inst:
                deg_html += f" &nbsp;—&nbsp; {inst}"

            det_list = [d for d in [year, score] if d]
            det_html = ", ".join(det_list)

            row_table = Table(
                [[Paragraph(deg_html, style_body), Paragraph(det_html, style_item_meta)]],
                colWidths=[420, 120]
            )
            row_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(row_table)

    # Certifications
    certifications = sections.get('certifications', [])
    if certifications:
        add_section_divider("Certifications & Honors")
        for cert in certifications:
            clean_c = cert.strip().lstrip('•-* ')
            story.append(Paragraph(f"&bull; {clean_c}", style_bullet))

    doc.build(story)
    buffer.seek(0)
    return buffer
