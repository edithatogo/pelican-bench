import pytest

from pelicanbench.mock_services import (
    MockHTTPResponse,
    ScriptedOpenAIService,
    ScriptedVisualJudge,
    openai_stream_completion,
)
from pelicanbench.semantic import AtomicQuestion


def test_mock_response_and_service_guards():
    with pytest.raises(ValueError, match="response code"):
        MockHTTPResponse(status_code=99)
    with pytest.raises(ValueError, match="negative"):
        MockHTTPResponse(delay_seconds=-1)
    assert MockHTTPResponse(payload=b"raw").body() == b"raw"
    assert MockHTTPResponse(payload="text").body() == b"text"
    with pytest.raises(ValueError, match="chunk_size"):
        openai_stream_completion("x", chunk_size=0)
    with pytest.raises(ValueError, match="model"):
        ScriptedOpenAIService([], models=())
    service = ScriptedOpenAIService([])
    with pytest.raises(RuntimeError, match="not been started"):
        _ = service.base_url
    service.start()
    try:
        with pytest.raises(RuntimeError, match="already running"):
            service.start()
        assert service.remaining_responses == 0
        assert service._next_response().status_code == 503
    finally:
        service.stop()
    service.stop()


def test_scripted_judge_guards_and_failure():
    with pytest.raises(ValueError, match="identity"):
        ScriptedVisualJudge(judge_id="", judge_revision="1")
    with pytest.raises(ValueError, match="within"):
        ScriptedVisualJudge(judge_id="judge", judge_revision="1", default_probability=2)
    question = AtomicQuestion("q", "question", "interaction", True)
    judge = ScriptedVisualJudge(judge_id="judge", judge_revision="1", fail_questions=["q"])
    with pytest.raises(RuntimeError, match="scripted judge failure"):
        judge.answer(image=b"png", question=question)
