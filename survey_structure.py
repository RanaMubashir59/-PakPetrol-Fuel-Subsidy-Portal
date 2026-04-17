# SURVEY STRUCTURE DEFINITION
# Maps each question to its type and analysis parameters

SURVEY_QUESTIONS = {
    # Demographics
    "Age": {"type": "numeric", "group": "demographics"},
    "Gender": {"type": "categorical", "group": "demographics", "options": ["Male", "Female"]},
    "Are you a student?": {"type": "categorical", "group": "demographics", "options": ["Yes", "No"]},
    "Do you own or regularly use a motorcycle?": {"type": "categorical", "group": "demographics", "options": ["Yes", "No"]},
    "City": {"type": "categorical", "group": "demographics"},
    
    # Usage Patterns
    "How far do you travel daily?": {"type": "numeric", "group": "usage"},
    "How often do you use your motorcycle?": {"type": "categorical", "group": "usage", "options": ["Daily", "3–5 times a week", "Rarely"]},
    "What is your approximate weekly fuel expense? (PKR)": {"type": "numeric", "group": "usage"},
    
    # Impact Scores (Likert 1-5)
    "Rising fuel prices affect my daily travel decisions": {"type": "likert", "group": "impact", "scale": [1, 2, 3, 4, 5]},
    "I reduce my travel due to high fuel costs": {"type": "likert", "group": "impact", "scale": [1, 2, 3, 4, 5]},
    "Fuel prices have caused me to miss classes or work": {"type": "likert", "group": "impact", "scale": [1, 2, 3, 4, 5]},
    "High fuel costs negatively impact my academic productivity": {"type": "likert", "group": "impact", "scale": [1, 2, 3, 4, 5]},
    "I feel financial stress due to fuel expenses": {"type": "likert", "group": "impact", "scale": [1, 2, 3, 4, 5]},
    
    # Specific Questions
    "On average how many days per month do you miss due to fuel issues?": {
        "type": "categorical",
        "group": "specific",
        "options": ["0", "1-2", "3-5", "More than 5"],
        "Q_number": 14
    },
    "Are you aware of any government fuel subsidy programs?": {
        "type": "categorical",
        "group": "specific",
        "options": ["Yes", "No"],
        "Q_number": 15
    },
    "A fuel subsidy would improve my mobility": {
        "type": "likert",
        "group": "perception",
        "scale": [1, 2, 3, 4, 5],
        "Q_number": 16
    },
    "A digital system (QR-based) would make subsidy distribution more transparent": {
        "type": "likert",
        "group": "perception",
        "scale": [1, 2, 3, 4, 5],
        "Q_number": 17
    },
    "I would use a digital fuel subsidy system if available": {
        "type": "likert",
        "group": "perception",
        "scale": [1, 2, 3, 4, 5],
        "Q_number": 18
    },
}

# CHI-SQUARE TEST DEFINITIONS
# Format: (test_name, row_variable, col_variable)
CHI_SQUARE_TESTS = [
    ("Subsidy Benefit (Q16 vs Q15)", "Are you aware of any government fuel subsidy programs?", "A fuel subsidy would improve my mobility"),
    ("Missed Days vs Gender (Q14 vs Q2)", "Gender", "On average how many days per month do you miss due to fuel issues?"),
]

print("✅ Survey structure loaded")
print(f"Total questions: {len(SURVEY_QUESTIONS)}")
print(f"Chi-square tests: {len(CHI_SQUARE_TESTS)}")
