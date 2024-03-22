from functools import cached_property
from typing import List

from buildingmotif.ingresses.base import Record, RecordIngressHandler
from buildingmotif.label_parsing import (
    Parser,
    analyze_failures,
    parse_list,
    results_to_tokens,
)


class NamingConventionIngress(RecordIngressHandler):
    def __init__(
        self,
        upstream: RecordIngressHandler,
        naming_convention: Parser,
    ):
        self.upstream = upstream
        self.naming_convention = naming_convention

    def dump_failed_labels(self):
        sorted_groups = sorted(
            analyze_failures(self.failures).items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )
        for group, failures in sorted_groups:
            print(f"Unparsed label: {group} ({len(failures)} failures)")
            for failure in failures:
                print(f"\t{failure}")
            print()

    @cached_property
    def records(self) -> List[Record]:
        results, failures = parse_list(
            self.naming_convention, [x.fields["label"] for x in self.upstream.records]
        )
        self.failures = failures
        self.results = results
        tokens = results_to_tokens(results)
        return [
            Record(
                rtype="token",
                fields={
                    "label": t["label"],
                    "tokens": t["tokens"],
                },
            )
            for t in tokens
        ]
