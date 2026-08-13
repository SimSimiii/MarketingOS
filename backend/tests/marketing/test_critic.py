"""What the critic asks one rewrite to do.

The critic's job is to find everything wrong. The loop's job is to fix one
thing at a time - and those are different jobs, which is why what the critic
reports and what the writer is handed are not the same list.
"""

from app.marketing.critic import MAX_EDITS_PER_PASS, Critique, Edit


def edit(severity: str = "major", line: str = "some line") -> Edit:
    return Edit(line=line, problem="it does not land", fix="make it land", severity=severity)


def test_a_rewrite_is_asked_for_a_few_changes_not_all_of_them():
    """Ten edits is not a revision, it is a rewrite order.

    The draft that comes back is a different email, which draws a different
    ten edits, and the loop spends its budget replacing drafts instead of
    improving one.
    """
    critique = Critique(edits=[edit(line=f"line {index}") for index in range(10)])

    assert len(critique.for_this_pass) == MAX_EDITS_PER_PASS
    assert [item.line for item in critique.for_this_pass] == ["line 0", "line 1", "line 2"], (
        "the critic ranked them; the top of its ranking is what gets done"
    )


def test_the_edits_that_were_held_back_are_counted_for_the_writer():
    critique = Critique(edits=[edit() for _ in range(7)])
    assert "4 smaller note(s) held back" in critique.render()


def test_nothing_is_held_back_when_there_was_little_to_say():
    critique = Critique(edits=[edit(), edit()])
    assert len(critique.for_this_pass) == 2
    assert "held back" not in critique.render()


def test_a_blocking_edit_is_never_held_back():
    """A blocking edit is the reason the email cannot ship. Dropping one to
    stay under a cap would leave the loop rewriting around the only thing
    that actually stops delivery."""
    critique = Critique(
        edits=[edit(line="minor one"), edit(line="minor two"), edit(line="minor three"),
               edit(severity="blocking", line="the unsupported claim")]
    )

    kept = critique.for_this_pass
    assert any(item.severity == "blocking" for item in kept)
    assert len(kept) == MAX_EDITS_PER_PASS


def test_every_edit_survives_when_they_all_block():
    critique = Critique(edits=[edit(severity="blocking", line=f"line {i}") for i in range(5)])
    assert len(critique.for_this_pass) == 5, "a cap must never hide a reason it cannot ship"


def test_a_critique_with_nothing_to_change_says_so():
    assert Critique(verdict="ship").render() == "No changes requested."
