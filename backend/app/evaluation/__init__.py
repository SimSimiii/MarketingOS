"""Measuring whether a change to MarketingOS actually made it better.

Two loops, deliberately separated because they answer different questions and
cost different amounts.

The mechanics loop is free and runs on every commit: how many model calls does
a campaign of this shape make, which model does each role get, how many format
repairs happened. Those are the failures that are invisible from the output -
a preset that re-prices cheap reactions as expensive judgment produces exactly
the same emails and a much larger bill - so they are asserted in the test
suite, against the scripted provider, and live in tests/marketing.

The quality loop is this package. It runs the real pipeline against real
models on a frozen set of businesses and requests, and writes down what came
back: what the cold readers felt, how many rewrites it took, what the sequence
pass said, and what it cost per email that actually shipped. It is billed and
deliberate - you run it when you have changed something you believe changes
the copy, and you compare the record against the last one.

The reason it can be this small is that the system already contains its own
instrument. The blind reader panel is a measurement of the copy by someone who
knows nothing about it; the gates are deterministic checks; the sequence pass
judges the set. None of that had to be invented here - it only had to be
written down in a form two runs can be compared with.
"""
