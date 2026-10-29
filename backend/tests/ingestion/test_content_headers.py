"""Content headers must keep the conditions that qualify a following feature list."""
import pytest

from app.ingestion.loaders.html_extract import extract_content


@pytest.mark.parametrize("container", ["section", "article", "main"])
def test_plan_header_keeps_price_period_and_paid_scope(container):
    html = f"""<html><body>
    <header><a href='/'>Site logo</a><nav>Private menu</nav></header>
    <{container}><header><h2>Optional: Go Pro!</h2>
    <p>From <strong>$19 / year</strong>, get these Pro-exclusive features:</p></header>
    <ul><li>Custom domains</li><li>Forms</li></ul></{container}>
    <footer>Unrelated footer</footer><script>Untrusted script</script>
    </body></html>"""
    content = extract_content(html)[2]
    assert content.index("Go Pro") < content.index("Custom domains")
    assert "$19 / year" in content
    assert "Pro-exclusive features" in content
    assert "Site logo" not in content
    assert "Private menu" not in content
    assert "Unrelated footer" not in content
    assert "Untrusted script" not in content


def test_hero_content_survives_outside_a_section_but_navigation_does_not():
    html = """<body><header><h1>Build one-page sites</h1><p>Core features are free.</p>
    <nav>Account navigation</nav></header><main><p>Choose a template.</p></main></body>"""
    content = extract_content(html)[2]
    assert "Build one-page sites" in content
    assert "Core features are free" in content
    assert "Choose a template" in content
    assert "Account navigation" not in content


def test_plain_section_header_keeps_a_feature_requirement():
    content = extract_content("<section><header>Requires Pro Standard or higher</header><p>Signup forms.</p></section>")[2]
    assert "Requires Pro Standard or higher" in content
    assert "Signup forms" in content
