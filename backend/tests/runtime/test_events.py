from app.runtime.events import AgentFailed, AgentStarted, EventBus


def test_subscriber_receives_published_event():
    bus = EventBus()
    received: list[AgentStarted] = []
    bus.subscribe(AgentStarted, received.append)

    event = AgentStarted(agent_id="a1", execution_id="e1")
    bus.publish(event)

    assert received == [event]


def test_multiple_handlers_all_called_in_order():
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe(AgentStarted, lambda e: calls.append("first"))
    bus.subscribe(AgentStarted, lambda e: calls.append("second"))

    bus.publish(AgentStarted(agent_id="a1", execution_id="e1"))

    assert calls == ["first", "second"]


def test_unrelated_event_type_not_triggered():
    bus = EventBus()
    received: list[AgentFailed] = []
    bus.subscribe(AgentFailed, received.append)

    bus.publish(AgentStarted(agent_id="a1", execution_id="e1"))

    assert received == []


def test_publish_with_no_subscribers_is_a_noop():
    bus = EventBus()
    bus.publish(AgentStarted(agent_id="a1", execution_id="e1"))  # should not raise
