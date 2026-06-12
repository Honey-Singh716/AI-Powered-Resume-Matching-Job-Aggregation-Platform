def send_application_notification(candidate_name: str, job_title: str, recruiter_id: int):
    """
    Simulates sending an email notification to the recruiter.
    In a real app, this would use smtplib, SendGrid, or AWS SES.
    """
    email_content = f"""
    ========================================================
    📧 NEW EMAIL NOTIFICATION 
    ========================================================
    To: Recruiter #{recruiter_id}
    Subject: New Application for {job_title}!
    
    Hello,
    
    Great news! You have a new applicant for the position:
    '{job_title}'.
    
    Candidate profile: {candidate_name}
    
    Log in to your dashboard to view their AI Match Score 
    and review their resume!
    
    Best regards,
    The AI Resume Matcher Team
    ========================================================
    """
    print(email_content)
