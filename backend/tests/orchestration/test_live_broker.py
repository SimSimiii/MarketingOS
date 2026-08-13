"""The replay guarantees the live view depends on.

A watching client loses its connection for all sorts of ordinary reasons -
a laptop sleeping, a reload, a flaky network. What must never happen is
that it comes back and silently misses the three minutes of campaign it was
disconnected for.
"""

from uuid import uuid4

from app.orchestration.live_broker import CLOSE, ExecutionEventBroker


def _drain(queue) -> list[dict]:
    events = []
    while not queue.empty():
        item = queue.get_nowait()
        events.append(item if item is CLOSE else item.payload)
    return events


def test_events_are_numbered_from_one_per_execution():
    broker = ExecutionEventBroker()
    first, second = uuid4(), uuid4()

    assert broker.publish(first, {"type": "a"}).id == 1
    assert broker.publish(first, {"type": "b"}).id == 2
    # A second run starts its own numbering - ids are positions in one
    # execution's stream, not a global counter.
    assert broker.publish(second, {"type": "a"}).id == 1


def test_a_subscriber_receives_events_published_after_it_joined():
    broker = ExecutionEventBroker()
    execution_id = uuid4()

    queue = broker.subscribe(execution_id)
    broker.publish(execution_id, {"type": "director_decision"})

    assert _drain(queue) == [{"type": "director_decision"}]


def test_reconnecting_with_a_position_replays_only_what_was_missed():
    broker = ExecutionEventBroker()
    execution_id = uuid4()

    broker.publish(execution_id, {"type": "one"})
    missed = broker.publish(execution_id, {"type": "two"})
    broker.publish(execution_id, {"type": "three"})

    queue = broker.subscribe(execution_id, after_id=missed.id)

    # Everything after the client's last known position, and nothing it
    # already saw.
    assert _drain(queue) == [{"type": "three"}]


def test_replayed_events_come_before_live_ones():
    broker = ExecutionEventBroker()
    execution_id = uuid4()

    first = broker.publish(execution_id, {"type": "one"})
    broker.publish(execution_id, {"type": "two"})

    queue = broker.subscribe(execution_id, after_id=first.id)
    broker.publish(execution_id, {"type": "three"})

    assert _drain(queue) == [{"type": "two"}, {"type": "three"}]


def test_subscribing_without_a_position_starts_from_now():
    broker = ExecutionEventBroker()
    execution_id = uuid4()
    broker.publish(execution_id, {"type": "history"})

    queue = broker.subscribe(execution_id)

    assert _drain(queue) == []


def test_last_event_id_reports_where_the_stream_is():
    broker = ExecutionEventBroker()
    execution_id = uuid4()

    assert broker.last_event_id(execution_id) == 0
    broker.publish(execution_id, {"type": "one"})
    broker.publish(execution_id, {"type": "two"})
    assert broker.last_event_id(execution_id) == 2


def test_history_is_never_evicted_from_under_a_live_subscriber():
    """Evicting a watched execution would reset its numbering and make a
    later replay hand the client the wrong events entirely."""
    broker = ExecutionEventBroker()
    watched = uuid4()
    queue = broker.subscribe(watched)
    broker.publish(watched, {"type": "one"})

    for _ in range(50):
        broker.publish(uuid4(), {"type": "noise"})

    assert broker.last_event_id(watched) == 1
    assert broker.publish(watched, {"type": "two"}).id == 2
    assert _drain(queue) == [{"type": "one"}, {"type": "two"}]


def test_closing_signals_every_watcher():
    broker = ExecutionEventBroker()
    execution_id = uuid4()
    first = broker.subscribe(execution_id)
    second = broker.subscribe(execution_id)

    broker.close(execution_id)

    assert _drain(first) == [CLOSE]
    assert _drain(second) == [CLOSE]


def test_unsubscribing_stops_delivery():
    broker = ExecutionEventBroker()
    execution_id = uuid4()
    queue = broker.subscribe(execution_id)

    broker.unsubscribe(execution_id, queue)
    broker.publish(execution_id, {"type": "after"})

    assert _drain(queue) == []
