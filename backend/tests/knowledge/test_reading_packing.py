from app.knowledge.compiler import _readings
from app.knowledge.corpus import Document, SourceCorpus


def test_packing_saves_calls_without_losing_or_splitting_any_source():
    docs = [Document(id=str(i), title=str(i), content=chr(65+i)*size)
            for i, size in enumerate([6,6,4,4])]
    plan = _readings(SourceCorpus.from_documents(docs), 10, 100)
    assert len(plan.batches) == 2
    assert all(sum(len(item.text) for item in batch) <= 10 for batch in plan.batches)
    assert sorted((item.document.id,item.text) for batch in plan.batches for item in batch) == sorted((d.id,d.content) for d in docs)
    assert plan.unread == 0


def test_packing_keeps_the_original_read_budget_and_reports_unread_text():
    docs = [Document(id=str(i), title=str(i), content=chr(65+i)*size)
            for i,size in enumerate([6,6,4,4])]
    plan = _readings(SourceCorpus.from_documents(docs),10,12)
    assert plan.unread == 8
    assert {item.document.id for batch in plan.batches for item in batch} == {"0","1"}


def test_equal_call_count_preserves_original_order():
    docs = [Document(id=str(i),title=str(i),content=chr(65+i)*size)
            for i,size in enumerate([4,6,6])]
    plan = _readings(SourceCorpus.from_documents(docs),10,100)
    assert [[item.document.id for item in batch] for batch in plan.batches] == [["0","1"],["2"]]
