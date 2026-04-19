"""Tests for the automatic quiz grader."""

from __future__ import annotations

from mooc.models import Question, QuestionType
from mooc.services.grading import grade_question


def _make(qtype, correct, **kw):
    return Question(
        quiz_id=1,
        question_type=qtype,
        text_ar="س",
        choices=kw.get("choices", []),
        correct_answer=correct,
        points=kw.get("points", 1.0),
        order_index=1,
    )


def test_multiple_choice():
    q = _make(QuestionType.MULTIPLE_CHOICE, ["Python"], choices=["Python", "Java"])
    assert grade_question(q, "Python") == (1.0, True)
    assert grade_question(q, "Java") == (0.0, False)


def test_true_false():
    q = _make(QuestionType.TRUE_FALSE, ["صح"], choices=["صح", "خطأ"])
    assert grade_question(q, "صح")[1] is True
    assert grade_question(q, "خطأ")[1] is False


def test_multiple_answer_requires_exact_set():
    q = _make(
        QuestionType.MULTIPLE_ANSWER,
        ["A", "B"],
        choices=["A", "B", "C"],
    )
    assert grade_question(q, ["A", "B"])[1] is True
    assert grade_question(q, ["A"])[1] is False
    assert grade_question(q, ["A", "B", "C"])[1] is False


def test_short_answer_case_insensitive():
    q = _make(QuestionType.SHORT_ANSWER, ["print"])
    assert grade_question(q, "PRINT")[1] is True
    assert grade_question(q, "printf")[1] is False


def test_essay_is_not_auto_graded():
    q = _make(QuestionType.ESSAY, [])
    assert grade_question(q, "some answer") == (0.0, False)
