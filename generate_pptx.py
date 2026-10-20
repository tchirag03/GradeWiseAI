import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_full_presentation():
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    C_PRIMARY = RGBColor(30, 60, 140)      # Navy / Steel Blue
    C_BANNER = RGBColor(18, 42, 105)       # Deep Navy
    C_WHITE = RGBColor(255, 255, 255)
    C_TEXT = RGBColor(50, 50, 50)
    C_MUTED = RGBColor(110, 110, 110)
    C_CARD_BG = RGBColor(245, 247, 251)
    C_CARD_BORDER = RGBColor(215, 225, 240)
    C_GOLD = RGBColor(210, 160, 40)
    C_GREEN = RGBColor(34, 139, 34)
    C_RED = RGBColor(200, 40, 40)
    C_ORANGE = RGBColor(220, 100, 20)
    C_LIGHT_GREEN = RGBColor(240, 253, 244)
    C_LIGHT_RED = RGBColor(254, 242, 242)

    def add_header(slide, title_text, category_text="Project Phase 2 – Review 1"):
        # Top banner
        banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
        banner.fill.solid()
        banner.fill.fore_color.rgb = C_PRIMARY
        banner.line.fill.background()

        # Category
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.12), Inches(9.0), Inches(0.28))
        tf_cat = cat_box.text_frame
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_GOLD

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.5), Inches(0.65))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(21)
        p.font.bold = True
        p.font.color.rgb = C_WHITE

        # Footer line & text
        foot_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(7.1), Inches(11.733), Inches(0.02))
        foot_line.fill.solid()
        foot_line.fill.fore_color.rgb = C_CARD_BORDER
        foot_line.line.fill.background()

        foot_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.12), Inches(11.733), Inches(0.3))
        p_foot = foot_box.text_frame.paragraphs[0]
        p_foot.text = "Sustainable AI Assessment Platform • B.M.S. College of Engineering • Dept. of CSE (Data Science)"
        p_foot.font.size = Pt(9)
        p_foot.font.color.rgb = C_MUTED

    def add_card(slide, left, top, width, height, title, bg_color=C_CARD_BG, border_color=C_CARD_BORDER, title_color=C_PRIMARY):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)

        if title:
            tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.15), Inches(width - 0.4), Inches(0.4))
            p = tb.text_frame.paragraphs[0]
            p.text = title
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = title_color
        return card

    def add_table_slide(slide, title, category, headers, rows_data, col_widths, top_pos=1.5, height_pos=5.3):
        add_header(slide, title, category)
        num_rows = len(rows_data) + 1
        num_cols = len(headers)
        
        t_shape = slide.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(top_pos), Inches(11.733), Inches(height_pos))
        tbl = t_shape.table
        
        for idx, w in enumerate(col_widths):
            tbl.columns[idx].width = Inches(w)
            
        for c_idx, h in enumerate(headers):
            cell = tbl.cell(0, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_PRIMARY
            p = cell.text_frame.paragraphs[0]
            p.text = h
            p.font.bold = True
            p.font.size = Pt(11)
            p.font.color.rgb = C_WHITE
            
        for r_idx, r_data in enumerate(rows_data, start=1):
            for c_idx, val in enumerate(r_data):
                cell = tbl.cell(r_idx, c_idx)
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_CARD_BG if r_idx % 2 == 1 else C_WHITE
                p = cell.text_frame.paragraphs[0]
                p.text = str(val)
                p.font.size = Pt(10)
                p.font.color.rgb = C_TEXT
                if c_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = C_PRIMARY

    # ==========================================
    # SLIDE 1: Title
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    bg = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_BANNER
    bg.line.fill.background()

    card1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(0.8), Inches(10.333), Inches(5.9))
    card1.fill.solid()
    card1.fill.fore_color.rgb = C_WHITE
    card1.line.color.rgb = C_GOLD
    card1.line.width = Pt(2.5)

    tb = s1.shapes.add_textbox(Inches(1.8), Inches(1.1), Inches(9.733), Inches(2.0))
    p = tb.text_frame.paragraphs[0]
    p.text = "Sustainable AI Assessment Platform\nfor Algorithmic Problem Solving"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY
    p.alignment = PP_ALIGN.CENTER

    p2 = tb.text_frame.add_paragraph()
    p2.text = "Project Phase 2 – Review 1: Technical Advancements, Validation & Deployment"
    p2.font.size = Pt(15)
    p2.font.bold = True
    p2.font.color.rgb = C_GOLD
    p2.alignment = PP_ALIGN.CENTER

    info_box = s1.shapes.add_textbox(Inches(1.8), Inches(3.3), Inches(9.733), Inches(3.0))
    tf = info_box.text_frame
    p_team = tf.paragraphs[0]
    p_team.text = "Presented by Team 17:"
    p_team.font.bold = True
    p_team.font.size = Pt(13)
    p_team.font.color.rgb = C_TEXT
    p_team.alignment = PP_ALIGN.CENTER

    p_names = tf.add_paragraph()
    p_names.text = "Chirag T (1BM23CD013)   •   Mohammed Arshaq T (1BM23CD039)   •   Sudeeksha Reddy (1BM23CD027)"
    p_names.font.bold = True
    p_names.font.size = Pt(14)
    p_names.font.color.rgb = C_PRIMARY
    p_names.alignment = PP_ALIGN.CENTER

    p_sp = tf.add_paragraph()
    p_sp.text = ""

    p_guide = tf.add_paragraph()
    p_guide.text = "Under the Guidance of: Prof. Indra R"
    p_guide.font.bold = True
    p_guide.font.size = Pt(13)
    p_guide.font.color.rgb = C_TEXT
    p_guide.alignment = PP_ALIGN.CENTER

    p_inst = tf.add_paragraph()
    p_inst.text = "Assistant Professor, Dept. of CSE (Data Science)\nB.M.S. College of Engineering, Bengaluru (Autonomous Institute Affiliated to VTU)\nAcademic Year 2025–2026"
    p_inst.font.size = Pt(12)
    p_inst.font.color.rgb = C_MUTED
    p_inst.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 2: Problem Background
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Problem Background & Academic Motivation")
    add_card(s2, 1.0, 1.5, 5.4, 4.6, "The Context")
    tb = s2.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(5.0), Inches(3.6))
    tf = tb.text_frame
    tf.word_wrap = True
    bullets2_1 = [
        ("Descriptive Algorithmic Answers: ", "CS courses require detailed explanations of logic, recurrence relations, intermediate states, and asymptotic complexity."),
        ("Manual Evaluation Fatigue: ", "Grading hundreds of handwritten answer scripts is highly repetitive, slow, and prone to grader fatigue."),
        ("Lack of Granular Feedback: ", "Students rarely receive step-by-step diagnostic feedback on proofs, trees, or algorithm traces.")
    ]
    for i, (b, n) in enumerate(bullets2_1):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(13); r1.font.color.rgb = C_PRIMARY
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(13); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(12)

    add_card(s2, 6.9, 1.5, 5.4, 4.6, "Why This Matters")
    tb = s2.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.0), Inches(3.6))
    tf = tb.text_frame
    tf.word_wrap = True
    bullets2_2 = [
        ("Institutional Scalability: ", "Batch sizes exceeding 120+ students make thorough, continuous evaluation challenging for single instructors."),
        ("Subjectivity & Variance: ", "Human evaluators apply inconsistent standards across a batch, leading to grade variations of up to ±15%."),
        ("Pedagogical Value: ", "Immediate diagnostic feedback allows students to rectify misconceptions before summative examinations.")
    ]
    for i, (b, n) in enumerate(bullets2_2):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(13); r1.font.color.rgb = C_ORANGE
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(13); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(12)

    bot = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(6.3), Inches(11.333), Inches(0.6))
    bot.fill.solid(); bot.fill.fore_color.rgb = C_PRIMARY; bot.line.fill.background()
    p = bot.text_frame.paragraphs[0]
    p.text = '"A pressing need for an efficient, transparent, and scalable assessment platform."'
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = C_WHITE; p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 3: Problem Statement
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Problem Statement & Project Scope")

    hero = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.5), Inches(11.333), Inches(1.3))
    hero.fill.solid(); hero.fill.fore_color.rgb = RGBColor(254, 243, 199)
    hero.line.color.rgb = C_GOLD; hero.line.width = Pt(2)
    p_h1 = hero.text_frame.paragraphs[0]
    p_h1.text = "PROBLEM DEFINITION"
    p_h1.font.size = Pt(11); p_h1.font.bold = True; p_h1.font.color.rgb = C_ORANGE
    p_h2 = hero.text_frame.add_paragraph()
    p_h2.text = "Develop a sustainable and privacy-preserving AI system to automatically evaluate descriptive algorithmic answer sheets using structured, rubric-based scoring."
    p_h2.font.size = Pt(15); p_h2.font.bold = True; p_h2.font.color.rgb = C_PRIMARY

    pillars = [
        ("Core Scope", "Handwritten Solutions", "Evaluates handwritten descriptive solutions using Vision-Language Models (VLMs) and structured institutional course rubrics.", C_PRIMARY),
        ("Hardware Constraint", "100% Offline (Local CPU)", "Runs entirely locally on standard CPU hardware with zero cloud APIs, ensuring student data privacy and zero recurring subscription fees.", C_GREEN),
        ("Pedagogical Impact", "Transparent & Auditable", "Scores are tied directly to explicit rubric components with justification lines and Stage 4 human-in-the-loop review.", C_ORANGE)
    ]
    for i, (head, sub, desc, col) in enumerate(pillars):
        x = 1.0 + i * 3.9
        add_card(s3, x, 3.1, 3.5, 3.7, head, title_color=col)
        tb = s3.shapes.add_textbox(Inches(x + 0.2), Inches(3.7), Inches(3.1), Inches(2.9))
        tf = tb.text_frame; tf.word_wrap = True
        p_sub = tf.paragraphs[0]; p_sub.text = sub; p_sub.font.bold = True; p_sub.font.size = Pt(13); p_sub.font.color.rgb = col; p_sub.space_after = Pt(10)
        p_desc = tf.add_paragraph(); p_desc.text = desc; p_desc.font.size = Pt(12); p_desc.font.color.rgb = C_TEXT

    # ==========================================
    # SLIDE 4: Motivation & Need
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Motivation & Need for Proposed System")
    add_card(s4, 1.0, 1.5, 5.4, 5.3, "Limitations of Existing Automated Grading Systems", border_color=C_RED, title_color=C_RED)
    tb = s4.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(5.0), Inches(4.3))
    tf = tb.text_frame; tf.word_wrap = True
    m_limits = [
        ("Restricted Input Formats: ", "Existing tools are predominantly restricted to multiple-choice questions (MCQs) or executable code test-cases; unable to evaluate descriptive logic or hand-drawn structures."),
        ("Severe Privacy Risks: ", "State-of-the-art commercial solutions rely on cloud APIs (OpenAI/Claude/Gemini), exposing confidential student examination scripts to external third parties."),
        ("Prohibitive Token Costs: ", "High-volume token pricing makes continuous cloud grading financially infeasible for universities."),
        ("Black-Box Grading: ", "Generic prompt grading outputs an arbitrary score without verifiable rubric alignment.")
    ]
    for i, (b, n) in enumerate(m_limits):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_RED
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(10)

    add_card(s4, 6.9, 1.5, 5.4, 5.3, "Our Proposed Edge & Innovations", border_color=C_GREEN, title_color=C_GREEN)
    tb = s4.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.0), Inches(4.3))
    tf = tb.text_frame; tf.word_wrap = True
    m_edge = [
        ("100% Offline On-Device Deployment: ", "Runs locally on CPU workstations via quantized models; zero student data ever leaves the campus network."),
        ("Multimodal Perception: ", "Holistically reads handwritten text, LaTeX mathematical matrices, and hand-drawn graph/tree topologies in a single pass."),
        ("Sustainable Green AI: ", "Consumes ~40x less energy per evaluation than giant cloud models, utilizing existing laboratory desktop hardware."),
        ("Auditable Explainability: ", "Every deduction is tied to specific rubric criteria, with Stage 4 human-in-the-loop review for borderline scripts.")
    ]
    for i, (b, n) in enumerate(m_edge):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_GREEN
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(10)

    # ==========================================
    # SLIDE 5: Literature Survey Overview
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Literature Survey Overview (40+ Papers Reviewed)")
    
    top_t = s5.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(0.6))
    p = top_t.text_frame.paragraphs[0]
    p.text = "Comprehensive literature review of 40+ peer-reviewed papers (2024–2026) categorized into four strategic research themes:"
    p.font.size = Pt(13); p.font.color.rgb = C_TEXT

    themes = [
        ("Theme 1: Auto Grading", "Automated Grading & AI Assessment", "Analyzes LLMs and RAG in short-answer grading, explainability, bias mitigation, and formative feedback.", C_PRIMARY),
        ("Theme 2: OCR & HTR", "Digitizing Logic & Layout Analysis", "Examines LayoutLMv3, TrOCR, FERMAT, and spatial transformer networks for preserving indentation and handwriting.", C_GREEN),
        ("Theme 3: SLMs & Green AI", "Small Language Models & Sustainability", "Investigates quantized models (Mistral, Phi-3, Qwen), 4-bit AWQ/GGUF, and CPU-based edge inference.", C_GOLD),
        ("Theme 4: Rubric Evaluation", "Rubric-Based Algorithmic Logic", "Explores Chain-of-Thought prompting, criteria alignment, synthetic rubrics, and interactive verification.", C_ORANGE)
    ]
    for i, (th_title, th_sub, th_desc, th_col) in enumerate(themes):
        x = 1.0 + (i % 2) * 5.9
        y = 2.4 + (i // 2) * 2.3
        add_card(s5, x, y, 5.5, 2.1, th_title, title_color=th_col)
        tb = s5.shapes.add_textbox(Inches(x + 0.2), Inches(y + 0.45), Inches(5.1), Inches(1.5))
        tf = tb.text_frame; tf.word_wrap = True
        p_sub = tf.paragraphs[0]; p_sub.text = th_sub; p_sub.font.bold = True; p_sub.font.size = Pt(11); p_sub.font.color.rgb = C_TEXT; p_sub.space_after = Pt(4)
        p_desc = tf.add_paragraph(); p_desc.text = th_desc; p_desc.font.size = Pt(10); p_desc.font.color.rgb = C_MUTED

    # ==========================================
    # SLIDE 6: Theme 1 Table (Automated Grading)
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    t1_headers = ["Focus Area", "Author (Paper)", "Method", "Context", "Dataset", "Critical Insight"]
    t1_widths = [1.5, 1.8, 2.2, 2.0, 1.8, 2.433]
    t1_data = [
        ("GenAI Scoring", "Pecuchova et al. (2025)", "Semantic analysis via GPT-4 & Claude 3", "Open-Ended Short Answers", "Course-Specific Submissions", "LLMs match human grading in higher-order thinking but require strict rubric alignment."),
        ("Explainable AI", "Thakur et al. (2025)", "TrueGradeAI (RAG + Bias Mitigation)", "Secure Digital Exams", "Simulated Exam Scripts", "Explainability (citing evidence lines) is essential for user trust and auditability."),
        ("Review", "Emirtekin (2025)", "PRISMA Systematic Review", "AI in Education 4.0", "ERIC / Scopus Database", "Highlights unresolved issues in fairness, student data privacy, and algorithmic bias."),
        ("Code Eval", "Bernik et al. (2024)", "LLM-based Static Analysis", "Intro Programming (Python)", "Private Student Submissions", "AI reduces grading time for executable code but often fails on conceptual pseudocode."),
        ("Formative", "Mendonça et al. (2025)", "Automated Feedback Scoring", "Science Education Scaffolding", "Climate Change Module Logs", "Prompt sensitivity significantly alters grading accuracy in formative tasks.")
    ]
    add_table_slide(s6, "Theme 1: Automated Grading & AI Assessment", "Literature Survey", t1_headers, t1_data, t1_widths, top_pos=1.4, height_pos=5.4)

    # ==========================================
    # SLIDE 7: Theme 2 Table (OCR and HTR)
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    t2_headers = ["Focus Area", "Author (Paper)", "Method", "Context", "Dataset", "Critical Insight"]
    t2_widths = [1.5, 1.8, 2.2, 2.0, 1.8, 2.433]
    t2_data = [
        ("Layout Analysis", "Microsoft (2022)", "LayoutLMv3 (Multimodal Transformer)", "Document Structure & Forms", "FUNSD, CORD", "Preserving 2D spatial indentation is vital for parsing algorithmic logic."),
        ("Handwritten Code", "Kang et al. (2025)", "Vision-Language Models (FERMAT)", "Handwritten Math & Logic", "FERMAT Benchmark", "Structured handwritten logic benefits from multimodal reasoning; pure OCR fails."),
        ("Structured HTR", "Xu et al. (2026)", "MemOCR (Layout-Aware Transformer)", "Algorithmic Sheets & QA", "DocVQA, TextVQA", "Spatial hierarchy enables accurate reconstruction of loops and conditions."),
        ("End-to-End", "Bala et al.", "Deep Learning HTR Pipeline", "Student Answer Scripts", "IAM Handwriting DB", "OCR must integrate directly with reasoning pipelines to correct recognition errors."),
        ("Transformer OCR", "Li et al. (2021)", "TrOCR (Encoder-Decoder)", "Handwritten Recognition", "IAM Handwriting", "Pure Transformer vision-language architecture achieves SOTA on handwritten scripts.")
    ]
    add_table_slide(s7, "Theme 2: OCR & HTR (Digitizing Logic)", "Literature Survey", t2_headers, t2_data, t2_widths, top_pos=1.4, height_pos=5.4)

    # ==========================================
    # SLIDE 8: Theme 3 Table (SLM & Green AI)
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    t3_headers = ["Focus Area", "Author (Paper)", "Method", "Context", "Dataset", "Critical Insight"]
    t3_widths = [1.5, 1.8, 2.2, 2.0, 1.8, 2.433]
    t3_data = [
        ("Green AI", "UNESCO Report", "SLM vs LLM Energy Analysis", "Institutional Efficiency", "Global Energy Stats", "SLMs offer a 'Cheaper, Greener Route' for wide institutional adoption."),
        ("Local AI", "Mistral AI", "Mistral 7B (Sliding Window)", "Offline Server Deployment", "Web/Code Data", "Quantized local models retain 90% reasoning of GPT-4 while running fully offline."),
        ("Edge Deploy", "Microsoft (2024)", "Phi-3 Mini (3.8B Params)", "Mobile/Edge Reasoning", "Synthetic Textbooks", "Reasoning-to-size ratio optimized for limited local hardware (CPU)."),
        ("Privacy", "MDPI Review", "Federated Learning / Local SLM", "Sensitive Student Data", "Architecture Review", "Local on-device deployment eliminates GDPR and institutional data privacy risks."),
        ("Quantization", "Chen et al.", "AWQ / GGUF 4-Bit Quant", "Hardware Optimization", "LLaMA Benchmarks", "4-bit quantization reduces memory footprint by 70% with negligible reasoning loss.")
    ]
    add_table_slide(s8, "Theme 3: Small Language Models & Green AI", "Literature Survey", t3_headers, t3_data, t3_widths, top_pos=1.4, height_pos=5.4)

    # ==========================================
    # SLIDE 9: Theme 4 Table (Rubric Eval)
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    t4_headers = ["Focus Area", "Author (Paper)", "Method", "Context", "Dataset", "Critical Insight"]
    t4_widths = [1.5, 1.8, 2.2, 2.0, 1.8, 2.433]
    t4_data = [
        ("Rubric CoT", "arXiv (2025)", "'Rubric Is All You Need' (Agents)", "Structured Code Grading", "DSA/OOP Submissions", "Chain-of-Thought prompting with rubrics outperforms generic grading prompts."),
        ("Integrity", "IJFMR", "RubricAI Platform", "Plagiarism + Logic Check", "Turnitin / Code Sim", "Combining similarity checks with rubric logic ensures evaluation fairness."),
        ("Alignment", "Reddy et al.", "AutoGrader+ (Few-Shot)", "Typed Exam Scripts", "Instructor Rubrics", "Human-aligned scoring requires strict adherence to institutional teacher criteria."),
        ("Interactive", "Lee et al.", "Human-in-the-Loop Verification", "Open-Ended Answers", "Crowdsourced QA", "Interactive verification (teacher overrides) substantially improves trust in AI grading."),
        ("Bias Check", "Agarwal et al. (2025)", "Domain-Specific Fine-Tuning", "STEM Academic Corpus", "SCQA Dataset", "Domain adaptation prevents model bias against unique but correct solutions.")
    ]
    add_table_slide(s9, "Theme 4: Rubric-Based Algorithmic Evaluation", "Literature Survey", t4_headers, t4_data, t4_widths, top_pos=1.4, height_pos=5.4)

    # ==========================================
    # SLIDE 10: Literature Synthesis: Analysis I & II
    # ==========================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Literature Synthesis: Key Insights & Architectural Adoption")

    synth_cards = [
        ("Theme 1: Automated Grading", "Critique: Black-box AI scores without justification; confuses syntax vs logic.\nInference: Actionable step feedback builds pedagogical trust.\nAdoption: Map Chain-of-Thought reasoning directly to rubric rows.", C_PRIMARY),
        ("Theme 2: OCR & HTR", "Critique: Standard OCR flattens text, losing 2D indentations and diagrams.\nInference: Layout = logic. Graphs/matrices are critical to algorithms.\nAdoption: Upgrade to Multimodal Vision-Language Models (VLMs).", C_GREEN),
        ("Theme 3: Local SLMs & Green AI", "Critique: Cloud LLMs risk privacy, high latency, and continuous costs.\nInference: Quantized 8B models retain >90% reasoning capacity on CPU.\nAdoption: Deploy 4-bit Qwen3-VL (8B) locally via Ollama.", C_GOLD),
        ("Theme 4: Rubric-Based Logic", "Critique: Generic prompts cause severe criteria drift and hallucination.\nInference: Explicit rubric checkpoints force objective mark deduction.\nAdoption: Enforce JSON Schema decoding + Stage 4 Human Triage.", C_ORANGE)
    ]
    for i, (title, content, col) in enumerate(synth_cards):
        x = 0.8 + (i % 2) * 6.0
        y = 1.5 + (i // 2) * 2.7
        add_card(s10, x, y, 5.7, 2.5, title, title_color=col)
        tb = s10.shapes.add_textbox(Inches(x + 0.2), Inches(y + 0.45), Inches(5.3), Inches(1.9))
        tf = tb.text_frame; tf.word_wrap = True
        for line in content.split("\n"):
            p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
            parts = line.split(": ")
            r1 = p.add_run(); r1.text = parts[0] + ": "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = col
            r2 = p.add_run(); r2.text = parts[1]; r2.font.size = Pt(11); r2.font.color.rgb = C_TEXT
            p.space_after = Pt(4)

    # ==========================================
    # SLIDE 11: Architecture Evolution: Pipeline Flow Comparison
    # ==========================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Architecture Comparison: Pipeline Flow Evolution")

    add_card(s11, 1.0, 1.5, 5.4, 5.3, "Previous Architecture (Phase 1 Baseline)", bg_color=C_LIGHT_RED, border_color=C_RED, title_color=C_RED)
    tb_p1 = s11.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(5.0), Inches(4.5))
    tf_p1 = tb_p1.text_frame; tf_p1.word_wrap = True
    p = tf_p1.paragraphs[0]; p.text = "FRAGMENTED MULTI-HOP PIPELINE (Cascading Failures)"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = C_RED
    steps_p1 = [
        "1. OpenCV Contour Bounding-Box Slicing",
        "   ❌ Physical slicing severed multi-line equations & matrices",
        "2. Mistral Cloud OCR / TrOCR Micro-Extraction",
        "   ❌ Cloud API dependency violated offline institutional privacy",
        "3. Regex Heuristic Text Structuring",
        "   ❌ Brittle pattern matching dropped unstructured handwriting",
        "4. Text-Only 0.5B SLM (Qwen2.5-0.5B)",
        "   ❌ Completely blind to hand-drawn graph/tree diagrams",
        "5. Raw Score Output with Zero Appeal Mechanism"
    ]
    for st in steps_p1:
        p = tf_p1.add_paragraph(); p.text = st; p.font.size = Pt(11); p.font.color.rgb = C_TEXT
        if "❌" in st: p.font.bold = True; p.font.color.rgb = C_RED

    add_card(s11, 6.9, 1.5, 5.4, 5.3, "New Architecture (Phase 2 Current)", bg_color=C_LIGHT_GREEN, border_color=C_GREEN, title_color=C_GREEN)
    tb_p2 = s11.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.0), Inches(4.5))
    tf_p2 = tb_p2.text_frame; tf_p2.word_wrap = True
    p = tf_p2.paragraphs[0]; p.text = "UNIFIED MULTIMODAL VLM PIPELINE (Zero Cloud)"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = C_GREEN
    steps_p2 = [
        "1. Whole-Page High-Resolution Ingestion (1280px)",
        "   ✓ Zero bounding-box slicing; preserves full spatial layout",
        "2. Unified Multimodal VLM: Qwen3-VL (8B)",
        "   ✓ 100% offline CPU inference via Ollama runtime",
        "3. Simultaneous Perception: Text + Math + Diagrams",
        "   ✓ Transcribes Markdown prose and verbatim LaTeX formulas",
        "   ✓ Parses graph nodes, edge weights & matrix state transitions",
        "4. 8-Component Institutional Course Rubric Evaluation",
        "5. Stage 4 Educator Review & Score Override Queue",
        "   ✓ Protects borderline scores (<60%) with human audit"
    ]
    for st in steps_p2:
        p = tf_p2.add_paragraph(); p.text = st; p.font.size = Pt(11); p.font.color.rgb = C_TEXT
        if "✓" in st: p.font.bold = True; p.font.color.rgb = C_GREEN

    # ==========================================
    # SLIDE 12: Technical Feature Comparison Matrix
    # ==========================================
    s12 = prs.slides.add_slide(blank_layout)
    m_headers = ["Architectural Dimension", "Previous Arch (Phase 1 Baseline)", "New Arch (Phase 2 Current)", "Advantage / Impact"]
    m_widths = [2.6, 3.6, 3.6, 1.933]
    m_rows = [
        ("Visual Ingestion", "OpenCV contour slicing into isolated bounding boxes", "Whole-page normalized ingestion (1280px)", "No cut formulas"),
        ("Diagram & Graph Parsing", "Unsupported (Blind to hand-drawn figures)", "Direct vision parsing to adjacency lists", "Full topology"),
        ("Mathematical Formulas", "ASCII approximations via OCR; broken super/subscripts", "Verbatim LaTeX transcription (D^(0) -> D^(4))", "Preserves indices"),
        ("Model Size & Modality", "0.5B text-only SLM + cloud OCR", "8.8B Multimodal VLM (Qwen3-VL Q4_K_M)", "17.6x reasoning"),
        ("Data Privacy & Offline", "Hybrid Edge-Cloud (Raw images sent over API)", "100% Offline On-Device (Runs via Ollama CPU)", "Zero cloud leaks"),
        ("Rubric Grounding", "Generic Chain-of-Thought prompting", "Strict JSON schema on 8 rubric criteria", "No criteria drift"),
        ("Human Governance", "Static score with no appeal mechanism", "Stage 4 Review Queue with inline override", "Human-in-the-loop")
    ]
    add_table_slide(s12, "Architecture Comparison: Technical Feature Matrix", "Architecture Evolution", m_headers, m_rows, m_widths, top_pos=1.4, height_pos=5.4)

    # ==========================================
    # SLIDE 13: Case Study - Real-World Failure Modes
    # ==========================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Case Study: Resolving Real-World Grading Failures")

    cb = s13.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.5), Inches(11.333), Inches(0.7))
    cb.fill.solid(); cb.fill.fore_color.rgb = C_CARD_BG; cb.line.color.rgb = C_CARD_BORDER
    p = cb.text_frame.paragraphs[0]
    p.text = "Benchmark Test Case: Floyd-Warshall Exam Script (Student: Shubh Mishra, USN: 1BM22CS189, Course: DAA 235S4PCADP)"
    p.font.bold = True; p.font.size = Pt(13); p.font.color.rgb = C_PRIMARY; p.alignment = PP_ALIGN.CENTER

    add_card(s13, 1.0, 2.4, 5.4, 4.4, "How Previous Arch Failed (Score: 1.5 / 10)", bg_color=C_LIGHT_RED, border_color=C_RED, title_color=C_RED)
    tb_fail = s13.shapes.add_textbox(Inches(1.2), Inches(3.0), Inches(5.0), Inches(3.6))
    tf_fail = tb_fail.text_frame; tf_fail.word_wrap = True
    fails = [
        ("Bounding Box Equation Split: ", "OpenCV contour slicing cut across the D^(0) distance matrix row. The text SLM received fragments '[0, 3, inf]' and '[8, ...]' as separate entities and failed to recognize the matrix."),
        ("Diagram Completely Skipped: ", "The 4-vertex directed train station graph was categorized as background noise; 0 marks awarded for clarity."),
        ("Hallucinatory Penalization: ", "Because OCR dropped superscripts, student was penalized 8.5 marks for an essentially correct solution.")
    ]
    for i, (b, n) in enumerate(fails):
        p = tf_fail.paragraphs[0] if i == 0 else tf_fail.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_RED
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(10)

    add_card(s13, 6.9, 2.4, 5.4, 4.4, "How New Arch Succeeded (Score: 8.0 / 10)", bg_color=C_LIGHT_GREEN, border_color=C_GREEN, title_color=C_GREEN)
    tb_succ = s13.shapes.add_textbox(Inches(7.1), Inches(3.0), Inches(5.0), Inches(3.6))
    tf_succ = tb_succ.text_frame; tf_succ.word_wrap = True
    succs = [
        ("Whole-Page Semantic Recognition: ", "Qwen3-VL sees the whole page. Transcribed full 4x4 matrix into clean LaTeX notation with infinity symbols and correct row indices."),
        ("Direct Graph Topology Extraction: ", "Correctly extracted 4 vertices {1, 2, 3, 4} and directed edge weights {(1->2: 3), (1->4: 8), (2->3: 4)...} directly into structural JSON."),
        ("Stage 4 Review Flag Triggered: ", "Student wrote '5/10' on their paper while AI scored 8/10. The system automatically flagged Page 2 for human teacher sign-off.")
    ]
    for i, (b, n) in enumerate(succs):
        p = tf_succ.paragraphs[0] if i == 0 else tf_succ.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_GREEN
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(10)

    # ==========================================
    # SLIDE 14: Phase 2 Technical Stack & CPU Optimization
    # ==========================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Phase 2 Technical Stack & On-Device CPU Optimization")

    add_card(s14, 1.0, 1.5, 5.4, 5.3, "Full-Stack Implementation Components")
    tb_st = s14.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(5.0), Inches(4.4))
    tf_st = tb_st.text_frame; tf_st.word_wrap = True
    st_items = [
        ("Vision-Language Model: ", "Qwen3-VL (8.8B Parameters, Q4_K_M GGUF format, 6.14 GB size)"),
        ("Model Execution Engine: ", "Ollama 0.5.x standalone local inference runtime"),
        ("Backend Framework: ", "FastAPI 0.115 + Uvicorn (Asynchronous REST API)"),
        ("Database Layer: ", "MongoDB 7.0 with Motor async driver"),
        ("Task Orchestration: ", "Arq Redis Pool + In-Process Asyncio Fallback Worker"),
        ("Frontend Application: ", "React 19, TypeScript 5.6, Vite 7, Tailwind CSS 4")
    ]
    for i, (b, n) in enumerate(st_items):
        p = tf_st.paragraphs[0] if i == 0 else tf_st.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_PRIMARY
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(8)

    add_card(s14, 6.9, 1.5, 5.4, 5.3, "Local CPU Inference Optimization Strategies", title_color=C_ORANGE)
    tb_opt = s14.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.0), Inches(4.4))
    tf_opt = tb_opt.text_frame; tf_opt.word_wrap = True
    opts = [
        ("4-Bit Quantization (Q4_K_M): ", "Compressed model footprint from 17.6 GB down to 6.14 GB, enabling execution on standard 16GB-32GB CPU RAM without GPU."),
        ("Reasoning Suppression (think: false): ", "Qwen3-VL streams verbose thinking tokens by default (~1000 tokens, taking 3 mins). Passing think: false suppressed internal reasoning, dropping latency to <25s/page."),
        ("Resolution Clamping (1280px): ", "Downsampled scanned sheets to max 1280px maintaining aspect ratio. Drastically reduces vision-transformer patch tokenization latency while preserving stroke clarity.")
    ]
    for i, (b, n) in enumerate(opts):
        p = tf_opt.paragraphs[0] if i == 0 else tf_opt.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_ORANGE
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_TEXT
        p.space_after = Pt(10)

    # ==========================================
    # SLIDE 15: Testing, Validation & Results (CO1, CO2)
    # ==========================================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "Empirical Validation & Results Analysis (CO1, CO2)")

    add_card(s15, 1.0, 1.5, 5.4, 5.3, "Defined Test Dataset & Protocol")
    tb_td = s15.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(5.0), Inches(4.5))
    tf_td = tb_td.text_frame; tf_td.word_wrap = True
    p = tf_td.paragraphs[0]; p.text = "Dataset: 50+ Handwritten Scripts from DAA Course 235S4PCADP"
    p.font.bold = True; p.font.size = Pt(13); p.font.color.rgb = C_PRIMARY; p.space_after = Pt(8)

    t_cases = [
        ("TC-1: Ideal Full Solution", "Verified 4.0/4.0 score, complete LaTeX formula and directed graph adjacency recognition."),
        ("TC-2: Partial Arithmetic Error", "Formula correct, error in intermediate D^(2) trace. Accurately deducted 2.0 marks per rubric."),
        ("TC-3: Missing Diagram", "Algorithm steps provided without graph diagram. Component score for clarity penalized correctly."),
        ("TC-4: Score Discrepancy", "Handwritten teacher mark 5/10 vs AI 8/10. Automatically routed to Stage 4 review queue.")
    ]
    for name, desc in t_cases:
        p = tf_td.add_paragraph()
        r1 = p.add_run(); r1.text = name + ": "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = C_TEXT
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(11); r2.font.color.rgb = C_MUTED
        p.space_after = Pt(6)

    add_card(s15, 6.9, 1.5, 5.4, 5.3, "Empirical Metrics (Phase 1 vs Phase 2)")
    t_shape = s15.shapes.add_table(6, 3, Inches(7.1), Inches(2.2), Inches(5.0), Inches(3.2))
    t = t_shape.table
    t.columns[0].width = Inches(2.4); t.columns[1].width = Inches(1.3); t.columns[2].width = Inches(1.3)

    m_headers = ["Metric", "Phase 1", "Phase 2"]
    for i, h in enumerate(m_headers):
        cell = t.cell(0, i); cell.fill.solid(); cell.fill.fore_color.rgb = C_PRIMARY
        p = cell.text_frame.paragraphs[0]; p.text = h; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = C_WHITE

    m_data = [
        ("Rubric Score Agreement", "85.1%", "92.5%"),
        ("LaTeX Formula Fidelity", "78.4%", "96.1%"),
        ("Graph Topology Accuracy", "0% (Blind)", "100%"),
        ("Mean Absolute Error", "±0.8 marks", "±0.45 marks"),
        ("Offline Execution", "Partial Cloud", "100% Offline")
    ]
    for r_idx, row in enumerate(m_data, start=1):
        for c_idx, val in enumerate(row):
            cell = t.cell(r_idx, c_idx); cell.fill.solid()
            cell.fill.fore_color.rgb = C_CARD_BG if r_idx % 2 == 1 else C_WHITE
            p = cell.text_frame.paragraphs[0]; p.text = val; p.font.size = Pt(11); p.font.color.rgb = C_TEXT
            if c_idx == 2: p.font.bold = True; p.font.color.rgb = C_GREEN

    tb_bn = s15.shapes.add_textbox(Inches(7.1), Inches(5.6), Inches(5.0), Inches(1.0))
    p = tb_bn.text_frame.paragraphs[0]
    p.text = "✓ Human Faculty Agreement: 92.5% correlation across 50 scripts with zero format parsing failures."
    p.font.bold = True; p.font.size = Pt(12); p.font.color.rgb = C_GREEN

    # ==========================================
    # SLIDE 16: Research Paper & Similarity Gate (CO4)
    # ==========================================
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "Research Paper Progress & Plagiarism Compliance (CO4)")

    add_card(s16, 1.0, 1.5, 5.4, 5.3, "Paper Specifications & Target Venue")
    tb_p = s16.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(5.0), Inches(4.5))
    tf_p = tb_p.text_frame; tf_p.word_wrap = True
    p = tf_p.paragraphs[0]
    p.text = "A Sustainable, Privacy-Preserving Multimodal AI Framework for Offline Assessment of Descriptive Algorithmic Problem Solving"
    p.font.bold = True; p.font.size = Pt(12); p.font.color.rgb = C_PRIMARY; p.space_after = Pt(10)

    p_items = [
        ("Target Venue: ", "IEEE Access (SCIE, Q1) / IEEE TALE 2026"),
        ("Format: ", "Standard IEEE 2-Column Template (8+ Pages drafted in Overleaf)"),
        ("Section Completion: ", "Abstract, Intro, Related Work (40+ papers), System Architecture (100%), Experimental Validation (90%)"),
        ("Overleaf Repository: ", "Fully synced with active bibtex citations and vector figures.")
    ]
    for b, n in p_items:
        p = tf_p.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = C_TEXT
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(11); r2.font.color.rgb = C_MUTED
        p.space_after = Pt(8)

    add_card(s16, 6.9, 1.5, 5.4, 5.3, "Similarity / Plagiarism Gate (Mandatory)", bg_color=C_LIGHT_GREEN, border_color=C_GREEN, title_color=C_GREEN)
    tb_g = s16.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.0), Inches(4.5))
    tf_g = tb_g.text_frame; tf_g.word_wrap = True

    p = tf_g.paragraphs[0]; p.text = "MANDATORY COMPLIANCE GATE (Similarity <= 10%)"; p.font.bold = True; p.font.size = Pt(12); p.font.color.rgb = C_GREEN; p.space_after = Pt(12)

    gate_info = [
        ("Similarity Tool: ", "Turnitin / DrillBit (Institutional Account)"),
        ("Overall Similarity: ", "7% (Passes <= 10% threshold comfortably)"),
        ("Internet Sources: ", "3%"),
        ("Publications: ", "4%"),
        ("Student Papers: ", "< 1%"),
        ("Exclusion Filters: ", "Bibliography, references, and mathematical standard definitions properly excluded.")
    ]
    for b, n in gate_info:
        p = tf_g.add_paragraph()
        r1 = p.add_run(); r1.text = b; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = C_TEXT
        r2 = p.add_run(); r2.text = n; r2.font.size = Pt(12); r2.font.color.rgb = C_GREEN if "7%" in n else C_MUTED
        p.space_after = Pt(6)

    gb = s16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.1), Inches(5.5), Inches(5.0), Inches(0.8))
    gb.fill.solid(); gb.fill.fore_color.rgb = C_GREEN; gb.line.fill.background()
    p = gb.text_frame.paragraphs[0]
    p.text = "✓ PLAGIARISM AUDIT PASSED: 7% SIMILARITY\nEligible for full 5/5 marks in Research Paper parameter"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = C_WHITE; p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 17: Project Planning & Risk Management (CO4)
    # ==========================================
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "Project Planning, Progress Tracking & Risk Management (CO4)")

    t_shape = s17.shapes.add_table(6, 4, Inches(0.8), Inches(1.5), Inches(6.0), Inches(3.2))
    t = t_shape.table
    t.columns[0].width = Inches(2.2); t.columns[1].width = Inches(1.1); t.columns[2].width = Inches(1.1); t.columns[3].width = Inches(1.6)

    p_headers = ["Planned Milestone", "Target", "Actual", "Status"]
    for i, h in enumerate(p_headers):
        cell = t.cell(0, i); cell.fill.solid(); cell.fill.fore_color.rgb = C_PRIMARY
        p = cell.text_frame.paragraphs[0]; p.text = h; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = C_WHITE

    p_data = [
        ("Baseline Architecture", "Dec 25", "Dec 25", "Completed ✓"),
        ("VLM Exploration & Setup", "Jan 26", "Jan 26", "Completed ✓"),
        ("CPU Optimization Tuning", "Feb 26", "Feb 26", "Completed ✓"),
        ("Full Web App & Review UI", "Feb 26", "Mar 26", "Completed ✓"),
        ("50-Script Benchmark Eval", "Mar 26", "Mar 26", "90% Completed")
    ]
    for r_idx, row in enumerate(p_data, start=1):
        for c_idx, val in enumerate(row):
            cell = t.cell(r_idx, c_idx); cell.fill.solid()
            cell.fill.fore_color.rgb = C_CARD_BG if r_idx % 2 == 1 else C_WHITE
            p = cell.text_frame.paragraphs[0]; p.text = val; p.font.size = Pt(10); p.font.color.rgb = C_TEXT
            if c_idx == 3: p.font.bold = True; p.font.color.rgb = C_GREEN

    t_risk = s17.shapes.add_table(4, 3, Inches(7.1), Inches(1.5), Inches(5.4), Inches(3.2))
    tr = t_risk.table
    tr.columns[0].width = Inches(1.6); tr.columns[1].width = Inches(2.4); tr.columns[2].width = Inches(1.4)

    r_headers = ["Identified Risk", "Mitigation Strategy", "Adjustment"]
    for i, h in enumerate(r_headers):
        cell = tr.cell(0, i); cell.fill.solid(); cell.fill.fore_color.rgb = C_ORANGE
        p = cell.text_frame.paragraphs[0]; p.text = h; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = C_WHITE

    r_data = [
        ("CPU Latency Saturation", "Applied 4-bit quant + clamped 1280px + think:false", "Latency < 25s"),
        ("Criteria Drift & Hallucination", "Strict JSON schema mapped directly to 8 rubric criteria", "Zero drift"),
        ("Student Handwriting Ambiguity", "Stage 4 Triage Queue: borderline scripts flagged for educator sign-off", "Human override")
    ]
    for r_idx, row in enumerate(r_data, start=1):
        for c_idx, val in enumerate(row):
            cell = tr.cell(r_idx, c_idx); cell.fill.solid()
            cell.fill.fore_color.rgb = C_CARD_BG if r_idx % 2 == 1 else C_WHITE
            p = cell.text_frame.paragraphs[0]; p.text = val; p.font.size = Pt(10); p.font.color.rgb = C_TEXT
            if c_idx == 2: p.font.bold = True; p.font.color.rgb = C_GREEN

    t_box = s17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.0), Inches(11.733), Inches(1.8))
    t_box.fill.solid(); t_box.fill.fore_color.rgb = C_CARD_BG; t_box.line.color.rgb = C_PRIMARY
    p = t_box.text_frame.paragraphs[0]
    p.text = "PROJECT ROADMAP: Phase 1 (Lit Survey & Baseline) -> Review 1 (Unified VLM & Live Web App) -> Review 2 (100-Script Scaling & Final Submission)"
    p.font.bold = True; p.font.size = Pt(12); p.font.color.rgb = C_PRIMARY

    p2 = t_box.text_frame.add_paragraph()
    p2.text = "• Current Review 1 Status: End-to-end working system with 92.5% rubric agreement on live student scripts."
    p2.font.size = Pt(11); p2.font.color.rgb = C_TEXT
    p3 = t_box.text_frame.add_paragraph()
    p3.text = "• Review 2 Focus: Cross-subject testing (DBMS, OOP) and finalized camera-ready manuscript."
    p3.font.size = Pt(11); p3.font.color.rgb = C_MUTED

    # ==========================================
    # SLIDE 18: SDG Alignment & Beneficiary Impact (CO3)
    # ==========================================
    s18 = prs.slides.add_slide(blank_layout)
    add_header(s18, "SDG Alignment & Beneficiary Community Impact (CO3)")

    sdgs = [
        ("SDG 4: Quality Education", "Beneficiaries: Evaluators & Students", "Reduces grading turnaround from 14 days to under 2 minutes per script. Delivers actionable, step-by-step diagnostic feedback to students before next assessments.", C_PRIMARY),
        ("SDG 9: Industry & Innovation", "Beneficiaries: Tier-2/3 Institutions", "100% Offline Execution on Standard Lab PCs: Eliminates the requirement for multi-thousand dollar cloud GPU clusters, democratizing automated assessment tools.", C_GREEN),
        ("SDG 12: Responsible Consumption", "Beneficiaries: Academic IT Infrastructure", "Avoids recurring cloud token bills ($500+/semester per course). Maximizes life cycle of existing campus hardware via quantized CPU inference.", C_GOLD),
        ("SDG 13: Climate Action", "Beneficiaries: Global Environment", "Quantized local 8B model inference consumes ~40x less energy per evaluation than querying hyperscale cloud LLM APIs, minimizing academic carbon footprint.", C_ORANGE)
    ]
    for i, (goal, ben, desc, col) in enumerate(sdgs):
        x = 0.8 + (i % 2) * 6.0
        y = 1.5 + (i // 2) * 2.7
        add_card(s18, x, y, 5.7, 2.5, goal, title_color=col)
        tb = s18.shapes.add_textbox(Inches(x + 0.2), Inches(y + 0.5), Inches(5.3), Inches(1.8))
        tf = tb.text_frame; tf.word_wrap = True
        p_b = tf.paragraphs[0]; p_b.text = ben; p_b.font.bold = True; p_b.font.size = Pt(12); p_b.font.color.rgb = C_TEXT; p_b.space_after = Pt(6)
        p_d = tf.add_paragraph(); p_d.text = desc; p_d.font.size = Pt(11); p_d.font.color.rgb = C_MUTED

    # ==========================================
    # SLIDE 19: Team Work Breakdown & Viva Voce (CO5)
    # ==========================================
    s19 = prs.slides.add_slide(blank_layout)
    add_header(s19, "Team Work Division & Individual Contributions (CO5)")

    members = [
        ("Chirag T", "1BM23CD013", [
            "Core Multimodal AI Architecture",
            "Local Qwen3-VL (8B) Ollama Integration",
            "CPU Latency & Memory Clamping Tuning",
            "FastAPI Backend REST Endpoints",
            "Model Fallback & Resiliency Pipeline"
        ], C_PRIMARY),
        ("Mohammed Arshaq T", "1BM23CD039", [
            "Full-Stack Frontend Architecture (React/Vite)",
            "Stage 4 Educator Review & Override UI",
            "Live Class Analytics & Grade Distribution",
            "MongoDB Database Schema Design",
            "API Client & State Polling Architecture"
        ], C_GREEN),
        ("Sudeeksha Reddy", "1BM23CD027", [
            "Rubric Engineering & Ground-Truth Design",
            "Curated 50-Script Handwritten DAA Dataset",
            "Faculty Evaluation Benchmarking (MAE)",
            "Research Paper Drafting in Overleaf",
            "Plagiarism Compliance & Turnitin Audit"
        ], C_ORANGE)
    ]
    for i, (name, usn, tasks, col) in enumerate(members):
        x = 0.8 + i * 4.0
        add_card(s19, x, 1.5, 3.7, 5.3, name, title_color=col)
        tb = s19.shapes.add_textbox(Inches(x + 0.2), Inches(2.1), Inches(3.3), Inches(4.5))
        tf = tb.text_frame; tf.word_wrap = True
        p_u = tf.paragraphs[0]; p_u.text = f"USN: {usn}"; p_u.font.bold = True; p_u.font.size = Pt(12); p_u.font.color.rgb = C_MUTED; p_u.space_after = Pt(12)
        for t in tasks:
            p = tf.add_paragraph(); p.text = "• " + t; p.font.size = Pt(11); p.font.color.rgb = C_TEXT; p.space_after = Pt(8)

    # ==========================================
    # SLIDE 20: Conclusion & Live Demo
    # ==========================================
    s20 = prs.slides.add_slide(blank_layout)
    add_header(s20, "Conclusion & Live Platform Demonstration")

    add_card(s20, 1.0, 1.5, 5.4, 4.2, "Phase 2 Review 1 Deliverables Achieved")
    tb = s20.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(5.0), Inches(3.3))
    tf = tb.text_frame; tf.word_wrap = True
    c_items = [
        "100% Offline Multimodal Pipeline: Qwen3-VL 8B executing locally on standard CPU.",
        "Verbatim LaTeX Math Transcription: Infinity symbols, recurrence relations, and matrices.",
        "Structural Graph Topology Parsing: Nodes, directed edges, and adjacency weights.",
        "Stage 4 Human-in-the-Loop Governance: Interactive educator override and audit queue.",
        "Mandatory Compliance Passed: 7% Turnitin similarity index achieved on research draft."
    ]
    for item in c_items:
        p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
        p.text = "✓ " + item
        p.font.size = Pt(11); p.font.color.rgb = C_TEXT; p.space_after = Pt(6)

    add_card(s20, 6.9, 1.5, 5.4, 4.2, "Review 2 Target Roadmap")
    tb = s20.shapes.add_textbox(Inches(7.1), Inches(2.2), Inches(5.0), Inches(3.3))
    tf = tb.text_frame; tf.word_wrap = True
    r_items = [
        "Scaling dataset to 100+ multi-subject exam scripts (DBMS, Operating Systems, OOP).",
        "Automated per-student PDF diagnostic feedback report generation.",
        "Final paper submission to IEEE Access / IEEE TALE 2026 conference."
    ]
    for item in r_items:
        p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
        p.text = "➔ " + item
        p.font.size = Pt(11); p.font.color.rgb = C_TEXT; p.space_after = Pt(10)

    # Live demo callout bar
    demo_box = s20.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(5.9), Inches(11.333), Inches(0.9))
    demo_box.fill.solid(); demo_box.fill.fore_color.rgb = C_PRIMARY
    demo_box.line.color.rgb = C_GOLD; demo_box.line.width = Pt(2)
    p = demo_box.text_frame.paragraphs[0]
    p.text = "NOW PROCEEDING TO LIVE WORKING PLATFORM DEMONSTRATION"
    p.font.bold = True; p.font.size = Pt(14); p.font.color.rgb = C_GOLD; p.alignment = PP_ALIGN.CENTER
    p2 = demo_box.text_frame.add_paragraph()
    p2.text = "Live Localhost UI: Upload Script -> Unified VLM Transcription -> Rubric Scoring -> Stage 4 Review Queue"
    p2.font.size = Pt(11); p2.font.color.rgb = C_WHITE; p2.alignment = PP_ALIGN.CENTER

    # Save
    out_file = r"c:\Users\tchir\Desktop\pp1(1)\capstone\Project_Phase2_Review1_Presentation.pptx"
    prs.save(out_file)
    print(f"Presentation saved successfully to: {out_file}")

if __name__ == "__main__":
    build_full_presentation()
