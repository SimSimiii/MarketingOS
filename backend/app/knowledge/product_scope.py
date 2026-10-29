"""Conservative ownership of an explicitly named product subject."""

import re


def is_product_subject(subject: str, company_name: str) -> bool:
    def key(value: str) -> str:
        value = re.sub(r"^the\s+", "", value, flags=re.IGNORECASE)
        return re.sub(r"[^\w]+", "_", value.casefold()).strip("_")

    own, target = key(company_name), key(subject)
    if not own or not target:
        return False
    names = {own}
    # "Acme" remains an explicit brand subject when the recorded name is
    # "Acme Analytics". Do not license generic prefixes such as "Social".
    first = own.split("_")[0]
    if len(first) >= 4 and first not in {"best", "team", "your", "social"}:
        names.add(first)
    return any(target == name or target.startswith(name + "_") for name in names)
