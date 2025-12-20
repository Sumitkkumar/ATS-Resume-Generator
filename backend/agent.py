import json
import os
import pathlib
import re
from dataclasses import dataclass
from typing import Dict

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# =========================
# LLM CLIENT (GEMINI ONLY)
# =========================

class LLMClient:
    def __init__(self, model: str = "models/gemini-3-flash-preview"):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def complete(self, prompt: str) -> str:
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 3500
            }
        )
        return response.text.strip()


# =========================
# CONFIG
# =========================

@dataclass
class JobResumeAgentConfig:
    model_name: str = "models/gemini-3-flash-preview"
    grey_hat: bool = True


# =========================
# AGENT
# =========================

class JobResumeAgent:
    def __init__(self, profile_path="profile.json", config=JobResumeAgentConfig()):
        self.profile = json.loads(pathlib.Path(profile_path).read_text())
        self.llm = LLMClient(model=config.model_name)
        self.grey_hat = config.grey_hat

    # -------------------------
    # Helpers
    # -------------------------

    def _normalize(self, s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    # -------------------------
    # Prompt (ATS-OPTIMIZED)
    # -------------------------

    def build_prompt(self, jd_text: str) -> str:
        profile_str = json.dumps(self.profile, indent=2)
        
        # Build detailed project requirements
        exp_details = []
        for exp in self.profile.get("experience", []):
            role_info = {
                "role": exp["role"],
                "role_id": self._normalize(exp["role"]),
                "projects": [p["title"] for p in exp.get("projects", [])]
            }
            exp_details.append(role_info)

        standalone_projects = [p["title"] for p in self.profile.get("projects", [])]
        
        # Build experience section template
        exp_template = []
        for exp in exp_details:
            role_section = f"ROLE_ID={exp['role_id']}\n"
            for proj in exp["projects"]:
                role_section += f"PROJECT: {proj}\n"
                role_section += f"- [Quantified bullet 1 for {proj}]\n"
                role_section += f"- [Quantified bullet 2 for {proj}]\n"
                role_section += f"- [Quantified bullet 3 for {proj}]\n\n"
            exp_template.append(role_section)
        
        # Build projects section template
        proj_template = []
        for proj in standalone_projects:
            proj_section = f"{proj}\n"
            proj_section += "- [Quantified bullet 1 with tech stack]\n"
            proj_section += "- [Quantified bullet 2 with impact]\n"
            proj_section += "- [Quantified bullet 3 with scale/metrics]\n\n"
            proj_template.append(proj_section)

        return f"""
            You are an expert ATS resume writer specializing in keyword optimization and role alignment.

            STEP 1 - ANALYZE THE JOB DESCRIPTION:
            Read the JD carefully and extract:
            1. All technologies, tools, frameworks, and platforms mentioned.
            2. Which skills are core vs supporting.
            3. What outcomes matter most (performance, scale, reliability, cost, UX, automation).
            4. The dominant role focus (Backend, Frontend, Full-Stack, Cloud, Data, etc.).

            STEP 2 - ANALYZE THE CANDIDATE PROFILE:
            From the candidate profile, identify:
            - Core skills they clearly possess.
            - Projects and experience that can support JD requirements.
            - Technologies that naturally coexist with their existing stack.

            STEP 3 - SKILL EXPANSION LOGIC (IMPORTANT):
            You are ALLOWED to add skills from the JOB DESCRIPTION even if they do NOT appear in the profile, under the following rules:

            ✓ JD-only skills MAY be added to the SKILLS section  
            ✓ JD-only skills MUST be:
            - Logically adjacent to existing profile skills
            - Commonly used together in real-world projects
            - Framed as applied/working exposure (not deep expertise)

            ✗ DO NOT claim leadership or ownership for JD-only skills  

            EXAMPLES:
            - Profile has Spring Boot, JD mentions Kafka → Kafka allowed
            - Profile has React, JD mentions Redux → Redux allowed

            STEP 4 - RESUME TAILORING RULES:
            Create a resume that:
            - Maximizes keyword overlap with the JD
            - Uses JD language naturally
            - Shows quantified impact everywhere
            - Keeps experience believable and internally consistent

            CRITICAL RULES (DO NOT VIOLATE):
            ✓ Do NOT include name, contact info, or location  
            ✓ Start directly with SUMMARY  
            ✓ EVERY project MUST have EXACTLY 3 bullet points  
            ✓ EVERY bullet MUST include quantified metrics (%, scale, latency, cost, users, time)  
            ✓ Use plain text ONLY (no markdown, no symbols like ** or ##)  
            ✓ Do NOT change company names, roles, or dates  
            ✓ Do NOT invent education or certifications  

            SKILLS SECTION RULES:
            - Include ALL relevant profile skills
            - Include JD-only skills that meet expansion rules
            - Order skills strictly by JD importance
            - Use a dense, ATS-friendly comma-separated list

            EXPERIENCE & PROJECT RULES:
            - JD-only skills MUST appear in bullets to justify their presence in SKILLS
            - Use verbs like:
            integrated, implemented, utilized, supported, collaborated on, worked with
            - Avoid words like:
            expert, led, owned (unless profile clearly supports it)

            PROFILE DATA:
            {profile_str}

            JOB DESCRIPTION:
            {jd_text}

            REQUIRED OUTPUT FORMAT (EXACT):

            SUMMARY:
            [3-4 lines tailored to the JD using its keywords]

            SKILLS:
            [Comma-separated list ordered by JD priority. Include profile skills + allowed JD-only skills.]

            EXPERIENCE:
            {''.join(exp_template)}

            PROJECTS:
            {''.join(proj_template)}

            FINAL REMINDERS:
            - Every JD keyword you add to SKILLS must appear somewhere in bullets
            - Every bullet must show impact
            - Complete ALL sections before stopping
            - Do not add any explanation text

            Generate the tailored resume now:
            """

    # -------------------------
    # Parsing (WITH DEBUG)
    # -------------------------

    def parse(self, text: str) -> Dict:
        sections = {
            "summary": [],
            "skills": [],
            "experience": {},
            "projects": {}
        }

        # Split into major sections first
        lines = text.splitlines()
        i = 0
        
        print("\n=== PARSING DEBUG ===")
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Check for section headers
            header = re.sub(r"[^a-z]", "", line.lower())
            
            # SUMMARY section
            if header == "summary":
                i += 1
                while i < len(lines):
                    l = lines[i].strip()
                    if not l:
                        i += 1
                        continue
                    next_header = re.sub(r"[^a-z]", "", l.lower())
                    if next_header in ["skills", "experience", "projects", "education"]:
                        break
                    sections["summary"].append(l)
                    i += 1
                continue
            
            # SKILLS section
            elif header == "skills":
                i += 1
                while i < len(lines):
                    l = lines[i].strip()
                    if not l:
                        i += 1
                        continue
                    next_header = re.sub(r"[^a-z]", "", l.lower())
                    if next_header in ["summary", "experience", "projects", "education"]:
                        break
                    parts = re.split(r"[,|.]", l)
                    sections["skills"].extend(p.strip() for p in parts if p.strip())
                    i += 1
                continue
            
            # EXPERIENCE section
            elif header == "experience":
                i += 1
                current_role = None
                current_project = None
                
                while i < len(lines):
                    l = lines[i].strip()
                    if not l:
                        i += 1
                        continue
                    
                    next_header = re.sub(r"[^a-z]", "", l.lower())
                    if next_header in ["summary", "skills", "projects", "education", "certifications"]:
                        break
                    
                    # Check for role
                    if "role_id=" in l.lower():
                        current_role = self._normalize(l.split("=", 1)[1])
                        sections["experience"].setdefault(current_role, {})
                        current_project = None
                        print(f"Line {i}: Found role '{current_role}'")
                    # Check for project
                    elif l.lower().startswith("project:"):
                        project_name = l.split(":", 1)[1].strip()
                        current_project = self._normalize(project_name)
                        if current_role:
                            sections["experience"][current_role].setdefault(current_project, [])
                            print(f"Line {i}: Found project '{project_name}' under role '{current_role}'")
                    # Check for bullet
                    elif l.startswith("-") or l.startswith("•"):
                        bullet = l[1:].strip()
                        if current_role and current_project and bullet:
                            sections["experience"][current_role][current_project].append(bullet)
                            print(f"Line {i}: Added bullet to {current_role}/{current_project}")
                    
                    i += 1
                continue
            
            # PROJECTS section
            elif header == "projects":
                i += 1
                current_project = None

                while i < len(lines):
                    l = lines[i].strip()

                    if not l:
                        i += 1
                        continue

                    next_header = re.sub(r"[^a-z]", "", l.lower())
                    if next_header in ["summary", "skills", "experience", "education", "certifications", "achievements"]:
                        break

                    # BULLET
                    if l.startswith("-") or l.startswith("•"):
                        bullet = l[1:].strip()
                        if current_project and bullet:
                            sections["projects"][current_project].append(bullet)
                        i += 1
                        continue

                    # NEW PROJECT TITLE (standalone)
                    is_likely_title = (
                        len(l) <= 80 and
                        not l.endswith(".") and
                        not l.endswith(":") and
                        not l.isupper()
                    )

                    if is_likely_title:
                        current_project = self._normalize(l)
                        sections["projects"][current_project] = []
                        i += 1
                        continue

                    # OTHERWISE: ignore (do NOT append to previous bullet)
                    i += 1

                continue
            
            i += 1

        # Print summary
        print("\n=== PARSING SUMMARY ===")
        print(f"Summary lines: {len(sections['summary'])}")
        print(f"Skills count: {len(sections['skills'])}")
        print(f"Experience roles: {list(sections['experience'].keys())}")
        for role, projects in sections['experience'].items():
            print(f"  {role}:")
            for proj, bullets in projects.items():
                print(f"    {proj}: {len(bullets)} bullets")
        print(f"Standalone projects: {list(sections['projects'].keys())}")
        for proj, bullets in sections['projects'].items():
            print(f"  {proj}: {len(bullets)} bullets")
        print("===================\n")

        return sections

    # -------------------------
    # PDF (ATS-FRIENDLY)
    # -------------------------

    def build_pdf(self, sections: Dict) -> bytes:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()

        pdf.add_font("Noto", "", "fonts/NotoSans-Regular.ttf", uni=True)
        pdf.add_font("Noto", "B", "fonts/NotoSans-Bold.ttf", uni=True)

        # HEADER
        pdf.set_font("Noto", "B", 16)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 10, self.profile["name"], ln=1)

        pdf.set_font("Noto", "", 10)
        pdf.set_x(pdf.l_margin)

        email = (self.profile.get("email") or "").strip()
        phone = self.profile.get("phone", "").strip()
        linkedin = (self.profile.get("links", {}).get("linkedin") or "").strip()
        github = (self.profile.get("links", {}).get("github") or "").strip()

        # Render as ONE wrapped line (ATS-safe) - using bullet separators instead of pipes
        contact_parts = []
        if email:
            contact_parts.append(email)
        if phone:
            contact_parts.append(phone)
        if linkedin:
            contact_parts.append(linkedin)
        if github:
            contact_parts.append(github)
        
        contact_line = " | ".join(contact_parts)  # Using bullet separator

        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, contact_line)

        pdf.ln(2)

        # TITLE
        pdf.set_font("Noto", "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, self.profile.get("title", ""))
        pdf.ln(3)

        # SUMMARY
        pdf.set_font("Noto", "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, "SUMMARY", ln=1)

        pdf.set_font("Noto", "", 10)
        pdf.set_x(pdf.l_margin)
        summary_text = "\n".join(sections["summary"]) if sections["summary"] else "No summary generated"
        pdf.multi_cell(0, 5, summary_text)
        pdf.ln(2)

        # SKILLS
        pdf.set_font("Noto", "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, "SKILLS", ln=1)

        pdf.set_font("Noto", "", 9)
        skills = list(dict.fromkeys(sections["skills"]))
        skills_text = ", ".join(skills) if skills else "No skills generated"
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, skills_text)
        pdf.ln(2)

        # EXPERIENCE (ROLE-BASED WITH PROJECTS)
        pdf.set_font("Noto", "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, "EXPERIENCE", ln=1)

        for exp in self.profile.get("experience", []):
            role_key = self._normalize(exp["role"])
            
            # Role header
            pdf.set_font("Noto", "B", 10)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                0, 5,
                f'{exp["role"]} | {exp["company"]} | {exp["start"]} - {exp["end"]}'
            )

            # Get projects for this role
            role_projects = sections["experience"].get(role_key, {})
            
            # Render each work project under this role
            for work_proj in exp.get("projects", []):
                proj_key = self._normalize(work_proj["title"])
                bullets = role_projects.get(proj_key, [])
                
                # Always show project title even if no bullets
                pdf.set_font("Noto", "B", 9)
                pdf.set_x(pdf.l_margin + 5)
                # Use multi_cell with tight spacing
                pdf.multi_cell(0, 4, work_proj["title"])
                
                if bullets:
                    pdf.set_font("Noto", "", 9)
                    for b in bullets:
                        pdf.set_x(pdf.l_margin + 5)
                        pdf.multi_cell(0, 5, f"• {b}")
                else:
                    # Show warning if no bullets
                    pdf.set_font("Noto", "", 8)
                    pdf.set_x(pdf.l_margin + 5)
                    pdf.multi_cell(0, 5, "- [No content generated for this project]")
            
            # If there are general bullets (not associated with a project)
            general_bullets = role_projects.get("general", [])
            if general_bullets:
                pdf.set_font("Noto", "", 9)
                for b in general_bullets:
                    pdf.set_x(pdf.l_margin + 5)
                    pdf.multi_cell(0, 5, f"• {b}")
            
            pdf.ln(2)

        # STANDALONE PROJECTS
        if self.profile.get("projects"):
            pdf.set_font("Noto", "B", 12)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 8, "PROJECTS", ln=1)

            for idx, p in enumerate(self.profile["projects"]):
                title = p["title"]
                norm_title = self._normalize(title)
                
                print(f"\n=== Looking for project: '{title}' (normalized: '{norm_title}') ===")
                print(f"Available keys in sections['projects']: {list(sections['projects'].keys())}")

                # Add spacing before project title (except first)
                if idx > 0:
                    pdf.ln(2)

                pdf.set_font("Noto", "B", 10)
                pdf.set_x(pdf.l_margin)
                # Use multi_cell with tight line height instead of cell
                pdf.multi_cell(0, 4, title)

                pdf.set_font("Noto", "", 9)
                bullets = sections["projects"].get(norm_title, [])
                
                print(f"Found {len(bullets)} bullets for '{title}'")
                
                if bullets:
                    for bullet_idx, b in enumerate(bullets):
                        # Debug: Check for leading newlines or spaces
                        if bullet_idx == 0:
                            print(f"First bullet raw repr: {repr(b[:100])}")
                        pdf.set_x(pdf.l_margin)
                        pdf.multi_cell(0, 5, f"• {b}")
                else:
                    pdf.set_font("Noto", "", 8)
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 5, "- [No content generated for this project]")

        # EDUCATION
        pdf.set_font("Noto", "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, "EDUCATION", ln=1)

        pdf.set_font("Noto", "", 10)
        for edu in self.profile.get("education", []):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                0, 5,
                f'{edu["degree"]} | {edu["school"]} | {edu.get("cgpa","")} | {edu["year"]}'
            )

        # CERTIFICATIONS
        if self.profile.get("certifications"):
            pdf.set_font("Noto", "B", 12)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 8, "CERTIFICATIONS", ln=1)

            pdf.set_font("Noto", "", 9)
            for c in self.profile["certifications"]:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, f"• {c}")

        # ACHIEVEMENTS
        if self.profile.get("achievements"):
            pdf.set_font("Noto", "B", 12)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 8, "ACHIEVEMENTS", ln=1)

            pdf.set_font("Noto", "", 9)
            for a in self.profile["achievements"]:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, f"• {a}")

        return bytes(pdf.output(dest="S"))

    # -------------------------
    # PUBLIC API
    # -------------------------

    def generate(self, jd: str) -> bytes:
        prompt = self.build_prompt(jd)
        
        print("\n=== GENERATED PROMPT ===")
        print(prompt)
        print("========================\n")
        
        output = self.llm.complete(prompt)

        print("\n=== LLM OUTPUT ===")
        print(output)
        print("==================\n")

        with open("llm_output.txt", "w", encoding="utf-8") as f:
            f.write(output)

        sections = self.parse(output)
        
        # Save parsed sections for debugging
        with open("parsed_sections.json", "w", encoding="utf-8") as f:
            json.dump(sections, f, indent=2)
        
        return self.build_pdf(sections)