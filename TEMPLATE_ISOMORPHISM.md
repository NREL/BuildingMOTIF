# Template Isomorphisms

## Preliminaries

A labeled graph *G* is parameterized as *G(E, V, L)* where *E* is the set of edges, *V* is the set of nodes, and *L* is the set of labels for edges and nodes (*|L| = |E| + |V|*).

A graph *G'(E', V', L')* is a *subgraph* of *G(E, V, L)* if *E' ⊆ E*, *V' ⊆ V* and *L' ⊆ L*.
A node-induced subgraph *G'* of *G* has *N' ⊆ N* and *E'* is **the** subset of edges in *E* that relate nodes in *N'*.
A subgraph monomorphism *G'* of *G* has *N' ⊆ N* and *E'* is **a** subset of edges in *E* that relate nodes in *N'*.
Put another way, the difference between a subgraph monomorphism and a node-induced subgraph is a node-induced subgraph has *all* of the edges from the original between the nodes *N'* in the subgraph, and a monomorphism has a *subset* of the edges from the original.

The isomorphism or monomorphism between two graphs *G* and *G'* is an *injective* mapping *M: V -> V'*.
The injective requirement means that each element of *V'* is mapped to at most one element of *V*.
A *subgraph homomorphism* is a subgraph monomorphism that does not have the injective requirement.
