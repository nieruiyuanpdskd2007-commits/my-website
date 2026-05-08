const projects = [
  {
    title: "Pacman AI Search Project",
    description:
      "Implemented DFS, BFS, UCS, and A* search algorithms in the UC Berkeley Pacman framework. Designed search strategies and heuristics for maze navigation.",
    tags: ["Python", "Search Algorithms", "A*"],
  },
  {
    title: "Gomoku AI Agent",
    description:
      "Built a search-based Gomoku AI agent with evaluation functions and decision-making strategies for a skill-based Gomoku environment.",
    tags: ["Python", "Game AI", "Minimax"],
  },
  {
    title: "SVD Image Compression",
    description:
      "Explored singular value decomposition, low-rank approximation, and their application in image compression.",
    tags: ["Linear Algebra", "SVD", "Image Processing"],
  },
  {
    title: "PCA / KPCA Study Notes",
    description:
      "Studied dimensionality reduction, covariance matrices, kernel methods, and applications in face recognition.",
    tags: ["Machine Learning", "PCA", "KPCA"],
  },
];

export default function ProjectsPage() {
  return (
    <main className="min-h-screen bg-white px-8 py-20 text-black">
      <section className="mx-auto max-w-5xl">
        <p className="text-sm uppercase tracking-[0.3em] text-gray-500">
          Portfolio
        </p>

        <h1 className="mt-6 text-4xl font-bold">Projects</h1>

        <p className="mt-5 max-w-2xl text-lg leading-8 text-gray-600">
          Selected coursework and technical projects in artificial intelligence,
          algorithms, and applied mathematics.
        </p>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {projects.map((project) => (
            <article
              key={project.title}
              className="rounded-2xl border border-gray-200 p-6 transition hover:-translate-y-1 hover:shadow-md"
            >
              <h2 className="text-2xl font-semibold">{project.title}</h2>

              <p className="mt-4 leading-7 text-gray-600">
                {project.description}
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                {project.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}