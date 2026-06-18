from groq import Groq
import json

import os
from dotenv import load_dotenv

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


    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

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
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise Exception(f"AI returned invalid JSON. Raw response: {result[:500]}")



