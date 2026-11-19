# Provisional RDF intake

The producer owns its IRIs, named graphs and release schema. This adapter verifies and materializes a reviewed upstream package. It has no PostgreSQL dependency. A receipt pins the producer Git commit and the byte digest of its manifest. The first receipt is proposed after an approved package exists on the upstream main branch.

Install Python 3.12 and rdflib==7.1.4. From a checkout, run:

    python pipeline/rdf/consume.py fetch --receipt pipeline/rdf/formal-sciences.json /tmp/formal-sciences-release
    python pipeline/rdf/consume.py verify /tmp/formal-sciences-release

The scheduled workflow runs after promotion to the default branch. Manual dispatch is also available there. Changed receipts enter a pull request targeting dev. Enable repository workflow permission to create pull requests for the proposal step. Any database projection, internal UUID crosswalk or operational deployment can be designed later.

Curricula's organization policy currently disables PR creation by the default Actions token. For unattended proposals, install a GitHub App scoped to this repository with Contents and Pull requests write access, configure CURRICULA_REVIEW_APP_ID as a repository variable and CURRICULA_REVIEW_APP_PRIVATE_KEY as an Actions secret. The workflow mints a short-lived token only for the trusted proposal job. The read-only verification path works independently.
