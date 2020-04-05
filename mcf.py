import collections

from adjustable_heap import AdjustableHeap


class Edge:
  __slots__ = ("u", "v", "flow", "capacity", "cost")

  def __init__(self, u, v, capacity, cost):
    self.u = u
    self.v = v
    self.flow = 0
    self.capacity = capacity
    self.cost = cost

  def directed_edge(self, u):
    """
    Returns a tuple (v, capacity, cost) when traversing the edge starting at u.
    """
    if self.u == u:
      return (self.v, self.capacity - self.flow, self.cost)
    return (self.u, self.flow, -self.cost)

  def add_flow(self, u, flow):
    if self.u == u:
      self.flow += flow
    else:
      self.flow -= flow


class MinCostFlow:
  __slots__ = ("edges", "potential")

  def __init__(self):
    self.edges = collections.defaultdict(list)
    self.potential = collections.Counter()

  def add_edge(self, u, v, capacity, cost):
    edge = Edge(u, v, capacity, cost)
    self.edges[u].append(edge)
    self.edges[v].append(edge)

  def add_flow(self, src, snk, flow_max=None):
    """
    Returns the min cost of adding `flow` more flow to the graph.
    """
    flow = 0
    flow_cost = 0
    while flow_max is None or flow < flow_max:
      heap = AdjustableHeap(key_func=lambda x: x[1])
      dist = {
        src: (0, None, flow, heap.push((src, 0, None if flow_max is None else flow_max - flow))),
      }

      while len(heap):
        u, dst, flow_cur = heap.pop()

        for edge in self.edges[u]:
          v, cap, cost = edge.directed_edge(u)
          if cap == 0:
            continue

          new_dist = dst + cost + self.potential[u] - self.potential[v]
          new_flow = cap if flow_cur is None else min(flow_cur, cap)

          v_dist = dist.get(v)
          if v_dist is None:
            dist[v] = (
              new_dist,
              edge,
              new_flow,
              heap.push((v, new_dist, new_flow)),
            )
          elif new_dist < v_dist[0]:
            heap_key = v_dist[3]
            dist[v] = (
              new_dist,
              edge,
              new_flow,
              heap_key,
            )
            heap.adjust_key(heap_key, (v, new_dist, new_flow))

      snk_dist = dist.get(snk)
      if snk_dist is None:
        break

      flow += snk_dist[2]
      flow_cost += snk_dist[0] + self.potential[snk]
      for v, v_dist in dist.items():
        self.potential[v] += v_dist[0]

      v = snk
      while True:
        _, edge, *_ = dist[v]
        if edge is None:
          break

        v, *_ = edge.directed_edge(v)
        edge.add_flow(v, snk_dist[2])

    return flow, flow_cost
