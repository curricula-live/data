# Variable — distinguishing syntax, binding and value

**Status:** review candidate only; canonical content unchanged.

The canonical graph currently records four directly connected statements:

| Claim UUID | Recorded statement |
| --- | --- |
| `611902f3-356c-4d88-87d8-a8fd2044d0ce` | `variable subtype_of symbol` |
| `3418b6fe-e488-4ee2-89c7-602c740477be` | `variable represents value` |
| `73870eea-b1e1-4ade-8d01-e358dec70d75` | `assignment uses variable` |
| `e0ce3538-7678-4823-aaa1-bfbe696f7c8b` | `predicate uses variable` |

These assertions are **historical canonical records**, not independently reviewed scientific claims. They provide insufficient information to distinguish a variable *identifier*, a variable *binding*, a variable's *storage location*, a value denoted by an identifier, and substitution in symbolic logic.

## Semantic issues to review

**1. `Variable subtype_of Symbol`.** A syntactic variable token can be represented by a symbol, but a variable as a binding or storage cell is not necessarily a kind of symbol. Test against both declarative mathematics and stateful programming languages before accepting a universal inclusion.

**2. `Variable represents Value`.** Representation, denotation, binding, reference and storage are not equivalent. An immutable variable binding, a mutable location, a logical free variable and a formal parameter may require different relation types and explicit contexts.

**3. `Assignment uses Variable`.** Can a variable be assigned, can an identifier denote the destination, and how does an operation change program state? The present `uses` relation does not specify effect or direction.

**4. `Predicate uses Variable`.** Is this an expression with free variables, a typed predicate in a programming language, or a proposition in logic? The direct relation is too broad to derive quantification or substitution properties.

## Proposed formalization work — not yet imported

For one *selected semantic model*, introduce a reviewed statement contract for the program state or environment. Example alternatives to **evaluate**, not automatically assert:

- A finite environment `ρ : Identifier ⇀ Value` for variable bindings.
- A store-based model `ρ : Identifier ⇀ Location`, `σ : Location ⇀ Value` when mutable locations matter.
- An explicitly scoped syntax model of free/bound variables in formulas.

The choice changes the interpretation of assignment and what counts as a valid inference. No particular model is entailed by the four current edges.

## Review admission order

1. Identify source-backed senses of Variable, Symbol, Value, Identifier, Assignment and Predicate.
2. Establish which canonical identities already exist before introducing any new concepts.
3. Record source version/rights and a claim-specific locator, avoiding archived V1 source promotion.
4. Define the predicates and scope; build counterexamples to overly general statements.
5. Only then propose a reviewed definition, valid examples and rule certificates.

Reproduce the record:

```bash
python scripts/semantic_risk_audit.py --concept variable
python scripts/knowledge_review_queue.py --concept variable
```

All scientific interpretation above is a *review question or model proposal*, not an accepted change.
