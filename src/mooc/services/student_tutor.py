"""AI tutor for students.

Builds Arabic-language prompts grounded in the actual course content so
the assistant cannot fabricate facts. Three modes:

* :func:`answer_about_lesson` — open Q&A scoped to the current lesson.
* :func:`hint_for_assignment` — gives a *hint pointing to a lesson*,
  not a finished answer, in line with the academic-integrity policy
  (NELC course requirement M.19).
* :func:`explain_quiz_mistake` — explains why a wrong answer was wrong
  on a previously-submitted quiz attempt.
"""

from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from ..models import Assignment, Course, Lesson, Module, Question, QuizAttempt
from . import ai


_TUTOR_SYSTEM = (
    "أنت مساعد تعليمي عربي يساعد الطالب على فهم المحتوى التعليمي. "
    "أجب باللغة العربية الفصحى، باختصار وبخطوات واضحة. "
    "اعتمد فقط على السياق المُعطى من المقرر. إذا كانت المعلومة غير موجودة "
    "في السياق، فاطلب من الطالب الرجوع للمعلم بدل التخمين."
)

_HINT_SYSTEM = (
    "أنت مرشد تعليمي. مهمتك إعطاء الطالب تلميحاً يقوده إلى المكان الصحيح "
    "في المقرر للإجابة على واجبه — دون أن تعطيه الإجابة الكاملة. "
    "اقترح عليه الدرس أو الفقرة التي تحتوي المفهوم، واسأله سؤالاً يساعده "
    "على التفكير. لا تكتب الإجابة النهائية للواجب أبداً (سياسة النزاهة الأكاديمية)."
)


def _course_corpus(db: Session, course: Course, max_chars: int = 4000) -> str:
    """Concatenate lesson titles + textual content of a course, truncated."""
    parts: List[str] = []
    for module in course.modules or []:
        parts.append(f"## وحدة: {module.title_ar}")
        for lesson in module.lessons or []:
            body = lesson.content or lesson.transcript_text or ""
            parts.append(f"### درس: {lesson.title_ar}\n{body}")
    blob = "\n\n".join(parts)
    if len(blob) > max_chars:
        blob = blob[:max_chars] + "\n…[تم اقتطاع السياق]"
    return blob


def _lesson_corpus(lesson: Lesson, max_chars: int = 2500) -> str:
    body = lesson.content or lesson.transcript_text or "(لا يوجد نص)"
    txt = f"# {lesson.title_ar}\n{body}"
    return txt[:max_chars]


def answer_about_lesson(lesson: Lesson, question: str) -> str:
    context = _lesson_corpus(lesson)
    messages = [
        {"role": "system", "content": _TUTOR_SYSTEM},
        {
            "role": "user",
            "content": (
                f"سياق الدرس:\n```\n{context}\n```\n\n"
                f"سؤال الطالب: {question}"
            ),
        },
    ]
    return ai.chat(messages)


def hint_for_assignment(
    db: Session, assignment: Assignment, question: str
) -> str:
    course = assignment.course
    context = _course_corpus(db, course)
    messages = [
        {"role": "system", "content": _HINT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"الواجب: {assignment.title_ar}\n"
                f"تعليمات الواجب: {assignment.instructions_ar}\n\n"
                f"محتوى المقرر (مرجع):\n```\n{context}\n```\n\n"
                f"سؤال الطالب يطلب التلميح: {question}"
            ),
        },
    ]
    return ai.chat(messages)


def explain_quiz_mistake(
    attempt: QuizAttempt, question: Question, given_answer: str
) -> str:
    correct = ", ".join(str(c) for c in (question.correct_answer or []))
    messages = [
        {"role": "system", "content": _TUTOR_SYSTEM},
        {
            "role": "user",
            "content": (
                f"السؤال: {question.text_ar}\n"
                f"إجابة الطالب: {given_answer}\n"
                f"الإجابة الصحيحة: {correct}\n"
                f"اشرح للطالب لماذا إجابته غير صحيحة وكيف يصل للإجابة الصحيحة."
            ),
        },
    ]
    return ai.chat(messages)
