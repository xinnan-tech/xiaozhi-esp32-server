from core.connection import ConnectionHandler


def _handler(client_abort=False, sentence_id=None):
    # 只测纯判定逻辑，不触发 __init__ 里的重资源初始化
    h = ConnectionHandler.__new__(ConnectionHandler)
    h.client_abort = client_abort
    h.sentence_id = sentence_id
    return h


def test_new_turn_is_not_cancelled():
    h = _handler(sentence_id="turn-b")
    assert h._is_turn_cancelled("turn-b") is False


def test_user_abort_cancels_current_turn():
    h = _handler(client_abort=True, sentence_id="turn-b")
    assert h._is_turn_cancelled("turn-b") is True


def test_stale_abort_from_previous_turn_does_not_kill_new_turn():
    # 上一轮 TTS 的迟到 abort 已置位，但新一轮已接管（sentence_id 已更新）：
    # 旧轮（turn-a）判废，新轮（turn-b）不受影响 —— #3437 的核心断言
    h = _handler(client_abort=True, sentence_id="turn-b")
    assert h._is_turn_cancelled("turn-a") is True
    h.client_abort = False
    assert h._is_turn_cancelled("turn-b") is False


def test_turn_replaced_by_newer_turn_stops_old_turn():
    h = _handler(sentence_id="turn-c")
    assert h._is_turn_cancelled("turn-b") is True


def test_none_sentence_id_only_abort_matters():
    h = _handler(sentence_id="turn-b")
    assert h._is_turn_cancelled(None) is False
    h.client_abort = True
    assert h._is_turn_cancelled(None) is True
