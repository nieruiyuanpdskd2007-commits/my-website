export default function SearchAlgorithmsPost() {
  return (
    <main className="min-h-screen bg-white px-8 py-20 text-black">
      <article className="mx-auto max-w-3xl">
        <p className="text-sm uppercase tracking-[0.3em] text-gray-500">
          AI Notes
        </p>

        <h1 className="mt-6 text-4xl font-bold leading-tight">
          Understanding DFS, BFS, UCS, and A*
        </h1>

        <p className="mt-4 text-gray-500">2026-05-08</p>

        <div className="mt-10 space-y-8 text-lg leading-8 text-gray-700">
          <section>
            <h2 className="text-2xl font-semibold text-black">
              1. Depth-First Search
            </h2>
            <p className="mt-3">
              Depth-first search explores one path as deeply as possible before
              backtracking. It is simple and memory-efficient, but it does not
              always find the shortest path.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-black">
              2. Breadth-First Search
            </h2>
            <p className="mt-3">
              Breadth-first search expands nodes level by level. When every
              step has the same cost, BFS can find the shortest path.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-black">
              3. Uniform Cost Search
            </h2>
            <p className="mt-3">
              Uniform cost search always expands the node with the lowest total
              path cost so far. It is suitable when different actions have
              different costs.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-black">4. A* Search</h2>
            <p className="mt-3">
              A* search combines the actual cost from the start state and a
              heuristic estimate to the goal. With an admissible heuristic, A*
              can find an optimal solution efficiently.
            </p>
          </section>
        </div>
      </article>
    </main>
  );
}