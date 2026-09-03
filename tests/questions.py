"""Evaluation questions (spec: §13 / §17). These are used ONLY by evaluation scripts and
the no-hardcoding test. Nothing in src/ references them; no answer strings exist anywhere."""

KNOWN_QUESTIONS = [
    "What vaccines are given to a newborn at birth?",
    "What is the schedule for pentavalent vaccination?",
    "When is the first measles-containing vaccine given?",
    "What is the purpose of Td vaccination during pregnancy?",
    "What should a health worker know about vaccine storage and the cold chain?",
    "What are the contraindications for BCG vaccination?",
    "What should be done if a child has missed scheduled vaccine doses?",
    "When is the rotavirus vaccine given and how many doses are required?",
    "How is the measles vaccine administered (dose and route)?",
    "Which vaccines are given to a pregnant woman and when?",
]

UNSEEN_QUESTIONS = [
    "Can a child receive vaccination if they have a mild fever?",
    "What is Mission Indradhanush?",
    "What is the dose of vitamin K given at birth?",
    "What adverse events can occur after DPT vaccination?",
    "How long can a vaccine be kept outside the cold chain before it must be discarded?",
]