# Semantic admission wave 2

Adds 25 directly source-attested CSO 3.5 research-topic relationships to wave one's 101 admissions. Canonical totals are 2,410 concepts, 24 predicates, 789 statements and 126 statement admission records. No new concept identities or predicates are introduced in this wave.

## Review decision

The candidate set contained 101 additional CSO `superTopicOf` edges whose endpoints each mapped uniquely to an existing canonical UUID. The selected 25 pairs are explicitly listed in `pipeline/semantic-admission/reviewed-cso-wave2.tsv`. Each passes the original exact archive-witness, one-to-one endpoint and canonical-label checks. The 87 earlier CSO links and 14 historical facts retain their statement identities and evidence unchanged.

The selected pairs concern research-topic organization: access control and authorization; cloud computing and virtual machines; computer systems and their research areas; security and privacy; viruses as a cyberattack topic; visualization; e-commerce; SQL injection; Java and UML; facial recognition; certificate authorities; RDF graphs and SPARQL; role hierarchies; logistic regression; blogs and social media. These choices do not assert that a protocol, language, artifact or operation is an instance or subclass of its parent research area.

CSO defines `superTopicOf` as a research-area hierarchy: https://cso.kmi.open.ac.uk/about . That source assertion, its direction and the editorial selection are the evidence for admission under `research_topic_parent_of`. It is not evidence of class subsumption or a pedagogical prerequisite. Supporting context for specific pairs includes W3C's SPARQL specification (https://www.w3.org/TR/sparql11-query/) and NIST's RBAC terminology (https://csrc.nist.gov/glossary/term/role_based_access_control); those do not independently certify the CSO hierarchy.

## Explicitly held relationships

`pipeline/semantic-admission/held-cso-wave2.tsv` records ten source pairs and a specific reason for holding each back. Examples include GPU/CPU, statistics/regression testing, IPv6/IPv4, authentication/authorization and image resolution/confusion matrix. This is a decision not to admit the supplied hierarchy; it does not assert that no useful relationship exists between the concepts. The other 66 mapped candidates remain unreviewed in this wave.

The admission generator rejects any overlap between the held pairs and either admitted allowlist. No held edge becomes a canonical negative assertion.

## Validation

The validator now binds each admitted statement endpoint to its reviewed canonical label, and recomputes each CSO witness from its recorded original subject, predicate and object. Mutation tests cover a swapped canonical endpoint, a changed source URI and an attempt to add an explicitly held pair to the allowlist.

Executed on 2026-11-17:

- Canonical validation: 2,410 concepts, 24 predicates, 789 statements, zero definition structures.
- Full data test suite: 78 passed, 18 PostgreSQL-dependent tests skipped.
- Fresh disposable PostgreSQL: canonical apply/verify followed by a second apply/verify with no drift; 126 admission records and five semantic policies.
- Companion Django API against that PostgreSQL: all 25 new statements retrieved from both endpoints, 50 checks passed; original source witnesses and incoming/outgoing direction preserved; inference and proof flags remain false.

No production or hosted development database was changed. The shared web preview does not yet expose this batch. Production publication still requires the repository's release workflow and reviewed API compatibility.
