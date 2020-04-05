from mcf import MinCostFlow

mcf = MinCostFlow()


mcf.add_edge("src", "a", 1, 1)
mcf.add_edge("src", "b", 1, 0)
mcf.add_edge("a", "snk", 1, 2)
mcf.add_edge("b", "snk", 1, 2)


print(mcf.add_flow("src", "snk", 3))
