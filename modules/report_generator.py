import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from config import REPORT_FOLDER, QUALITY_WEIGHTS

def generate_pdf_report(profile_a, profile_b, comp_details, rec_details, fusion_stats=None, file_paths=None):
    """
    Generates a professional PDF report containing:
    - Dataset profiling summary
    - Quality scores side-by-side
    - Compatibility analysis breakdown
    - AI Recommendation details & Fusion Gain
    - Fusion statistics (if executed)
    Saves to the reports/ directory and returns the path.
    """
    os.makedirs(REPORT_FOLDER, exist_ok=True)
    
    file_name = f"report_{profile_a['filename'].split('.')[0]}_{profile_b['filename'].split('.')[0]}.pdf"
    pdf_path = os.path.join(REPORT_FOLDER, file_name)
    
    # Page setup
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles for Premium Look
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=24
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=16,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569')
    )
    
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    story = []
    
    # Header Banner
    story.append(Paragraph("Dataset Selection & Fusion Analysis Report", title_style))
    story.append(Paragraph(f"AI-Based Recommendation System | Generated Date: 2026-07-30", subtitle_style))
    
    # Section 1: Overview
    story.append(Paragraph("1. Datasets Overview", h1_style))
    story.append(Spacer(1, 4))
    
    overview_data = [
        ["Metric", profile_a.get('filename', 'Dataset A'), profile_b.get('filename', 'Dataset B')],
        ["Number of Rows", str(profile_a.get('num_rows', '0')), str(profile_b.get('num_rows', '0'))],
        ["Number of Columns", str(profile_a.get('num_cols', '0')), str(profile_b.get('num_cols', '0'))],
        ["File Size", profile_a.get('file_size_str', 'N/A'), profile_b.get('file_size_str', 'N/A')],
        ["Memory Usage", profile_a.get('memory_usage_str', 'N/A'), profile_b.get('memory_usage_str', 'N/A')],
        ["Duplicate Rows", str(profile_a.get('duplicate_rows', '0')), str(profile_b.get('duplicate_rows', '0'))],
        ["Quality Score", f"{profile_a.get('quality_score', 0)}/100", f"{profile_b.get('quality_score', 0)}/100"]
    ]
    
    t_overview = Table(overview_data, colWidths=[150, 190, 190])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (1,6), (1,6), colors.HexColor('#f0fdf4') if profile_a['quality_score'] >= 70 else colors.HexColor('#fffbeb')),
        ('BACKGROUND', (2,6), (2,6), colors.HexColor('#f0fdf4') if profile_b['quality_score'] >= 70 else colors.HexColor('#fffbeb')),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 15))
    
    # Section 2: Quality Score Breakdown
    story.append(Paragraph("2. Detailed Quality Score Breakdown", h1_style))
    story.append(Spacer(1, 4))
    
    quality_data = [
        ["Quality Metric", "Weight", f"{profile_a['filename']}", f"{profile_b['filename']}"]
    ]
    
    for metric, score_a in profile_a["quality_breakdown"].items():
        score_b = profile_b["quality_breakdown"].get(metric, 0.0)
        weight_pct = f"{QUALITY_WEIGHTS.get(metric, 0.0) * 100:.0f}%"
        # format metric name for display
        metric_disp = metric.replace("_", " ").title()
        quality_data.append([metric_disp, weight_pct, f"{score_a}/100", f"{score_b}/100"])
        
    t_quality = Table(quality_data, colWidths=[150, 60, 160, 160])
    t_quality.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
    ]))
    story.append(t_quality)
    story.append(Spacer(1, 15))
    
    # Section 3: Compatibility analysis
    story.append(Paragraph("3. Pairwise Compatibility Metrics", h1_style))
    story.append(Spacer(1, 4))
    
    comp_metrics = [
        ["Compatibility Attribute", "Score", "Detail / Explanation"],
        ["Schema Similarity", f"{comp_details['schema_similarity']}%", "Jaccard overlap of column headers"],
        ["Header Name Matching", f"{comp_details['column_name_similarity']}%", "Fuzzy header matching coefficient"],
        ["Data Type Compatibility", f"{comp_details['dtype_compatibility']}%", "Type matches on overlapping headers"],
        ["Common Column Ratio", f"{comp_details['common_columns_ratio']}%", "Overlap relative to total dimensions"],
        ["Unique Feature Gain", f"{comp_details['unique_feature_gain']}%", "New features B would introduce to A"],
        ["Row Key Overlap", f"{comp_details['row_overlap']}%", comp_details['key_info']],
        ["Correlation Similarity", f"{comp_details['correlation_similarity']}%", "Statistical correlation structures overlap"],
        ["Missing Value Alignment", f"{comp_details['missing_value_overlap']}%", "Null locations Jaccard correlation"]
    ]
    
    t_comp = Table(comp_metrics, colWidths=[150, 70, 310])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 15))
    
    # Page break for recommendations
    story.append(PageBreak())
    
    # Section 4: AI Recommendations
    story.append(Paragraph("4. AI Selection & Fusion Recommendation", h1_style))
    story.append(Spacer(1, 4))
    
    rec_text = "FUSE DATASETS" if rec_details['recommendation'] == 'FUSE' else f"USE {rec_details['recommendation'][-1]}"
    rec_color = '#0284c7' if rec_details['recommendation'] == 'FUSE' else '#16a34a'
    
    summary_box_data = [
        [
            Paragraph("<b>RECOMMENDED ACTION:</b>", bold_body), 
            Paragraph(f"<font color='{rec_color}'><b>{rec_text}</b></font>", bold_body)
        ],
        [
            Paragraph("<b>CONFIDENCE RATING:</b>", bold_body), 
            Paragraph(f"<b>{rec_details['confidence_score']}%</b>", bold_body)
        ],
        [
            Paragraph("<b>FUSION GAIN SCORE:</b>", bold_body), 
            Paragraph(f"<b>{rec_details['fusion_gain_score']} pts</b> (Estimated Fused Quality: {rec_details['estimated_fused_quality']}/100)", bold_body)
        ]
    ]
    
    t_summary_box = Table(summary_box_data, colWidths=[150, 380])
    t_summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bae6fd')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#e0f2fe'))
    ]))
    story.append(t_summary_box)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Decision Reasoning & Key Findings:", bold_body))
    for reason in rec_details['reasoning']:
        story.append(Paragraph(f"• {reason}", bullet_style))
        
    story.append(Spacer(1, 15))
    
    # Section 5: Fusion execution details
    if fusion_stats:
        story.append(Paragraph("5. Executed Fusion Summary", h1_style))
        story.append(Spacer(1, 4))
        
        fusion_data = [
            ["Metric Attribute", "Value", "Notes"],
            ["Applied Strategy", fusion_stats['strategy'].upper(), f"Primary key: {fusion_stats['primary_key'] or 'None (Concat/Union)'}"],
            ["Initial Rows", f"A: {fusion_stats['rows_before_a']} | B: {fusion_stats['rows_before_b']}", f"Total raw: {fusion_stats['rows_before_a'] + fusion_stats['rows_before_b']}"],
            ["Resulting Rows", str(fusion_stats['rows_after']), f"Delta: {fusion_stats['rows_after'] - max(fusion_stats['rows_before_a'], fusion_stats['rows_before_b'])}"],
            ["Initial Columns", f"A: {fusion_stats['cols_before_a']} | B: {fusion_stats['cols_before_b']}", ""],
            ["Resulting Columns", str(fusion_stats['cols_after']), f"Delta: {fusion_stats['cols_after'] - max(fusion_stats['cols_before_a'], fusion_stats['cols_before_b'])}"],
            ["Duplicates Cleaned", str(fusion_stats['duplicate_rows']), "Exact row duplicates removed during fusion"],
            ["Missing Cells Ratio", f"{fusion_stats['missing_cells']} ({fusion_stats['missing_ratio']}%)", "Null values in merged structure"]
        ]
        
        t_fusion = Table(fusion_data, colWidths=[150, 150, 230])
        t_fusion.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ]))
        story.append(t_fusion)
        story.append(Spacer(1, 10))
        
        if file_paths:
            story.append(Paragraph("Generated Exports For Download:", bold_body))
            story.append(Paragraph(f"CSV file: <code>{file_paths.get('csv_filename')}</code>", bullet_style))
            if file_paths.get('xlsx_filename'):
                story.append(Paragraph(f"Excel file: <code>{file_paths.get('xlsx_filename')}</code>", bullet_style))
            story.append(Paragraph(f"JSON file: <code>{file_paths.get('json_filename')}</code>", bullet_style))
            
    # Build document
    doc.build(story)
    return pdf_path, file_name
