from groq import Groq
import json

import os
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

from repositories.candidate_repo import get_candidate_by_id


def ask_ai(prompt: str, candidate_id: int = None, role: str = None, db = None):
    if role == "recruiter":
        system_prompt = "You are an expert AI Recruitment Assistant. Your goal is to help the recruiter draft compelling job descriptions, formulate technical interview questions, evaluate candidate skill sets, and write professional outreach emails. Provide concise, actionable, and industry-standard HR and recruitment advice."
    else:
        system_prompt = "You are a helpful AI Career Advisor."
        
        if candidate_id and db:
            candidate = get_candidate_by_id(candidate_id, db)
            if candidate:
                system_prompt += f"\n\nThe user you are talking to has the following profile:\nSkills: {candidate.skills}\nExperience: {candidate.experience}\n\nProvide tailored, personalized advice based on their specific background."

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response.choices[0].message.content
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

def parse_resume(
        resume_text:str
):
    prompt = f"""
    Extract the following information from this resume.
    
    Do not write any explainations.
    Do not include any text other than the JSON object.
    DO not write code blocks.
    
    Return ONLY valid JSON.


    Format:

    {{
    "skills": [],
    "experience": "",
    "education": ""
    }}

    Resume:

    {resume_text}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    result = response.choices[0].message.content
    
    # Strip markdown code fences if the AI wraps the JSON in ```json ... ```
    cleaned = result.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (e.g. ```json)
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail="AI could not parse the resume. Please try uploading again."
        )

    # Validate the parsed result has the expected structure
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="AI returned unexpected format. Please try again.")
    
    if "skills" not in parsed:
        parsed["skills"] = []
    if "experience" not in parsed:
        parsed["experience"] = ""
    if "education" not in parsed:
        parsed["education"] = ""
    
    # Ensure skills is always a list
    if isinstance(parsed["skills"], str):
        parsed["skills"] = [s.strip() for s in parsed["skills"].split(",") if s.strip()]

    return parsed



