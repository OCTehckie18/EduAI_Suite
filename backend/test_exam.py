from app.models.exam import Exam, ExamQuestion, ExamChoice

new_exam = Exam(
    course_id=1,
    title="Test Exam",
    description="Test",
    time_limit=60,
    attempts_allowed=1,
    randomize_questions=False,
    status="draft"
)
new_exam.int_id = 1

question_id_counter = 1
choice_id_counter = 1

new_question = ExamQuestion(
    int_id=question_id_counter,
    question_text="Q1",
    question_type="mcq",
    points=1.0,
    order=0
)
question_id_counter += 1

new_choice = ExamChoice(
    int_id=choice_id_counter,
    choice_text="C1",
    is_correct=True
)
choice_id_counter += 1
new_question.choices.append(new_choice)

new_exam.questions.append(new_question)

print(new_exam.model_dump())
