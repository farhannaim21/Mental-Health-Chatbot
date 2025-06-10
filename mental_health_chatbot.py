# mental_health_chatbot.py

# Store user session data
user_sessions = {}

def ask_gender(user_id):
    return "Hello! To get started, could you please tell me your gender? (male/female/other)"

def ask_age():
    return "Could you please tell me your age? (Enter a number between 1-120)"

def ask_stress_questions():
    return [
        "Have you been feeling overwhelmed or unable to cope with daily tasks recently? (yes/no)",
        "Have you been experiencing frequent mood swings or irritability? (yes/no)",
        "Have you been having trouble sleeping or experiencing changes in your sleep patterns? (yes/no)",
        "Have you been feeling fatigued or lacking energy most days? (yes/no)",
        "Have you been avoiding social interactions or activities you usually enjoy? (yes/no)"
    ]

def ask_sleep_schedule():
    return "What is your typical sleep schedule? (e.g., 'I sleep at 11 PM and wake up at 7 AM')"

def ask_gender_specific_questions(gender):
    if gender == 'female':
        return "Can you tell me about your menstrual cycle? (regular/irregular)"
    elif gender == 'male':
        return "Have you noticed any changes in your energy levels or mood recently? (yes/no)"
    return None

def process_message(user_id, message):
    """Handles user responses and progresses the conversation."""
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "ask_gender", "stress_score": 0, "responses": {}}

    session = user_sessions[user_id]
    step = session["step"]

    if step == "ask_gender":
        if message.lower() in ['male', 'female', 'other']:
            session["responses"]["gender"] = message.lower()
            session["step"] = "ask_age"
            return ask_age()
        return "Please enter a valid gender (male/female/other)."

    elif step == "ask_age":
        if message.isdigit() and 1 <= int(message) <= 120:
            session["responses"]["age"] = int(message)
            session["step"] = "ask_stress_questions"
            session["question_index"] = 0
            return ask_stress_questions()[0]
        return "Please enter a valid age (1-120)."

    elif step == "ask_stress_questions":
        questions = ask_stress_questions()
        if message.lower() in ['yes', 'no']:
            if message.lower() == "yes":
                session["stress_score"] += [3, 2, 2, 2, 1][session["question_index"]]
            session["question_index"] += 1

            if session["question_index"] < len(questions):
                return questions[session["question_index"]]
            session["step"] = "ask_sleep_schedule"
            return ask_sleep_schedule()
        return "Please answer 'yes' or 'no'."

    elif step == "ask_sleep_schedule":
        session["responses"]["sleep_schedule"] = message
        session["step"] = "ask_gender_specific_questions"
        return ask_gender_specific_questions(session["responses"]["gender"])

    elif step == "ask_gender_specific_questions":
        session["responses"]["gender_specific"] = message
        session["step"] = "provide_recommendation"
        return provide_recommendation(session["responses"], session["stress_score"])

    return "I didn't understand that. Please try again."

def provide_recommendation(responses, stress_score):
    recommendations = "\nHere are your recommendations:\n"

    if stress_score >= 7:
        recommendations += "- High stress detected. Consider mindfulness, meditation, or talking to a professional.\n"
    elif stress_score >= 4:
        recommendations += "- Moderate stress detected. Exercise, sleep, and a balanced diet may help.\n"
    else:
        recommendations += "- Your stress levels seem low. Keep up the good work!\n"

    recommendations += f"- Your sleep schedule: {responses['sleep_schedule']}. Maintaining a routine can improve mental health.\n"

    if responses["gender"] == "female" and responses["gender_specific"] == "irregular":
        recommendations += "- Irregular menstrual cycle detected. Consult a doctor if necessary.\n"
    elif responses["gender"] == "male" and responses["gender_specific"] == "yes":
        recommendations += "- Noticed changes in mood/energy? Consider getting a health check-up.\n"

    return recommendations
